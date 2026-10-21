# Non-secret host-local configuration

Start offline first. `./nana config` shows the complete current LifeConfig. Save a
non-secret local copy with0600, set revision=current+1, keep project_root/material
hashes intact, and explicitly set provider_hosts, remote_privacy=[PUBLIC,PROJECT],
provider_timeout_ms<=15000, provider_calls_per_day/hour, per_provider_calls_per_day,
provider_cost_ceiling_micro, provider_total_calls_limit and
provider_total_reserved_cost_micro according to a NEW approved host budget.
Apply via `./nana config --document /private/life-update.json` (CAS, not last-write-wins).
Do not reuse the development First-Life allowance or credential automatically.

Use `./nana provider-command --document /private/command.json` for each existing
ProviderCommand transition with expected_revision. Initial providers.json revision0.
Example provider command (no credential):

```json
{"operation":"UPSERT_PROVIDER","expected_revision":0,"provider":{"provider_profile_id":"host.provider","display_name":"Explicit host provider","protocol":"OPENAI_COMPATIBLE_CHAT","locality":"REMOTE","base_url":"https://api.deepseek.com","secret_ref":"host.provider","permitted_privacy":["PUBLIC","PROJECT"],"default_timeout_ms":15000,"default_cost_ceiling":50000}}
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
