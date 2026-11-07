"""Original byte/cost ledger, exact body reservation; no paid model calls."""
from nana_core.continuity.world_loop.cognition import CognitionSession, CognitionRequest
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.presence.resources import resource_state
from nana_core.storage import canonical
from .helpers import fresh, capture, policy


def prepared(session, key, mid):
    rid = session.prepare(key, 'INTERPRET', (mid,))
    row = session.store.one('cognitive_requests', rid)
    request = CognitionRequest.model_validate_json(canonical(session.records.read(row['record_id'])['payload']['request']))
    return rid, row, request


def test_actual_wire_body_is_identical_and_byte_reservation_covers_response_probe(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as runtime, provider_harness() as (transport, state):
        mid = capture(runtime, 'source', {'data': 'SYNTHETIC 虹光🙂 and quoted "evidence"'})
        session = CognitionSession(runtime, transport, policy())
        rid, row, request = prepared(session, 'measured', mid)
        old_body = {'model': transport.model_id, 'stream': False,
                    'messages': transport.messages(request), 'max_tokens': request.budget.output_tokens,
                    'response_format': {'type': 'json_object'}}
        body = canonical(old_body).encode()
        assert transport.request_body(request) == body
        assert row['reserved_bytes'] == len(body) + transport.response_bound(request) + 1
        legacy = len(request.model_dump_json().encode())*2+16384+transport.response_bound(request)
        assert row['reserved_bytes'] < legacy
        assert resource_state(runtime.store, runtime.config).reserved_bytes == row['reserved_bytes']
        assert session.execute(rid)['state'] == 'PROPOSED'
        actual = runtime.store.one('cognitive_requests', rid)
        assert actual['input_bytes'] == len(body) and state['calls'] == 1
        assert actual['input_bytes'] + actual['output_bytes'] <= row['reserved_bytes']
        assert actual['reserved_cost_micro'] == row['reserved_cost_micro']


def test_changed_serializer_is_stopped_before_dispatch_without_refund_or_retry(tmp_path, monkeypatch):
    with fresh(tmp_path/'s'/'self.db') as runtime, provider_harness() as (transport, state):
        mid = capture(runtime, 'source', {'data': 'SYNTHETIC content'})
        session = CognitionSession(runtime, transport, policy())
        rid, row, _ = prepared(session, 'changed', mid)
        original = transport.request_body
        monkeypatch.setattr(transport, 'request_body', lambda request: original(request)+b' '*128)
        outcome = session.execute(rid)
        assert outcome['state'] == 'STALE' and state['calls'] == 0
        assert runtime.store.one('cognitive_requests', rid)['error_code'] == 'WIRE_RESERVATION_CHANGED_NO_DISPATCH'
        assert resource_state(runtime.store, runtime.config).reserved_bytes == row['reserved_bytes']
        assert session.execute(rid)['replayed'] and state['calls'] == 0


def test_legacy_conservative_prepared_reservation_remains_compatible(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as runtime, provider_harness() as (transport, state):
        mid = capture(runtime, 'source', {'data': 'SYNTHETIC legacy request'})
        session = CognitionSession(runtime, transport, policy())
        rid, row, request = prepared(session, 'legacy', mid)
        legacy = len(request.model_dump_json().encode())*2+16384+transport.response_bound(request)
        with runtime.store.transaction('test.legacy_reservation') as tx:
            tx.update('cognitive_requests', rid, reserved_bytes=legacy)
        assert session.execute(rid)['state'] == 'PROPOSED' and state['calls'] == 1
        assert runtime.store.one('cognitive_requests', rid)['reserved_bytes'] == legacy


def test_exact_body_can_fit_existing_byte_ceiling_without_changing_call_or_cost_limits(tmp_path):
    from nana_core.presence.contracts import LivingRuntimeConfig
    with fresh(tmp_path/'s'/'self.db') as runtime, provider_harness() as (transport, state):
        mid = capture(runtime, 'source', {'data': 'SYNTHETIC authorized byte bound'})
        session = CognitionSession(runtime, transport, policy())
        _, row, request = prepared(session, 'measure-only', mid)
        exact = row['reserved_bytes']
        legacy = len(request.model_dump_json().encode())*2+16384+transport.response_bound(request)
        # One reservation is already retained. Allow precisely one more at the
        # original shared ceiling; legacy padding cannot fit that same ceiling.
        runtime.config = runtime.config.model_copy(update={'living': LivingRuntimeConfig(
            max_model_bytes_per_day=(exact*200+89)//90+1024, background_fraction_percent=90)})
        assert exact+legacy > runtime.config.living.max_model_bytes_per_day
        rid, second, _ = prepared(session, 'independent-second', mid)
        assert second['reserved_bytes'] <= exact+1024
        assert state['calls'] == 0  # Neither preflight invokes a provider.
        assert resource_state(runtime.store, runtime.config).reserved_bytes <= runtime.config.living.max_model_bytes_per_day
        assert runtime.store.one('cognitive_requests', rid)['reserved_cost_micro'] == row['reserved_cost_micro']
