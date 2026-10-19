# Owned application life — developer quickstart

Run from repository root with the existing environment. No API key/provider is
required. Use fresh paths and only data you explicitly own. This controls a local
development application, not your desktop or other applications.

First terminal: keep the separately owned target alive:

```bash
.venv/bin/python -c 'from pathlib import Path
import time
from nana_core.continuity.hands.host import OwnedApplication
with OwnedApplication(Path("/tmp/rae-owned-app")) as app:
    print(app.profile, flush=True)
    time.sleep(3600)'
```

Second terminal: initialize explicitly, then run the normal Nana CLI:

```bash
.venv/bin/python -m nana_core.life init \
  --home /tmp/rae-life --project "$PWD" --demo-materials \
  --owned-application-profile /tmp/rae-owned-app/application/profile.json \
  --allow-local-artifacts --allow-local-skills
.venv/bin/python -m nana_core.life run --home /tmp/rae-life
```

The allow flags are an explicit trusted development bootstrap, not an inferred
permission from a profile. The created Grant is finite and4h; restarting `run`
does not renew it. Do not rerun initialization over existing state to regrant.
The target should stay alive across Nana process restart; a new target process
has a different binding and is not automatically a continuation of the old grant.

Useful local commands:

```text
/life
/status
/actions
/outcomes
/busy
/available
/pause
/resume
/sources
/forget <explicit source memory id>
/revoke
/quit
```

Finite tasks can run without chat input. Expect actual baseline failures, learning,
later improvement, multi-field skill development, and counterexamples. A task
failure is not hidden or reset. `/work` is a project-mode command and is rejected
in owned application mode; it cannot replay retired tasks. `/forget` withdraws
Core memory/derived support, not the independently owned application's external
files. No claim that forgetting erases an already performed physical effect.
`/revoke` prevents new authorized effects; it does not rewrite what already happened.

Stop Nana with `/quit` before stopping the target terminal. All files are under
the two explicit temporary paths. No social delivery or remote model call occurs.

Reproduce the extended real task journey and system tests:

```bash
.venv/bin/python -m tools.nana_controlled_hands.qualification \
  --repo "$PWD" --root /tmp/rae-journey-fresh \
  --output /tmp/rae-journey-fresh.json --seconds 35 --real-heldout
.venv/bin/python -m pytest tests/controlled_hands -q
```

On a heavily loaded machine, choose a longer bounded duration (for example60s)
so finite work can finish; do not change the pass assertions. To repeat the actual
30-minute resource qualification, choose another fresh root and `--seconds 1805`.
No clock acceleration. Do not commit generated DBs or host profiles.
