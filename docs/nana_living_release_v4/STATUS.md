# Living V4 — current development delivery and host gates

**Current continuous work after153196b:**402 code adds scoped archive claim
conversion, actual sampled-frame/H1 integration, original-C Bilibili selection
and native background metadata subscription. See IMPLEMENTATION and
evidence/continuation-402. New full image and unified task acceptance are still
in progress; the c8/401 delivery and measurements below are the last sealed
release, not evidence for this unsealed working source.


[实测/文档，2026-10-29] **Development-qualified V4 candidate, ready for host
reconciliation; product acceptance remains PARTIAL. First-Life NOT_READY;
Beta NO.** Continue `dev/nana-core-living-release-v4-codex`, executable source
`c8aa8c986219199d0d027ccce0791788516e9d85`, retaining `af584900` and the complete
`435ca7a` ancestry.
The earlier `13ddd48` business-code pin no longer describes this candidate.
The frozen Master/Matrix and inherited 61/63 criteria are unchanged. This work
extends S2/S3/S4/S5/S6/S7/S8 and the Platform/Governance axes; development evidence
does not grant formal-host, human-use or Advanced Growth qualification.

Current evidence: [final-401](evidence/final-401/),
[qualification](qualification.json), [deployment](DEPLOY.md) and the single
[host task card](HOST_TASK_CARD.md). The full prior status is archived below.

## Implemented and exercised in this candidate

| Capability | Actual connection and evidence | Remaining boundary |
|---|---|---|
| Provider durability | Host-local AES-256-GCM vault, native HOST_ADMIN CAS bind/rotate/revoke, original secret-reference route; actual BFF SIGKILL restores binding. CredentialEpochFD2 invalidates running-child future selection/cache after revoke/rotation; shared-reference revoke disables dependent profiles. | No paid provider call in this V4 run. Explicit runtime opt-in/budget still required; bind/rotate requires Core restart. Dispatched calls are not cancelled. Vault protects neither root/service UID nor theft of key plus ciphertext. |
| Speech/history and shared life | Opted-in speech history and body-free pending receipts reuse original Store; restart/readback/withdrawal and binding scope/entity/privacy/watermark gates exercised. Original C-approved sharing candidates project to Web/Android. | Atomic API v2 replies; no token stream. Cards have delivery NONE. Background notification delivery is not implemented/qualified. Physical phone ASR/TTS and naturalness NOT_RUN. |
| C causal continuity | Original C attention/need/provenance defects fixed, with complete source ancestry and withdrawal. Controlled software ablation: two baseline failures become passes on current code. | Software ablation is not model ablation or proof of human feeling, open semantic generalization or long-term companionship. |
| QQ/Bilibili adapters | Original C → Manager → Grant/DeliveryAdmission → Kernel → independent Verify; exact canonical activation binding without changing approval digests. Bili NAV account binding; execution reserves 3 requests, Verify 1. Synthetic loopback exercises send/verify/restart/UNKNOWN paths. | Real account/event/send/cutover NOT_RUN. Frame acquisition, full autonomous selection and actual watching/comment/DM life are not complete. Synthetic social effects are not platform delivery. |
| Legacy history | Full selected-source freeze, immutable archive/index, search, withdrawal and pinned batch-review plans; synthetic archive tests pass. | Private data not read. RealMemoryIngress import executor remains disabled and unimplemented; approval alone cannot enable real import. Archive is not a second Subject Store. |
| Identity/runtime/recovery | Current c8 image runs UID999; actual DEV SIGKILL/recreate epochs 2→3→4 and B8 same-ID recovery/revoke pass again. Original Store/Loop/authority and schema13/PRECISION_V2 retained. Guarded vault bindings require FD2-compatible runtime metadata; restart/rollback reject incompatible targets before stopping a healthy Core. | Empty-vault legacy offline and ordinary memory-only FD1 remain supported; guarded credentials never downgrade to plaintext. Formal cloud is unobserved. bwrap remains BLOCKED, with no unsandboxed fallback. |

One public Bilibili search was attempted: HTTP200 / API code0, then parsing failed
on a mixed invalid row. The parser now skips invalid rows; there was no second
public read. The first failure is retained. This is not a successful real search
qualification or evidence of viewing a video.

## Matched release and validation

