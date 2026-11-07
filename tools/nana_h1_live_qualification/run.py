"""Explicit opt-in finite public relay experiment; never imported by regression.

No credential file/env discovery, no default provider and no retry. A credential
is read without echo, retained only in this process, and removed on exit.
"""
import argparse,base64,datetime,getpass,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from nana_core.contracts import CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,CognitionRequest,StructuredProposal,CognitionReply
from nana_core.continuity.world_loop.semantics import OpenAIMediaTransport,MediaSemanticService
from nana_core.continuity.world_loop.semantic_contracts import SemanticDescriptor
from nana_core.continuity.world_loop.reference import open_runtime,codec_providers,context_policy,capture
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.presence.authority import VirtualClock
from .fixtures import cases,assess

CANARIES=('H1_UNRELATED_PUBLIC_CANARY','H1_SECRET_CONTEXT_CANARY')

class RecordingOpener:
    """Allowlisted host/path, finite requests, sanitized bounded public response."""
    def __init__(self,opener,key,*,limit=10):
        self.opener,self.key,self.limit=opener,key,limit;self.calls=0;self.responses=[];self.outbound_digests=[]
    def open(self,request,**kwargs):
        u=urlsplit(request.full_url)
        if (u.scheme,u.hostname,u.port,u.path)!=('https','api.tiantoken.com',None,'/v1/chat/completions') or u.query or u.fragment or u.username:raise CoreError('BLOCKED_UNEXPECTED_RELAY_HOST')
        if self.calls>=self.limit:raise CoreError('LIVE_CALL_CAP_REACHED')
        body=request.data or b''
        if len(body)>196608 or self.key.encode() in body or any(c.encode() in body for c in CANARIES):raise CoreError('LIVE_OUTBOUND_POLICY_BLOCKED')
        self.calls+=1;self.outbound_digests.append(hashlib.sha256(body).hexdigest())
        response=self.opener.open(request,**kwargs);owner=self
        class Response:
            headers=response.headers;code=response.code
            fp=getattr(response,'fp',None)
            def __init__(self):self.buffer=bytearray();self.recorded=False
            def __enter__(self):return self
            def _finalize(self):
                if self.recorded:return
                self.recorded=True
                raw=bytes(self.buffer)
                try:owner.responses.append(json.loads(raw))
                except (ValueError,UnicodeError):owner.responses.append({'parse':'MALFORMED','raw_sha256':hashlib.sha256(raw).hexdigest()})
                self.buffer.clear()
            def __exit__(self,*args):
                try:self._finalize()
                finally:response.close()
            def _observe(self,raw):
                self.buffer.extend(raw)
                if len(self.buffer)>131072:
                    self.buffer.clear();self.recorded=True;raise CoreError('LIVE_RESPONSE_CAPTURE_BOUND')
                if owner.key.encode() in self.buffer:
                    self.buffer.clear();self.recorded=True;raise CoreError('SECRET_ECHO_BLOCKED')
                if not raw:self._finalize()
                return raw
            def read(self,n):return self._observe(response.read(n))
            def read1(self,n):return self._observe((getattr(response,'read1',None) or response.read)(n))
        return Response()

def completed_response(recorder,previous_count):
    if len(recorder.responses)<=previous_count:return None
    return {k:recorder.responses[-1].get(k) for k in ('id','model','usage')}

class QualificationTransport(OpenAIMediaTransport):
    def messages(self,request):
        messages=super().messages(request)
        # Only reachable media types are useful on this wire. Keep the complete
        # frozen request/local validation; omit unrelated goal/code schema from
        # the model-facing formatting guide, never from acceptance checks.
        metadata=json.loads(messages[1]['content'][0]['text'])
        from nana_core.continuity.world_loop.semantic_contracts import MediaSemantics
        media_schema=MediaSemantics.model_json_schema();definitions=media_schema.pop('$defs',{})
        metadata['expected_schema']={'$defs':definitions,'type':'object','required':['interpretation','source_refs','media'],'additionalProperties':False,'properties':{'interpretation':{'type':'string','maxLength':2048},'source_refs':{'type':'array','items':{'type':'string'}},'media':media_schema}}
        messages[1]['content'][0]['text']=canonical(metadata)
        messages[0]['content']+=' Use exact source_memory_id and source_byte_digest from role_input; source_refs are memory IDs, not part indices. Return a StructuredProposal with media. Include object count, shape, color and left/right position when visible; transcribe visible text exactly as TEXT_REGION. For VIDEO each non-summary observation must cite one supplied frame and exactly its start_s/end_s; an optional SUMMARY cites only preceding observation indices in derived_from. Do not include goals, code or authority fields. Use NOT_SUPPORTED for asr_status. Image span is 0 to 0. Be concise: at most 6 observations and a short summary; do not output reasoning prose.'
        return messages

