"""Explicit synthetic HTTP provider harness; never real-model evidence."""
import json,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from contextlib import contextmanager
from ...storage import canonical,digest
from ..open_agency.contracts import Objective,Operator
from .cognition import CognitionRequest,StructuredProposal,InterestProposal,OpenAIJSONTransport

def propose_from_context(request):
    """Data-driven reference interpreter, not a narrative script or real LLM.

    New opportunities describe data/desired result, not pre-inserted Goals. It
    compiles different domain plans from supplied finite capability descriptions.
    """
    if request.cognitive_role in {'PLAN','REPLAN'} and request.role_input:
        from ..open_agency.contracts import PlannerInput
        from ..open_agency.planning import BoundedPlanner
        proposal=BoundedPlanner().plan(PlannerInput.model_validate_json(canonical(request.role_input)))
        return StructuredProposal(interpretation='Reference bounded planner; proposal not authority',source_refs=request.source_context_refs,plan_operator_ids=proposal.operator_ids)
    if request.cognitive_role=='LEARN' and request.role_input:
        return StructuredProposal(interpretation='Candidate hypothesis, requires independent trials',source_refs=request.source_context_refs,method=request.role_input['hypotheses'][0])
    if request.cognitive_role=='SKILL' and request.role_input:
        from .extension import TransformCodeProposer
        from ..open_agency.code_skills import CodeSpec
        spec=CodeSpec.model_validate_json(canonical(request.role_input['spec']))
        code=TransformCodeProposer().implement(spec,request.role_input.get('diagnostic'))
        return StructuredProposal(interpretation='Generated candidate requires isolated tests',source_refs=request.source_context_refs,skill_source=code.source)
    context=json.loads(request.context_json);ideas=[];seen=set()
    for block in context['blocks']:
        if block['kind']!='MEMORY':continue
        row=json.loads(block['data_json']);mid=row['memory_id']
        if mid not in request.source_context_refs:continue
        try:body=json.loads(row['text'])
        except ValueError:continue
        hints=body.get('opportunities',[])
        if 'world_claim' in body:
            claim=body['world_claim']
            hints=[*hints,{'topic':'world-'+claim['predicate'].replace(':','-')[:48],'motive':'UNRESOLVED_QUESTION','value':'RELEVANT','possible_behaviors':['WATCH']}]

        if 'decoded' in body:
            d=body['decoded'];mod=d['modality']
            hints=[{'topic':'media-'+mod.lower(),'motive':'CURIOSITY','domain':'media','value':'HIGH','resource':'synthetic://media/'+mod.lower(),'kind':'observe'}]
        for hint in hints:
            topic=hint['topic']
            if topic in seen:continue
            seen.add(topic);obj=None;skill=hint.get('skill_task')
            if hint.get('resource') and not skill:
                resource=hint['resource'];ops=[Operator(operator_id='inspect',capability='world.observe',resource=resource,produces=('observed',),args={})]
                desired=('observed',)
                if hint.get('skill_record_id'):
                    ops=[Operator(operator_id='use-skill',capability='world.skill',resource=resource,produces=('computed',),args={'skill_record_id':hint['skill_record_id'],'data':hint['data']},expected_digest=digest(hint['expected']))];desired=('computed',)
                if hint.get('method'):
                    ops.append(Operator(operator_id='analyze',capability='world.compute',resource=resource+'/compute',requires=('observed',),produces=('analyzed',),args={'method':hint['method'],'input_from':'inspect'},strategy_selectable=True,expected_digest=digest(hint['expected']) if 'expected' in hint else None))
                    ops.append(Operator(operator_id='publish',capability='world.publish',resource=resource+'/report',requires=('analyzed',),produces=('reported',),args={'input_from':'analyze'}));desired=('reported',)
                obj=Objective(objective_id='world.'+topic,scope=hint.get('scope','world'),motivation_source=hint.get('motive','CURIOSITY'),task_domain=hint.get('domain','media'),desired=desired,operators=tuple(ops),priority=hint.get('priority',1))
            ideas.append(InterestProposal(topic=topic,motivation_source='CAPABILITY_GAP' if skill else hint.get('motive','CURIOSITY'),source_memory_ids=(mid,),interpretation='Consider a sourced opportunity; subject choice and execution remain separate.',objective=obj,skill_task=skill,possible_behaviors=('LEARN',) if hint.get('skill_record_id') else tuple(hint.get('possible_behaviors',())),expected_value=hint.get('value','RELEVANT')))
    return StructuredProposal(interpretation='Sourced data interpreter; no authority and no semantic-quality claim.',source_refs=request.source_context_refs,interests=tuple(ideas[:4]),uncertainty='RELEVANT',confidence=.4)

@contextmanager
def provider_harness(proposer=propose_from_context,*,mode='ok',delay=0):
    state={'calls':0,'request_ids':[]}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_POST(self):
            try:
                n=int(self.headers.get('Content-Length',0))
                if not 1<=n<=196608:self.send_error(413);return
                body=json.loads(self.rfile.read(n));content=body['messages'][-1]['content']
                if isinstance(content,list):
                    metadata=json.loads(content[0]['text'])
                    parts=metadata['role_input']['parts']
                    if len(content)!=len(parts)+1:raise ValueError('fixture part count')
                    for part,wire in zip(parts,content[1:]):
                        if part['kind']=='IMAGE':
                            url=wire['image_url']['url'];prefix='data:image/png;base64,'
                            if not url.startswith(prefix):raise ValueError('fixture image contract')
                            part['data_b64']=url[len(prefix):]
                        else:part['data_b64']=wire['input_audio']['data']
                    content=canonical(metadata)
                request=CognitionRequest.model_validate_json(content)
                state['calls']+=1;state['request_ids'].append(request.request_id)
                actual_delay=state.get('delay',delay);selected_mode=state.get('mode',mode)
                if actual_delay:time.sleep(actual_delay)
                if selected_mode=='rate_limit':self.send_error(429);return
                if selected_mode=='context_overflow':self.send_error(413);return
                content=proposer(request).model_dump_json()
                finish='stop'
                if selected_mode=='malformed':content='not valid JSON'
                if selected_mode=='partial':finish='length'
                response={'model':'harness-v1','choices':[{'finish_reason':finish,'message':{'content':content,**({'refusal':'synthetic refusal'} if selected_mode=='refusal' else {})}}],'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}}
                raw=canonical(response).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);worker.start()
    transport=OpenAIJSONTransport(f'http://127.0.0.1:{server.server_port}/v1/chat/completions','harness-v1',provider_id='synthetic.http',harness=True)
    try:yield transport,state
    finally:server.shutdown();server.server_close();worker.join(2)
