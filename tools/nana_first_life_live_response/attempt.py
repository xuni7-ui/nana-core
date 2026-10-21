"""ONE new source/INTERPRET request per explicit repair iteration, existing ledger.

Requires host memory-only FD. Never searches credentials or resets configuration.
"""
import argparse,json,sqlite3,os,stat
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config
from nana_core.life.provider import ExplicitFDResolver,configured_router
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
from tools.nana_first_life_integration.live_review import semantic,REF,scan_and_save,secret_from_terminal
from tools.nana_first_life_integration.dev import preflight

HOME=Path('/workspace/nana-first-life/integration-30m-01/fresh-host')
IDENTITY='37281abf-18c0-4460-b1de-566d3e0734b7'
HYPOTHESES=('BOUNDED_TEXT_BLOCK_CONTENT_COMPATIBILITY','DIAGNOSE_STRICT_SEMANTIC_PATH','FINITE_MEMORY_CITATION_VOCABULARY')


def render_existing(app,event_key,text,attempt_id):
    """New RENDER only, from a still-supported, already committed original C.

    Does not execute/retry a rejected request or produce a second judgment.
    The explicitly supplied project question and returned wording stay volatile.
    """
    from nana_core.continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.subject import SubjectInput
    if LiteralSpanInterpreter().interpret(text).kind!='PROJECT_STATUS':raise CoreError('QUALIFICATION_PROJECT_STATUS_REQUIRED')
    r=app.runtime;s=r.store
    row=s.db.execute('SELECT * FROM subject_events WHERE source_key=?',(event_key,)).fetchone()
    if not row or not row['record_id']:raise CoreError('QUALIFICATION_EXISTING_JUDGMENT_REQUIRED')
    event=SubjectInput.model_validate_json(canonical(RecordService(s).read(row['record_id'])['payload']['input']))
    if event.domain!='LOCAL_INTERACTION' or event.privacy_class!='PROJECT' or event.interaction_signal.kind!='PROJECT_STATUS':raise CoreError('QUALIFICATION_PROJECT_STATUS_REQUIRED')
    before=len(s.all('subject_cycles'));cycle=r.subject.run(event)
    if not cycle.replayed or cycle.context_fit.mode!='PROJECT_STATUS' or before!=len(s.all('subject_cycles')):raise CoreError('QUALIFICATION_EXISTING_JUDGMENT_REQUIRED')
    session,rid=app._model('first-life.render-validation.'+attempt_id,'RENDER',event.source_memory_ids[0],text,event.interaction_signal.topic_key,'PROJECT',cycle)
    wording=session.take_dialogue_draft(rid)
    if not wording:raise CoreError('QUALIFICATION_NO_USABLE_WORDING')
    return {'record_id':rid,'cycle_id':cycle.cycle_id,'original_C_replayed_without_new_judgment':True,'render_state':'UNVERIFIED_MODEL_WORDING','raw_body_persisted':False},wording