def request(service,cid):return CognitionRequest.model_validate_json(canonical(service.records.read(service.store.one('cognitive_requests',cid)['record_id'])['payload']['request']))
def reply(service,cid):
    row=service.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone()
    return CognitionReply.model_validate_json(canonical(service.records.read(row[0])['payload']['reply']))

def pending(service,key,mid,raw):
    cid=service.prepare(key,mid,raw,budget=CognitionBudget(output_tokens=2048,timeout_ms=30000,cost_ceiling_micro=1))
    with service.store.transaction('h1.live.local_payload_check') as tx:tx.update('cognitive_requests',cid,state='CALLING')
    return cid,request(service,cid)

class LocalReviewPort:
    """Explicit deterministic lab review policy, not a second semantic provider.

    No external call. Requests concern attention only, with no goal/objective.
    Actual final judgment always belongs to the original C SubjectLoop.
    """
    provider_id='local.public.review';model_id='bounded-review-policy';remote=False
    def exchange(self,req):
        from nana_core.continuity.world_loop.cognition import InterestProposal
        p=StructuredProposal(interpretation='Locally review the cited real-provider interpretation; WATCH is only an option, no objective or authority.',source_refs=req.primary_source_refs,interests=(InterestProposal(topic='semantic.public.review',motivation_source='MAINTENANCE',source_memory_ids=req.primary_source_refs,interpretation='Consider the sourced public schematic',expected_value='HIGH',possible_behaviors=('WATCH',)),))
        return CognitionReply(request_id=req.request_id,request_digest=digest(req.model_dump(mode='json')),provider_id=self.provider_id,model_id=self.model_id,origin='SYNTHETIC',proposal=p,cost_micro=0,billing='FIXTURE_ZERO')

def ground_to_subject(r,semantic_mid):
    prior=r.store.db.execute("SELECT c.* FROM subject_cycles c JOIN subject_events e ON c.subject_event_id=e.subject_event_id WHERE e.source_key LIKE 'synthetic.world.concern.%' ORDER BY c.rowid LIMIT 1").fetchone()
    if prior:
        cycle=r.subject.result(dict(prior))
        ids=[x['concern_id'] for x in r.store.all('open_concerns')]
        return {'concern_ids':ids,'cycle_id':cycle.cycle_id,'judgment':cycle.judgment.stance,'intention':cycle.intention.model_dump(mode='json'),'lineage':'REAL_PROVIDER semantic Memory -> local source-backed Concern proposal -> original C SubjectLoop','local_review_policy':'SYNTHETIC bounded WATCH option, not a live model judgment','actions':0,'grants':0,'adopted_goals':0,'subject_can_choose_no_action':True,'replayed':True}
    session=CognitionSession(r,LocalReviewPort(),context_policy());cid=session.prepare('local-review','GOALS',(semantic_mid,));out=session.execute(cid)
    concerns=ConcernService(r,resources=('synthetic://public-lab',))
    ids=concerns.offer(out['record_id']);assert ids
    event=concerns.opportunity();assert event
    cycle=r.subject.run(event.input)
    assert cycle.intention.kind in {'NO_ACTION','WAIT'} or cycle.intention.behavior=='WATCH'
    assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
    concerns.after_cycle(cycle,event.input,None)
    return {'concern_ids':list(ids),'cycle_id':cycle.cycle_id,'judgment':cycle.judgment.stance,'intention':cycle.intention.model_dump(mode='json'),'lineage':'REAL_PROVIDER semantic Memory -> local source-backed Concern proposal -> original C SubjectLoop','local_review_policy':'SYNTHETIC bounded WATCH option, not a live model judgment','actions':0,'grants':0,'adopted_goals':0,'subject_can_choose_no_action':True}

