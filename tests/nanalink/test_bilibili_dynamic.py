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
