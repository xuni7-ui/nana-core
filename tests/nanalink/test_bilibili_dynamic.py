from nana_core.nanalink.bilibili_dynamic import normalize_dynamic
from nana_core.nanalink.contracts import Account


def test_subscription_event_is_private_account_bound_and_source_preserving():
    account=Account(platform='bilibili',adapter_id='bilibili.account',account_id='42')
    row={'id_str':'123','type':'DYNAMIC_TYPE_AV','modules':{'module_author':{'mid':43,'pub_ts':1},
         'module_dynamic':{'desc':{'text':'new video'},'major':{'archive':{'bvid':'BV1t55v6DE2v'}}}},'likes':1}
    event=normalize_dynamic(account,row,now_us=2000000,origin='SYNTHETIC_LOOPBACK')
    assert event.account==account and event.privacy=='PERSONAL' and event.sender_id=='43'
    assert [s.kind for s in event.segments]==['text','video','dynamic']
    assert event.raw_reference=='bilibili:dynamic:123'
    assert normalize_dynamic(account,{**row,'likes':999},now_us=3000000,origin='SYNTHETIC_LOOPBACK').raw_sha256==event.raw_sha256
    other=account.model_copy(update={'account_id':'44'})
    assert normalize_dynamic(other,row,now_us=2000000,origin='SYNTHETIC_LOOPBACK').key != event.key
    assert normalize_dynamic(account,row,now_us=0,origin='SYNTHETIC_LOOPBACK') is None


def test_forwarded_dynamic_preserves_origin_without_conflating_authors():
    account=Account(platform='bilibili',adapter_id='bilibili.account',account_id='42')
    row={'id_str':'123','type':'DYNAMIC_TYPE_FORWARD','modules':{'module_author':{'mid':43,'pub_ts':1},
         'module_dynamic':{'desc':{'text':'forwarder comment'}}},
         'orig':{'id_str':'456','modules':{'module_author':{'mid':99},
                 'module_dynamic':{'desc':{'text':'original text is not promoted'}}}}}
    event=normalize_dynamic(account,row,now_us=2000000,origin='SYNTHETIC_LOOPBACK')
    assert event.sender_id=='43' and event.parent_id=='456'
    assert [(s.kind,s.reference) for s in event.segments]==[
        ('text',None),('forwarded_dynamic','bilibili:dynamic:456'),
        ('forwarded_author','bilibili:user:99'),('dynamic','bilibili:dynamic:123')]
    assert all(s.text != 'original text is not promoted' for s in event.segments)
    changed={**row,'orig':{'id_str':'456','modules':{'module_author':{'mid':100}}}}
    assert normalize_dynamic(account,changed,now_us=2000000,origin='SYNTHETIC_LOOPBACK').raw_sha256 != event.raw_sha256
    malformed={**row,'orig':{'id_str':'123','modules':{'module_author':{'mid':99}}}}
    invalid=normalize_dynamic(account,malformed,now_us=2000000,origin='SYNTHETIC_LOOPBACK')
    assert invalid.parent_id is None and all(not s.kind.startswith('forwarded_') for s in invalid.segments)