| Artifact | Current identity |
|---|---|
| Core | 265 files; two offline builds identical; SHA256 `c562b41aada49a48736269e29c8f07487f07b7b15c2694d75356541562c7d92c` |
| Image | `sha256:4dcf4cd458ee4f1fc629c350d2f437eb2615b45bcd86373188df4a13840b7c97`; Debian13, SQLite3.51.3, OpenSSL3.5.7, cryptography50 probe PASS; five retained SDK prefixes: 13ddd48/3665d39/dbfb37e/af584900/c8aa8c9 |
| Web | SHA256 `8c8e50508fe95b213c80b241f86dd41049d641990e12d79836af170ca011d59a` |
| Android | 4.0.1-debug / 401; 4,728,727 bytes; SHA256 `7f8cb5c0e9ef76eca1169692f4f6acd706697182f229eb15d91e7abb4cf3e926`; original appId and signer `b2fec5a0…63016ec41`; actual build 28s |

Matched bundle: repository `NANA_CORE_LIVING_V4_RELEASE/`; its manifest must name
source `c8aa8c986219199d0d027ccce0791788516e9d85`. APK remains the unchanged
af584900 native/UI build at `/mnt/data/nana-space-4.0.1-debug.apk`; this server
hardening requires no additional APK download.

Current-image install/repeat/corruption qualification **PASS**:6,935 entries,
zero pyc, read-only0555, all five private SDK bindings verified. First install
returns READY_FOR_SWITCH without a Subject or production change. Repeat install
has zero persistent changes and identical full-tree content/metadata digest
`ec955e9e58a861d74418125ca8ac25513bc53b06ab0659312cf2401cb4305653`
(access time excluded). Deliberate corruption in the owned DEV slot reports the
exact missing `core-releases/c8aa8c9…/src/nana_core/clock.py`, expected SHA,
actual null and no repair. Evidence: install-c8-first/install-c8-repeat/
sealed-c8-corruption in final-401. The former af4804 receipts remain scoped history.
Current Operator code checks configured and persisted-active SDK aliases, exact
UID, integrity and state inside the candidate runtime before staging or trusting
READY. Incompatibility returns `HOST_CONFIGURATION_REVIEW_REQUIRED`; actual host
compatibility remains unknown.

Current focused provider/recovery/controller hardening: **227 PASS / 42.90s**.
Earlier af584900 affected Python suite: **325 PASS / 95.12s**. Earlier af584900
frontend/browser evidence, on unchanged native/UI source: **53 unit tests PASS**,
TypeScript/build PASS. Browser: 48 PASS and four old UNKNOWN-assertion failures;
the four corrected assertions rerun PASS / 7.7s, without weakening the no-POST
assertion. Actual authenticated DEV TLS BFF/Core browser: **8 PASS / 27.6s**.
These are scoped executions, not a unique combined test total. Full unrelated
regressions were not repeated. First failures remain evidence.

A first 300s af584900 DEV life qualification **FAILED** before dispatch with
`REALIZATION_HANDS_EXECUTION_CONTEXT_CHANGED`: 12 successful actions / 3 goals,
below the unchanged required 42 / 12. The context guard, probe and qualifier are
byte-identical to `435ca7a`; the exact changed context field is UNKNOWN. A separate
forensic run on unchanged af584900 source then completed **300.163s**, with 42
successful actions / 12 goals / 14 owned effects, zero context changes/rejections,
actual SIGKILL recovery, backup-delete propagation and B8 restoration PASS.
It preserved all assertions and used observation only. This qualifies that
controlled af584900 path; c8 changes provider/secret/Supervisor/controller code,
with owned C/Hands business unchanged. The first failure is retained without
reinterpretation. Neither short run is the original formal 24h qualification.

## Product gates and consolidated next action

The formal Subject `8acff4fb-2532-4a97-a4b7-e59e2ae2f797`, cloud HEAD `30845fb`
and local hotfixes are **USER_REPORTED / NOT_ATTESTED**. This environment has no
safe host/VPN/secret binding. No Genesis, production switch, private-data read,
real social send or paid provider call occurred in this V4 work.

The host operator can now reconcile read-only metadata, source hashes and
hotfixes, then prepare the matched slot with the supplied four-mode deploy tool.
Only after the existing approval may it switch the existing Supervisor/Subject;
retain the old QQ writer and recovery path meanwhile. See the task card for one
consolidated request covering the actual switch, bounded PUBLIC/PROJECT provider
wallet and secure binding, selected private archive preview, and platform Grants.

This is not all CODE_COMPLETE: real private-memory import, frame-based viewing,
full autonomous Bilibili selection and background delivery retain code gaps.
Actual provider dialogue, ten-message continuity, phone pairing/speech, human
review, formal same-Subject 24h/cross-day life, real platform effects and B1 PC
backup remain NOT_RUN. No evidence supports an AstrBot/OpenClaw superiority claim.

## Historical snapshot — 435ca7a / Android 4.0.0 (superseded)

