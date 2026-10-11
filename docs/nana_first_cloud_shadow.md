# First host-local Shadow probe

## Truth boundary

Approved Core source: `ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513` (55 files). The operator support package in `tools/nana_host_shadow` is a separate addition, not part of that approved commit. It builds the Core source directly from that Git object, verifies a pinned aggregate SHA-256 and every file before importing. It does not install dependencies into AstrBot or import AstrBot/Iris.

Current result: **BLOCKED_NO_HOST_CHANNEL**. Environment spec 45 has no host capabilities, outbound identities, runtime variables or credential bindings; VPN is unconfigured and TCP grants are empty. No known target was supplied. No login, connection attempt, production source access, private record read or real host probe occurred. One known SSH-config metadata check was permission-denied (UNKNOWN); this does not prove there can never be another host channel.

Final development regression: **291 passed / 0 failed / 1 skipped**. E12 is the only skip. The initial full run had 12 failures and 19 setup errors because the default sandbox refused AF_INET socket creation; its logs are retained. Rerunning with authorized test-network access passed without modifying old tests or Core source. Targeted initial launcher/test setup failures and corrections are separately retained. Public-content requests, real-model calls, production calls and private record/secret reads are all zero for this task. New dependencies and Core SQL tables: zero.

Evidence: `docs/nana_first_shadow_evidence/final_delivery.json`, `final_junit.xml`, `development_continuity.json`, `sigkill_recovery.json`, `package_manifest.json`. The source package archive is 105393 bytes, SHA-256 `84996e143cc5cb3366d0e1598233ea7b07199e87957d7d6ea1bd408633685306`; binary archives and runtime DBs are deliberately not pushed to Git. The committed builder can regenerate a package from the approved Core object plus reviewed support. Its new archive hash may differ if support changes.

This package can perform an **adapter-local** probe on an operator-selected host. It does **not** install an AstrBot message-stream hook. Dynamic hook registration, probe isolation, production service health and production version/schema compatibility remain UNKNOWN. A local probe running on a verified host is real-host engineering evidence; it does not establish that the running AstrBot emitted that event. The report intentionally keeps `FIRST_REAL_CLOUD_SHADOW=NOT_RUN` until separately verified host/binding evidence exists. Do not promote this report to full real AstrBot integration PASS.

The current tools therefore prepare a reversible **host-local adapter fallback**, not the still-unverified running-AstrBot connection. There is no production hook uninstall claim to make: no such hook was installed. No production before/after health or memory authority was inspected; those remain UNKNOWN rather than inferred from fixture results.

## Build without touching production

From the development checkout, with the approved Git object already present:

```bash
.venv/bin/python -m tools.nana_host_shadow.build /tmp/nana-shadow-approved-bundle --repo .
```

The destination must be new. Retain and review the reported manifest hash and support-file hashes. Transfer this directory through an already authorized operator channel into a new independent host directory, without overwriting anything. No remote-transfer command or host address is inferred by this tooling. Source package integrity is pinned; the support manifest is not a cryptographic signature and needs operator review/trusted transport.

## Minimal host-local commands

`HOST_PYTHON` below means an already installed interpreter with Python >=3.12, SQLite >=3.51.3 and Pydantic exactly 2.13.4. These are existing Core constraints, not a reason to upgrade production dependencies. If compatibility is BLOCKED, stop that path. Do not run pip in the AstrBot environment.

Substitute the reviewed package and **new** private data directory:

```bash
HOST_PYTHON -I /opt/nana_shadow/package/nana-shadow preflight
HOST_PYTHON -I /opt/nana_shadow/package/nana-shadow start --workdir /opt/nana_shadow/data --host-instance nana-host --window-seconds 30
HOST_PYTHON -I /opt/nana_shadow/package/nana-shadow start --workdir /opt/nana_shadow/data --host-instance nana-host --window-seconds 0
HOST_PYTHON -I /opt/nana_shadow/package/nana-shadow rollback --workdir /opt/nana_shadow/data
HOST_PYTHON -I /opt/nana_shadow/package/nana-shadow collect --workdir /opt/nana_shadow/data
```

Start is foreground and automatically closes the observer/store at the deadline, at most 600 seconds. For early stop from a second terminal use `stop --workdir ...`, then `rollback --workdir ...`. Stop is a scoped token request; no arbitrary process kill or service command exists. No daemon, socket, boot configuration or global installation is created. The second start verifies persisted identity and redelivery after a genuine process restart.

## Probe and barriers

Only the typed, locally constructed `LocalProbe` with `synthetic=true`, `private=false`, `source=operator_probe`, `external_delivery=false` and the fixed probe ID can enter the temporary observer. Dictionaries/host messages, mismatching flags and stale installation tokens are rejected. The observer has an explicit install/receive/uninstall lifecycle but no host hook registration claim.

The fixed event enters the existing HostObservationAdapter, append-only Evidence and Observation. InitiativeHostGate persists an evidence-referenced GoalCandidate and one local Scheduler job. ShadowBridge stores the proposed Goal/Plan/Decision as draft CLAIMs, not executable goals/plans. A proposed external send is stopped. The persistent Store fence and disabled CapabilityPort are both exercised; kernel proposal, Grant and budget creation all fail SHADOW_BLOCKED. The barrier results are persisted in an audit event. No production owner or memory-authority record is created or changed.

The report compares persisted Evidence metadata with the synthetic legacy-side input metadata, without calling the legacy AI. The stable probe timestamp is saved once; repeated processes do not substitute restart time. Unique Observation, candidate, Scheduler job and barrier audit remain idempotent.

## Rollback and evidence

Normal shutdown unregisters the local observer, closes Store and marks STOPPED before releasing the session lock. Repeated rollback is safe and retains the Shadow DB, identity, probe metadata, reports and package manifest. An actual SIGKILL is recorded as UNKNOWN_UNCLEAN_TERMINATION, never a clean observer-uninstall claim. Because this implementation has no external hook, process death removes its local callback; the next start uses the same Store/identity and verifies the barrier again. No external action is retried.

Collector emits report hashes and identity/session metadata only, not raw DB content. It refuses collection while the runtime is active. Original production health/source/configuration/authority remain UNKNOWN until an authorized host observer proves them; development zero-production calls must not be presented as an actual production before/after fingerprint.

## Iris compatibility probe

Optional, **only** for an operator-provided frozen schema snapshot:

```bash
HOST_PYTHON -I /opt/nana_shadow/package/nana-shadow schema-only --frozen-snapshot /operator/reviewed/frozen-iris.db
```

This performs only metadata queries for `memories`, `nodes`, `edges`; an authorizer denies reads of application rows. It uses read-only immutable SQLite, rejects WAL/journal/symlink/hardlink paths, excludes SQL defaults and never opens JSON/FAISS. Output is UNASSESSED, not production compatibility PASS. Making a snapshot from a live database is **not** implemented or silently authorized by this command. If a safe frozen file is unavailable, retain UNKNOWN and skip. No private database is needed for first startup.

## Remaining shortest path

Provide an already authorized, identifiable host channel or have the operator execute the reviewed bundle locally on the Nana host. First obtain metadata compatibility and proof of that host identity. Use only the adapter-local probe unless a verified restart-free AstrBot API can safely distinguish internal probes from real messages. Do not request API keys, read private messages, restart AstrBot, attach a broad stream or relax barriers to overcome this blocker.
