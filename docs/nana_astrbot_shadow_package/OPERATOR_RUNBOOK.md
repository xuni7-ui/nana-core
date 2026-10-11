# Operator runbook — preparation, not an executed real reload

1. Transfer one reviewed archive manually. Verify checksum; unpack to an independent directory. ./observer.sh verify; ./observer.sh preflight.
2. Optional development engineering-only rehearsal: ./observer.sh harness; repeat once to prove dedup/identity; ./rollback.sh; ./observer.sh collect. This is C, not real AstrBot dispatcher.
3. Nana audit652a72f is now available. astrbot_shim.py supplies the smallest source-backed lifecycle registrar, to wire into Nana existing plugin explicitly. Message-stream RealAstrBotBinding remains disabled. No unknown symbol invocation. Lifecycle C is not dispatcher A.
4. New-plugin load is still blocked: reload(name) does not discover an unregistered directory; prove an already-authorized full-load channel first. A single Dashboard reload click is NOT an established solution. After separately authorized host install: if the user already has a browser Dashboard session, the USER manually performs the minimum audited plugin load/reload/unload. Codex does not read/find/create JWT or call the API. Watcher is not assumed available.
5. Nana records real registry -> isolated internal dispatcher -> metadata callback -> Core -> duplicate/barrier -> unregister -> health/zero-drift evidence. No private message body/Iris row/model API read is required.
6. Review and pin the sanitized real receipt in PROJECT_BRAIN/source; run verifier. C is never sufficient for host_binding=VERIFIED.

Schema tooling requires an explicitly reviewed frozen SQLite metadata source with no active WAL/SHM/journal: ./observer.sh schema-only --frozen-path /reviewed/frozen.db --kind l2 (or kg). It never reads application rows/defaults. Native L1/profile compatibility and real Iris remain UNKNOWN. Creating a production data snapshot is not authorized by this runbook.
