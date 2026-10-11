# Exact rollback boundary

Development harness: foreground command ends; callback unregister and Store close are in finally. ./rollback.sh only reads its own sanitized closure receipt; it cannot kill processes or touch a real registry. SIGKILL recovery reopens the same private Store and deduplicates already committed observations.

Future real binding: audited unregister(registration_id) -> registry_probe absent -> observer.close -> verify host health + source/config fingerprints unchanged. If unregister fails, report UNLOAD_NOT_PROVEN; do not clear registry, monkey-patch core, restart or delete another plugin. Without the audited shim, automated real rollback is BLOCKED_API_EVIDENCE. Do not install.

Never delete runtime evidence to hide UNKNOWN. Authority owner/memory authority unchanged. No Action/Grant/production budget is created by this kit.
