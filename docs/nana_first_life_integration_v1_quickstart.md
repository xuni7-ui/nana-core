# First-Life Dev — private development experience

Run from `/workspace/nana-core` using its existing `.venv`. No installation or
production account is required. Only PUBLIC/PROJECT input; never type keys/private
history. Existing old staging and bundle remain untouched.

```bash
# Terminal1: create a fresh isolated Subject, explicitly permit local report work.
.venv/bin/python -m tools.nana_first_life_integration.dev init --home /workspace/nana-first-life/my-dev --allow-owned-work
.venv/bin/python -m tools.nana_first_life_integration.dev start --home /workspace/nana-first-life/my-dev
# Terminal2: chat or inspect the SAME already running Subject.
.venv/bin/python -m tools.nana_first_life_integration.dev chat --home /workspace/nana-first-life/my-dev
.venv/bin/python -m tools.nana_first_life_integration.dev inspect --home /workspace/nana-first-life/my-dev
.venv/bin/python -m tools.nana_first_life_integration.dev stop --home /workspace/nana-first-life/my-dev
```

`start` performs preflight automatically. `preflight` runs it separately without
initializing/repairing a Store. `health`, `pause`, `resume`, `backup`, and
`emergency-stop` are available. Emergency stop requests pause→revoke→stop from the
single owner; a lost receipt is UNKNOWN and must be investigated before retry.
No blind resend. Restart with the same `start` command after the old process exits;
identity/history persist, revoked Grants are not reissued.

Default conversation is explicitly offline/limited. It is not a natural model
conversation and must not be used for a formal human naturalness score. Enabling
live requires a separately approved provider/config/budget and an inherited FD:
`start --live-authorized --secret-fd <fd-number> --secret-ref <opaque-reference>`.
No key in argv/env/config/file; do not paste one into this command or chat. Each
normal rendered turn may use INTERPRET + RENDER (two reserved calls), not one.
UNKNOWN stops the model path; no automatic retry or fallback. No credential search.

To reset development, initialize a **different fresh home**; the old identity and
history remain preserved. Do not delete/overwrite DBs. `backup` creates an online
quarantined review copy, not a runnable duplicate. For a fresh-host restore use
`export --package <path> --destination-id <UUID>` with the old Runtime stopped;
then `restore --package <path> --sha256 <digest> --destination-id <same UUID>` into
an absent home. Export retires the original writer; restore revokes old execution
Grants and requires new host configuration. Roll back through another lawful
forward transfer, never by running an old copied snapshot as a second writer.

Inspector is metadata only. A private creative idea may exist, with original C
choice/source/risk references visible, while content remains withheld. It is not
raw chain-of-thought. Governance still sees action/Grant/effect/UNKNOWN metadata.
No QQ/Bili send, private Iris connector, user-device or production integration.

For the reproducible integrated journey:

```bash
.venv/bin/python -m tools.nana_first_life_integration.journey --root /workspace/nana-first-life/fresh-journey --seconds 1800 --output /tmp/first-life-journey.json
```

This creates fresh owned-dev state and real local application effects, one explicit
synthetic semantic call, finite autonomous work, pause/resume, actual SIGKILL,
backup and fresh-host transfer. It does not qualify real naturalness. Inspect the
`fresh-journey/fresh-host` identity/history after completion; old `life` is retired.
Use that received home to resume the **same** Subject with host bindings separate.
Human ratings use the existing `nana_core.life review` contract; only a real user
can submit acceptance. No private transcript or automated PASS rating is generated.

Before a formal review, `tools.nana_first_life_integration.review_prepare --home
<received-home>` prepares that SAME restored Subject, not a fresh personality. It
explicitly installs a synthetic reference PRIMARY_USER role through the existing
trusted bootstrap service, tests independent source-grounded reframing, and pauses
autonomous work. This is a typed reference binding, not a real platform account or
imported personal relationship. Role source retains its existing PERSONAL data
classification; PUBLIC/PROJECT model context does not silently declassify it.
High relationship salience is demonstrated within C, without creating a Grant.

The completed30min Subject is now at:
`/workspace/nana-first-life/integration-30m-01/fresh-host`.
Old `integration-30m-01/life` is retired; do not start it or copy its DB.

```bash
.venv/bin/python -m tools.nana_first_life_integration.dev inspect --home /workspace/nana-first-life/integration-30m-01/fresh-host
.venv/bin/python -m tools.nana_first_life_integration.dev start --home /workspace/nana-first-life/integration-30m-01/fresh-host
# Another terminal: PROJECT-only private chat, currently offline/limited.
.venv/bin/python -m tools.nana_first_life_integration.dev chat --home /workspace/nana-first-life/integration-30m-01/fresh-host
```

Current instance is safely STOPPED/paused with old execution Grants revoked. Live
strict semantic qualification failed despite HTTP200; do not count offline replies
as human-naturalness PASS. Current key is not retained; later live startup requires
explicit memory-only FD binding. Do not rerun the one-shot `live_review` script to
replay the failed request. It intentionally rejects reuse/config reset. The seven
unspent authorized call slots are not an automatic retry policy. Repair/validate
strict-response compatibility before opening a new bounded review attempt.
