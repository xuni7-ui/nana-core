# Portable Cloud Runtime & Subject Migration V1 — qualified development bundle

Base `024e22649365560ef57e0f3fa82e41383d95d315`, same development branch
`dev/nana-core-cloud-first-life-launch-v1-codex`. Runtime distribution source pin:
`bfea92cc205b91ad7a3ca8dca4eb7c955b6d57a0`. Final handoff commit also contains the
verification/evidence/runbooks, without changing that shipped runtime source.
GLOBAL_STAGE H; S1/S4 integration + Platform/Governance axes, no new Foundation.

## Delivered artifact

`/workspace/nana-deliverables/portable-cloud-v1/nana-first-life-portable-v1.tar.gz`
(3,000,155 bytes), SHA256:
`228ef80e53ef961a409a651746a207a11a8bc72affe1940998e5c108fec9119a`.
The same directory contains its checksum, trusted stdlib `nana-unpack.py`,
QUICKSTART/MIGRATION/SECRETS/RECOVERY/LIMITATIONS and delivery checksums. Archive
contains214 immutable files including runtime code/SQL, native-compatible hashed
wheels, lock, launcher, configuration guidance, public example materials and docs.
It does not contain a Subject or the current Nana database. Two builds from the
same commit produce the identical archive; timestamps use source commit time.

Tested platform: Debian13 x86_64, CPython3.12.14, SQLite3.53.1, glibc2.41. Supported
V1 installer requires Linux x86_64/CPython3.12 and SQLite>=3.35 with JSON/FTS5;
other OS/library combinations need preflight and are not independently qualified.
ARM64, real external server, production and paid-provider portability NOT_RUN.
No OS packages are installed; operator supplies Python3.12+venv. Text path does
not require ffmpeg. Existing five dependency versions are pinned with exact wheel
SHA256 and installed using --isolated/--no-index/--require-hashes. New dependencies0.

## Actual user interface and implementation map

- `./nana preflight`: host checks without creating/repairing a Subject; missing
  installation/dependency, unsupported platform, corrupt config, wrong schema,
  unsafe socket, live stale owner, retired lineage, grants or DB fail closed.
- `./nana init --fresh`: explicitly new identity, NEW SUBJECT CREATED, no history
  inheritance/overwriting. No auto-init in start/restore on a missing directory.
- `./nana start`, `status`, `health`, `chat`, `inspect`, `pause`, `resume`, `stop`,
  `restart`, `emergency-stop`: original foreground Runtime/private Unix IPC.
  Stop requests pause→revoke→stop and confirms stopped ownership. No daemon,
  second runtime, public HTTP listener or platform-specific brain.
- `./nana backup --output ...`: stopped, deletion-aware, quarantined consistent DB
  +privacy sidecar+checksum/time/identity metadata. **Not a runnable clone**.
- `./nana export --retire-source ...` / `restore`: original lawful B8 source
  retirement, exact destination UUID, checksum/manifest/schema/lineage verification,
  clean destination activation, old Grants revoked. Restore explicitly pauses;
  source remains retired, host config/provider/secret/device handles not inherited.
- `./nana config` / `config --document ...`: existing typed non-secret LifeConfig
  with revision CAS; separately configured provider-command reuses B9 contracts.
  Paid use requires new host permission, explicit live flag and memory-only binding.

`src/nana_core/life/portable_runtime.py` is a thin host CLI around existing
LifeApplication, NanaRuntime, Store, SubjectPackageService and Inspector. Source
and material roots derive from installed location, never cwd or Codex paths.
`packaging/portable` holds stdlib bootstrap/runbooks/owned examples;
`tools/nana_portable_cloud` builds, safely unpacks and qualifies the actual package.
Deprecated Codex bridge/lab/integration entrypoints are not shipped. No operational
Codex absolute path literal remains in the selected runtime. No business SQL/table,
Core identity, decision, Grant, Manager, privacy or migration contract changed.

## Independent installed-host qualification