def execute(home,output,resolver,hypothesis,*,render_event_key=None,question=None):
    if Path(home)!=HOME or hypothesis not in HYPOTHESES:raise CoreError('QUALIFICATION_SCOPE_DENIED')
    if Path(output).exists():raise CoreError('QUALIFICATION_OUTPUT_EXISTS_NO_REPLAY')
    cfg=load_config(home)
    if cfg.provider_timeout_ms>15000 or set(cfg.remote_privacy)-{'PUBLIC','PROJECT'}:raise CoreError('QUALIFICATION_POLICY_DENIED')
    ready=preflight(home,live=True,resolver=resolver)
    if ready['state']!='PREFLIGHT_PASS' or ready['identity_id']!=IDENTITY:raise CoreError('QUALIFICATION_PREFLIGHT_BLOCKED')
    # Original immutable ledger includes one fixture+one old failed call. It is
    # never reset/replaced/refunded, including failures and UNKNOWN reservations.
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as d:
        count,cost=d.execute('SELECT count(*),coalesce(sum(reserved_cost_micro),0) FROM cognitive_requests').fetchone()
    if not 2<=count<9 or cost+50000>400000:raise CoreError('QUALIFICATION_REMAINING_BUDGET_DENIED')
    calls=[];wording=None;original=OpenAIJSONTransport.exchange;report={'hypothesis':hypothesis,'attempt_id':str(uuid4()),'calls':calls,'retry':0,'fallback':0,'actual_billing':'UNKNOWN','human_review':'NOT_RUN'}
    def observed(port,request):
        u=urlsplit(port.endpoint)
        if calls or u.scheme!='https' or u.hostname!='api.deepseek.com' or u.port is not None or u.path not in {'/chat/completions','/v1/chat/completions'} or u.query or u.fragment or u.username or port.model_id!='deepseek-flash':raise CoreError('QUALIFICATION_DISPATCH_DENIED')
        item={'request_id':request.request_id,'model_requested':port.model_id,'role':request.cognitive_role};calls.append(item)
        try:return original(port,request)
        finally:
            item.update(parser=port.last_parse_diagnostic.model_dump(mode='json') if port.last_parse_diagnostic else None,http=port.last_http_observation.model_dump(mode='json') if port.last_http_observation else None,provider_metadata=port.last_response_metadata)
    try:
        OpenAIJSONTransport.exchange=observed
        router=configured_router(home,cfg,resolver=resolver,authorized=True)
        with LifeApplication(home,router=router) as app:
            app.pause();before={t:len(app.runtime.store.all(t)) for t in ('identities','goals','actions','grants')}
            if render_event_key is not None:
                if hypothesis!='FINITE_MEMORY_CITATION_VOCABULARY' or not question:raise CoreError('QUALIFICATION_RENDER_SCOPE_DENIED')
                report['render'],wording=render_existing(app,render_event_key,question,report['attempt_id'])
            else:report['semantic']=semantic(app,attempt_id=report['attempt_id'])
            assert before=={t:len(app.runtime.store.all(t)) for t in before}
            report['identity_id']=app.runtime.identity_id
            report['status']='LIVE_RENDER_PASS' if wording else 'LIVE_SEMANTIC_PASS' if report['semantic'].get('qualification')=='LIVE_CURRENT_SUBJECT_SEMANTIC_INTEGRATION_PASS' else 'PARTIAL_STOPPED_ITERATION'
    except (CoreError,ValueError,AssertionError,OSError) as exc:
        report['status']='LOCAL_OR_INTEGRATION_BLOCKED_NO_RETRY'
        report['code']=exc.code if isinstance(exc,CoreError) else 'QUALIFICATION_LOCAL_VALIDATION_FAILED'
    finally:
        OpenAIJSONTransport.exchange=original
    scan_and_save(home,output,report,resolver)
    if wording:print(json.dumps({'live_reply_candidate':wording,'human_review':'NOT_RUN','transcript_saved':False},ensure_ascii=False),flush=True)
    return report


def resolver_from_fd(fd):
    mode=os.fstat(fd).st_mode
    if not (stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):raise CoreError('QUALIFICATION_MEMORY_PIPE_FD_REQUIRED')
    return ExplicitFDResolver(fd,REF)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,default=HOME);p.add_argument('--output',type=Path,required=True);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--secret-fd',type=int);group.add_argument('--private-terminal-binding',action='store_true');p.add_argument('--hypothesis',choices=HYPOTHESES,required=True);p.add_argument('--render-event-key');a=p.parse_args()
    resolver=secret_from_terminal() if a.private_terminal_binding else resolver_from_fd(a.secret_fd)
    try:
        question=None
        if a.render_event_key:
            import sys,termios
            flags=termios.tcgetattr(0);masked=termios.tcgetattr(0);masked[3]&=~termios.ECHO
            termios.tcsetattr(0,termios.TCSANOW,masked)
            try:
                print('PROJECT_QUESTION_READY_NO_PERSISTENCE',flush=True);question=sys.stdin.readline(2049).strip()
            finally:termios.tcsetattr(0,termios.TCSANOW,flags)
        out=execute(a.home,a.output,resolver,a.hypothesis,render_event_key=a.render_event_key,question=question);print(json.dumps({'state':out['status'],'calls':len(out['calls']),'attempt_id':out['attempt_id']}))
    finally:resolver.clear()

if __name__=='__main__':main()
