"""Operational resource offer, not motivation or a grant. Estimates stay labeled."""
import json
from ..contracts import DTO
from .contracts import DAY

class ResourceState(DTO):
    derived: bool = True
    accounting: str = 'CONSERVATIVE_RESERVATIONS_NOT_PROVIDER_BILLING'
    calls: int
    reserved_bytes: int
    admission_bytes: int = 0
    background_admission_bytes: int = 0
    byte_accounting: str = "MEASURED_COMPLETE_WIRE_OR_CONSERVATIVE_RESERVATION"
    actual_input_bytes: int
    actual_output_bytes: int
    reserved_estimated_cost_micro: int
    actual_cost_micro: int
    background_reserved_bytes: int
    byte_limit: int
    estimated_cost_limit_micro: int
    pressure: str
    unresolved_calls: int
    unresolved_live_calls: int = 0
    unresolved_terminal_calls: int = 0
    max_observed_latency_us: int | None
    unknown_cost_calls: int = 0
    provider_reported_input_tokens: int | None = None
    provider_reported_output_tokens: int | None = None
    real_usage_reported_calls: int = 0
    fixture_reported_input_tokens: int | None = None
    fixture_reported_output_tokens: int | None = None
    fixture_usage_reported_calls: int = 0
    usage_missing_or_invalid_calls: int = 0
    token_accounting: str = 'UPSTREAM_REPORTED_NOT_BYTES_OR_BILLING;FIXTURE_SEPARATE;MISSING_NOT_ZERO'
    external_execution_authority: bool = False


def accounted_bytes(row):
    """Only a complete, accepted measured exchange settles unused byte allowance.

    Financial reservations/call counts are untouched. UNKNOWN, partial, absent,
    zero, oversize or rejected measurements retain the full original reserve.
    """
    received = row['input_bytes']; sent = row['output_bytes']
    if (row['state']=='PROPOSED' and type(received) is int and type(sent) is int
            and received>0 and sent>0 and received+sent<=row['reserved_bytes']):
        return received+sent
    return row['reserved_bytes']


from ..continuity.accounting import PREFIX,decode_usage_receipt,reported_usage_pair as _reported_usage_pair


def reported_token_usage(store,world,*,legacy_calls=0):
    """Metadata-only projection of accepted original cognition receipts.

    A provider's report is not an invoice or a measured tokenizer binding.
    UNKNOWN/unaccepted receipts retain reservations and missing usage;
    new numeric receipts survive content erasure, legacy reports may be missing;
    local fixture totals can never be presented as commercial model evidence.
    """
    real=[0,0,0];fixture=[0,0,0];missing=legacy_calls
    for request in world:
        saved=store.one('core_meta',PREFIX+request['request_id'])
        if saved:
            value=decode_usage_receipt(saved['key'],saved['value_json'])
            pair=(value['input_tokens'],value['output_tokens']) if value else None
            origin=value['origin'] if value else None
        else:
            row=store.db.execute("SELECT json_extract(CAST(a.payload AS TEXT),'$.reply.origin'),"
                "json_extract(CAST(a.payload AS TEXT),'$.reply.usage') "
                "FROM continuity_records r JOIN artifacts a ON a.artifact_id=r.payload_artifact_id "
                "WHERE r.record_kind='COGNITION_PROPOSAL' AND r.target_id=? AND r.lifecycle='ACTIVE' LIMIT 1",
                (request['request_id'],)).fetchone()
            try:pair=_reported_usage_pair(json.loads(row[1])) if row and row[1] is not None else None
            except (ValueError,TypeError):pair=None
            origin=row[0] if row else None
        if pair is None or origin not in {'REAL_PROVIDER','SYNTHETIC'}:
            missing+=1;continue
        bucket=real if origin=='REAL_PROVIDER' else fixture
        bucket[0]+=pair[0];bucket[1]+=pair[1];bucket[2]+=1
    return {'provider_reported_input_tokens':real[0] if real[2] else None,
        'provider_reported_output_tokens':real[1] if real[2] else None,'real_usage_reported_calls':real[2],
        'fixture_reported_input_tokens':fixture[0] if fixture[2] else None,
        'fixture_reported_output_tokens':fixture[1] if fixture[2] else None,'fixture_usage_reported_calls':fixture[2],
        'usage_missing_or_invalid_calls':missing}