Final archive was safely unpacked into two clean host-like directories, each with
its own newly created venv and **offline** wheel installation. Child environment
was minimal, without PYTHONPATH/Codex credentials/editable-checkout imports. Every
runtime operation used the installed bundle and an unrelated cwd.

Actual Fresh A and separate Fresh B have distinct identities. A synthetic source
and original C create bounded private intent; one exact owned-example Grant is
installed but no effect executed. A local fake transport produces an explicit
SYNTHETIC UNKNOWN row, not a real provider call. Export retires A; its subsequent
start fails. B imports the bound package, keeps canonical identity and private
state, revokes Grants and preserves UNKNOWN/reservation without retry. Source
identity `1ec9bdc9-7439-45bb-81f6-9608e17468c1` is an isolated qualification Subject,
**not current Nana**. The real received Nana's identity/7request rows/300000
USDmicro reservation/two remaining live slots remain unchanged; no export/start.

B's original runtime actually starts, answers an offline PROJECT surface input,
rejects duplicate startup, deduplicates the same event, restarts with a new PID
and epoch, is SIGKILLed, then fences the dead owner and recovers its stale socket.
Epochs4→5→6, no duplicated effects/requests. Emergency stop confirms exit.
Stopped Inspector leaves DB hashes unchanged and never reveals private content.
Source withdrawal removes private support; official backup applies deletion and
remains quarantined. Same identity, lineage, history support and unknown survive.

Additional installed-process qualification checks echo-disabled PTY with only a
TEST_ONLY canary, memory FD vs disk FD, resolver cleanup, valid schema12 package
rejection before destination creation, corrupt package even with matching outer
hash and a simulated live-but-stale owner. No real credential/provider is used.

## Evidence and recovered failures

Focused28 pass; explicit full repository tests1407 pass/0fail/12skip. The incremental
archive member-count and total decompression guards, with two negative cases,
were added after full collection and included in final focused28; shipped Core
was unchanged during full execution. E12/opt-in real capture remain NOT_RUN. Five JUnit record_property
warnings do not represent failed assertions. Initial collection filename collision
was corrected by a package marker, no test deletion or weakened assertion.

Initial installed candidate generated source __pycache__, so its next checksum
check correctly rejected it. Bootstrap now disables bytecode generation. A first
rehearsal health probe observed the retiring old PID too early; qualification now
requires the newly launched PID, not merely an old healthy socket. All initial
failure summaries remain in evidence; final artifact was actually reinstalled and
requalified. Archive validation is incremental/bounded, no extractall, traversal,
symlink, duplicate/oversize/member-count or occupied-destination escape.

## Limits, remote use and readiness

PORTABLE_CLOUD_BUNDLE_READY YES within declared development scope. Fresh, lawful
same-Subject transfer, known-source/destination writer fencing, safe secret
binding, preflight, Inspector/private state and managed backup/lawful restore PASS.
Remote entry READY as CLI over **existing authenticated host SSH**, no new HTTP,
no public port and no claimed SSH-server deployment. Ordinary backups remain
quarantined; runnable recovery requires lawful SubjectPackage/source fencing.
Lost-source disaster recovery/distributed anti-copy attestation is not implemented.
This does not claim malicious operators cannot copy archives to different hosts.

Default restored host uses included public materials, paused/no Grants; old goals,
skills and device resources need source/current host reevaluation and new exact
permission. Explicit current project-state binding is host-local, not imported
as personality/current truth. Host-local provider configuration, secrets, native
IPC bindings, socket/PID and execution authority do not travel with the Subject.
No arbitrary same-DB copy/parallel activation or stale snapshot rollback is offered.

No actual current Subject/server migration, production/main/R045, private history,
real social/device access, new paid calls, S10 or additional residency. Master and
fixed63criteria unchanged, schema13/43business tables/new tables0/deps0. HumanReview
NOT_RUN; First-Life integration qualified/Beta NO. Stop after this handoff.