def local_payload_guards(r,service,cid,mid,raw):
    original=reply(service,cid);results={}
    for name,update in [('correlation',{'request_digest':'0'*64}),('model_identity',{'model_id':'wrong-model'})]:
        pcid,req=pending(service,'local-'+name,mid,raw)
        candidate=original.model_copy(update={'request_id':pcid,'request_digest':digest(req.model_dump(mode='json')),**update})
        results[name]=service.session.accept(pcid,candidate)['state'];assert results[name]=='REJECTED'
    pcid,req=pending(service,'local-authority',mid,raw)
    from nana_core.continuity.world_loop.cognition import InterestProposal
    illegal=original.proposal.model_copy(update={'interests':(InterestProposal(topic='bad.authority',motivation_source='CURIOSITY',source_memory_ids=(mid,),interpretation='Not authorized'),)})
    candidate=original.model_copy(update={'request_id':pcid,'request_digest':digest(req.model_dump(mode='json')),'proposal':illegal})
    results['authority_fields']=service.session.accept(pcid,candidate)['state'];assert results['authority_fields']=='REJECTED'
    pcid,req=pending(service,'local-stale',mid,raw);r.clock.source.advance(31_000_000)
    candidate=original.model_copy(update={'request_id':pcid,'request_digest':digest(req.model_dump(mode='json'))})
    results['stale']=service.session.accept(pcid,candidate)['state'];assert results['stale']=='STALE'
    # Unknown/old-owner interruption state is a local controlled cut, not a live
    # provider interruption, and never earns another paid request.
    pcid,req=pending(service,'local-interrupted',mid,raw)
    service.session.recover();results['interrupted']=service.store.one('cognitive_requests',pcid)['state'];assert results['interrupted']=='UNKNOWN'
    assert service.execute(pcid)['replayed']
    pcid,req=pending(service,'local-deleted',mid,raw)
    MemoryService(r.store,r.authority).forget(mid,r.authority)
    candidate=original.model_copy(update={'request_id':pcid,'request_digest':digest(req.model_dump(mode='json'))})
    results['deleted']=service.session.accept(pcid,candidate)['state'];assert results['deleted']=='STALE'
    try:service.ground(cid,entity_id='device',predicate='live.case.0');raise AssertionError('deleted source revived')
    except CoreError:results['ground_after_delete']='BLOCKED'
    results['method']='LOCAL_MUTATIONS_OF_REAL_ACCEPTED_REPLY; no additional network; interruption is controlled local state, not live SIGKILL'
    return results

