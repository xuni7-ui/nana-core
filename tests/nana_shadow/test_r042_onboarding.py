"""Synthetic build/readback tests, never an independent real-host review."""
import ast
from datetime import datetime, timezone, timedelta
import json
import subprocess
from types import MappingProxyType
import pytest
from tools.nana_astrbot_shadow import sealed_trust
from tools.nana_astrbot_shadow.one_shot import (OneShotReceipt, Provenance, review_document,
    parse_receipt, ProductionTrustStore, FixtureTrustStore)
from tools.nana_astrbot_shadow.onboarding import validate_review, render_seal, source_review, prepare
from tools.nana_host_shadow.safety import canonical, digest

NOW=datetime(2026,10,12,12,tzinfo=timezone.utc)

def core_metadata():
    return {'identity_id':'11111111-1111-1111-1111-111111111111','identity_revision':1,
        'core_evidence_id':'22222222-2222-2222-2222-222222222222',
        'observation_id':'33333333-3333-3333-3333-333333333333','goal_candidate_id':'a'*64,
        'shadow_decision_id':'cloud.shadow:'+'b'*64,'shadow_plan_id':'cloud.shadow:'+'b'*64+'#plan_draft',
        'dedup_result':'NEW','barrier_result':'SHADOW_BLOCKED','event_timestamp':NOW.isoformat(),
        'metadata_hash':'c'*64,'zero_execution_counts':{k:0 for k in ('actions','attempts','grants','budgets','strategies')},
        'model_semantics_verified':False}


def review(origin=Provenance.ASTRBOT_REAL_MESSAGE):
    # Structurally real-shaped synthetic data for validator tests, NOT a review.
    r=OneShotReceipt(receipt_id='r04-'+'1'*32,issued_at=NOW.isoformat(),expires_at=(NOW+timedelta(seconds=600)).isoformat(),
        store_binding='a'*64,hash_scope='r04-host',platform_scope='aiocqhttp',sender_hash='b'*64,
        conversation_hash='c'*64,event_type_scope='GroupMessage',review_provenance=origin,review_receipt_digest='0'*64)
    r=r.model_copy(update={'review_receipt_digest':digest(review_document(r))})
    return {'schema_version':1,'kind':'AUTHORIZATION_REVIEW','reviewer_origin':'NANA_INDEPENDENT_HOST_REVIEW',
        'operator_authorization_digest':r.authorization_digest,'host_metadata_evidence_digest':'d'*64,
        'confirmation':'INDEPENDENTLY_REVIEWED_EXACT_ONE_SHOT','receipt':r.canonical(),
        'review':review_document(r),'runtime_report':None}


def test_default_two_anchors_empty_and_not_overridden(monkeypatch):
    for k in ('PRODUCTION_REVIEW_PINS','REAL_RUNTIME_PROOF_PINS','TRUST_ALL','ALLOW_REAL'):
        monkeypatch.setenv(k,'true')
    r=parse_receipt(review()['receipt'])
    assert sealed_trust.SEAL_MODE=='EMPTY'
    assert not sealed_trust.PRODUCTION_REVIEW_PINS and not sealed_trust.REAL_RUNTIME_PROOF_PINS
    assert not ProductionTrustStore().validates(r,review_document(r))
    assert not FixtureTrustStore().validates(r,review_document(r))
    with pytest.raises(TypeError):sealed_trust.PRODUCTION_REVIEW_PINS['a']='b'


def test_contract_and_render_do_not_mint_production_trust():
    d=review();r,mode,proof=validate_review(d,now=NOW)
    assert mode=='ONE_SHOT' and proof=={}
    source=render_seal(r,mode,proof,'2'*40)
    tree=ast.parse(source)
    values={n.targets[0].id:ast.literal_eval(n.value.args[0] if isinstance(n.value,ast.Call) else n.value)
            for n in tree.body if isinstance(n,ast.Assign)}
    assert values['PRODUCTION_REVIEW_PINS']=={r.review_receipt_digest:r.authorization_digest}
    assert values['EXACT_RECEIPT_DIGEST']==r.receipt_digest
    assert values['EXACT_STORE_BINDING']==r.store_binding
    assert values['REAL_RUNTIME_PROOF_PINS']=={}
    assert not ProductionTrustStore().validates(r,d['review'])  # rendered bytes NOT loaded!


