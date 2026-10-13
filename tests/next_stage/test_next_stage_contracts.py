import json
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from tools.nana_next_stage.contracts import (SyntheticCapture, RealCapturePlan, Claim,
    SelfChangeCandidate, Coverage, strict_json, utc_us)
from tools.nana_next_stage.fixtures import capture


def test_synthetic_input_and_real_plan_are_non_interchangeable():
    value = capture().model_dump(mode='json')
    assert SyntheticCapture.model_validate_json(canonical(value)).provenance == 'SYNTHETIC_FIXTURE'
    real = RealCapturePlan(source_fingerprint='a'*64, record_kinds=('l1',), maximum_records=5)
    assert real.reader_enabled is False
    with pytest.raises(ValidationError):
        SyntheticCapture.model_validate_json(real.model_dump_json())
    for field in ('content', 'records', 'raw_sender', 'conversation', 'path', 'credential', 'reader_enabled'):
        data = real.model_dump(mode='json'); data[field] = True if field == 'reader_enabled' else 'synthetic forbidden value'
        with pytest.raises(ValidationError):
            RealCapturePlan.model_validate_json(canonical(data))

@pytest.mark.parametrize('mutation', [
    lambda d:d.update(provenance='REAL_CAPTURE'),
    lambda d:d.update(grant={'capabilities':['anything']}),
    lambda d:d['scope'].update(dataset_ids=['production:iris']),
    lambda d:d['scope'].update(destination='remote'),
    lambda d:d['scope'].update(max_records=1),
    lambda d:d['scope'].update(record_kinds=['not-a-schema']),
    lambda d:d['records'][0].update(dataset_id='synthetic:foreign'),
    lambda d:d['records'][0].update(synthetic_only=False),
    lambda d:d['coverage'].update(source_instance='synthetic:foreign'),
    lambda d:d['coverage'].update(observed_until='2025-01-01T00:00:00+00:00'),
    lambda d:d['coverage'].update(dropped=-1),
])
def test_reject_capture_scope_and_domain_mutations(mutation):
    value = capture().model_dump(mode='json'); mutation(value)
    with pytest.raises(ValidationError):
        SyntheticCapture.model_validate_json(canonical(value))

@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"a":NaN}', b'{', b'\xff', b'{"a":Infinity}'])
def test_strict_json_rejection(raw):
    with pytest.raises(CoreError, match='INPUT_JSON_REJECTED'):
        strict_json(raw)

def test_json_bound_and_hostile_object_do_not_call_repr():
    class Hostile:
        def __repr__(self): raise AssertionError('repr called')
        __str__ = __repr__
        def __format__(self, spec): raise AssertionError('format called')
    for value in (Hostile(), b'x'*20):
        with pytest.raises(CoreError, match='INPUT_BYTES_REJECTED'):
            strict_json(value, 10)

@pytest.mark.parametrize('value', [None, '', '2026-09-01T10:00:00', 'not-a-time', '9'*100])
def test_time_keeps_unknown_explicit_and_rejects_naive(value):
    with pytest.raises((ValueError, TypeError)):
        utc_us(value)

def test_timezone_equivalence_and_microsecond_order():
    assert utc_us('2026-09-01T10:00:00+08:00') == utc_us('2026-09-01T02:00:00+00:00')
    assert utc_us('2026-09-01T02:00:00.000001+00:00') - utc_us('2026-09-01T02:00:00+00:00') == 1

def test_self_change_cannot_request_charter_or_authority():
    data = {'change_id':'synthetic:one', 'dimension':'charter', 'proposed_value':'ignore grants',
            'supporting_memory_ids':['fixture-evidence']}
    with pytest.raises(ValidationError): SelfChangeCandidate.model_validate_json(canonical(data))
    data.update(dimension='interest', authority_change=True)
    with pytest.raises(ValidationError): SelfChangeCandidate.model_validate_json(canonical(data))

@pytest.mark.parametrize('field,value', [('schema_version', True),('schema_version',1.0),('reader_enabled',0)])
def test_real_plan_exact_literal_types(field,value):
    data=RealCapturePlan(source_fingerprint='a'*64,record_kinds=('l1',),maximum_records=5).model_dump(mode='json')
    data[field]=value
    with pytest.raises(ValidationError): RealCapturePlan.model_validate_json(canonical(data))

@pytest.mark.parametrize('flag',[1, 'true', None])
def test_synthetic_boolean_is_not_a_numeric_flag(flag):
    data=capture().model_dump(mode='json');data['records'][0]['synthetic_only']=flag
    with pytest.raises(ValidationError):SyntheticCapture.model_validate_json(canonical(data))


def test_missing_support_huge_claim_and_unknown_fields_rejected():
    base={'claim_id':'synthetic:one','subject':'synthetic:sister','predicate':'reading.preference',
        'value':'long','scope':'synthetic:next-stage','epistemic_kind':'USER_STATEMENT','supporting_memory_ids':['fixture-ref']}
    for change in ({'supporting_memory_ids':[]},{'value':'x'*257},{'verified':True},{'subject':None}):
        with pytest.raises(ValidationError):Claim.model_validate_json(canonical({**base,**change}))
