# NANA-MAINLINE-C6C7-B6B10-V1 — implementation and offline qualification

Branch: `dev/nana-core-c6c7-portable-subject-v1-codex`.
Exact base: `e26288e8ffcc1697b1a1f86b55f304b76d9b04ed`.
Local implementation commits: `e0f97a3`, `d3cf192`, `0eb4017`, `ec0f247`.
The final containing documentation commit identifies this delivery; no self-hash.
**No automatic push. No D2 implementation. No production/host operation.**

## What is reused

The 21 business-source files of Relational assets at
`67326d195edd0693d41eacc63fcc00e1c3205bd6` are reused rather than recreating C6/C7.
Their bootstrap/tendency/social-appetite/tradeoff/voluntary commitment implementation
continues to use the one SubjectLoop, RecordService, MemoryService, deletion graph,
CommitmentService and existing Scheduler. Prior long soaks/recovery reports are
not imported as new evidence. Existing regressions are retained.

C6 adds explicit `role_kind=PRIMARY_USER` to a versioned RelationalAnchorSpec.
`primary_user_view` only projects that role; conversation volume, model output and
role-label text cannot assign it. SubjectBootstrapAuthority is app construction,
not OperatorAuthority/Manager/Grant, never given to a model/frontend client.
Changing the primary user requires a new exact revision and source declaration.
Anchors are nonexclusive; social_appetite has no anchor/entity argument.

C7 foundation: typed initial tendencies are light source declarations, not a
permanent priority order. Independent observed support/counterevidence forms
PERSONALITY_TENDENCY through existing Growth. Self narrative is a derived view,
not identity/policy or an LLM-written charter. A strong conviction can decline an
ordinary restraint request while a supported relational bond can justify accepting
the same finite request; desire remains and indefinite control can be negotiated
or declined. No `if subject/user name` behavior branch.

Fresh identity accepts optional typed `IdentityBootstrap` instance data (name,
expression, synthetic provenance); neutral default Subject/unspecified. Existing
identities cannot be rebootstrapped and are not renamed by upgrade.

## Module map and contracts

| Area | Permanent implementation | Input → output / authority |
|---|---|---|
| B6/B7 | continuity/extensions.py | Open namespaced platform/surface/device/activity/skill/media/interest/project/perception descriptors; authority/privacy/provenance stay closed |
| B6 | continuity/surfaces.py | SurfaceEnvelope + SubjectInput → existing SubjectLoop cycle; identity/entity/privacy/time must match; stable source key dedup |
| B6 | ContinuityViews | L0 live source/device/cycle refs; L1 recent memory/concerns/commitments/projects; L2 durable narrative/lesson/history refs. Same canonical Store, bounded, filtered before payload read |
| B8 | continuity/portable.py | Official managed backup → three-file hashed package → clean quarantined import → explicit trusted activation |
| B9 | continuity/providers.py | Provider/model descriptors; existing cognition session; fixture media proposals; disposable EmbeddingCache |
| B10 | continuity/application.py | Application-owned services → typed frontend session; no DB/controller handles, no frontend direct authoritative writes |

Surface metadata contains subject, namespaced platform/surface/adapter, nullable
device, entity/conversation/session, event kind, occurred/observed time, correlation,
privacy, synthetic provenance reference and source event key. Core recorded time
comes from the existing subject_events.ingested_at_us, exposed alongside the view.
Real ingress remains disabled; new envelope and memory provenance are synthetic-only.
A new descriptor alone cannot register a Capability or alter an authority enum.

No second ContextAssembler. Frontend assemble_context and provider deliberate use
the existing assembler/DeliberationSession, preserving scope/privacy/destination/
conflict/freshness/budget rules. Models receive serialized data, propose only.

## Offline transfer protocol (actual API)

```python
from nana_core.continuity.portable import (
    PortableTransferAuthority, SubjectPackageService, verify_package)

# App-owned controller; stop/close NanaRuntime and reopen existing Store first.
source_controller = PortableTransferAuthority()
export = SubjectPackageService(source_store, source_controller).export(
    package_path, destination_id=target_uuid, source_commit=build_commit,
    authority=source_controller)
manifest, files = verify_package(package_path, expected_sha256=export['sha256'])

# On another machine: exact app-provisioned destination UUID and CLEAN private root.
destination_controller = PortableTransferAuthority(
    destination_id=target_uuid, destination_root=clean_private_root)
path = SubjectPackageService.import_quarantined(
    package_path, clean_private_root, expected_sha256=export['sha256'],
    destination_id=target_uuid, authority=destination_controller)
# Open ContinuityStore(path, ..., schema_target=manifest.source_schema), inspect.
SubjectPackageService(restored_store, destination_controller).activate(
    transfer_id=manifest.transfer_id, destination_id=target_uuid,
    authority=destination_controller)
# Close maintenance Store. A new NanaRuntime now acquires a higher lease epoch.
```

