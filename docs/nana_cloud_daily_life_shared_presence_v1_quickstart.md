# Cloud daily life — development entry

Use the repository's existing `.venv`; no install, credential, AstrBot, account,
GUI session or production service is needed. These commands affect only your
explicit fresh development directories. A source-backed reference Subject uses
real owned application effects and shadow conversation surfaces. This is not a
qualified natural-language companion or a production deployment.

## Try the actual runtime

Keep an owned target application alive in one terminal:

```bash
.venv/bin/python -c 'from pathlib import Path
import time
from nana_core.continuity.hands.host import OwnedApplication,daily_tasks
with OwnedApplication(Path("/tmp/cdl-owned-target"), tasks=daily_tasks()) as target:
    print(target.profile, flush=True)
    time.sleep(10800)'
```

Initialize once in a second terminal, then run the original foreground CLI:

```bash
.venv/bin/python -m nana_core.life init --home /tmp/cdl-life \
  --project "$PWD" --demo-materials --daily-life --timezone Asia/Shanghai \
  --owned-application-profile /tmp/cdl-owned-target/application/profile.json \
  --allow-local-artifacts --allow-local-skills
.venv/bin/python -m nana_core.life run --home /tmp/cdl-life \
  --seconds 10800 --headless --control --json
```

`init` explicitly bootstraps one finite four-hour owned-resource Grant. `run`
never renews it. The application profile is host configuration, not authority.
The app must remain alive across Core restart; a replacement app has a different
binding and cannot inherit the old execution permission. bwrap qualification is
required for skills; absence fails closed. No arbitrary shell/dependency install.

Use a third terminal for bounded private local requests:

```bash
.venv/bin/python -m nana_core.life health --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"view","view":"life"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"control","command":"pause"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"control","command":"resume"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"surface","observation":{"binding_id":"qq.shadow","event_id":"project-turn-1","topic":"public-project","text":"只是吐槽，接口名有点长","approved_summary":"This explicit synthetic project concerns API naming.","summary_authorization":"EXPLICIT_PROJECT_SUMMARY"}}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"continuity","binding_id":"bili.shadow","tier":"L1_RECENT"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"backup","name":"checkpoint"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"control","command":"revoke"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
printf '%s\n' '{"operation":"control","command":"stop"}' | .venv/bin/python -m nana_core.life request --home /tmp/cdl-life --json
```

`busy` / `available` use the same control shape. Busy is an explicit availability
signal, not a relationship score. Default presence is PUBLIC only; it does not
silently authorize sharing PROJECT information. `review-share` needs cycle_id
and binding_id and only assesses a shadow candidate, never sends. Ordinary CLI
stdin remains available if `--headless` is omitted. `/life`, `/status`, `/pause`,
`/resume`, `/forget <memory-id>`, `/revoke`, `/quit` reuse the existing commands.

The socket is private, same-UID, and checked against the active lease PID.
Uncertain response after sending means UNKNOWN: do not retry automatically.
A rejected pre-dispatch connection is distinguished from uncertain completion.
Reopen the read-only status/continuity view before making a new deliberate input.
No Grant/model route/manager mutation is exposed by this control endpoint.

A raw message body is volatile. Only an explicitly approved PUBLIC/PROJECT
summary persists, as a user statement with a source—not a verified world fact.
No private chats, accounts or third-party history may be supplied to this demo.
An explicit `forget` request takes `memory_id`; deletion propagates to the derived
summary, context and share support. Already changed external files are not undone.

## Configuration and operations

`life.json` is typed, host-local and CAS-versioned; timezone uses IANA names.
`providers.json` is the existing separate Provider Configuration service. Neither
is a portable personality. Disabled surfaces reject new input, with no change to
Subject authority. Example exact mutation (current config revision required):

```json
{"operation":"surface-enabled","binding_id":"qq.shadow","enabled":false,"expected_revision":1}
```

