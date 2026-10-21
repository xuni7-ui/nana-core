# Recovery and operational boundaries

`./nana status` and `./nana health` identify the current owner; Inspector is read-only.
Failed preflight/start returns START_BLOCKED. Never repair a corrupt config by
silently loading defaults. Keep its failure evidence; restore only a known valid
non-secret host config through CAS. An init typo is not permission to create Nana.

A crashed **dead** owner can be fenced by the original Store/Runtime at startup.
A live PID with stale lease is blocked, never killed or displaced automatically.
An old owned socket is removed only after the original writer lock is acquired.
A foreign regular file/symlink at the control path is rejected. Duplicate startup
is blocked by the original flock/lease; no second process can become a writer.

`./nana stop` requests pause→revoke→stop and waits for confirmed exit.
`./nana emergency-stop` uses the same safe control path. If the receipt or verifier
is missing, keep UNKNOWN and do not resend effects/messages/provider calls. Do not
kill arbitrary PIDs or remove locks to force startup. A machine failure may need
trusted host intervention; this bundle does not grant system-wide privileges.

Stopped consistent backup:
`./nana backup --output /private/checkpoint.db`
The DB, privacy journal and JSON metadata include checksum/time/identity. It is a
quarantined review copy, **not runnable**. It does not grant an independent writer.
For runnable relocation/recovery use MIGRATION.md's lawful SubjectPackage. A lone
backup cannot prove the old host is fenced: do not silently activate it. Disaster
recovery with lost-source authority requires separate lineage attestation; this
release does not pretend to solve distributed split-brain.

Logs: <home>/runtime.log and runtime.log.1, bounded sanitized health/queue metadata.
Foreground output reports lifecycle, never secret/transcript/raw thought by
default. Provider attempt/error/parser metadata remains in the original governed
Store; Inspector's metadata view is read-only. `chat` prints wording only on the
private user's terminal; avoid redirecting transcripts to shared logs.