@pytest.mark.parametrize('change',[{'schema_version':True},{'kind':'FIXTURE'}, {'reviewer_origin':'FIXTURE'},
    {'confirmation':'force'}, {'operator_authorization_digest':'0'*64}, {'host_metadata_evidence_digest':'*'},
    {'body':'PRIVATE-SYNTHETIC-CANARY'}, {'runtime_report':{}}, {'receipt':'{}'}, {'review':{}},
    {'operator_authorization_digest':'e'*64}, {'host_metadata_evidence_digest':None}])
def test_bad_or_extra_review_data(change):
    d={**review(),**change}
    with pytest.raises(ValueError):validate_review(d,now=NOW)

@pytest.mark.parametrize('origin',[Provenance.FIXTURE,Provenance.LOCAL_SYNTHETIC,Provenance.ASTRBOT_LIFECYCLE])
def test_fixture_promotion_blocked(origin):
    with pytest.raises(ValueError,match='FIXTURE'):validate_review(review(origin),now=NOW)


def test_expiration_future_and_digest_corruption():
    d=review()
    for clock in (NOW-timedelta(seconds=3),NOW+timedelta(seconds=600)):
        with pytest.raises(ValueError):validate_review(d,now=clock)
    body=json.loads(d['receipt']);body['sender_hash']='f'*64;d['receipt']=canonical(body)
    with pytest.raises(ValueError):validate_review(d,now=NOW)


def test_runtime_proof_is_separate_verify_only_never_arm():
    from tools.nana_astrbot_shadow.one_shot_proof import ZERO_KEYS
    d=review();r=parse_receipt(d['receipt']);d['kind']='RUNTIME_PROOF_REVIEW'
    d['runtime_report']={'schema_version':1,'receipt_id':r.receipt_id,'receipt_digest':r.receipt_digest,
        'source_provenance':'ASTRBOT_REAL_MESSAGE','trust_domain':'PRODUCTION','observer_callback_received':True,
        'sanitizer_accepted':True,'core':core_metadata(),'noncore_zero':{k:0 for k in ZERO_KEYS},'binding_evidence_digest':'d'*64}
    r,mode,proof=validate_review(d,now=NOW+timedelta(days=1))
    assert mode=='VERIFY_ONLY' and proof=={digest(d['runtime_report']):'d'*64}
    # Compile/readback is safe data-only; do NOT load a fake real seal into production.
    assert 'VERIFY_ONLY' in render_seal(r,mode,proof,'2'*40)
    for change in ({'source_provenance':'FIXTURE'},{'trust_domain':'FIXTURE'},{'noncore_zero':None},
                   {'binding_evidence_digest':'e'*64},{'core':None},{'receipt_digest':'f'*64}):
        bad={**d,'runtime_report':{**d['runtime_report'],**change}}
        with pytest.raises(ValueError):validate_review(bad,now=NOW)


def test_review_source_is_immutable_git_not_worktree(tmp_path):
    repo=tmp_path/'review-repo';repo.mkdir()
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL).decode().strip()
    git('init');p=repo/'reviews/r042/synthetic.json';p.parent.mkdir(parents=True);p.write_text(canonical(review(Provenance.FIXTURE)))
    git('add','.');git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-m','Synthetic fixture')
    sha=git('rev-parse','HEAD');p.write_text('PRIVATE-UNCOMMITTED-CANARY')
    d=source_review(repo,sha,'reviews/r042/synthetic.json')
    assert d['reviewer_origin']=='NANA_INDEPENDENT_HOST_REVIEW'
    with pytest.raises(ValueError):validate_review(d,now=NOW)
    for ref,path in [('HEAD','reviews/r042/synthetic.json'),(sha,'../../file'),(sha,'/file'),(sha,'review.json')]:
        with pytest.raises(ValueError):source_review(repo,ref,path)


