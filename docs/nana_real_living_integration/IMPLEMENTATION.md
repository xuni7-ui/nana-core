# H / First-Life Real Living Integration

Advanced Growth S1/S2/S3/S4/S5/S7/S8 + Platform/Shared Life/Governance. Based on
First-Life latest remote a07e906. Independent branch
`dev/nana-core-real-living-integration-v1-codex`. V3 ea1e225 remains a separate UI
line; no apps/nana-space changes and no Host Operator/Docker/genesis implementation
replacement. Master and fixed63 criteria unchanged.

## Concrete integration changes

1. Optional `POST /api/nana-space/v2/providers/commands`, advertised as
   `capabilities.provider_configuration_write`. HostConfiguration must explicitly
   set `allow_provider_configuration=true` (default false), authenticated caller
   must have HOST_ADMIN, and original Origin/CSRF or native Bearer admission still
   applies. Body: original WriteRequest fields + `command` of existing strict
   ProviderCommand (see provider-command.schema.json). Both ledger and configuration
   revisions apply. Existing durable idempotency/UNKNOWN receipts are reused.
   Retry after a missing response is GET receipts/{original-key}, not resubmit.
2. This calls original ProviderConfigService/atomic CAS. A first explicit command
   can create the missing **host config** at revision0; it cannot initialize a
   Subject. Source inspection/new tests found this is a real post-genesis gap:
   provider configuration may be absent while the Subject is already valid.
   Only secret_ref is accepted, never secret value. Live permission, budgets,
   endpoint allowlists and explicit FD resolver remain separate. Save is no model
   call, discovery, qualification or automatic restart. Remote SECRET remains denied.
3. Existing Inspector's source-backed affect metadata now accompanies needs,
   relationship, interests and activities in home. No generated mood label or
   emotion score. V3 can display these existing items without a new UI truth store.
4. `GET .../backup/status` is authenticated derived metadata over the caller's
   own existing BACKUP receipts. No backup bodies/paths/keys. B1 PC delivery,
   schedule and restore remain NOT_OBSERVED/NOT_EXPOSED, never a fake offsite PASS.
5. `living_preflight.py` verifies an explicitly named existing identity/lineage,
   exact schema13, bounded readonly quick/FK checks, socket path and host config.
   Missing providers are a clear configuration gate, not a hidden genesis/init.
   No start, migration, repair, activation or credentials. The original Supervisor
   remains the only lifecycle controller; old-owner/Grant/UNKNOWN fences stay.
6. `legacy_plan.py` consumes bounded explicit **hash-only** output of the existing
   integration.exporter, binds the plan digest to subject/lineage, preserves input
   hashes/time gaps/relationship ambiguity and dedup/conflicts. Reconciliation now
   namespaces record IDs by source, including independently produced envelopes.
   Plans are exclusive0600 output, never overwrite an approval. No import command,
   personal body, old Grant or action replay. Discarding a plan rolls back all its
   effects because no Subject write occurred.

## Existing abilities deliberately reused

- Original Supervisor/Runtime: existing-home start/stop latch, process identity,
  single owner, restart/SIGKILL recovery, pinned Release/precision compatibility.
- Original V2 auth: one-use pairing, native Keystore exchange, refresh/revoke,
  Subject/lineage validation, cookie/CSRF, write generation/idempotency receipts.
- Original provider configuration/router: 9 operations, separate primary/fallback,
  privacy/runtime limit intersection, exact-model mode, no post-dispatch fallback;
  OpenAI transport only where actually implemented. No universal-vendor claim.
- Original C/D/World/Experience/G/I: bounded own activity and rest, source-backed
  judgment/share candidates, BUSY/refusal/withdrawal effects, learned/qualified
  skill lifecycle. This task does not add a second will or change these motives.
- Original exporter/IrisAdapter/LegacyImporter: source/time/summary semantics,
  synthetic rehearsal, replay/collision guards. Their existing synthetic-only
  import contract is NOT silently relaxed for real private history.
- Original B1 freeze/encrypt/send/receive/verify-restored tools, safe-point backup,
  explicit public recipient and pinned private-Tailscale transport. No new daemon.

## Commands / deployment handoff (not executed on cloud)

Use a qualified Python3.12 + SQLite>=3.51.3. From the checkout, `PYTHONPATH=src`:

```
python tools/nana_first_life_android_v2/living_preflight.py --home EXPLICIT_HOME --subject-id EXISTING_ID --lineage-binding EXISTING_DIGEST
python tools/nana_first_life_android_v2/legacy_plan.py --bundles HASH_ONLY_EXPORTS.json --binding EXPLICIT_BINDING.json --output NEW_REVIEW_PLAN.json
```

The binding uses original Binding fields; plan output declares privacy import
UNAUTHORIZED. Preserve separately authorized declared data classes, retention,
source ownership and exact digest for a later private import approval. Hashes are
still metadata and do not waive private-source authorization.

For provider setup use existing `provider-command` CLI or the optional new HTTP
command. Core maps COGNITION/VISION/STT/TTS/EMBED and other existing operations;
ASR/audio/embedding remote adapters not already implemented are not magically
qualified. Host supplies FD/Resolver at runtime after separate model consent;
no ambient env/key/history search or plaintext vault/config persistence is added.

New module is added to the exact portable allowlist. A new pinned release is
required for these new endpoints; old qualified image0d842676 stays unchanged.
Do not add a flag to an old image and pretend it contains new code. Host Operator
can review/update the Core release through the existing release integrity gate,
not replace the private Python/SDK or change production in this development task.

## CotEX interface handoff

V2's existing fields/ten page enum/commands remain stable. Additive home affect
items and capabilities are safe for existing consumers. Optional provider command
schema and backup.status are server extensions. V3's existing native allowlist
DOES NOT yet include these two operations: CotEX must add explicit finite native
mappings and matching authorization tests before enabling native write controls.
Never enable an arbitrary URL/path bridge or place a Provider key in React.
Web same-origin adapters can use them only when the advertised host capability and
session role permit; configuration responses return actual revision, not a toast.

Model returned ID/usage, rich readable life narratives, multimodal upload,
private-memory commit and human dialogue are not supplied by these extensions.
