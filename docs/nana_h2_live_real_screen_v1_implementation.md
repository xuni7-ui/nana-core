# H2-LIVE Real Screen Qualification V1

GLOBAL_STAGE H; WORKSTREAM H2_LIVE_REAL_SCREEN_QUALIFICATION_V1.

Base: `06c80a907af49c3b80bf097f90c71e02d552aaf8`, remote verified before development;
parent `798cc3318410e24b1b529ffde59d366982853388`.
Branch: `dev/nana-core-h2-live-real-screen-v1-codex`.
Frozen qualified source: `86b7d18e9e54edc6d77c6b868e64c838c0132ba5`.
Final handoff commit is obtained with `git rev-parse HEAD`; the final docs/evidence
commit does not change the frozen executable source.

## Result and scope

Final measured results are in the matching evidence directory. Qualification is
L1: a real OS-created Xorg dummy display, one own mapped window, real XGetImage
capture and RGB decode. It is not L0 file/PNG injection, L2 user desktop capture or
L3 production streaming. Graphics rendered by the harness are public test inputs;
no generated PNG is substituted for the screen backend's OS capture result.
No ambient DISPLAY, window enumeration, clipboard, accessibility tree, browser
profile, account notification, camera, microphone or Iris content was read.

H1 interpretation is SYNTHETIC_LOOPBACK, a deliberately narrow dominant-color
pixel oracle using the existing transport. No live provider or credential is
used. OCR, general scene/object understanding, physical screen behavior, OS
consent dialogs/secure desktops and cross-platform capture quality are NOT_RUN.
H1-LIVE historical PARTIAL_PROVIDER_QUALIFICATION is unchanged.

## Modules and authority

* `continuity/sensors/screen.py`: strict ScreenBackendDescriptor,
  ScreenCaptureReceipt and RealScreenPerceptionPort. A host supplies an explicit
  backend/profile/clock, enables it, and pins session/geometry/revision. The port
  has no Store, Runtime, Subject, model or mutation authority. V1 only admits
  PUBLIC IMAGE pixels from an explicit owned window, bounded to500000 pixels.
* `sensors/contracts.py`: backward-compatible synthetic default plus explicit
  REAL_OS_CONTROLLED origin and validated receipt on captured media. Data remains
  excluded from DTO serialization/repr.
* `sensors/coordinator.py`: existing owner/lease/preemption/Manager/privacy/budget
  checks precede bytes. Real captures use recorded.public-media, never synthetic
  evidence. Pixel equality can debounce semantics across different encodings;
  source observations retain separate time/event/capture identities. Route
  revision and short time bounds remain required. Capture ambiguity becomes
  UNKNOWN with durable reservation and no retry. Old source revisions cannot
  resume semantic work under a new binding. C WATCH can cite transitive
  semantic/world evidence through bounded128-node existing dependencies.
* `world_loop/perception.py`: original decoder verifies receipt identity, time,
  source/backend, dimensions and pixel/encoded digest. Existing RECORDED_PUBLIC
  domain represents real PUBLIC evidence with explicit REAL_OS_CONTROLLED subtype;
  no schema widening. Absent optional fields are omitted so legacy synthetic
  serialized source/history identity is preserved.
* `sensors/application.py`: existing privacy-filtered B10 settings add optional
  sanitized backend/health/qualification projection. No OS handles, authority or
  second ContextBuilder/frontend loop.
* `tools/nana_h2_live_screen/x11_surface.py`: optional Linux host harness. Fixed
  dummy-only Xorg config disables device/GPU auto-add and VT switching, TCP
  listening and hardware input synthesis. Private temporary Xauthority is scoped
  to the owned display, never stored in repository/Subject/evidence. Own Xlib
  drawing creates the test surface; XGetImage reads exactly that drawable, not a
  full desktop crop. Size and geometry checked before capture, after capture,
  and again by Core decode. Owned child death guard and explicit cleanup bound
  process lifetime. A private host lock serializes only this qualification
  harness; busy/unavailable never chooses another desktop/backend.
* `tools/.../lab.py`: explicit host injection into original Runtime, config,
  resolver, CapabilityRouter, OpenAIMediaTransport, H1 MediaSemanticService and
  reference WorldModel/Concern work. No Grants, planner or external executor.
* `tools/.../qualification.py`: finite opt-in preflight/scenes/virtual/wall/crash/
  resume runner. Only original D.step schedules observations and C opportunities.
  Graphics changes belong to the test environment, never a Nana action.

No new Subject table/schema, dependency, Store, Runtime, Scheduler or SubjectLoop.
Schema13,43 business tables. Optional host Xorg/libX11/dummy/Pillow were already
available; nothing was installed. Non-Linux/platform implementations are future
adapters, not claimed working slots or a hidden fallback.

## Lifetime and failure behavior

Host source config is application-local JSON, never Subject identity. A restarted
host constructs a new display and explicitly renews source revision before use.
Pending old revision work is fenced. Repeated recovery cannot recapture or
redispatch semantics. Expired ephemeral H1 payload stays expired; UNKNOWN never
fallback/retry. Old historical evidence remains evidence of its original event,
not permission for a new window. Topology invalidation is latched until rebind.

Scope/privacy/Manager denial and min interval occur before bytes. Enable is not
OS consent. WATCH may shorten an opportunity interval only inside host bounds;
Primary User, curiosity and visible authorization language cannot expand scope.
An external Manager veto preserves C's original WATCH judgment/history.

