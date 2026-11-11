"""Two independently authenticated HTTP admissions into the original Core.

Only the original in-flight dialogue prototype is enabled in this fixture.
"""
import threading
import pytest
from .test_message_sequence_http import sequence_api
from .test_http_integration import login, http, base
from .test_continuous_inputs import wait_pending


def block_first_interpret(service):
    release=threading.Event();blocked=threading.Event()
    factory=service.fixture_owner['control'].app.router.factory;original=factory.create
    def create(*args):
        port=original(*args);exchange=port.exchange
        def once(request):
            if request.cognitive_role=='INTERPRET' and not blocked.is_set():
                blocked.set();assert release.wait(8)
            return exchange(request)
        port.exchange=once;return port
    factory.create=create
    return release,blocked


def test_concurrent_http_review_uses_one_original_purpose_and_individual_receipts(tmp_path):
    release=threading.Event();blocked=threading.Event();answers={};threads=[]
    with sequence_api(tmp_path,coalesce_continuations=True) as (server,service,calls):
        control=service.fixture_owner['control'];factory=control.app.router.factory;original=factory.create
        def create(*args):
            port=original(*args);exchange=port.exchange
            def once(request):
                if request.cognitive_role=='INTERPRET' and not blocked.is_set():
                    blocked.set();assert release.wait(5)
                return exchange(request)
            port.exchange=once;return port
        factory.create=create;headers=login(server,service)
        bootstrap=http(server,'bootstrap',headers=headers)[1]
        assert bootstrap['capabilities']['conversation_continuation'] is True
        parent={**base(service,'http-parent'),'text':'SYNTHETIC initial thought',
                'thread_id':'same-recipient','privacy_class':'PROJECT','require_model':True}
        def start(name,body):
            thread=threading.Thread(target=lambda:answers.update({name:http(server,'messages','POST',body,headers)}),daemon=True)
            threads.append(thread);thread.start()
        try:
            start('parent',parent);assert blocked.wait(3)
            child={**base(service,'http-child'),'text':'SYNTHETIC added thought',
                   'thread_id':'same-recipient','privacy_class':'PROJECT','require_model':True,
                   'continuation_of':'http-parent'}
            start('child',child)
            wait_pending(control,1)  # This must happen before releasing the first model.
            release.set()
            for thread in threads:thread.join(7);assert not thread.is_alive()
            root=answers['parent'][1]['data'];follow=answers['child'][1]['data']
            assert answers['parent'][0]==answers['child'][0]==200
            assert root['state']==follow['state']=='VERIFIED',answers
            assert root['result']['state']=='SHADOW_INPUT_REVIEWED_NO_REPLY'
            assert root['result']['text'] is None and root['result']['reply_response_id'] is None
            assert follow['result']['respond_to_memory_ids']==[
                root['result']['message_memory_id'],follow['result']['message_memory_id']]
            assert follow['result']['text']=='A deliberately synthetic language response'
            assert follow['result']['reply_response_id'] and len(calls)==3
            # A closed parent window must not break the child's original receipt.
            for body in (parent,child):
                saved=answers['parent' if body is parent else 'child'][1]['data']
                assert http(server,'messages','POST',body,headers)[1]['data']==saved
                assert http(server,'receipts/'+body['idempotency_key'],headers=headers)[1]['data']==saved
            assert len(calls)==3 and not service.inflight_messages
            assert 'SYNTHETIC added thought' not in service.ledger.document.path.read_text()
        finally:
            release.set()
            for thread in threads:thread.join(7)


@pytest.mark.parametrize('change',['thread','topic','retained','generation','epoch','principal','owner','wire'])
def test_unbound_http_continuation_never_reserves_or_dispatches(tmp_path,change):
    with sequence_api(tmp_path,coalesce_continuations=True) as (server,service,calls):
        release,blocked=block_first_interpret(service);headers=login(server,service)
        http(server,'bootstrap',headers=headers)
        parent={**base(service,'bound-parent'),'text':'SYNTHETIC first input',
                'thread_id':'same-recipient','require_model':True}
        replies=[];thread=threading.Thread(target=lambda:replies.append(http(server,'messages','POST',parent,headers)),daemon=True)
        thread.start()
        try:
            assert blocked.wait(3)
            child={**base(service,'unbound-child'),'text':'SYNTHETIC addition',
                   'thread_id':'same-recipient','require_model':True,'continuation_of':'bound-parent'}
            if change=='thread':child['thread_id']='other-recipient'
            elif change=='topic':child['topic']='other-topic'
            elif change=='retained':child['retain_shared_life']=True
            elif change=='generation':child['run_generation']='f'*32
            elif change=='epoch':child['owner_epoch']+=1
            elif change=='owner':service.continuation_owner=None
            elif change=='wire':child['text']='🌙'*2048
            elif change=='principal':
                from .test_http_integration import PW
                device,refresh=service.auth.login_device(PW,'SYNTHETIC other device')
                headers={'Authorization':'Bearer '+service.auth.native_session(device,refresh)}
            revision=service.ledger.revision
            code,value,_=http(server,'messages','POST',child,headers)
            assert code==(413 if change=='wire' else 409),value
            assert service.ledger.revision==revision
            assert not service.fixture_owner['control'].pending_inputs
            assert service.inflight_messages[('host.web','bound-parent')]['done'].is_set()
            assert not calls  # The held first provider has not completed yet.
        finally:
            release.set();thread.join(7)
        assert not thread.is_alive() and replies[0][1]['data']['state']=='VERIFIED'
        assert len(calls)==2 and not service.inflight_messages


