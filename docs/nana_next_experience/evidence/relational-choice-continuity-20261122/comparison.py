import json,time,sys
from pathlib import Path
from tests.world_loop.helpers import fresh,policy
from tests.person_self.test_relational_cognitive_choice import prepare,request,ConsiderExistingWish
from tests.world_loop.test_model_framing import bind
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
seen=[]
def propose(value):
    body=transport.request_body(value)
    seen.append({'wire_bytes':len(body),'context_bytes':len(value.context_json.encode()),'schema_bytes':len(json.dumps(value.expected_schema,separators=(',',':')).encode())})
    raw=json.loads(ConsiderExistingWish().propose(value))
    return StructuredProposal(interpretation='SYNTHETIC same bounded request',subject_cognition=CognitiveProposal.model_validate_json(json.dumps(raw)))
path=Path(sys.argv[1]);start=time.perf_counter();cpu=time.process_time()
with fresh(path) as r,provider_harness(proposer=propose) as (transport,state):
    bind(transport);prepare(r);event=request(r,'cost')
    session=CognitionSession(r,transport,policy());budget=CognitionBudget(input_tokens=65536)
    cycle=r.subject.cognize(event,model=session.subject_port(privacy_class='PERSONAL',budget=budget),authority=r.authority,policy=policy())
    print(json.dumps({'case':'same-existing-ASK-original-C-and-SELF','result':cycle.relational_decision.response.decision,'calls':state['calls'],
        'measurements':seen,'real_provider_tokens':None,'real_provider_cost':None,
        'sqlite_allocated_bytes':sum(p.stat().st_blocks*512 for p in path.parent.glob(path.name+'*')),
        'wall_seconds':time.perf_counter()-start,'parent_cpu_seconds':time.process_time()-cpu,'real_models':0},sort_keys=True))
