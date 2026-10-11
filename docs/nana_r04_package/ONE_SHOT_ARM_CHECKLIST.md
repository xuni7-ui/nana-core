# One-shot arm
- Provenance ASTRBOT_REAL_MESSAGE, exact store binding, independent reviewed digest/source pin.
- Exact sender/conversation scoped hashes/platform/event type, no wildcard/body.
- UTC start/end, max600sec, skew2sec, max_uses1, unique receipt id.
- CREATED→REVIEWED→ARMED only. Terminal receipt cannot re-arm; use new receipt.
- No ordinary config/env/force/fixture option opens the real gate.
- Arm/start is not message send permission for Core; Shadow reply/Action/Grant0.
