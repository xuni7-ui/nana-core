# Living V4 · one host-operator task card

For the authorized cloud Nana/Host Operator. The user needs only Android.
Candidate source: `c8aa8c986219199d0d027ccce0791788516e9d85`; matched bundle
`NANA_CORE_LIVING_V4_RELEASE/`, Android 4.0.1-debug/401.
The APK retains the af584900 native/UI build; server hardening needs no further
APK download.
[Status and limits](STATUS.md) · [deployment procedure](DEPLOY.md).

1. **Reconcile before preparing.** Formal Subject
   `8acff4fb-2532-4a97-a4b7-e59e2ae2f797`, `/opt/nana-core` HEAD `30845fb`,
   hotfixes and running `nana-bff-supervisor`/`astrbot`/`napcat` are
   USER_REPORTED / NOT_ATTESTED here. There is no host/VPN/secret access in this
   workspace. On the authorized host, collect read-only sanitized git HEAD,
   dirty source paths/hashes, reviewed hotfix differences, image/runtime IDs,
   numeric disk/RAM headroom and existing Subject/lineage/config binding.
   `python3 -B tools/host_facts.py` in the bundle collects allowlisted Docker
   service metadata only; it does not attest hotfixes, host identity or Subject.
   Preserve valid hotfixes and existing local changes; return no keys, env, private
   logs, databases or history bodies.

2. **Prepare a slot; keep the live writer.** Verify `SHA256SUMS`, source and image
   against `MANIFEST.json`, then run the commands below in the unpacked bundle.
   Existing host Python3.10+ and the explicit local Docker Operator context are
   required. The ordinary Core must never receive the Docker socket.

   ```sh
   sha256sum -c SHA256SUMS
   ./deploy.sh --check
   ./deploy.sh --dry-run
   ./deploy.sh --install
   ./deploy.sh --install
   ```

   Modes are check, dry-run, install and approved rollback; rollback uses the
   original Supervisor protocol and explicit password FD described in DEPLOY.
   The candidate checks both configured and persisted-active SDK aliases, exact
   UID/integrity/state before staging. `HOST_CONFIGURATION_REVIEW_REQUIRED` needs
   reconciliation, never an invented READY. Install success means READY_FOR_SWITCH.
   Review exact conflicts; do not overwrite a
   sealed slot. Retain the current service/image/config, consistent backup and
   rollback path. No Genesis, Store replacement, competing Compose project, old
   QQ writer stop/fence or active-version switch before its existing approval.

3. **Stage one concrete approval request after reconciliation.** Name the
   preserved Subject/lineage, reviewed hotfix disposition, exact image/runtime/Web
   hashes, backup receipt, switch and compatible rollback. Include only the
   additional actions actually requested: provider/model plus bounded wallet and
   PUBLIC/PROJECT privacy allowance; secure credential binding; explicitly
   selected private archive preview; exact QQ/Bili account/capability/resource
   Grants and writer handover. No approval is inferred from a configured key,
   account login, archive plan or readiness result.

4. **Bind credentials outside Subject data after authorization.** Proposed
   original HostConfiguration field: `provider_vault` =
   `/opt/nana-core/data/host/provider-vault`, mapping to
   `/srv/nana-core/data/host/provider-vault` on the host. Reconcile actual paths;
   this must be outside Subject `home`, with a private UID999-owned parent. The
   service creates a0700 vault and0600 wrapping key/encrypted CAS document.
   Preserve its host binding separately from Subject exports; root/service UID
   or possession of key plus ciphertext can expose credentials. Use protected
   native HOST_ADMIN BIND/REVOKE or a safe FD, never chat/argv/env/JS/storage/logs.
   Preserve CAS and original `serve --live-provider-authorized` spending opt-in.
   Bind/rotate needs explicit Core restart; BFF restart restores an approved
   vault binding. CredentialEpochFD2 invalidates future selection/cache in the
   running child after revoke/rotation; revoke disables dependent profiles but
   cannot cancel dispatched requests. Guarded bindings require FD2-compatible
   runtime metadata; restart/rollback rejects incompatible targets before stopping
   a healthy Core. Empty-vault legacy offline and memory-only FD1 stay supported;
   guarded credentials never downgrade to plaintext. UNKNOWN: inspect receipt,
   never resend.

5. **Qualify the real host and phone, recording real limits.** After approved
   switch, verify same Subject/Store/lineage, authenticated bootstrap/provider
   readiness, ten actual messages, restart continuity, Android cover-install
   with existing pairing, local speech, and an actual same-Subject 24h window.
   Real QQ/Bili sends need the exact activation/account and original Grants,
   C/Manager/DeliveryAdmission/Kernel/independent Verify. Do not treat loopback
   receipts as platform delivery. Human/phone/formal24h are NOT_RUN; First-Life
   NOT_READY and Beta NO remain until their evidence exists.

Private archive work is **preview only after explicit private-read approval**:
use selected files, verified Subject/lineage/hash pins and the selected release's
own isolated interpreter with `tools/legacy_archive.py` freeze/verify/search/
import-preview/withdraw. Do not export private bodies into reports. The real
RealMemoryIngress import executor is disabled and unimplemented; approval or
`--private-read-authorized` cannot enable it. Frame-based viewing, full autonomous
selection, background notification delivery and formal bwrap qualification also
retain implementation/qualification gaps. Host permissions cannot close these
code gaps by themselves.