Only digest/geometry/time/coverage/interpretation/support references persist.
PNG/RGB bytes and hydrated H1 payloads last one bounded capture slice. No screenshot
files or thumbnails enter Git, Store, queue, evidence or B8. Existing dependencies
make explicit Memory forget retire downstream support; disabling/removing a
source instead preserves valid past history. B8 actual export/import tests retain
identity and historical provenance while excluding active display/config handles;
a new host must explicitly bind a new source. A binding digest in historical
provenance is non-executable, not portable active configuration.

## Reproducible controlled runbook

From the repository with its existing virtualenv and preinstalled optional Linux
Xorg dummy/libX11/Pillow support:

```bash
.venv/bin/python -m tools.nana_h2_live_screen.qualification preflight
.venv/bin/python -m pytest tests/h2_live_screen --live-screen -v
.venv/bin/python -m tools.nana_h2_live_screen.qualification scenes --live-screen --root /tmp/owned-screen-scenes --output /tmp/owned-screen-scenes.json
.venv/bin/python -m tools.nana_h2_live_screen.qualification virtual --live-screen --root /tmp/owned-screen-virtual --output /tmp/owned-screen-virtual.json
.venv/bin/python -m tools.nana_h2_live_screen.qualification wall --live-screen --seconds 300 --root /tmp/owned-screen-wall --output /tmp/owned-screen-wall.json
```

Use fresh dedicated roots. Only one live harness at a time; preflight/default
pytest never captures. Missing flag rejects before opening a display. No need to
set DISPLAY, provide an OS window selector or enter credentials. No daemon is
installed. Normal return/exception closes window/display/process/private files;
SIGKILL tests use an owned parent-death signal and parent-owned cleanup/reaping of
only the worker's explicit test PID/temp directory. No process-wide kill/scanning.
The original Runtime lease must expire before another owner resumes; no force
lease takeover. Don't manually run crash mode outside a disposable cleanup-owning
test parent. A crash cannot authorize capture on a new display.

## Qualification matrix and limits

A normal geometry/text; B color/position change; C same RGB later time; D visual
injection; E pseudo user text; F authority spoof; G faint field/high uncertainty;
H rapid changes/min-interval denial; I unchanged temporal observations/debounce;
J resize invalidation then explicit trusted rebind. All use real OS captures.
Semantics only asserts dominant colors/uncertainty, never OCR recognition. The
adversarial test additionally feeds an unauthorized MEDIA goal proposal through
H1 and requires rejection; visible text itself never enters command ingress.
This establishes authority isolation, not immunity of every future model to
all prompt injection.

Source-backed C WATCH reaches host-limited5000ms interval, not action execution.
User preemption loses ephemeral bytes safely; pending/backpressure/coalescing are
bounded in original D. Six actual SIGKILL cuts span before source open, after
capture/before ingest, after ingest, before semantic dispatch, after response and
before Concern. All six use the real backend, and resumed processes perform zero
capture/provider replay. Host binding revision renews to2.

The24h virtual run uses the real owned window with accelerated injected time,
including WATCH, user preemption, disable/rebind, Manager veto and coalescing.
The >=300-second run uses actual wall clock, sparse10-second Scheduler capture
opportunities, four graphics conditions and FD/thread/RSS/CPU/latency/owned-child
measurements. Frozen-source fresh-process outputs are evidence; development
smokes are not substituted for final runs.

Pre-freeze combined qualification had171 passes/1 resume handshake failure while
two independently starting Xorg harnesses ran concurrently. It failed closed
before capture. Serial harness ownership was added and retested; no permission
check or assertion was weakened. Early development DTO/assertion mistakes were
corrected before freeze. Final evidence records actual final outcomes, including
any final failure rather than erasing it.

## Explicit non-goals

No real user desktop, physical monitor, live camera/mic/ASR/provider, production
stream, Hands/mouse/key, QQ/Bili/AstrBot/Iris, UI, new Registry, cloud deployment
or main/R045 changes. No real external effects or social sends. The owned OS test
surface is the only authorized real source; other sessions require a separate
host adapter/consent/qualification. A successful L1 result grants none of them.

## Final frozen-source measured result

STATUS = REAL_OS_SCREEN_QUALIFIED, strictly L1 owned public OS window.
Fresh-process focused18/18 PASS, six real-backend SIGKILL cases PASS. Full default
offline regression1178 passed/0 failed/12 skipped in159.68s;11 skips are the opt-in
screen cases already passed in the explicit live suite, one is E12 NOT_RUN.
Full includes original H2/Provider/H1/D/World/OpenAutonomy/B8 suites.

Final standalone scenes13 captures +24 virtual hours25 captures +300.045719563s
real wall29 captures =67 measured OS captures in those three final workloads;
additional focused/development captures are deliberately not aggregated here.
Wall queue max1/pending0;FD4→4,threads1→1,RSS peak increment23176KiB,own-process CPU
8.836s;capture-step latency mean97.119ms/max140.389ms. These are observed local
resource measurements, not hardware-independent performance promises. Owned Xorg
was alive during the run and stopped afterward. Virtual queue max3/hot requests25,
coalesced154, WATCH/preemption/Manager/disable-rebind PASS. Store scans show zero
raw PNG/base64-PNG/auth-cookie markers, schema13/43 tables, clean foreign keys and
zero Actions/Grants in all three standalone runs.

No executable source/test/tool changes after86b7d18. Small text-only evidence and
manifest record measurements/source fingerprints; manifest excludes itself and
09_STATE anchor. Final dev push is authorized by this task and separately verified
with ls-remote. It is not a deployment or permission to capture any user desktop.