The following is the preserved earlier delivery record, including its old source
pin, memory-only-vault limitation, artifacts, counts and pending gates. It is not
the current candidate's qualification; see [archived machine snapshot](evidence/qualification-435ca7a.json).

<details>
<summary>Expand the complete prior STATUS</summary>

# Living V4 — actual delivery and remaining product gates

GLOBAL_STAGE H / Advanced Growth. **Integrated development release delivered;
V4 product acceptance remains PARTIAL.** First-Life NOT_READY; Beta NO.
Runtime source: `13ddd484156f8216dabd1d339f0bba696f801dab`. Later delivery commits
contain qualification tools, documents and artifacts; business code matches
this pin. Frozen Master/Matrix bytes and61/63 criteria remain unchanged.

## What works in this delivery

| Capability | Source | Actual connection | Formal Subject | Frontend | Restart | Actual evidence |
|---|---|---|---|---|---|---|
| S1 identity/lineage | inherited | original Runtime | host not accessed | existing binding | DEV PASS | SIGKILL, recreate epochs2→3→4; B8 same ID, old source fenced |
| S2 Memory/Person-Self | reused | explicit retention to original service | not observed | per-turn consent, source/withdrawal | controlled PASS | persisted relationship convention recalled on another topic after restart; withdrawn support removed |
| S3 affect/relationship | inherited, unchanged | same C cycle | not observed | source-backed social rhythm only | inherited | no new affect/relationship Store; no subjective-feeling claim |
| S4 living Runtime | reused | actual image/Supervisor | not deployed here | real bootstrap/readiness | actual DEV PASS | original ten APIs, gateway/owner separation, stop latch and crash recovery |
| S5 cognition/World | reused | Router→session→World→Concern→C | live model NOT_RUN | actual model-route metadata | original recovery | synthetic transport plus one real public metadata HTTP read; no paid model |
| S6 judgment/planning | inherited | original C/Planner | not observed | goals/concerns projections | inherited | Precision subset passed; no new planner/authority |
| S7 Hands/Verify | inherited | original bounded ports | no real effect | original restricted controls | original semantics | no user-device/production/social action performed |
| S8 learning | inherited | original experience/lesson path | not observed | actual learning projections | original | domain learning and counterexample/transfer contracts retained; no developer change counted as Nana learning |
| S9 skills | inherited | original qualification | bwrap BLOCKED | actual status | fail closed | no fallback to unsandboxed code; other capabilities unaffected |
| S10 deep change | inherited partial | no authority modification | NOT_RUN | no new execution authority | lineage preserved | isolated candidates differ from authoritative self-modification |
| Provider configuration | integrated | real BFF/owner commands/CAS | host gate pending | native memory input; models/routes | Core restart supported; BFF restart needs rebinding | original budget/privacy intersection; source refs only; no plaintext persistence |
| Bilibili | partial | bounded public read plus original source pipeline | not connected autonomously | existing surface projection | sourced records survive | metadata/search transport; synthetic semantic chain and withdrawal. Full watching, interest-led account loop/comments/DM are incomplete |
| QQ/Iris history | inherited adapters | shadow/offline migration contract | not switched/imported | status only | original provenance | no real writer switch, private import or social send |
| Speech | new native code | local on-device ASR/local Chinese TTS | no extra model | explicit mic/read/stop | cleanup on pause/unmount | APK compiles; physical speech service/permission qualification NOT_RUN |

This table separates existing code from actual formal use. Formal Subject
`8acff4fb-2532-4a97-a4b7-e59e2ae2f797` and cloud `30845fb`/hotfixes are user
reports, not independent observations. No Genesis was executed here.

## Reproducible engineering results

- Core253 files, two identical offline archives:
  `728ef440fc34ab5c1b821814fae93408ee0b7384c5bad6959d274cb9ec5e5347`.
- Image `sha256:b5e55b2988135a991c3d9ac46b50e7c5fe9b75ce66335eb38e1429895b5fa54c`.
  Complete image gzip331,154,026 bytes in12 bounded parts; combined SHA
  `87866ddc44424276298724bee902ed079e9438035fe81c071d13310c8e2ab9e0`.
- Matched Web SHA `3e6b5c1b3904132dd7b9374fa89128d9c82e177823da973a9c9256577d4f6751`.
- Android4.0.0-debug/400:4,722,261 bytes, existing appId and signer retained.
  Exact APK digest is in `evidence/apk.json` and the handoff manifest.
- Actual final-image mounted interpreter checks passed for all three retained
  Core versions: Python3.12.14, SQLite3.51.3, OpenSSL3.5.7, Pydantic2.13.4, UID999.
