"""Read-only operational readiness over original route, policy and reservations.

Zero dispatch, credential resolution, reservation, memory/goal mutation or retry.
READY_LOCAL_GATES means local gates pass, never HTTP/model qualification.
"""

from ..contracts import CoreError
from ..continuity.provider_config import ProviderConfigService, ProviderConfigurationAuthority
from ..continuity.provider_routing import RouteRequest, ProviderSettingsService
from ..presence.contracts import HOUR


def budget(app, snapshot, *, calls=1):
    """Intersect host ceilings using the original immutable request reservations."""
    cfg, store = app.config, app.runtime.store
    now = app.runtime.clock.utc_now_us()
    count, cost = store.db.execute(
        "SELECT count(*),coalesce(sum(reserved_cost_micro),0) FROM cognitive_requests"
    ).fetchone()
    hour = store.db.execute(
        "SELECT count(*) FROM cognitive_requests WHERE created_at_us>=?", (now - HOUR,)
    ).fetchone()[0]
    day = store.db.execute(
        "SELECT count(*) FROM cognitive_requests WHERE created_at_us>=?", (now - 24 * HOUR,)
    ).fetchone()[0]
    profile = store.db.execute(
        "SELECT count(*) FROM cognitive_requests c "
        "JOIN continuity_records r ON r.record_id=c.record_id "
        "JOIN artifacts a ON a.artifact_id=r.payload_artifact_id "
        "WHERE c.created_at_us>=? AND "
        "json_extract(CAST(a.payload AS TEXT),'$.request.route_snapshot.provider_profile_id')=?",
        (now - 24 * HOUR, snapshot.provider_profile_id),
    ).fetchone()[0]
    if cfg.provider_total_calls_limit is not None and count + calls > cfg.provider_total_calls_limit:
        raise CoreError("PROVIDER_TOTAL_CALL_BUDGET")
    if (cfg.provider_total_reserved_cost_micro is not None
            and cost + calls * cfg.provider_cost_ceiling_micro > cfg.provider_total_reserved_cost_micro):
        raise CoreError("PROVIDER_TOTAL_RESERVED_COST_BUDGET")
    if hour + calls > cfg.provider_calls_per_hour:
        raise CoreError("PROVIDER_HOURLY_BUDGET")
    if day + calls > cfg.provider_calls_per_day:
        raise CoreError("PROVIDER_DAILY_BUDGET")
    if profile + calls > cfg.per_provider_calls_per_day:
        raise CoreError("PROVIDER_PROFILE_DAILY_BUDGET")
    return {"reserved_calls_total": count, "reserved_cost_micro_total": cost,
            "calls_last_hour": hour, "calls_last_day": day,
            "minimum_calls_for_dialogue": calls, "unknown_reservations_refunded": False}


def provider_readiness(app, *, privacy="PROJECT", operation="COGNITION"):
    result = {"operation": operation, "privacy_class": privacy, "state": "UNKNOWN",
              "network_calls": 0, "live_check": "LIVE_PROVIDER_CHECK_NOT_AUTHORIZED",
              "qualification": "NOT_ESTABLISHED_BY_READINESS", "dispatch_happened": False}
    try:
        authority = ProviderConfigurationAuthority()
        config = ProviderConfigService(app.home / "providers.json", authority)
        document = config.load()
        result["configuration_revision"] = document.revision
        if not document.providers or not document.models or not document.routes:
            raise CoreError("PROVIDER_UNCONFIGURED")
        if app.router is None:
            raise CoreError("RUNTIME_PROVIDER_UNBOUND")
        from ..presence.resources import resource_state

        result["unresolved_calls"] = resource_state(app.runtime.store, app.runtime.config).unresolved_calls
        if app.session is not None and sum(w.is_alive() for w in app.session._workers) >= 2:
            raise CoreError("PROVIDER_WORKER_BOUND_PRE_DISPATCH")
        snapshot = app.router.inspect(RouteRequest(
            operation=operation, privacy_class=privacy,
            timeout_ms=app.config.provider_timeout_ms,
            cost_ceiling=app.config.provider_cost_ceiling_micro,
            context_limit=app.config.provider_context_tokens,
            output_limit=app.config.provider_output_tokens,
        ), app.policy)
        result["route"] = snapshot.model_dump(mode="json")
        result["budget"] = budget(app, snapshot, calls=2 if operation == "COGNITION" else 1)
        result["state"] = "READY_LOCAL_GATES"
    except CoreError as exc:
        result["state"] = "PROVIDER_UNCONFIGURED" if exc.code == "PROVIDER_CONFIG_UNAVAILABLE" else exc.code
    return result


def provider_settings(app):
    """Project the active runtime resolver, not a fresh resolver-free factory."""
    if app.router is None:
        from .live_api.provider_settings import projection
        return projection(app.home)
    authority = ProviderConfigurationAuthority()
    config = ProviderConfigService(app.home / "providers.json", authority)
    return ProviderSettingsService(config, authority, app.router.factory).projection()