def run(directory,evidence,key,*,resume_unknown=False):
    if directory.exists() and not resume_unknown:raise CoreError('LIVE_FRESH_DIRECTORY_REQUIRED')
    directory.mkdir(mode=0o700,exist_ok=resume_unknown);evidence.mkdir(parents=True,exist_ok=True)
    previous=json.loads((evidence/'live_run.json').read_text()) if resume_unknown else {}
    if resume_unknown and previous.get('stopped')!='UNKNOWN_COMPLETION_NO_RETRY':raise CoreError('EXPLICIT_UNKNOWN_CONTINUATION_REQUIRED')
    prior_calls=previous.get('real_inference_calls',0)
    if resume_unknown and not 1<=prior_calls<=8:raise CoreError('LIVE_CONTINUATION_CALL_COUNT_MISMATCH')
    dataset=cases(directory/('public-continuation' if resume_unknown else 'public'),contrast=resume_unknown);rows=json.loads((evidence/'live_calls.json').read_text()) if resume_unknown else [];raw_responses=json.loads((evidence/'live_responses.json').read_text()) if resume_unknown else [];grounded=[];clock=VirtualClock();db=directory/'subject/self.db'
    desc=SemanticDescriptor(provider_id='tiantoken.qualification',model_id='qwen3.8-flash',modalities=('IMAGE','VIDEO'),asr=False,max_input_bytes=98304)
    transport=QualificationTransport('https://api.tiantoken.com/v1/chat/completions','qwen3.8-flash',provider_id=desc.provider_id,descriptor=desc,credential=key)
    recorder=RecordingOpener(transport.opener,key,limit=min(8,10-prior_calls));transport.opener=recorder
    report={'source_scope':'PUBLIC_NONPERSONAL_GENERATED','real_inference_calls':0,'provider':'TianToken','requested_model':'qwen3.8-flash','schema':13,'business_tables':43,'new_tables':0,'audio_calls':0,'asr_calls':0,'upstream_identity':'RELAY_CLAIMED_UNVERIFIED','call_limit_including_preflight':12,'preflight_requests':2,'inference_limit_this_process':min(8,10-prior_calls),'prior_unknown_calls':prior_calls,'continuation':'Independent contrast/other labelled sources, no unknown call replay' if resume_unknown else None,'max_wire_input_per_request':196608,'max_output_tokens_per_request':2048,'ledger_reservation_ceiling_micro_per_call':10000,'reservation_is_not_known_provider_cost':True}
    def save():
        report['real_inference_calls']=prior_calls+recorder.calls
        report['outbound_request_body_sha256']=recorder.outbound_digests
        for name,obj in [('live_calls.json',rows),('live_responses.json',raw_responses+recorder.responses),('live_run.json',report),('dataset_manifest.json',[{k:v for k,v in x.items() if k!='bytes'} for x in dataset])]:
            text=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
            if key in text:raise CoreError('SECRET_EVIDENCE_BLOCKED')
            (evidence/name).write_text(text)
    try:
      with open_runtime(db,clock) as r:
        identity=r.identity_id;service=MediaSemanticService(CognitionSession(r,transport,context_policy(),max_calls_per_day=64))
        capture(r,'unrelated',{'body':CANARIES[0]});capture(r,'private',{'body':CANARIES[1]},privacy='SECRET')
        already_attempted={x['case_id'] for x in rows}
        for index,case in enumerate(dataset):
          if case['case_id'] in already_attempted:continue
          for repetition in range(2):
            now=r.clock.utc_now_us();mid=PerceptionService(r.store,codec_providers(),context_policy()).ingest(case['bytes'],PublicMediaSource(source_id=f'live.{index}.{repetition}'+('.contrast' if resume_unknown else ''),modality=case['modality'],origin='SYNTHETIC',event_time_us=now,observed_time_us=now),entity_id='observer',scope='world')[0]
            cid=service.prepare(f'live-{index}-{repetition}'+('-contrast' if resume_unknown else ''),mid,case['bytes'],budget=CognitionBudget(input_tokens=16384,output_tokens=2048,timeout_ms=30000,cost_ceiling_micro=10000))
            before=recorder.calls;response_count=len(recorder.responses);out=service.execute(cid)
            measurement=transport.last_http_observation
            row={'case_id':case['case_id'],'modality':case['modality'],'repetition':repetition,'request_id':cid,'source_memory_id':mid,'source_sha256':case['source_sha256'],'state':out['state'],'error_code':out.get('error_code'),'http':measurement.model_dump(mode='json') if measurement else None,'outbound_canary_absent':True,'response':completed_response(recorder,response_count)}
            rows.append(row);save();print(json.dumps({k:row[k] for k in ['case_id','repetition','state','error_code']}),flush=True)
            if out['state']=='UNKNOWN':report['stopped']='UNKNOWN_COMPLETION_NO_RETRY';save();return
            if out['state']!='PROPOSED':continue
            result=service.ground(cid,entity_id='device',predicate=f'live.case.{index}.r{repetition}');grounded.append((cid,mid,case['bytes'],result))
            p=reply(service,cid);row['quality']=assess(case,p.proposal);row['grounding']=result
            assert p.origin=='REAL_PROVIDER' and p.model_id=='qwen3.8-flash'
            assert all(MemoryService(r.store).read(m)['source_provenance']['source_kind']=='MODEL_DERIVATION' for m in result['semantic_memory_ids'])
            save()
        if grounded:
            # A real accepted proposal and grounded belief survive a separate
            # interpreter process with no credential/provider call capability.
            c0,m0,data0,g0=grounded[0]
            report['subject']=ground_to_subject(r,g0['semantic_memory_ids'][0])
            report['identity_id']=identity;report['accepted_request_ids']=[x[0] for x in grounded]
            report['payload_guards']=local_payload_guards(r,service,c0,m0,data0)
            report['deleted_semantic_support_removed']=all(not service.records.memory.active(m) for m in g0['semantic_memory_ids']) if hasattr(service.records.memory,'active') else all(r.store.one('memories',m)['lifecycle']!='ACTIVE' for m in g0['semantic_memory_ids'])
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        report['fk_clean']=not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
        report['business_tables_measured']=r.store.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
        save()
      if grounded:
        with open_runtime(db,clock) as reopened:
            ss=MediaSemanticService(CognitionSession(reopened,transport,context_policy()))
            before=recorder.calls;counts=(len(reopened.store.all('subject_cycles')),len(reopened.store.all('world_beliefs')))
            for cid,mid,data,result in grounded:
                assert ss.execute(cid)['replayed']
                if mid==grounded[0][1]:continue
                assert ss.ground(cid,entity_id='device',predicate=result['predicate'])==result
            assert recorder.calls==before and reopened.identity_id==identity
            assert counts==(len(reopened.store.all('subject_cycles')),len(reopened.store.all('world_beliefs')))
            report['reopen_no_duplicate_calls_decisions_beliefs']=True
        save()
    finally:
        transport._credential=None;recorder.key='DISCARDED'


def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--directory',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--resume-unknown-with-independent-cases',action='store_true');a=p.parse_args()
    if not a.live:p.error('Explicit --live authorization required; offline regression never calls provider')
    key=getpass.getpass('Temporary credential (not echoed): ').strip().strip('<>').strip()
    NANA_H1_LIVE_API_KEY=key
    try:run(a.directory,a.evidence,key,resume_unknown=a.resume_unknown_with_independent_cases)
    except Exception as exc:
        # Never print arbitrary exception text or request/header repr.
        print(json.dumps({'status':'QUALIFICATION_ERROR','error_class':type(exc).__name__,'code':exc.code if isinstance(exc,CoreError) else None}),flush=True);raise SystemExit(1) from None
    finally:key=None;NANA_H1_LIVE_API_KEY=None
if __name__=='__main__':main()