def test_priority_pause_is_responsive_while_parent_and_child_are_inflight(tmp_path):
    with sequence_api(tmp_path,coalesce_continuations=True) as (server,service,calls):
        release,blocked=block_first_interpret(service);headers=login(server,service)
        http(server,'bootstrap',headers=headers);answers={};threads=[]
        def start(name,body):
            thread=threading.Thread(target=lambda:answers.update({name:http(server,'messages','POST',body,headers)}),daemon=True)
            threads.append(thread);thread.start()
        try:
            start('root',{**base(service,'pause-root'),'text':'SYNTHETIC original',
                'thread_id':'same-recipient','require_model':True})
            assert blocked.wait(3)
            start('child',{**base(service,'pause-child'),'text':'SYNTHETIC addition',
                'thread_id':'same-recipient','require_model':True,'continuation_of':'pause-root'})
            wait_pending(service.fixture_owner['control'],1)
            code,result,_=http(server,'commands','POST',{**base(service,'pause-priority'),'operation':'PAUSE'},headers)
            assert code==200 and result['data']['state']=='VERIFIED',result
            assert not release.is_set() and all(thread.is_alive() for thread in threads)
        finally:
            release.set()
            for thread in threads:thread.join(7)
        assert all(not thread.is_alive() for thread in threads)
        assert all(row[1]['data']['state']=='VERIFIED' for row in answers.values()),answers
        assert len(calls)==3


def test_disabled_core_does_not_admit_continuations_or_renew_a_closed_window(tmp_path):
    with sequence_api(tmp_path) as (server,service,calls):
        headers=login(server,service)
        assert http(server,'bootstrap',headers=headers)[1]['capabilities']['conversation_continuation'] is False
        child={**base(service,'no-parent'),'text':'SYNTHETIC new input','continuation_of':'absent'}
        assert http(server,'messages','POST',child,headers)[0]==409
        assert service.ledger.revision==0 and not calls


def test_duplicate_child_is_receipt_only_and_second_new_child_is_not_admitted(tmp_path):
    with sequence_api(tmp_path,coalesce_continuations=True) as (server,service,calls):
        release,blocked=block_first_interpret(service);headers=login(server,service)
        http(server,'bootstrap',headers=headers);answers=[];threads=[]
        def start(body):
            thread=threading.Thread(target=lambda:answers.append(http(server,'messages','POST',body,headers)),daemon=True)
            threads.append(thread);thread.start()
        try:
            start({**base(service,'one-root'),'text':'SYNTHETIC first','require_model':True})
            assert blocked.wait(3)
            child={**base(service,'one-child'),'text':'SYNTHETIC second','require_model':True,'continuation_of':'one-root'}
            start(child);control=service.fixture_owner['control'];wait_pending(control,1)
            revision=service.ledger.revision
            duplicate=http(server,'messages','POST',child,headers)
            assert duplicate[0]==200 and duplicate[1]['data']['state']=='RUNNING'
            extra={**base(service,'extra-child'),'text':'SYNTHETIC third','require_model':True,'continuation_of':'one-root'}
            assert http(server,'messages','POST',extra,headers)[0]==409
            assert service.ledger.revision==revision and len(control.pending_inputs)==1
        finally:
            release.set()
            for thread in threads:thread.join(7)
        assert len(answers)==2 and all(row[1]['data']['state']=='VERIFIED' for row in answers)
        assert len(calls)==3


def test_privacy_fence_covers_entire_parent_wait_not_just_its_core_rpc(tmp_path,monkeypatch):
    """Injected journal watermark change; actual withdrawal is covered separately."""
    with sequence_api(tmp_path,coalesce_continuations=True) as (server,service,calls):
        factory=service.fixture_owner['control'].app.router.factory;original=factory.create
        first=threading.Event();second=threading.Event();release=threading.Event();answers=[];threads=[]
        def create(*args):
            port=original(*args);exchange=port.exchange
            def once(request):
                if request.cognitive_role=='INTERPRET':
                    if not first.is_set():first.set();assert release.wait(8)
                    else:second.set();assert release_second.wait(8)
                return exchange(request)
            port.exchange=once;return port
        release_second=threading.Event();factory.create=create
        headers=login(server,service);http(server,'bootstrap',headers=headers)
        watermark=[service._privacy_watermark()]
        monkeypatch.setattr(service,'_privacy_watermark',lambda:watermark[0])
        def start(body):
            thread=threading.Thread(target=lambda:answers.append(http(server,'messages','POST',body,headers)),daemon=True)
            threads.append(thread);thread.start()
        try:
            start({**base(service,'privacy-root'),'text':'SYNTHETIC first','require_model':True})
            assert first.wait(3)
            start({**base(service,'privacy-child'),'text':'SYNTHETIC second','require_model':True,'continuation_of':'privacy-root'})
            wait_pending(service.fixture_owner['control'],1);release.set();assert second.wait(3)
            # Root Core RPC has returned; original BFF write lane is still held.
            assert len(threads)==2 and all(thread.is_alive() for thread in threads)
            watermark[0]='synthetic-withdrawal-watermark'
        finally:
            release.set();release_second.set()
            for thread in threads:thread.join(7)
        assert len(answers)==2 and all(row[1]['data']['state']=='VERIFIED' for row in answers)
        assert all(row[1]['data']['result']=={'state':'BODY_WITHHELD_SOURCE_CHANGED'} for row in answers)
        assert len(calls)==3 and not service.ledger.volatile