Configuration write uses temporary file, fsync, atomic replace and directory fsync.
Malformed config fails closed. The runtime is one foreground process; another
instance cannot obtain the same Store/lease. SIGTERM stops at a safe point;
SIGKILL recovery retains original committed decisions and settles their existing
follow-up without rerunning C or blindly resending effects.

The log rotates into at most `runtime.log` and `runtime.log.1`. It contains only
clock/state/queue depth. CLI JSON stdout is a trusted operational projection,
not a public/social endpoint. Restrict or rotate the host's stdout capture too.
Disk pressure pauses future work. Health is process readiness, not Beta approval.
`deploy/development/nana-cloud-life.service.example` is an uninstalled rehearsal
artifact; it requires explicit host paths/user and skill sandbox qualification.
It does not configure a second daemon or auto-restart/regrant.

## Backup and transfer

A running runtime makes consistent backups through its control socket. Stopped
runtime backup:

```bash
.venv/bin/python -m nana_core.life backup --home /tmp/cdl-life \
  --destination /tmp/cdl-review/checkpoint.db --json
```

Backups are quarantined review/recovery material, not runnable clones. Preserve
the associated privacy sidecar and deletion journal. Do not clear quarantine or
copy a snapshot over newer authoritative state. This version does not authorize
lost-host promotion without proving the former writer fenced.

For an orderly fresh-host move, stop the source, generate a destination UUID,
then use the existing B8 retirement transfer:

```bash
.venv/bin/python -m nana_core.life transfer --home /tmp/cdl-life \
  --package /tmp/cdl-subject.zip --destination-id <destination-uuid> \
  --source-commit <full-current-commit> --retire-source --json
.venv/bin/python -m nana_core.life receive --home /tmp/cdl-fresh-host \
  --package /tmp/cdl-subject.zip --sha256 <returned-package-sha256> \
  --destination-id <same-destination-uuid> --host-config <explicit-new-host-config.json> --json
```

`<...>` tokens are placeholders. New host config must explicitly bind approved
materials, paths and surfaces. The package contains only original B8 manifest,
subject SQLite and privacy metadata. Secrets/provider configuration, sockets,
PID and host settings are not copied. Old Grants are revoked and budgets have no
new headroom; rebind/requalify destination effects separately. Source cannot
resume as another writer. `--pending-effects` is explicit opt-in for quarantined
unsettled effect history; UNKNOWN remains UNKNOWN and held budgets are consumed
conservatively, not refunded. No uncertain effect is automatically replayed.

## Reproduce the combined journey

```bash
.venv/bin/python -m pytest tests/cloud_life -q
.venv/bin/python -m tools.nana_cloud_daily_life.qualification \
  --repo "$PWD" --root /tmp/cdl-journey-fresh \
  --output /tmp/cdl-journey-fresh.json --seconds 7205
```

This is actual wall-clock residency, one owned target, original C/D/F/G/I,
shadow QQ-like/Bili-like events, real effects, pause/revoke/delete, actual SIGKILL,
consistent backup and original B8 fresh-host transfer. It is not a paid provider,
live QQ/Bili or user device. For a bounded rehearsal choose 90 seconds and a new
root; that explicitly reports SHORT, never two-hour PASS. For 24h staging choose
86405 seconds and another fresh root; initial finite Grant expiry is expected,
not a reason to renew authority automatically. 72h remains a separate qualification.

## Real cognition and human review remain separate

No historical API key or old UNKNOWN request may be reused. The provider path is
the existing explicit FD/SecretResolver and configurable Router. A new provider,
verified endpoint, safe host binding, PUBLIC/PROJECT scope and fresh budget must
be authorized before any new paid call. Current task has made zero such calls.
Historical TianToken one UNKNOWN remains parked; no retry/fallback or billing claim.

After real provider qualification, the user—not Codex—can complete the anonymous
naturalness worksheet in the evidence directory. Retain structured ratings only;
do not save private dialogue or let an empty worksheet imply HUMAN_REVIEWED_PASS.
Provider alone, Hands alone, or shadow integration alone cannot upgrade FirstLife
or Cloud Daily-Life Beta.