def test_prepare_same_store_restart_no_authority(tmp_path):
    from tools.nana_astrbot_shadow.one_shot_cli import initialize,operator_ledger
    directory=tmp_path/'shadow';directory.mkdir(mode=0o700);info=initialize(directory)
    scope={'platform_scope':'aiocqhttp','conversation_hash':'b'*64,'sender_hash':'c'*64,'event_type_scope':'GroupMessage'}
    out=tmp_path/'request';result=prepare(directory,scope,out,now=NOW)
    r=parse_receipt((out/'receipt.json').read_text())
    assert r.store_binding==info['store_binding']==result['store_binding']
    assert r.hash_scope=='r04-host' and result['production_authority_created'] is False
    assert r.review_receipt_digest==digest(json.loads((out/'review.json').read_text()))
    with operator_ledger(directory) as ledger:
        assert ledger.binding==info['store_binding']
        assert not any(ledger.store.all(t) for t in ('grants','actions','attempts','budgets'))
        assert not ledger.trust.validates(r,review_document(r))
    for extra in ({'sender_id':'raw-synthetic-id'},{'message':'private-synthetic-text'}):
        with pytest.raises(ValueError):prepare(directory,{**scope,**extra},tmp_path/'bad',now=NOW)


def test_verify_only_rejects_arm_and_consume_before_ledger_access():
    # Test the gate with a detached ledger, no production pin is injected.
    from tools.nana_astrbot_shadow.one_shot import ReceiptLedger
    ledger=object.__new__(ReceiptLedger);ledger.trust=ProductionTrustStore()
    with pytest.raises(ValueError,match='SEAL_NOT_EXECUTABLE'):ledger._execution_seal()


@pytest.mark.parametrize('change',[{'body':'PRIVATE-SYNTHETIC-CANARY'}, {'identity_id':'raw-user-id'},
    {'zero_execution_counts':{'actions':0}}, {'identity_revision':True}, {'metadata_hash':None},
    {'event_timestamp':'naive'}, {'shadow_plan_id':'raw-conversation'}, {'model_semantics_verified':True}])
def test_post_review_cannot_export_private_or_unknown_core_fields(change):
    from tools.nana_astrbot_shadow.onboarding import validate_core_metadata
    with pytest.raises(ValueError):validate_core_metadata({**core_metadata(),**change})


def test_verify_only_gate_explicit(monkeypatch):
    from tools.nana_astrbot_shadow.one_shot import ReceiptLedger
    monkeypatch.setattr(sealed_trust,'SEAL_MODE','VERIFY_ONLY')  # gate only, no pin
    ledger=object.__new__(ReceiptLedger);ledger.trust=ProductionTrustStore()
    with pytest.raises(ValueError,match='SEAL_NOT_EXECUTABLE'):ledger._execution_seal()
    ledger.trust=FixtureTrustStore();ledger._execution_seal()


def test_review_document_recomputes_digest_without_grant(tmp_path):
    from tools.nana_astrbot_shadow.one_shot_cli import initialize
    from tools.nana_astrbot_shadow.onboarding import make_review
    directory=tmp_path/'shadow';directory.mkdir(mode=0o700);initialize(directory)
    scope={'platform_scope':'aiocqhttp','conversation_hash':'b'*64,'sender_hash':'c'*64,'event_type_scope':'GroupMessage'}
    request=tmp_path/'request';prepare(directory,scope,request)
    r=parse_receipt((request/'receipt.json').read_text())
    approval={'reviewer_origin':'NANA_INDEPENDENT_HOST_REVIEW','operator_authorization_digest':r.authorization_digest,
        'host_metadata_evidence_digest':'d'*64,'confirmation':'INDEPENDENTLY_REVIEWED_EXACT_ONE_SHOT'}
    result=make_review(request,approval,tmp_path/'review.json')
    assert result['production_authority_created'] is False
    assert result['review_receipt_digest']==r.review_receipt_digest
    assert not ProductionTrustStore().validates(r,review_document(r))
    for extra in ({'body':'PRIVATE-SYNTHETIC'},{'sender_id':'SYNTHETIC-RAW'}):
        with pytest.raises(ValueError):make_review(request,{**approval,**extra},tmp_path/'bad.json')
    (request/'review.json').write_text('{}')
    with pytest.raises(ValueError,match='DIGEST'):make_review(request,approval,tmp_path/'bad.json')