- Actual four-mode preparation: check correctly reports NOT_INSTALLED;
  dry-run changes nothing; install seals9,737 entries and passes mounted ABI;
  second install has zero persistent changes. Deliberately removing one owned
  DEV source file returns its exact missing path/hash and refuses repair/switch.
- Actual final-image DEV lifecycle: same identity and lineage across automatic
  BFF SIGKILL recovery and container recreation; consistent quarantined backup;
  original B8 transfer, old-source fencing and grant revocation passed.

Local Docker28.4 uses vfs and the32GiB environment required serialized creation
and explicit DEV disk-headroom waits. Ubuntu/Docker29 cloud is not independently
qualified here. A failed concurrent allocation and the first incorrect Web
digest remain recorded. Only this run's four unreferenced partial clone trees
were cleared after metadata checks; original trusted images/data/evidence remain.

## Validation scope

148 targeted Python tests passed in36.25s. Packaging/stdin/rollback supplement:
4 passed; dialogue/memory/StorageGuard/recovery:10 passed. Some scopes overlap;
these are separate executions, not an inflated unique-test total. Frontend44,
real Core browser8 across1440/360/390/412px and Android native1 passed. Android
build succeeded. Full unrelated repository tests were not repeated, per V4's
deployment-focused instruction. First failures are retained beside final results.

The browser used an actual owned DEV Subject, authenticated TLS BFF and original
Core, not a mocked successful API. It demonstrated real settings/routing writes,
readbacks and receipts, definite pre-dispatch rejection and topic refusal.
Loopback semantic tests exercise original INTERPRET/RENDER and retained sources;
they are SYNTHETIC, not real model or human-naturalness qualification.

## S2 long-term retention

Controlled qualification distinguishes saved, retrieved and source-supported
recall: adopted conventions and retained exchanges survive restart; ordinary
transient text stays out of long-term artifacts; withdrawn sources disappear
from later context. UNKNOWN requests are not replayed after restart. StorageGuard
still gates mutations; no second memory index or authority is introduced.

`evidence/retention-storage.json` records actual numeric DEV DB/WAL sizes, memory,
artifact/cycle counts and integrity checks. It is not a formal cloud measurement.
Growth/hour and real day/week recall remain NOT_MEASURED/NOT_RUN; no short test,
virtual clock or successful retrieval is presented as long-term companionship.

## Additional improvements chosen during implementation

1. **Remember this moment**: one explicit submission can enter original sourced
   Person-Self history; the receipt says whether it was saved. Default remains
   transient, withdrawal follows the existing chain.
2. **Know why chat is unavailable**: route/secret/budget/policy failure is separated
   from an already dispatched UNKNOWN. Actual returned model is shown only when
   a real render receipt supports it. Topic refusal still works without a model.
3. **Source-backed room rhythm**: original SOCIAL_APPETITE becomes a modest room
   cue with source/time, rather than a fabricated mood score or random story.
4. **Local voice without extra cloud cost**: on-device-only ASR/local TTS,
   explicit foreground action and cancellation; unavailable services stay unavailable.
5. **Lower-cost delivery**: identical interpreter aliases save191,579,184 runtime
   file bytes in the new independently sealed image; all old versions remain.
   This is not a claimed global CPU/latency speedup.
6. **Safer one-command preparation**: no Docker CLI required; immutable version
   slots, typed config proposal, exact corruption diagnostics, two-phase ABI check
   and verified-backup-before-rollback. The wrapper preserves credential stdin.

## What remains and the next useful step

The recommended immediate step is read-only reconciliation of the actual live
host/hotfixes using the supplied tool, then one reviewed service-switch approval
with backups and rollback retained. This environment has no safe host/VPN binding.
It must not overwrite unknown production hotfixes or create another formal Subject.

After that, obtain explicit provider budget/safe credential binding for real
dialogue and phone review. The new broker is **memory-only**: BFF/container restart
requires rebinding; durable host-vault integration is incomplete. API v2 replies
remain atomic, not live token streams. Full interest-driven Bilibili video/account
integration, private-history import, real B1 PC backup and real platform cutover
still need their remaining code/environment/authorization. bwrap stays blocked.

No evidence yet supports claiming overall user-experience superiority to AstrBot
or OpenClaw. Source continuity, recoverable state, provenance and precise receipts
are implemented distinctions; real comparative daily-use qualification is NOT_RUN.
Real provider calls0; private data/social sends/production changes0. Human review
NOT_RUN; original5h PARTIAL_EXTERNAL_LIMIT and pending stable long residency are
preserved. This delivery does not upgrade First-Life or Beta.

</details>
