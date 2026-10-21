"""Explicit First-Life live gate + private review, memory-only FD credential.

No default execution, credential lookup, retry or fallback. User separately
approved at most8 new calls and400000 USDmicro conservative reservations.
"""
import argparse,json,os,sqlite3,sys,termios,time
from pathlib import Path
from nana_core.contracts import CoreError
from nana_core.storage import canonical,digest
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.life.provider import ExplicitFDResolver,configured_router
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport,CognitionBudget
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from tools.nana_first_life_integration.dev import preflight

REF='first-life.deepseek.ephemeral'


def configure(home):
    """Host config only; original immutable attempt ledger owns all budgets."""
    home=Path(home);cfg=load_config(home)
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        calls,reserved=db.execute('SELECT count(*),coalesce(sum(reserved_cost_micro),0) FROM cognitive_requests').fetchone()
    # Only the one known loopback reservation is allowed as this mission base.
    if calls!=1 or reserved!=0:raise CoreError('FIRST_LIFE_LIVE_BUDGET_BASE_MISMATCH_NO_RENEWAL')
    authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'providers.json',authority);conf=service.load()
    if conf.providers or conf.models or conf.routes:raise CoreError('FIRST_LIFE_EXISTING_PROVIDER_CONFIGURATION_NO_OVERWRITE')
    cfg=update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'provider_hosts':('api.deepseek.com',),'remote_privacy':('PUBLIC','PROJECT'),'provider_timeout_ms':15000,'provider_context_tokens':32768,'provider_output_tokens':2048,'provider_calls_per_day':9,'provider_calls_per_hour':9,'per_provider_calls_per_day':8,'provider_cost_ceiling_micro':50000,'provider_total_calls_limit':9,'provider_total_reserved_cost_micro':400000}),expected_revision=cfg.revision)
    provider=ProviderProfile(provider_profile_id='first-life.deepseek',display_name='DeepSeek First-Life qualification',protocol='OPENAI_COMPATIBLE_CHAT',locality='REMOTE',base_url='https://api.deepseek.com',secret_ref=REF,permitted_privacy=('PUBLIC','PROJECT'),default_timeout_ms=15000,default_cost_ceiling=50000,chat_thinking_mode='DISABLED')
    model=ModelProfile(model_profile_id='first-life.deepseek.flash',provider_profile_id=provider.provider_profile_id,remote_model_id='deepseek-flash',model_version='qualification-not-permanent-default',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=32768,output_limit=2048)
    route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=model.model_profile_id,fallback_model_profile_ids=(),permitted_privacy=('PUBLIC','PROJECT'),timeout_ceiling_ms=15000,cost_ceiling=50000,context_ceiling=32768,output_ceiling=2048)
    for op,field,value in [('UPSERT_PROVIDER','provider',provider),('UPSERT_MODEL','model',model),('SET_CAPABILITY_ROUTE','route',route)]:
        conf=service.update(ProviderCommand(operation=op,expected_revision=conf.revision,**{field:value}),authority)
    return cfg


