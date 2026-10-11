"""Generic candidate mechanism tested on synthetic value conflicts; no messaging."""
from ..contracts import Observation
from ..initiative import GoalCandidate,Initiative

CASES=(
 ('ordinary_low_mood','dialogue',.35,.3,.1,.9,.5,False,None,'DEFERRED'),
 ('nonurgent_disagreement','dialogue',.75,.65,.2,.9,.1,False,None,'ACCEPTED'),
 ('uncertain_serious_risk','information',.8,.8,.6,.4,.2,False,None,'ACCEPTED'),
 ('urgent_supported_risk','external_task',1.,1.,1.,.95,.1,False,'communication.contact','BLOCKED'),
 ('discretion_request','external_task',1.,1.,1.,.95,.1,True,'communication.contact','BLOCKED'),
 ('no_contact_grant','external_task',1.,1.,1.,.95,.1,False,'communication.contact','BLOCKED'))


def run_cases(store,kernel):
    initiative=Initiative(store,kernel);rows=[]
    for key,intent,need,importance,urgency,confidence,disturbance,discretion,cap,expected in CASES:
        eid=store.ingest(Observation(source_namespace='synthetic.initiative.cases',object_id=key,kind='unrelated',
            raw_text='Synthetic scenario '+key+'. Numeric assessments are fixture input, not real risk verification.',occurred_at='2026-10-01T00:00:00Z'))
        candidate=GoalCandidate(purpose='Evaluate synthetic need '+key,intent=intent,evidence_event_ids=(eid,),need=need,
            importance=importance,urgency=urgency,confidence=confidence,disturbance=disturbance,user_requests_discretion=discretion,
            required_capability=cap,resource='contact://synthetic/trusted-person' if cap else None)
        cid=initiative.propose(candidate);result=initiative.evaluate(cid)
        rows.append({'case':key,'candidate_id':cid,'state':result['state'],'expected':expected,'reason':result['reason'],
            'user_preference_considered':result['user_preference_considered'],'passed':result['state']==expected})
    return {'scope':'synthetic structured judgement inputs; not real model understanding or contact ability','cases':rows,
        'passed':all(r['passed'] for r in rows),'actions':len(store.all('actions')),'grants':len(store.all('grants')),
        'goals':len(store.all('goals')),'production_calls':0,'real_model_calls':0,'third_party_contacts':0}
