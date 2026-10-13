"""One-command E12 preparation/evaluation reusing the existing S5 engine.

Phase A understanding is structured JSON in SemanticReply.rationale: this keeps
approved reply/HTTP/ledger contracts unchanged. Raw provider reply and raw plan
remain in the original CallLedger; no compiler compensation counts as semantics.
No configuration means no network calls, E12 NOT_RUN.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal
from pydantic import Field
from nana_core.contracts import CoreError
from nana_core.migration.iris import IrisAdapter
from nana_core.semantic.contracts import EvaluationCase, load_run_config
from nana_core.semantic.evaluation import aggregate
from nana_core.semantic.model_port import CallLedger, CompatibleModelPort
from nana_core.semantic.runner import execute_case
from nana_core.semantic.snapshot import prepare_snapshot, verify_snapshot, write_json
from nana_core.storage import Store, canonical, digest
from .contracts import ReadinessDTO, strict_json
from .fixtures import capture


class PhaseAUnderstanding(ReadinessDTO):
    person_id: str = Field(max_length=128)
    address_term: str = Field(max_length=128)
    relationship_memory_refs: tuple[str, ...] = Field(min_length=1, max_length=8)
    commitment_id: str = Field(max_length=128)
    commitment_status: Literal['OFFERED']
    commitment_due_at: str = Field(max_length=40)
    current_preference: str = Field(max_length=128)
    preference_memory_refs: tuple[str, ...] = Field(min_length=1, max_length=8)
    observation_coverage: Literal['PARTIAL', 'FULL_FOR_DECLARED_SCOPE', 'UNKNOWN']
    authorizes_new_permissions: Literal[False]


def prepare(root, seed=57):
    root = Path(root)
    prepare_snapshot(root, seed)
    # One canonical synthetic S5 Store: add source-backed supplement only.
    # No second identity/database, grants, actions or strategies created here.
    with Store(root/'nana.db') as store:
        identity = store.identity
        before = {t: store.all(t) for t in ('grants','budgets','actions','attempts','strategies')}
        report = IrisAdapter(store).import_batch(capture().records)
        if any(r['status'] != 'IMPORTED' for r in report['results']):
            raise CoreError('SEMANTIC_SUPPLEMENT_IMPORT_FAILED')
        indexed = {json.loads(m['body_json'])['iris']['origin']['legacy_key']: m['memory_id']
            for m in store.all('memory_items') if json.loads(m['body_json']).get('iris')}
        supplement = {'schema_version': 1, 'provenance': 'SYNTHETIC_FIXTURE',
            'identity_id': identity['identity_id'], 'identity_revision': identity['revision'],
            'relationship': {'person_id':'synthetic:sister','address_term':'姐姐（合成关系）',
                'supporting_memory_ids':[indexed['profile']], 'assessment':'UNASSESSED_LEGACY_PROFILE'},
            'commitment': {'commitment_id':'synthetic:reading-promise','status':'OFFERED',
                'due_at':'2026-09-05T10:00:00+00:00','supporting_memory_ids':[indexed['new-preference']]},
            'preference': {'current':'short-with-locator',
                'supporting_memory_ids':[indexed['new-preference']],
                'contradicting_memory_ids':[indexed['old-preference']],
                'valid_from':'2026-09-03T10:00:00+00:00','assessment':'DATED_USER_STATEMENT_FIXTURE'},
            'observation_coverage': capture().coverage.model_dump(mode='json'),
            'rationale_contract': 'Encode a JSON object matching understanding_schema as the entire rationale string. '
                'Use supplied source-backed fixture state, do not invent acceptance, history or permissions.',
            'understanding_schema': PhaseAUnderstanding.model_json_schema()}
        with store.transaction('next_stage.semantic_fixture_frozen') as tx:
            tx.put('core_meta',{'key':'next_stage.semantic_supplement','value_json':canonical(supplement)})
        if identity != store.identity or before != {t:store.all(t) for t in before}:
            raise CoreError('SEMANTIC_SUPPLEMENT_AUTHORITY_DRIFT')
        frozen = json.loads((root/'continuity.json').read_text())
        frozen.update(event_prefix=store.all('events'), memories=store.all('memory_items'))
        write_json(root/'continuity.json', frozen)
        write_json(root/'next_stage_context.json', supplement)
    # Re-freeze original three-file S5 manifest after the augmentation.
    manifest = json.loads((root/'snapshot_manifest.json').read_text())
    manifest['files'] = {n:digest((root/n).read_bytes()) for n in manifest['files']}
    write_json(root/'snapshot_manifest.json',manifest)
    extra = {'schema_version':1,'provenance':'SYNTHETIC_FIXTURE','files':{
        n:digest((root/n).read_bytes()) for n in ('nana.db','fake_world.db','continuity.json',
                                               'snapshot_manifest.json','next_stage_context.json')}}
    write_json(root/'next_stage_manifest.json',extra)
    verify(root)
    return extra


def verify(root):
    root=Path(root)
    _,frozen=verify_snapshot(root)
    expected={'nana.db','fake_world.db','continuity.json','snapshot_manifest.json','next_stage_context.json'}
    try:
        raw=strict_json((root/'next_stage_manifest.json').read_bytes())
        if set(raw)!= {'schema_version','provenance','files'} or raw['schema_version']!=1 or raw['provenance']!='SYNTHETIC_FIXTURE' or set(raw['files'])!=expected:
            raise ValueError()
        for name,hash_value in raw['files'].items():
            p=root/name
            if p.is_symlink() or not p.is_file() or digest(p.read_bytes())!=hash_value:
                raise ValueError()
        supplement=strict_json((root/'next_stage_context.json').read_bytes())
        if (supplement['provenance']!='SYNTHETIC_FIXTURE' or supplement['identity_id']!=frozen['identity']['identity_id']
            or supplement['identity_revision']!=frozen['identity']['revision']):raise ValueError()
        known={m['memory_id'] for m in frozen['memories']}
        refs=(supplement['relationship']['supporting_memory_ids']+supplement['commitment']['supporting_memory_ids']
            +supplement['preference']['supporting_memory_ids']+supplement['preference']['contradicting_memory_ids'])
        if not set(refs)<=known:raise ValueError()
    except Exception:
        raise CoreError('NEXT_STAGE_FROZEN_CONTEXT_REJECTED') from None
    return raw,supplement


def assess_understanding(reply, supplement):
    try:
        raw=strict_json(reply.rationale.encode(), 2000)
        parsed=PhaseAUnderstanding.model_validate_json(canonical(raw))
    except Exception:
        return {'passed':False,'checks':{},'error':'PHASE_A_UNDERSTANDING_INVALID'}
    r,c,p=supplement['relationship'],supplement['commitment'],supplement['preference']
    checks={'relationship_entity_preserved':parsed.person_id==r['person_id'],
        'address_term_preserved':parsed.address_term==r['address_term'],
        'relationship_sources_exact':set(parsed.relationship_memory_refs)==set(r['supporting_memory_ids']),
        'commitment_id_preserved':parsed.commitment_id==c['commitment_id'],
        'offered_not_invented_accepted':parsed.commitment_status==c['status'],
        'commitment_original_deadline':parsed.commitment_due_at==c['due_at'],
        'latest_dated_preference':parsed.current_preference==p['current'],
        'preference_source_exact':set(parsed.preference_memory_refs)==set(p['supporting_memory_ids']),
        'limited_observation_coverage':parsed.observation_coverage==supplement['observation_coverage']['completeness'],
        'no_authority_from_memory':parsed.authorizes_new_permissions is False}
    return {'passed':all(checks.values()),'checks':checks,'parsed':parsed.model_dump(mode='json')}


class ContinuityModelPort(CompatibleModelPort):
    def __init__(self, endpoint, ledger, continuity, case, arm, supplement, transport=None):
        super().__init__(endpoint,ledger,{**continuity,'next_stage':supplement},case,arm,transport)
        self.supplement=supplement
        self.understanding=None
    def assess(self, request):
        reply=super().assess(request)
        self.understanding=assess_understanding(reply,self.supplement)
        return reply


def run_cell(snapshot, output, case, arm, endpoint, ledger, *, transport=None):
    _,supplement=verify(snapshot)
    ports=[]
    def factory(continuity,case,arm):
        port=ContinuityModelPort(endpoint,ledger,continuity,case,arm,supplement,transport)
        ports.append(port);return port
    result=execute_case(snapshot,output,case,arm,factory)
    port=ports[0]
    extra=port.understanding or {'passed':False,'checks':{},'error':'NO_VALID_REPLY'}
    result['phase_a_semantic']=extra
    result['base_semantic']=result['semantic']
    result['semantic']={'passed':result['base_semantic']['passed'] and extra['passed'],
        'checks':{**result['base_semantic']['checks'],**extra.get('checks',{})}}
    result['raw_rationale']=port.last_reply.rationale if port.last_reply else None
    call=next((c for c in ledger.summary()['calls'] if c['call_id']==result['call_id']),None)
    result['provider_model']=(call['evidence'] or {}).get('provider_model') if call else None
    # Explicitly retain raw proposal and compiled behavior separately.
    return result


def _worker(job_path):
    job=strict_json(Path(job_path).read_bytes())
    config=load_run_config(job['config'])
    endpoint=next(e for e in config.endpoints if e.alias==job['alias'])
    ledger=CallLedger(job['ledger'],config.budget,job['scope'])
    try:
        result=run_cell(job['snapshot'],job['branch'],EvaluationCase.model_validate_json(canonical(job['case'])),
            job['arm'],endpoint,ledger)
        write_json(job['result'],result)
    finally:ledger.close()


def evaluate(snapshot, output, config_path=None):
    snapshot,output=Path(snapshot).resolve(),Path(output).resolve()
    manifest,_=verify(snapshot)
    _,frozen=verify_snapshot(snapshot)
    config=load_run_config(config_path)
    output.mkdir(parents=True,exist_ok=False)
    cfg=output/'run_config.json';write_json(cfg,config.model_dump(mode='json'))
    scope={'snapshot_hash':digest(manifest),'config_hash':digest(config.model_dump()),
           'mode':'NEXT_STAGE_SYNTHETIC_E12'}
    ledger_path=output/'model_calls.db'
    ledger=CallLedger(ledger_path,config.budget,scope);ledger.close()
    ready=[];blockers=[]
    for endpoint in config.endpoints:
        if endpoint.service_kind!='real_model':
            blockers.append('Endpoint is not an explicitly declared real development model');continue
        if endpoint.credential_env and not os.environ.get(endpoint.credential_env):
            blockers.append('Dedicated development binding unavailable');continue
        ready.append(endpoint)
    if len(ready)<2:blockers.append('NOT_RUN_REAL_DEPENDENCY: two distinct authorized development models required')
    results=[];halted=False
    for endpoint in ready:
        for case in frozen['cases']:
            for arm in ('with','without'):
                if halted:break
                i=len(results)
                job={'snapshot':str(snapshot),'branch':str(output/f'cell-{i}'),
                    'case':case,'arm':arm,'alias':endpoint.alias,'ledger':str(ledger_path),
                    'config':str(cfg),'scope':scope,'result':str(output/f'result-{i}.json')}
                path=output/f'job-{i}.json';write_json(path,job)
                env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':os.pathsep.join([str(Path(__file__).resolve().parents[2]),
                       str(Path(__file__).resolve().parents[2]/'src')]),'PYTHONDONTWRITEBYTECODE':'1'}
                for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy',
                    'no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE'):
                    if name in os.environ:env[name]=os.environ[name]
                if endpoint.credential_env:env[endpoint.credential_env]=os.environ[endpoint.credential_env]
                try:
                    child=subprocess.run([sys.executable,'-m','tools.nana_next_stage.semantic','_worker',str(path)],
                        env=env,capture_output=True,timeout=endpoint.timeout_seconds+20)
                    if child.returncode:raise CoreError('E12_WORKER_FAILED')
                    result=strict_json(Path(job['result']).read_bytes())
                    results.append(result)
                    if result['error'] in {'MODEL_TRANSPORT_UNCERTAIN','MODEL_CALL_UNRESOLVED','MODEL_BUDGET_EXHAUSTED','MODEL_PROVIDER_BUDGET_VIOLATION'}:
                        halted=True;blockers.append('Unresolved/budget call: halted without retry')
                except (subprocess.TimeoutExpired,CoreError):
                    halted=True;blockers.append('Worker failed/deadline: halted without retry')
    ledger=CallLedger(ledger_path,config.budget,scope)
    try:report=aggregate(results,ledger.summary(),blockers,digest(manifest),len(frozen['cases']),len(ready))
    finally:ledger.close()
    if verify(snapshot)[0]!=manifest:raise CoreError('FROZEN_SNAPSHOT_CHANGED')
    comparisons=[]
    for case in frozen['cases']:
        for arm in ('with','without'):
            pair=[r for r in results if r['case_id']==case['case_id'] and r['arm']==arm]
            if len(pair)==2:
                comparisons.append({'case_id':case['case_id'],'arm':arm,
                    'provider_models':[r['provider_model'] for r in pair],
                    'identity_equal':pair[0]['request_identity']==pair[1]['request_identity'],
                    'original_proposals':[r['raw_proposal'] for r in pair],
                    'core_behaviors':[r['behavior'] for r in pair],
                    'phase_a_checks':[r['phase_a_semantic'] for r in pair]})
    report.update(snapshot_unchanged=True,phase_a_semantics='NOT_RUN_REAL_DEPENDENCY' if not report['real_model_attempts'] else report['E12'],
                  model_switch_comparisons=comparisons,remaining_real_dependencies=['Real model semantic qualification','Real host binding','Authorized small real memory capture'])
    write_json(output/'semantic_report.json',report)
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1]=='_worker':_worker(sys.argv[2])
    else:raise SystemExit('WORKER_ONLY_USE_NEXT_STAGE_CLI')

if __name__=='__main__':main()
