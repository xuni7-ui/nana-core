"""Operational resource offer, not motivation or a grant. Estimates stay labeled."""
from ..contracts import DTO
from .contracts import DAY

class ResourceState(DTO):
    derived: bool = True
    accounting: str = 'CONSERVATIVE_RESERVATIONS_NOT_PROVIDER_BILLING'
    calls: int
    reserved_bytes: int
    actual_input_bytes: int
    actual_output_bytes: int
    reserved_estimated_cost_micro: int
    actual_cost_micro: int
    background_reserved_bytes: int
    byte_limit: int
    estimated_cost_limit_micro: int
    pressure: str
    unresolved_calls: int
    max_observed_latency_us: int | None
    unknown_cost_calls: int = 0
    external_execution_authority: bool = False


def resource_state(store,config):
    day=store.clock.utc_now_us()//DAY*DAY
    rows=store.db.execute('SELECT * FROM runtime_cognition_calls WHERE started_at_us>=?',(day,)).fetchall()
    living=config.living
    world=store.db.execute('SELECT * FROM cognitive_requests WHERE created_at_us>=?',(day,)).fetchall() if store.schema_target>=13 else []
    rb=sum(r['reserved_bytes'] for r in rows);cost=sum(r['reserved_cost_micro'] for r in rows)
    rb+=sum(r['reserved_bytes'] for r in world);cost+=sum(r['reserved_cost_micro'] for r in world)
    limits=(living.max_model_bytes_per_day,living.max_estimated_cost_micro_per_day)
    pressure='EXHAUSTED' if rb>=limits[0] or cost>=limits[1] or len(rows)+len(world)>=config.max_calls_per_day else 'CONSTRAINED' if rb*2>=limits[0] or cost*2>=limits[1] else 'AVAILABLE'
    latencies=[r['wall_latency_us'] for r in rows if r['wall_latency_us'] is not None]
    latencies.extend(r['latency_us'] for r in world if r['latency_us'] is not None)
    return ResourceState(calls=len(rows)+len(world),reserved_bytes=rb,actual_input_bytes=sum(r['input_bytes'] or 0 for r in [*rows,*world]),actual_output_bytes=sum(r['output_bytes'] or 0 for r in [*rows,*world]),
        reserved_estimated_cost_micro=cost,actual_cost_micro=sum(r['actual_cost_micro'] or 0 for r in [*rows,*world]),background_reserved_bytes=sum(r['reserved_bytes'] for r in rows if r['lane']=='BACKGROUND')+sum(r['reserved_bytes'] for r in world),
        byte_limit=limits[0],estimated_cost_limit_micro=limits[1],pressure=pressure,unresolved_calls=sum(r['state'] in {'RESERVED','UNKNOWN'} for r in rows)+sum(r['state'] in {'CALLING','UNKNOWN'} for r in world),unknown_cost_calls=sum(r['actual_cost_micro'] is None and r['state'] in {'CALLING','UNKNOWN','FAILED'} for r in world),max_observed_latency_us=max(latencies) if latencies else None)


def allocation_reason(store,config,row):
    state=resource_state(store,config);l=config.living
    if state.calls>=config.max_calls_per_day:return 'COGNITION_BUDGET_EXHAUSTED'
    if state.unresolved_calls:return 'UNRESOLVED_PROVIDER_CALL'
    if state.reserved_bytes+l.call_reserved_bytes>l.max_model_bytes_per_day:return 'MODEL_BYTE_RESERVATION_EXHAUSTED'
    if state.reserved_estimated_cost_micro+l.call_estimated_cost_micro>l.max_estimated_cost_micro_per_day:return 'MODEL_ESTIMATED_COST_EXHAUSTED'
    if row['event_type']!='USER_EVENT' and (state.background_reserved_bytes+l.call_reserved_bytes)*100>l.max_model_bytes_per_day*l.background_fraction_percent:return 'BACKGROUND_SUB_BUDGET_PRESERVES_FOREGROUND'
    return None
