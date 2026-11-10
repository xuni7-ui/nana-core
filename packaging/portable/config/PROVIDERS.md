# Non-secret host-local configuration

Start offline first. `./nana config` shows the complete current LifeConfig. Save a
non-secret local copy with0600, set revision=current+1, keep project_root/material
hashes intact, and explicitly set provider_hosts, remote_privacy=[PUBLIC,PROJECT],
provider_timeout_ms=120000 (configurable within the original600000ms ceiling), provider_calls_per_day/hour, per_provider_calls_per_day,
provider_cost_ceiling_micro, provider_total_calls_limit and
provider_total_reserved_cost_micro according to a NEW approved host budget.
Apply via `./nana config --document /private/life-update.json` (CAS, not last-write-wins).
Do not reuse the development First-Life allowance or credential automatically.

Use `./nana provider-command --document /private/command.json` for each existing
ProviderCommand transition with expected_revision. Initial providers.json revision0.
Example provider command (no credential):

```json
{"operation":"UPSERT_PROVIDER","expected_revision":0,"provider":{"provider_profile_id":"host.provider","display_name":"Explicit host provider","protocol":"OPENAI_COMPATIBLE_CHAT","locality":"REMOTE","base_url":"https://api.deepseek.com","secret_ref":"host.provider","permitted_privacy":["PUBLIC","PROJECT"],"default_timeout_ms":120000,"default_cost_ceiling":50000}}
```

Then UPSERT_MODEL at revision1, with model_profile_id, provider_profile_id,
remote_model_id (your explicitly selected model), model_version, operations=[COGNITION],
input_modalities=[TEXT],output_modalities=[TEXT],context_limit/output_limit.
SET_CAPABILITY_ROUTE at revision2 uses route.operation=COGNITION,
primary_model_profile_id, fallback_model_profile_ids=[], permitted_privacy,
timeout_ceiling_ms/cost_ceiling/context_ceiling/output_ceiling within Core/host limits.
These are the original strict ProviderProfile/ModelProfile/CapabilityRoute contracts.
No discovery/network call occurs while configuring. Provider/model are replaceable
resources, never Subject identity or execution authority. Secret value is supplied
only at explicit live start as described in SECRETS.md.


## App runtime settings (new source; separately opted in)

A compatible Gateway can expose GET/POST `/api/nana-space/v2/providers/runtime`
when its private HostConfiguration explicitly sets `allow_provider_runtime_budget: true`
and `allow_provider_configuration: true`, and the original launcher already has
`--live-provider-authorized`. Default is off; changing a provider profile or
binding platform credentials does not enable it. The authenticated App/Web user
must have HOST_ADMIN and explicitly consent to paid provider requests. This
repository work does not enable any production host or perform a paid test.

The model page reviews a registered profile/host and host-global hourly/daily/
per-provider call ceilings, context/output settings and internal per-call resource
reservation. Requests within one dialogue are counted separately. Reservation
units are not monetary invoices; fees remain the provider's actual charges.
The original total mission-call/total-reservation caps, timeout, source/identity,
Vault and route/profile privacy constraints remain. Existing private authorization
is preserved; this control adds PUBLIC/PROJECT host permission, not private history.

Saving uses the original life.json CAS and original operation receipt. Apply with
the existing explicit host restart after reviewing current settings; saving never
restarts, resolves a key, tests a model or confirms actual availability. UNKNOWN
uses the original receipt only and never automatically retries, even if updated
settings are visible. A compatible new APK is needed for the two finite native
operations; native source mapping alone is not device qualification.

Defaultfalse is omitted from serialized HostConfiguration for ordinary older
Gateway compatibility. When opting true, retain the previous private host config
for whole-Gateway rollback or use a Gateway that understands this field; no
Subject DB rollback or identity initialization is required. Final release bundles
must match the source and be independently installed before selection in CURRENT.
