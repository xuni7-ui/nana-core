"""Reproduce bounded provider-config parse reuse vs A b016e6c's original reader.

PYTHONPATH=src:. python tools/nana_next_experience/experiments/provider_config_cache.py
Synthetic host-local documents only. No model, network, Subject or secret values.
"""
import gc
import json
import math
import os
from pathlib import Path
import platform
import statistics
import tempfile
import time
import tracemalloc

from nana_core.contracts import CoreError
from nana_core.continuity.provider_config import (ProviderConfigService, ProviderConfigurationAuthority,
    ProviderConfiguration, ProviderProfile, ModelProfile, CapabilityRoute, _validated_configuration)
from nana_core.continuity.privacy import _json_object
from nana_core.continuity.provider_routing import RuntimeProviderFactory, RoutingPolicy, ProviderSettingsService
from nana_core.continuity.providers import ProviderRegistry
from nana_core.life.provider import provider_status
from nana_core.storage import canonical


class BaselineConfigService(ProviderConfigService):
    """Original A b016e6c _load body, same file-check/DTO contracts."""
    def _load(self):
        try:
            fd = self._file(self._path, os.O_RDONLY)
            with os.fdopen(fd, 'rb') as stream:
                raw = stream.read(262145)
            if len(raw) > 262144:
                raise ValueError()
            obj = json.loads(raw, object_pairs_hook=_json_object)
            return self.document_type.model_validate_json(canonical(obj))
        except FileNotFoundError:
            raise CoreError('PROVIDER_CONFIG_UNAVAILABLE') from None
        except CoreError:
            raise
        except (ValueError, TypeError, OSError):
            raise CoreError('PROVIDER_CONFIG_INVALID') from None


def baseline_status(home):
    authority=ProviderConfigurationAuthority()
    service=BaselineConfigService(home/'providers.json',authority)
    factory=RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy())
    return {'provider_settings':ProviderSettingsService(service,authority,factory).projection(),
            'real_provider_qualified':'NOT_RUN','network_calls':0}


def document(pcount,mcount,revision=1):
    providers=tuple(ProviderProfile(provider_profile_id=f'provider.p{i}',display_name=f'Provider {i}',
        protocol='OPENAI_COMPATIBLE_CHAT',locality='REMOTE',base_url='https://provider.example/v1',
        secret_ref=f'provider.p{i}') for i in range(pcount))
    models=tuple(ModelProfile(model_profile_id=f'model.m{i}',provider_profile_id=providers[i%pcount].provider_profile_id,
        remote_model_id=f'model-{i}',model_version='1',operations=('COGNITION',),input_modalities=('TEXT',),
        output_modalities=('TEXT',),context_limit=64000,output_limit=4096) for i in range(mcount))
    return ProviderConfiguration(revision=revision,providers=providers,models=models,
        routes=(CapabilityRoute(operation='COGNITION',primary_model_profile_id=models[0].model_profile_id),))


def measure(fn,count=40):
    wall=[];cpu=time.process_time_ns()
    for _ in range(count):
        start=time.perf_counter_ns();fn();wall.append((time.perf_counter_ns()-start)/1e6)
    return wall,(time.process_time_ns()-cpu)/1e6/count


def comparison(old,new):
    assert old()==new();new() # Both file/OS caches warm; candidate parse warm.
    times={'baseline':[],'candidate':[]};cpus={'baseline':[],'candidate':[]}
    for round_number in range(6):
        order=[('baseline',old),('candidate',new)]
        if round_number%2:order.reverse()
        for label,fn in order:
            walls,cpu=measure(fn);times[label].extend(walls);cpus[label].append(cpu)
    return {label:{'n':len(times[label]),'wall_median_ms':statistics.median(times[label]),
                   'wall_p95_ms':sorted(times[label])[math.ceil(len(times[label])*.95)-1],
                   'cpu_mean_ms':statistics.mean(cpus[label])} for label in times}


def main():
    result={'baseline_commit':'b016e6c79b29cc3e02848a8dbc9780a077846efc',
        'python':platform.python_version(),'platform':platform.platform(),'cases':[],
        'measurement':'local synchronous reads; alternating 6x40 calls per arm; OS caches warm; exact DTO/projection equality asserted',
        'scope':'synthetic host configs; no model/HTTP/Token/billing measurement; traced Python memory is not RSS',
        'cold_control':'forced parse miss clears previous cache on every candidate call (including clear overhead); file/OS caches still warm'}
    with tempfile.TemporaryDirectory(prefix='nana-parse-') as folder:
        home=Path(folder);home.chmod(0o700);path=home/'providers.json'
        for pcount,mcount in [(1,1),(8,32),(64,256)]:
            config=document(pcount,mcount);raw=config.model_dump_json().encode()
            assert len(raw)<=262144;path.write_bytes(raw);path.chmod(0o600)
            authority=ProviderConfigurationAuthority();baseline=BaselineConfigService(path,authority)
            candidate=ProviderConfigService(path,authority);_validated_configuration.cache_clear()
            def cold_candidate():
                _validated_configuration.cache_clear()
                return candidate.load()
            row={'providers':pcount,'models':mcount,'document_bytes':len(raw),
                 'load_warm':comparison(baseline.load,candidate.load),
                 'status_projection_warm':comparison(lambda:baseline_status(home),lambda:provider_status(home)),
                 'load_forced_miss':comparison(baseline.load,cold_candidate)}
            _validated_configuration.cache_clear();gc.collect();tracemalloc.start()
            before=tracemalloc.get_traced_memory()[0];candidate.load();gc.collect()
            current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            row['single_entry_python_traced_retained_bytes']=current-before
            row['single_entry_python_traced_peak_bytes']=peak-before;result['cases'].append(row)
        # Worst schema-size case, four retained revisions. No unbounded history.
        _validated_configuration.cache_clear();gc.collect();tracemalloc.start()
        before=tracemalloc.get_traced_memory()[0]
        for revision in range(4):
            path.write_bytes(config.model_copy(update={'revision':revision}).model_dump_json().encode())
            candidate.load()
        gc.collect();current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        result['four_max_schema_entries_python_traced_retained_bytes']=current-before
        result['four_entry_cache_info']=_validated_configuration.cache_info()._asdict()
    _validated_configuration.cache_clear();print(json.dumps(result,indent=2))


if __name__=='__main__':main()
