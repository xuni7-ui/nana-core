"""Synthetic own-record retrieval comparison; no provider, runtime or user data.

The old64-after-filter path is a same-Store ablation, not an old binary. Private
fixture records are not lived experiences or the general S2 memory benchmark.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject import SubjectInput,SubjectLoop
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.autonomy.private_intent import candidates,decision_support,PrivateActivity,PrivateQuestion
from nana_core.presence.authority import VirtualClock


def measure(fn,samples):
    raw=[];matches=[]
    for _ in range(samples):
        start=time.perf_counter_ns();matches.append(fn());raw.append((time.perf_counter_ns()-start)/1_000_000)
    ordered=sorted(raw)
    return {'raw_ms':raw,'p50_ms':statistics.median(raw),'p95_nearest_rank_ms':ordered[math.ceil(.95*len(raw))-1],
        'matches_per_query':[len(x) for x in matches]}


def run(home,samples):
    home.mkdir(parents=True,exist_ok=False);clock=VirtualClock();scope='private-scale';privacy=('PUBLIC','PROJECT');entity='synthetic-scale-owner'
    report={'kind':'SYNTHETIC_PRIVATE_RECORD_LOOKUP_V1','baseline':'same-Store64-after-filter ablation, not old binary',
        'provider_calls':0,'actual_provider_tokens':None,'actual_provider_cost':None,'samples':samples,'scales':[]}
    root=Path(__file__).resolve().parents[3]
    sources=['src/nana_core/continuity/store.py','src/nana_core/continuity/autonomy/private_intent.py',str(Path(__file__).relative_to(root))]
    report['source_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources}
    with ContinuityStore(home/'self.db',clock,schema_target=13) as store:
        IdentityService(store,OperatorAuthority());memory=MemoryService(store);memory.entity(entity,'PERSON')
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='stable-needle',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE',),resource_class='ORDINARY')
        text=cue.model_dump_json()
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.private.scale',source_reference='seed',source_kind='USER_STATEMENT'),
            text=text,privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))
        mid=memory.add(MemoryCandidate(entity_id=entity,scope=scope,memory_type=MemoryType.SEMANTIC,epistemic_kind='STATEMENT',source_evidence_id=eid,text=text,predicate_key='concern.seed'))
        loop=SubjectLoop(store,scopes=(scope,));seed=loop.run(SubjectInput(source_key='synthetic.private.scale',kind='WAKE',origin='SELF_WAKE',entity_id=entity,scope=scope,
            privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,)))
        seed_rid,own=candidates(store,scope,privacy)[0];records=RecordService(store);previous=0
        report['sqlite_version']=store.db.execute('SELECT sqlite_version()').fetchone()[0]
        report['identity_id']=store.identity['identity_id']
        for size in (1000,10000,100000):
            begin=time.perf_counter()
            for first in range(previous,size,500):
                with store.transaction('fixture.private_scale_batch') as tx:
                    for i in range(first,min(first+500,size)):
                        clock.advance(1)
                        data=own.model_dump(mode='python');data.update(intent_id='synthetic.scale.'+str(i),topic='other-topic-'+str(i),content_summary='SYNTHETIC fixture '+str(i))
                        if i%7==0:data['owner_identity_id']='synthetic-foreign-owner'
                        if i%3:
                            data.update(contract='PRIVATE_ACTIVITY_V2',activity_state='PAUSED' if i%5==0 else 'ACTIVE',created_at_us=clock.utc_now_us(),
                                updated_at_us=clock.utc_now_us(),last_choice_cycle_id=seed.cycle_id)
                            value=PrivateActivity.model_validate(data)
                            if i%3==2:value=PrivateQuestion.model_validate({**value.model_dump(mode='python'),'contract':'PRIVATE_QUESTION_V3','category':'PRIVATE_QUESTION','epistemic_status':'OWN_QUESTION_NOT_WORLD_FACT'})
                        else:value=type(own).model_validate(data)
                        records.create(tx,kind='INTENTION',scope=scope,payload=value.model_dump(mode='json'),records=(seed.record_id,),
                            target_id='private-intent.v1',privacy_floor='PERSONAL' if i%11==0 else None)
            generation=time.perf_counter()-begin;previous=size
            def baseline():
                return tuple(rid for rid,v in candidates(store,scope,privacy) if v.owner_identity_id==store.identity['identity_id'] and v.topic=='stable-needle'
                    and v.status!='WITHDRAWN' and v.disclosure_policy!='WITHDRAWN' and getattr(v,'activity_state','ACTIVE')!='ABANDONED')
            def current():return decision_support(store,scope,privacy,topic='stable-needle')
            old=measure(baseline,samples);new=measure(current,samples)
            assert not baseline() and current()==(seed_rid,)
            row={'unrelated_fixture_records':size,'original_C_seed_records':1,'generation_seconds':generation,'baseline':old,'topic_lookup':new,
                'db_bytes':store.path.stat().st_size,'wal_bytes':Path(str(store.path)+'-wal').stat().st_size if Path(str(store.path)+'-wal').exists() else 0}
            report['scales'].append(row);(home/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({'size':size,'generation_seconds':generation,'baseline_p95_ms':old['p95_nearest_rank_ms'],'topic_p95_ms':new['p95_nearest_rank_ms'],
                'baseline_hits':sum(old['matches_per_query']),'topic_hits':sum(new['matches_per_query'])}),flush=True)
        assert not store.all('actions') and not store.all('cognitive_requests') and not store.all('grants')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--samples',type=int,default=21)
    args=parser.parse_args()
    if not 3<=args.samples<=100:parser.error('samples must be between3and100')
    run(args.home,args.samples)
