# Single message
- Human sends only the uniquely authorized test event, never tool auto-send.
- Result-path only; early all-message observation unavailable.
- Metadata-only: never body/result text/prompt/attachments/profile/history/Iris.
- Consumption transaction before Evidence. Crash/timeout after commit cannot revive permission.
- A mismatched event does not consume; expired/terminal/replay events cannot enter Core.
- Missing result/streaming path may never hit callback; report NOT_VERIFIED, not PASS.