Preconditions: no active lease, in-flight cognition, unresolved possible effect or
held budget. Unknown host metadata is rejected. Source retires BEFORE archive is
published and cannot resume normal transactions or acquire a lease. Failure after
retirement leaves it retired; retry export only for the same target/source commit.
Never restore source authority as an automatic rollback.

Archive contains exactly subject.sqlite, privacy.json, manifest.json; fixed entry
names/timestamps, bounded sizes, no code/pickle extraction. Expected outer SHA and
per-file hashes are checked, duplicate/extra/symlink entries rejected; schema SQL
fingerprint is compared against local supported migrations. Identity/revision/
source cutoff/transfer/destination are checked before activation. Content hashes
are integrity checks, not signatures against a malicious authorized packager.

Identity, subject history, evidence, memory, primary binding, commitments, projects,
preferences, reflections/lessons and their causal refs remain in the same DB.
Transient lease/PID/boot/health and live runtime handles do not migrate. Privacy
journal exports opaque erasure intents only; local backup paths are reconstructed.
Old grants are revoked and budget limits reduced to spent on explicit activation;
historical authorization events remain history. Offline execution fence stays.
Fresh lease epoch exceeds the exported high-water. Migration preserves identity;
SubjectForkProposal is reserved/unsupported and cannot activate another lineage.

This protocol requires a trusted fixed destination controller/root. It is not a
distributed consensus/anti-copy mechanism. Root/raw DB or archive clones, whole-disk
rollback or an operator constructing a second independent destination controller
remain outside this boundary. The deletion intents are current at export cutoff;
older detached archives cannot discover future erasures on another offline machine.
They must be handled as stale backups requiring current deletion-journal review,
not automatically reimported into a second root. No global erasure claim.

## Provider/media/embedding and frontend

ProviderDescriptor covers identity/version, modalities, operations, context/output
limits, local/remote privacy, tool-proposal support and cost/latency tags. Ports:
cognition, embedding, vision, image generation, STT, TTS, audio understanding/audio
generation and video understanding. V1 invocation is deterministic LOCAL_FIXTURE
only; LOCAL/REMOTE descriptors do not authorize real execution. No new SDK/secret.

MediaSession filters source headers before reading, verifies exact source refs,
canonical proposal/output bounds and post-call freshness. It does not write
Evidence or execute generated output. Embedding cache metadata includes provider,
model/version/dimension/index-format/source token/rebuild token. Swap/change/erase
requires rebuild; vectors are process-local and excluded from packages. No claim
of real multimodal quality or E12.

Frontend views: SelfFrame, LivingSelfState, relationship/primary user, tendencies/
narrative, memory summary, goal/commitment/project refs, runtime health, providers,
live/recent/durable continuity. Send input/propose goal goes through SubjectLoop;
forget through MemoryService; primary user through explicitly enabled trusted
bootstrap controller. Settings are finite presentation-only session settings.
Capability approval/revocation hooks only return non-executable review proposals.
Python private attributes are not a hostile-code sandbox; future remote adapters
must enforce authentication and construct a narrow FrontendPolicy server-side.

## Schema, tests and limits

Explicit development10 reuses existing 39 business tables (zero added). It extends
existing record/assertion CHECKs and request-dedup index through the reused asset.
C default7/D default8 remain unchanged; migrations7/8/9→10 preserve identity and
foreign keys. Production migrations NOT_RUN/NOT_AUTHORIZED. New dependencies=0.

Targeted: `.venv/bin/python -m pytest tests/portable_subject -q`: **17 passed**.
Fourteen logical checks include three distinct migration paths, two separate
packages, primary/deference/appetite independence, cross-surface dedup/privacy,
old-authority fencing, erasure/replay, provider/media/cache and frontend closure.
No new long soak or repeated standalone crash matrix was added.

Full regression: `.venv/bin/python -m pytest -q tests`: **928 passed / 0 failed /
1 skipped (E12), 90.73 seconds**. The configured-directory regression (`pytest -q`)
was 455 passed/1 skipped in 53.65s; it is explicitly not the full repository count.
No business source changed during/after the final full run.
Runtime: CPython3.12.14 / SQLite3.53.1 / Pydantic2.13.4; SQLite gate≥3.51.3 retained.
E12=NOT_RUN; real models/private data/external actions=0. Real memory ingress=NO.
main/R045/FIRST_REAL_ASTRBOT_SHADOW and production unchanged. No push.

Not implemented: live/distributed migration, forks, encrypted export/signature
key management, remote frontend authentication/server/UI, actual provider SDKs,
real media/embedding quality, full narrative personality development or D2 work.
Next mainline recommendation: D2–D7 Living Runtime, requiring a separate task;
this delivery stops at C6/C7 foundation + B6–B10.