def semantic(app,*,resume_before_dispatch=False,attempt_id=None):
    """Exactly one new source/request; failure or ambiguity stops this process."""
    r=app.runtime;s=r.store
    if attempt_id is not None:
        from uuid import UUID
        if str(UUID(attempt_id))!=attempt_id:raise CoreError('QUALIFICATION_ATTEMPT_ID_REQUIRED')
    path=app.home/('qualification-'+attempt_id+'.json' if attempt_id else 'review-project-note.json')
    source_reference='first-life.live-source'+('.'+attempt_id if attempt_id else '')
    request_key='first-life.live-response.'+attempt_id if attempt_id else 'first-life.one-new-live-semantic'
    note={'origin':'DEVELOPER_CONTROLLED_PROJECT_SOURCE_NOT_NANA_EXPERIENCE','resource_state':'A public project note about verified owned development work needs review','opportunities':[{'topic':'first-life-note','motive':'CURIOSITY','value':'HIGH','possible_behaviors':['EXPLORE','WATCH','REST']}]}
    if path.exists():
        if not resume_before_dispatch or json.loads(path.read_text())!=note or s.db.execute('SELECT 1 FROM cognitive_requests WHERE request_key=?',(request_key,)).fetchone():raise CoreError('FIRST_LIFE_SOURCE_ALREADY_EXISTS_NO_REPLAY')
    else:path.write_text(canonical(note));path.chmod(0o600)
    mid=capture(r,source_reference,json.loads(path.read_text()))
    session=app._session('PROJECT')
    cid=session.prepare(request_key,'INTERPRET',(mid,),budget=CognitionBudget(input_tokens=32768,output_tokens=2048,timeout_ms=15000,cost_ceiling_micro=50000),pinned_only=True)
    result=session.execute(cid)
    out={'execution':'REAL_PROVIDER' if session.transport.remote else 'SYNTHETIC_LOOPBACK','request_id':cid,'state':result['state'],'error_code':result.get('error_code'),'identity_id':r.identity_id,'source_memory_id':mid,'source_sha256':digest(path.read_bytes()),'retry':0,'fallback':0}
    if result['state']!='PROPOSED':return out
    reply=session.proposal(result['record_id']);out.update(provider=reply.provider_id,model=reply.model_id,usage=reply.usage,billing=reply.billing,http=reply.http_observation.model_dump(mode='json') if reply.http_observation else None)
    claim=SourcedClaim(entity_id=r.config.entity_id,predicate='first-life.semantic',kind='MODEL_BELIEF',value=reply.proposal.interpretation,confidence=reply.proposal.confidence,valid_from_us=r.clock.utc_now_us())
    derived=capture(r,'first-life.live-derivation'+('.'+attempt_id if attempt_id else ''),{'world_claim':claim.model_dump(mode='json'),'request_id':cid,'request_digest':reply.request_digest,'provider_id':reply.provider_id,'model_id':reply.model_id},kind='MODEL_DERIVATION',parents=(mid,))
    world=WorldModel(s,scopes=r.config.scopes,privacy_classes=('PUBLIC','PROJECT'));belief=world.ingest(derived)
    service=ConcernService(r,resources=('synthetic://first-life/note',));concerns=service.offer(result['record_id']);event=service.opportunity()
    out.update(world_before=world.view(r.config.entity_id,'first-life.semantic').state,belief_id=belief,concern_ids=concerns,source_kind='MODEL_DERIVATION')
    if event is None:
        out['qualification']='PARTIAL_NO_ELIGIBLE_CONCERN_NO_SECOND_CALL';return out
    cycle=r.subject.run(event.input)
    out.update(cycle_id=cycle.cycle_id,judgment=cycle.judgment.stance,intention=cycle.intention.kind,behavior=cycle.intention.behavior)
    if cycle.intention_id:
        row=s.one('subject_intentions',cycle.intention_id)
        if row['state']=='PENDING':r.subject.transition_intention(row['intention_id'],expected_revision=row['revision'],state='DEFERRED')
    contrary=SourcedClaim(entity_id=r.config.entity_id,predicate=claim.predicate,kind='RAW_OBSERVATION',value='The owned note was corrected by its controller',valid_from_us=r.clock.utc_now_us())
    path.write_text(canonical({'origin':'DEVELOPER_CONTROLLED_SOURCE_CORRECTION','resource_state':contrary.value}))
    counter=capture(r,'first-life.live-counter-source'+('.'+attempt_id if attempt_id else ''),{'world_claim':contrary.model_dump(mode='json')});world.ingest(counter)
    out['world_conflict']=world.view(r.config.entity_id,claim.predicate).state
    corrected=contrary.model_copy(update={'corrects':belief})
    correction=capture(r,'first-life.live-corrected-source'+('.'+attempt_id if attempt_id else ''),{'world_claim':corrected.model_dump(mode='json')});world.ingest(correction)
    out['world_corrected']=world.view(r.config.entity_id,claim.predicate).state
    path.write_text(canonical({'resource_state':'source withdrawn by the controlled owner'}))
    for key in (mid,counter,correction):app.forget(key)
    assert service.opportunity() is None
    after=r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.first-life.live-withdrawn'+('.'+attempt_id if attempt_id else ''),kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us()))
    out.update(world_withdrawn=world.view(r.config.entity_id,claim.predicate).state,after_choice=after.intention.kind,after_cycle_id=after.cycle_id,qualification='LIVE_CURRENT_SUBJECT_SEMANTIC_INTEGRATION_PASS' if session.transport.remote else 'SYNTHETIC_SEMANTIC_INTEGRATION_PASS')
    assert out['world_conflict']=='CONFLICT' and out['world_corrected']=='SUPPORTED_BELIEF' and out['world_withdrawn']=='UNKNOWN' and after.intention.kind=='NO_ACTION'
    return out


