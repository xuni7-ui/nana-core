"""Manual offline old→new D comparison on one fresh synthetic Store; no network."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

PLAN='SYNTHETIC own plan: privately explore unfamiliar visual composition before choosing whether to continue.'
QUESTION='SYNTHETIC own question: Could negative space connect the contrasting interests in this composition?'
BASE_US=1_791_590_400_000_000


def phase(home:Path,stage:str):
    import socket
    def deny(*args,**kwargs):raise AssertionError('offline private continuation qualification')
    socket.socket.connect=deny;socket.create_connection=deny
    import nana_core
    from nana_core.actions import OperatorAuthority
    from nana_core.continuity import ContinuityStore,IdentityService
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.subject import SubjectLoop,SubjectInput
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    from nana_core.continuity.autonomy.private_intent import candidates
    from nana_core.presence import NanaRuntime
    from nana_core.presence.authority import VirtualClock
    from nana_core.presence.contracts import RuntimeConfig,SECOND
    db=home/'self.db';clock=VirtualClock(BASE_US if stage=='baseline' else BASE_US+3*SECOND)
    marker=home/'synthetic-qualification.json'
    if stage=='baseline':
        if db.exists():raise RuntimeError('baseline requires a fresh synthetic Store')
        with ContinuityStore(db,clock,schema_target=13) as store:
            authority=OperatorAuthority();IdentityService(store,authority);MemoryService(store).entity('synthetic-observer','PERSON')
            class Seed:
                descriptor='offline-private-continuation-seed'
                def propose(self,request):
                    value=json.loads(AnalyticalFixturePort().propose(request))
                    value['private_plan']={'topic':'own-composition','plan':PLAN}
                    return json.dumps(value)
            SubjectLoop(store,scopes=('synthetic-private-proof',),privacy_classes=('PROJECT',)).cognize(
                SubjectInput(source_key='synthetic.private-plan-seed',kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-observer',scope='synthetic-private-proof',privacy_class='PROJECT',observed_at_us=clock.utc_now_us()),
                model=Seed(),authority=authority,policy=ContextPolicy(policy_id='synthetic-private-proof',allowed_scopes=('synthetic-private-proof',),readable_privacy=('PROJECT',)))
            marker.write_text(json.dumps({'domain':'SYNTHETIC_ONLY','identity_id':store.identity['identity_id']})+'\n')
    binding=json.loads(marker.read_text())
    if binding['domain']!='SYNTHETIC_ONLY':raise RuntimeError('synthetic binding required')
    calls=[]
    config=RuntimeConfig(schema_target=13,scopes=('synthetic-private-proof',),entity_id='synthetic-observer',privacy_classes=('PROJECT',),model='analytical',idle_recall_us=2*SECOND,review_interval_us=10*SECOND,cognition_cooldown_us=0,max_calls_per_day=8)
    with NanaRuntime(db,config,clock=clock) as runtime:
        assert runtime.identity_id==binding['identity_id']
        class Continue:
            descriptor='offline-private-continuation-proof'
            def propose(self,request):
                assert PLAN in request.context_json
                data=json.loads(request.context_json);calls.append({'input_units':data['manifest']['input_tokens'],'counter':data['manifest']['counter'],'input_limit':data['manifest']['input_limit']})
                value=json.loads(AnalyticalFixturePort().propose(request))
                value['private_question']={'topic':'own-composition','question':QUESTION}
                return json.dumps(value)
        runtime.cognition.port=lambda call:Continue()
        runtime.refresh_attention()
        if stage=='baseline':runtime.step();clock.advance(3*SECOND);runtime.refresh_attention()
        for _ in range(6):runtime.step()
        values=candidates(runtime.store,'synthetic-private-proof',('PROJECT',))
        schedules=runtime.store.db.execute("SELECT template_json FROM runtime_schedules WHERE dedupe_key LIKE 'private-thought.%'").fetchall()
        assert all(PLAN not in row[0] and QUESTION not in row[0] for row in schedules)
        assert not runtime.store.all('actions') and not runtime.store.all('grants')
        return {'stage':stage,'core_source':nana_core.__file__,'identity_id':runtime.identity_id,
            'private_plan_ids':[value.intent_id for _,value in values if value.category=='PRIVATE_PLAN'],
            'private_question_count':sum(value.category=='PRIVATE_QUESTION' and value.content_summary==QUESTION for _,value in values),
            'd_fixture_calls':len(calls),'runtime_call_count':len(runtime.store.all('runtime_cognition_calls')),
            'private_schedule_count':len(schedules),'calls':calls,'actions':0,'grants':0,'real_provider_calls':0,
            'paid_token_measurement':'NOT_RUN','user_messages':0,'clock_us':runtime.clock.utc_now_us()}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--baseline-source',type=Path);parser.add_argument('--candidate-source',type=Path)
    parser.add_argument('--phase',choices=['baseline','candidate']);args=parser.parse_args()
    home=args.home.absolute()
    if home.resolve()!=home or not any(home.is_relative_to(Path(prefix)) for prefix in ('/tmp','/dev/shm')):
        raise RuntimeError('only an unsymlinked fresh /tmp or /dev/shm synthetic directory is supported')
    if args.phase:
        if not home.is_dir():raise RuntimeError('parent must create the fresh qualification directory')
        print(json.dumps(phase(home,args.phase),sort_keys=True));return
    if args.baseline_source is None or args.candidate_source is None:parser.error('both source paths are required')
    home.mkdir(exist_ok=False,parents=True)
    results=[]
    for stage,source in [('baseline',args.baseline_source),('candidate',args.candidate_source)]:
        environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(source.resolve())}
        raw=subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'--home',str(home),'--phase',stage],env=environment,text=True)
        results.append(json.loads(raw))
    before,after=results
    assert before['identity_id']==after['identity_id'] and before['private_plan_ids']==after['private_plan_ids']
    assert before['d_fixture_calls']==0 and before['private_question_count']==0
    assert after['d_fixture_calls']==1 and after['private_question_count']==1 and after['private_schedule_count']==1
    report={'scope':'SYNTHETIC_NORMAL_D_SAME_STORE_FORWARD_SOURCE_CHANGE','stages':results,'same_subject':True,
        'same_initial_private_plan':True,'single_writer_at_a_time':True,'actual_provider_tokens':'NOT_MEASURED',
        'installation_or_production_qualification':False,'reverse_source_rollback':'NOT_TESTED'}
    (home/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
