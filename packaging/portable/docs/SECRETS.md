# Explicit memory-only credential binding

No credentials ship in the bundle. Do not use a chat key, shell history search,
.env, environment variable, shell argument, persistent key file or API-key URL.
Host-local provider configuration stores only opaque secret_ref, endpoints,
model profiles and routes. It is never part of SubjectPackage.

Configure an explicitly approved provider using existing typed provider-command
JSON/CAS transitions. Set host ceilings using `./nana config --document <private-nonsecret-life-json>`;
`./nana config` shows the initial typed host configuration, revision and local paths.
Use revision+1 when updating. Remote privacy must remain PUBLIC/PROJECT; core
privacy, Manager, budget and original UNKNOWN/no-retry gates still apply.
See config/PROVIDERS.md for the concrete non-secret configuration sequence.

For the original opaque reference already configured on this new host:

```
./nana start --live --secret-ref host.provider
```

Only AFTER CREDENTIAL_INPUT_READY_ECHO_DISABLED paste the separately authorized
current credential. It passes TTY→memory pipe→original ExplicitFDResolver; echo
is disabled before read, never argv/env/config/log/Store. Runtime exit clears it.
Without a private TTY it fails closed. A host-inherited memory pipe/socket is
preferred: add `--secret-fd 3`; disk-file FDs are rejected. The host supervisor
provides that FD securely, not a plaintext file or command substitution.

A cold restart requires a fresh explicit binding. No implicit secret lookup,
paid call on startup, model fallback after dispatch, or replay of old rejected/
UNKNOWN calls. Configure exact limits through the existing host config/provider
service; no registry duplication, new Grant or personality change occurs.