def secret_from_terminal():
    if not os.isatty(0):raise CoreError('EXPLICIT_PRIVATE_TERMINAL_BINDING_REQUIRED')
    original=termios.tcgetattr(0);masked=termios.tcgetattr(0);masked[3]&=~termios.ECHO
    termios.tcsetattr(0,termios.TCSANOW,masked)
    try:
        print('CREDENTIAL_INPUT_READY_ECHO_DISABLED',flush=True)
        raw=os.read(0,4097)
        if not raw.endswith(b'\n') or len(raw)>4096:raise CoreError('SECRET_INPUT_BOUND')
        left,right=os.pipe()
        try:
            os.write(right,raw);os.close(right);right=None
            resolver=ExplicitFDResolver(left,REF)
        finally:
            os.close(left)
            if right is not None:os.close(right)
        raw=None;return resolver
    finally:termios.tcsetattr(0,termios.TCSANOW,original)


def scan_and_save(home,output,data,resolver):
    credential=resolver.resolve(REF);needle=credential.reveal_for_header().encode();matches=0
    try:
        repo=Path(__file__).resolve().parents[2]
        import subprocess
        names=subprocess.check_output(['git','ls-files','-z'],cwd=repo).decode().split('\0')
        paths=[repo/n for n in names if n]
        # Explicit mission roots only; never inspect the old unread bundle or
        # arbitrary untracked user files. Include pending source/evidence too.
        pending=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=repo).decode().split('\0')
        paths.extend(repo/n for n in pending if n.startswith(('src/','tests/first_life_integration/','tools/nana_first_life_integration/','tools/nana_first_life_live_response/','tests/live_response/','docs/nana_first_life_live_response_v1','docs/nana_first_life_integration_v1','PROJECT_BRAIN/')))
        paths.extend(Path(home).glob('subject/self.db*'))
        paths.extend(Path(home).rglob('*.json'))
        paths.extend(Path('/tmp').glob('nana-first-life-*.log'))
        paths.extend(Path('/tmp').glob('nana-first-life-*.xml'))
        encoded=json.dumps(data,ensure_ascii=False,indent=2).encode()
        matches+=int(needle in encoded)
        matches+=int(needle in subprocess.check_output(['git','diff','--binary','HEAD'],cwd=repo))
        for path in paths:
            if path.is_file() and not path.is_symlink():matches+=int(needle in path.read_bytes())
        if matches:raise CoreError('FIRST_LIFE_SECRET_LEAK_BLOCK')
        data['secret_audit']={'present':True,'persisted':False,'exact_matches':matches,'scope':'TRACKED_DIFF_PENDING_MISSION_SOURCE_EVIDENCE_HOME_DB_JSON_TASK_LOGS_XML_BUNDLE_EXCLUDED','binding':'CURRENT_TURN_EXPLICIT_STDIN_MEMORY_PIPE_EXISTING_FD_RESOLVER_NO_ARGV_ENV_FILE'}
        output=Path(output)
        fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    finally:credential.clear();needle=None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--review-seconds',type=int,default=3600);p.add_argument('--resume-local-pre-dispatch-report',type=Path);a=p.parse_args()
    resolver=None;calls=[];original=OpenAIJSONTransport.exchange;report={'scope':'CURRENT_FIRST_LIFE_PROJECT_ONLY','authorized_new_calls':8,'conservative_reserved_limit_usd_micro':400000,'actual_billing':'UNKNOWN','retry':0,'fallback':0,'calls':calls,'human_review':'NOT_RUN'}
    def measured(port,request):
        if len(calls)>=8:raise CoreError('FIRST_LIFE_LIVE_CALL_CAP')
        entry={'request_id':request.request_id,'role':request.cognitive_role,'provider_id':port.provider_id,'requested_model':port.model_id,'retry':0,'fallback':0};calls.append(entry)
        try:
            reply=original(port,request);entry.update(state='PARSED',returned_model=reply.model_id,usage=reply.usage,billing=reply.billing);return reply
        except Exception:
            entry['state']='NO_VALID_REPLY';raise
        finally:entry['http']=port.last_http_observation.model_dump(mode='json') if port.last_http_observation else None;entry['allowlisted_metadata']=port.last_response_metadata
    try:
        if a.output.exists():raise CoreError('FIRST_LIFE_LIVE_OUTPUT_EXISTS_NO_REPLAY')
        if a.resume_local_pre_dispatch_report:
            prior=json.loads(a.resume_local_pre_dispatch_report.read_text())
            if prior['calls'] or prior.get('code')!='MEMORY_NOT_CURRENT' or prior.get('secret_audit',{}).get('exact_matches')!=0:raise CoreError('FIRST_LIFE_PRIOR_DISPATCH_NOT_PROVEN_ABSENT')
            with sqlite3.connect((a.home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
                baseline=db.execute('SELECT count(*),coalesce(sum(reserved_cost_micro),0) FROM cognitive_requests').fetchone()
            if baseline!=(1,0):raise CoreError('FIRST_LIFE_PRIOR_DISPATCH_NOT_PROVEN_ABSENT')
            cfg=load_config(a.home) # no budget reset, no route/config renewal
        else:cfg=configure(a.home)
        resolver=secret_from_terminal();ready=preflight(a.home,live=True,resolver=resolver)
        if ready['state']!='PREFLIGHT_PASS':raise CoreError('FIRST_LIFE_LIVE_PREFLIGHT_BLOCKED')
        router=configured_router(a.home,cfg,resolver=resolver,authorized=True)
        OpenAIJSONTransport.exchange=measured
        with LifeApplication(a.home,router=router) as app:
            app.pause();before={t:len(app.runtime.store.all(t)) for t in ('actions','grants','goals')};report['semantic']=semantic(app,resume_before_dispatch=bool(a.resume_local_pre_dispatch_report))
            assert before=={t:len(app.runtime.store.all(t)) for t in before}
            report['identity_id']=app.runtime.identity_id
        if report['semantic'].get('qualification')!='LIVE_CURRENT_SUBJECT_SEMANTIC_INTEGRATION_PASS':
            report['status']='PARTIAL_OR_UNKNOWN_STOPPED_NO_RETRY';scan_and_save(a.home,a.output,report,resolver);print(json.dumps({'state':report['status'],'calls':len(calls),'request_state':report['semantic']['state']}),flush=True);return
        # New epoch, same canonical Subject and attempt ledger. No execute/replay.
        with LifeApplication(a.home,router=router) as app:
            app.pause();assert app.runtime.identity_id==report['identity_id']
            session=app._session('PROJECT');session.recover()
            assert len(app.runtime.store.all('cognitive_requests'))==2 and len(calls)==1
            report['restart_no_duplicate_provider_call']=True
        report['status']='LIVE_SEMANTIC_PASS_PRIVATE_HUMAN_ENTRY_READY'
        scan_and_save(a.home,a.output,report,resolver)
        print(json.dumps({'state':report['status'],'identity_id':report['identity_id'],'real_calls':len(calls),'remaining_calls':8-len(calls),'human_review':'NOT_RUN'}),flush=True)
        from nana_core.life.__main__ import run
        run(a.home,min(a.review_seconds,7200),headless=True,router=router,control_enabled=True)
        report['status']='REVIEW_RUNTIME_STOPPED_HUMAN_RESULT_NOT_AUTO_ASSIGNED'
        scan_and_save(a.home,a.output,report,resolver)
    except (CoreError,OSError,ValueError) as exc:
        report['status']='BLOCKED_OR_UNKNOWN_NO_RETRY';report['code']=exc.code if isinstance(exc,CoreError) else 'FIRST_LIFE_LOCAL_OR_TRANSPORT_ERROR'
        if resolver:scan_and_save(a.home,a.output,report,resolver)
        print(json.dumps({'state':report['status'],'code':report['code'],'calls':len(calls)}),flush=True)
    finally:
        OpenAIJSONTransport.exchange=original
        if resolver:resolver.clear()

if __name__=='__main__':main()
