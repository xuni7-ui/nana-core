# B1 first real Subject backup — preparation only

The existing tools are reused, not rewritten. No PC/private backup was performed
in this task. Snapshot/public recipient/PC identity must be explicitly authorized;
private signing/decryption keys remain on the PC. Never use historical chat keys.

1. Obtain an original Core safe-point `BACKUP` through the authenticated HostAdmin
   operation with its one-use confirmation. Record its actual receipt. It must be
   a registered quarantined review copy with the current privacy sidecar, not a
   tar/copy of a live DB. A new genesis by itself is not a backup or DR qualification.
2. Trusted host operator (explicit paths, not APK-provided file handles):

```
python tools/nana_first_life_android_v2/b1_backup.py freeze --snapshot REGISTERED_SNAPSHOT --privacy-anchor EXPLICIT_ANCHOR --output NEW_FROZEN_BUNDLE
python tools/nana_first_life_android_v2/b1_backup.py encrypt --bundle FROZEN_BUNDLE --bundle-sha256 EXPECTED_SHA --public-key PC_PUBLIC_KEY --recipient-fingerprint EXPECTED_PUBLIC_FINGERPRINT --output NEW_CIPHERTEXT
```

3. Dedicated PC receiver account uses forced command `nana-b1-receiver` mapped to
   `b1_backup.py receive --root PRIVATE_PC_DIRECTORY`. Restrict the SSH account to
   this receiver, not an arbitrary remote shell. The existing receiver is POSIX;
   native Windows needs independently qualified ACLs or an explicit WSL/POSIX host.
4. Send only ciphertext via the original explicit known-hosts + SSH agent + actual
   independent host tailscaled socket. No default SSH identity/key discovery,
   Funnel, old nanadocker identity replacement or plaintext fallback. Offline PC,
   timed out or unmatched receipt means backup incomplete/UNKNOWN, retry0.
5. PC locally decrypts in its own secure keyring and checks expected frozen SHA,
   then runs `verify-restored --bundle DECRYPTED_BUNDLE --bundle-sha256 EXPECTED_SHA`.
   This verifies integrity/privacy/quarantine, not permission to run a second Nana.
   Current privacy withdrawal reconciliation and authorized B8 lineage/fencing
   must precede any active restore. Same-disk `/srv/.../backups` is not B1.

Only independently observed PC receive + restore evidence can qualify B1. The new
GET backup/status deliberately returns STATUS_NOT_EXPOSED without this telemetry;
HTTP local backup VERIFIED is not silently promoted to PC delivery or recovery.
