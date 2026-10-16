# C6/C7 + B6–B10: portable personal subject (development)

Status: implementation contract. Base e26288e8ffcc1697b1a1f86b55f304b76d9b04ed.

One identity, Store and SubjectLoop remain authoritative. No D2 work, production
operation, real ingress, model call or automatic push is authorized by this task.

## Reuse and extensions

C6/C7 reuse the existing Relational asset at
67326d195edd0693d41eacc63fcc00e1c3205bd6 (21 source files), including explicit v10
opt-in (zero new tables), typed bootstrap, sourced tendencies, voluntary deference
and existing CommitmentService. Primary-user role is an explicit typed binding;
it is not governance, exclusive companionship, identity or social satiation.
New stores use a neutral Subject bootstrap; existing identities are not rewritten.

B6 Surface envelopes are synthetic-only typed extensions to existing SubjectInput.
Platform/device/activity descriptors are open namespaced data. Authority, privacy,
lifecycle and provenance domains stay closed. L0/L1/L2 are bounded projections,
not storage partitions. Classification precedes payload reads.

B8 is an offline **transfer**, not cloning or distributed migration. Export uses
existing SQLite backup and quarantine. Source writes are retired before a package
is released. The package binds one destination ID, schema/source revision and
content hashes. Import requires a clean private directory, validates before opening,
preserves subject history, restores deletion intents locally, and fences all old
execution authority. Lease PID/boot/instance and host health are excluded; fresh
lease epoch exceeds the exported high-water. Failed transfer stays retired or
quarantined, never silently resumes the source. Privileged raw DB/package clones
are outside this local single-writer boundary; no claim of distributed anti-clone.

B9 descriptors and typed fixture ports reuse the existing cognition contract;
provider registration grants no authority. Embeddings are reconstructible caches,
not memories. Credentials and runtime provider objects never enter the package.

B10 is an in-process application facade, not a server/UI. A client receives typed
views/results; commands enter existing transitions through app-owned controllers.
It never receives Store, OperatorAuthority or governance handles. Future capability
approval/revocation requests remain non-executable proposals.

## Migration and limits

Default C schema remains 7 and D remains 8; v10 is explicit. No new dependencies.
No package loader executes archived Python/pickle, interpolates SQL or extracts
arbitrary paths. Integrity hashes detect corruption, not a malicious authorized
operator replacing both manifest and payload. Real memory ingress stays disabled.