def resource_state(store,config):
    day=store.clock.utc_now_us()//DAY*DAY
    rows=store.db.execute('SELECT * FROM runtime_cognition_calls WHERE started_at_us>=?',(day,)).fetchall()
    living=config.living
    world=store.db.execute('SELECT * FROM cognitive_requests WHERE created_at_us>=?',(day,)).fetchall() if store.schema_target>=13 else []
    foreground=set(x[0] for x in store.db.execute("SELECT c.request_id FROM cognitive_requests c JOIN continuity_records r ON r.record_id=c.record_id JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE c.created_at_us>=? AND json_extract(CAST(a.payload AS TEXT),'$.request.role_input.dialogue') IS NOT NULL",(day,))) if store.schema_target>=13 else set()
    rb=sum(r['reserved_bytes'] for r in rows);cost=sum(r['reserved_cost_micro'] for r in rows)
    rb+=sum(r['reserved_bytes'] for r in world);cost+=sum(r['reserved_cost_micro'] for r in world)
    limits=(living.max_model_bytes_per_day,living.max_estimated_cost_micro_per_day)
    admission=sum(r['reserved_bytes'] for r in rows)+sum(accounted_bytes(r) for r in world)
    background=sum(r['reserved_bytes'] for r in rows if r['lane']=='BACKGROUND')+sum(accounted_bytes(r) for r in world if r['request_id'] not in foreground)
    pressure='EXHAUSTED' if admission>=limits[0] or cost>=limits[1] or len(rows)+len(world)>=config.max_calls_per_day else 'CONSTRAINED' if admission*2>=limits[0] or cost*2>=limits[1] else 'AVAILABLE'
    latencies=[r['wall_latency_us'] for r in rows if r['wall_latency_us'] is not None]
    latencies.extend(r['latency_us'] for r in world if r['latency_us'] is not None)
    return ResourceState(**reported_token_usage(store,world,legacy_calls=len(rows)),calls=len(rows)+len(world),reserved_bytes=rb,admission_bytes=admission,background_admission_bytes=background,actual_input_bytes=sum(r['input_bytes'] or 0 for r in [*rows,*world]),actual_output_bytes=sum(r['output_bytes'] or 0 for r in [*rows,*world]),
        reserved_estimated_cost_micro=cost,actual_cost_micro=sum(r['actual_cost_micro'] or 0 for r in [*rows,*world]),background_reserved_bytes=sum(r['reserved_bytes'] for r in rows if r['lane']=='BACKGROUND')+sum(r['reserved_bytes'] for r in world if r['request_id'] not in foreground),
        byte_limit=limits[0],estimated_cost_limit_micro=limits[1],pressure=pressure,unresolved_calls=sum(r['state'] in {'RESERVED','UNKNOWN'} for r in rows)+sum(r['state'] in {'CALLING','UNKNOWN'} for r in world),unresolved_live_calls=store.db.execute("SELECT count(*) FROM runtime_cognition_calls WHERE state='RESERVED'").fetchone()[0]+(store.db.execute("SELECT count(*) FROM cognitive_requests WHERE state='CALLING'").fetchone()[0] if store.schema_target>=13 else 0),unresolved_terminal_calls=sum(r['state']=='UNKNOWN' for r in rows)+sum(r['state']=='UNKNOWN' for r in world),unknown_cost_calls=sum(r['actual_cost_micro'] is None and r['state'] in {'CALLING','UNKNOWN','FAILED','PROPOSED','REJECTED'} for r in world),max_observed_latency_us=max(latencies) if latencies else None)


def allocation_reason(store,config,row):
    state=resource_state(store,config);l=config.living
    if state.calls>=config.max_calls_per_day:return 'COGNITION_BUDGET_EXHAUSTED'
    if state.unresolved_live_calls:return 'UNRESOLVED_PROVIDER_CALL'
    cap=config.provider_unknown_calls_per_day
    if cap and row['event_type']!='USER_EVENT' and state.unresolved_terminal_calls>=cap:return 'UNKNOWN_BILLING_BACKGROUND_PAUSED'
    if state.admission_bytes+l.call_reserved_bytes>l.max_model_bytes_per_day:return 'MODEL_BYTE_RESERVATION_EXHAUSTED'
    if state.reserved_estimated_cost_micro+l.call_estimated_cost_micro>l.max_estimated_cost_micro_per_day:return 'MODEL_ESTIMATED_COST_EXHAUSTED'
    if row['event_type']!='USER_EVENT' and (state.background_admission_bytes+l.call_reserved_bytes)*100>l.max_model_bytes_per_day*l.background_fraction_percent:return 'BACKGROUND_SUB_BUDGET_PRESERVES_FOREGROUND'
    return None
