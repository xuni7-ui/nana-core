"""Single owned HTTP ablation probe, not commercial model quality or cost."""
import json,sys,time
from pathlib import Path
from tests.person_self.test_provider_subject_seedless import bare,event
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.autonomy.private_intent import candidates
root=Path(sys.argv[1]);report_path=Path(sys.argv[2]);assert root.is_absolute() and str(root).startswith(('/tmp/','/dev/shm/')) and not root.exists() and not report_path.exists();root.mkdir()
observed=[]
def propose(request):
 identity=json.loads(request.context_json)['manifest'];focus=request.media_input()['subject_cognition'];selected=focus.get('task')=='SYNTHETIC original focus: explore color relationships';observed.append(selected)
 return StructuredProposal(interpretation='SYNTHETIC focus candidate',subject_cognition=CognitiveProposal(identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC considered',proposed_operations=('DRAFT',) if selected else ('WAIT',),private_question={'topic':'own-color','question':'SYNTHETIC How could color relationships inform a new composition?'} if selected else None))
with provider_harness(proposer=propose) as (transport,state),bare(root,VirtualClock()) as r:
 policy=ContextPolicy(policy_id='focus-ablation',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',));session=CognitionSession(r,transport,policy);budget=CognitionBudget(input_tokens=32768)
 source=event(r,'focus-ablation').model_copy(update={'text':'SYNTHETIC original focus: explore color relationships','task_class':'own.research'})
 before=time.perf_counter_ns();cpu=time.process_time_ns();cycle=r.subject.cognize(source,model=session.subject_port(privacy_class='PROJECT',budget=budget),authority=r.authority,policy=policy);cpu=(time.process_time_ns()-cpu)//1000;wall=(time.perf_counter_ns()-before)//1000
 row=dict(r.store.all('cognitive_requests')[0]);report={'focus_received':observed==[True],'stance':cycle.judgment.stance,'private_questions':len(candidates(r.store,'own-scope',('PROJECT',))),'provider_calls':state['calls'],'original_ledger_rows':len(r.store.all('cognitive_requests')),'fixture_ledger_rows':len(r.store.all('runtime_cognition_calls')),'memories':len(r.store.all('memories')),'actions':len(r.store.all('actions')),'budget':budget.model_dump(mode='json'),'reserved_bytes':row['reserved_bytes'],'wire_input_bytes':row['input_bytes'],'wire_output_bytes':row['output_bytes'],'wall_us':wall,'cpu_us':cpu,'real_model_calls':0,'actual_commercial_tokens':None,'actual_commercial_cost':None,'limits':'Single data-driven owned HTTP fixture. Same input/budget. Not P95, commercial-token count, independent learning, installation or naturalness.'}
 with report_path.open('x') as stream:stream.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
