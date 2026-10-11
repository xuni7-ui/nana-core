# Pre-install (NOT executed by Codex)

- Verify archive SHA256 against the independently supplied receipt; unpack to a NEW independent directory; run observer.sh verify and preflight.
- Preserve approved Core SHA ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513. No global pip, environment changes, source overwrite or startup changes.
- Real install is BLOCKED_API_EVIDENCE at this development baseline. This kit is NOT an auto-discovered AstrBot plugin; copying it into the plugins tree will not enable a hook.
- Nana must supply sanitized exact source audit: AstrBot version/file hashes, plugin manager register/reload/unload, dispatcher entry, registry access, callback return/no-response semantics, temporary callback removal, strict internal probe isolation.
- Confirm production container's SQLite/dependency compatibility before same-process Core. Never run bootstrap private-extension module replacement inside AstrBot. Private runtime belongs only to the short-lived foreground engineering harness. Do not install a permanent second runtime.
- Host private messages default DROP. Flags in message text are not a permit. No body getters, repr, serializer, JWT, Dashboard API or network.
- If registration requires restart, stop: BLOCKED_RESTART_REQUIRED. If synthetic isolation unavailable, do not attach a message stream.
