# Open Life V1 — owned development quickstart

No credential, paid provider, social account or user device is required.
This is an Advanced Growth development environment, not production deployment.
Use the original standalone runtime; no second daemon/Subject/Store.

## Reproduce the whole lifecycle

From the repository with its existing Python environment:

```bash
.venv/bin/python -m tools.nana_open_life.qualification \
  --root /tmp/my-fresh-open-life \
  --output /tmp/my-open-life-result.json \
  --wall-seconds 120
.venv/bin/python -m tools.nana_open_life.soak \
  --root /tmp/my-fresh-open-life-virtual \
  --output /tmp/my-open-life-virtual.json
```

Both roots must be new. The first creates only owned application/browser child
processes. It follows one actual Subject through source→World→research→C problem
reframe→Goal/Plan→HTTP Hand→independent Unix/disk Verify→Failure→original G learning
→different later tasks→bounded isolated skill composition→two actual Kernel uses
→share candidate deferred while busy→retirement/source withdrawal→restart→backup
→lawful transfer. The original source is retired during transfer; it is not a
second runnable copy. No test is a naturalness/human qualification.

The second advances60 virtual days over finite unchanged source opportunities.
It is not a60-day real residency or repetition of the old Foundation24h.

## Configure an existing *development* host

Provider/secret config is unnecessary. Host settings remain outside SubjectPackage.
Use the existing LifeConfig CAS service while the runtime is stopped, supplying
its actual expected revision. Example application-owned setup:

```python
from nana_core.life.config import load_config, update_config
from nana_core.continuity.open_life.sources import IntakeSource

cfg = load_config(home)
update_config(home, cfg.model_copy(update={
    'revision': cfg.revision + 1,
    'advanced_life': True,
    'world_source_root': '/your/explicit/owned/project-source-directory',
    'world_sources': (IntakeSource(
        source_id='project-feed', channel='STRUCTURED_FEED',
        location='feed.json', privacy='PROJECT',
        semantic_format='SOURCED_CLAIM_JSON'),),
}), expected_revision=cfg.revision)
```

`feed.json` is an owned fixture with a typed `world_claim`, for example entity_id
`project-user`, predicate `project.status`, kind `INTERPRETED`, value `review-needed`,
valid_from_us an actual nonfuture source timestamp, optional expiry/confidence.
This deterministic JSON adapter is a semantic derivation, not raw world truth or
live LLM understanding. Opaque documents use `semantic_format='OPAQUE'` and offer
attention without inventing facts. No recursive file scanning occurs.

OWNED_HTTP requires an explicit `http://127.0.0.1:<port>/<path>` descriptor. It has
no redirect, credential or arbitrary external-host path. A dispatch is reserved
before HTTP. A timeout/killed attempt blocks later poll IDs for that source.
Do not clear UNKNOWN or change IDs to retry it. No reconciliation/reset command
is supplied without independent status evidence.

OwnedBrowser runs only against an explicitly constructed OwnedApplication profile.
HTML navigation/form preparation does not grant execution. Actual form apply still
needs ordinary Kernel authority; Verify uses original independent IPC and disk.
The shipped child bootstrap locates its own installed source and uses a minimal
explicit environment, so it does not need Codex paths or inherited PYTHONPATH.

## Inspect and stop

Use existing `nana inspect`, private owner CLI/IPC status, pause, stop, backup and
lawful transfer. Inspector now contains advanced_life metadata: opportunities,
problems, current goal lifecycle/hierarchy, learning stages and bounded rhythm.
It has no raw thought/transcript view or mutation authority. See previous portable
runtime quickstart for exact Fresh/Transfer/SSH entry; do not copy a live DB into
another runnable directory or carry old Grants to a new host.

Human Review is independent Track B. Its NOT_RUN state does not stop construction,
and this delivery does not grant real social, new paid models, private history,
actual desktop/mobile/game control or production activation.

## Automatic source/research virtual-time qualification

```bash
.venv/bin/python -m tools.nana_open_life.soak --runtime-sources \
  --root /tmp/my-fresh-automatic-research \
  --output /tmp/my-automatic-research.json
```

This runs the original LifeApplication with configured sources, one original C
and original background work. After C EXPLORE, ResearchWork advances one source
per slice; the driver does not call research notice/gather/compare. The60 virtual
days include unchanged input, source expiry to UNKNOWN, then a later owned-file
revision. The synthetic host lease is long enough for hourly virtual jumps;
production/runtime defaults are unchanged. No paid provider, private data or
external effect is involved.

LOW/repeated assessments reach original C. Queue admission only checks current
source/privacy/expiry/idempotency. Inspector retains that C considered the motive
and chose IGNORE rather than claiming an external veto erased the wish.
