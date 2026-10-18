# H2-LIVE controlled screen frontend contract

GLOBAL_STAGE H; H2_LIVE_REAL_SCREEN_QUALIFICATION_V1. This extends existing B10
PERCEPTION_SETTINGS / PERCEPTION_STATUS and application commands; no new UI or
frontend-owned capture loop. The host binds the backend. Primary User role,
source enable, Manager PASS and WATCH are independently insufficient permission.

## Read-only backend projection

An explicitly host-bound screen source adds this optional field to the existing
sanitized settings source object:

```json
{
  "source_profile_id": "screen.controlled",
  "source_kind": "SCREEN",
  "privacy_class": "PUBLIC",
  "revision": 4,
  "screen_backend": {
    "backend_id": "x11.owned-window",
    "session_kind": "OWNED_X11_DUMMY",
    "capture_scope": "EXPLICIT_WINDOW",
    "supports_window": true,
    "supports_region": false,
    "supports_full_desktop": false,
    "consent": "EXPLICIT_HOST_BINDING",
    "controlled_surface": true,
    "image_format": "PNG",
    "max_pixels": 500000,
    "health": "AVAILABLE",
    "binding_status": "HOST_BOUND",
    "qualification_level": "L1_REAL_OS_CONTROLLED_NOT_PHYSICAL_DESKTOP"
  }
}
```

The actual source config, opaque resource refs, OS window handles, display socket,
process IDs, session nonce, authorization cookie and raw pixels are not returned.
The projection is infrastructure metadata, not Subject belief or permission.
Backend health can report SCREEN_SESSION_CHANGED, SCREEN_TOPOLOGY_CHANGED,
SCREEN_SESSION_UNAVAILABLE or SCREEN_SCOPE_DENIED. Config/controller errors fail
closed, with UNAVAILABLE rather than a guessed alternative display.

## Commands remain existing B10 transitions

Existing CONFIGURE_PERCEPTION and REQUEST_CAPTURE policy applies. Examples:

```json
{"operation":"DISABLE_PERCEPTION_SOURCE","expected_revision":4,"target_id":"screen.controlled"}
```

`client.request_capture(source_id='screen.controlled', request_id='ui.capture.1',
expected_revision=4)` only returns REQUESTED and enqueues metadata. D owner then
checks scope, source revision, host allow, Manager veto, budget, health, deadline
and adapter binding before bytes. Duplicate request IDs cannot reread a screen.

Source changes use monotonic config revision/CAS. A frontend enable/update cannot
renew a stale OS binding: the trusted host must explicitly construct a new port
and bind the new profile revision. Resize/session invalidation is latched; merely
restoring old dimensions does not silently authorize reuse. Removal stops future
capture without erasing history. Explicit Memory forget handles erasure.

## Receipt and status semantics

Historical source Memory contains a typed ScreenCaptureReceipt: origin
REAL_OS_CONTROLLED; source profile/revision; backend ID; opaque binding digest;
EXPLICIT_WINDOW; capture start/end; dimensions; encoded and RGB pixel digests;
CAPTURED status. It is provenance, not a receipt granting action authority.
Raw pixels are ephemeral and are not exposed by a frontend history endpoint.

The existing PERCEPTION_STATUS supplies last technical/semantic record references,
last capture time, effective interval, pending/coalesced/dropped counts and minimal
Manager block references. A blocked WATCH remains a C desire; capture did not
occur. Neither the frontend nor H2 rewrites C's judgment.

A later identical pixel buffer is a new temporal observation. Within configured
short debounce and unchanged route revision, semantic dispatch may be suppressed;
this is not evidence of an unchanged world outside the observed window/time.
Capture UNKNOWN is terminal for that request; missing bytes or a new binding do
not authorize retry. Technical capture, semantic interpretation, world belief,
Concern and C judgment retain separate provenance/state.

## Qualification limits

L1 means genuine OS capture of a self-created public test window. It does not mean
physical monitor capture, private desktop permission, OCR quality, a live model,
H2 production streaming or Hands. Windows/macOS/Android require future explicit
host adapters and OS consent; this contract grants none. No screen text can
become a user request, Primary User binding, Manager rule, Grant or keyboard/mouse
instruction. No screenshot preview/thumbnail persistence is added.
