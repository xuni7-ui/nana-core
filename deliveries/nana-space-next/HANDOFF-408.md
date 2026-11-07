# Next Experience 408 — matched phone/Web/Core delivery

Core and frontend source: `f712136da20a48da437ce260674c967cf13c2ce0`.
Artifact branch: `delivery/nana-space-next-apk`, directory `deliveries/nana-space-next`.
Use `MANIFEST-408.json` and `SHA256SUMS-408` from its pinned delivery commit. Older404/405 remain historical files.

Phone: cover-install `nana-space-4.0.8-next-debug.apk` over `life.nana.space.dev`; same signing certificate and existing Keystore identity. Do not uninstall or clear data. Use the existing approved HTTPS server. Installing the APK does not upgrade that server. Original v2 login/pairing remain; new catalog and older-memory search require the matching BFF. No Key is stored in JS/APK. Real phone qualification remains pending.

This candidate includes original chat-layout improvements, authorized provider catalog, scoped older-memory literal search, selected-release Gateway bootstrap and native concern/rest/presence improvements. It does not claim token streaming, paid provider tests, semantic FAISS qualification, voice/media or cross-day naturalness. No474MB V4.0.3 package or old seal is changed.

## Operator steps: isolated candidate, no live changes

From the downloaded delivery directory:

```sh
sha256sum -c SHA256SUMS-408
python3 server-408/verify-delivery.py --root . --manifest MANIFEST-408.json
python3 server-408/nana-unpack.py server-408/nana-core-f712136-portable.tar.gz --sha256 3ca1e517c23f43bfbce52678fde9d2514973f19d7eabd1dfeee5908b2a318159 --destination /srv/nana-core/candidates/next-408
```

The parent must be an existing private operator-owned directory. Unpacker rejects an existing destination, links, traversal and oversized archives. If the destination exists, stop and inspect; do not erase it. No Subject is created during extraction. Check `runtime.json` source against the commit above; bootstrap verifies the279-file bundle. Hashes are integrity evidence, not production approval.

Reuse the already qualified Debian13 image/private SDK. Preserve `/srv/nana-core/runtime` → `/opt/nana-core/runtime` read-only. The source package supplies locked offline wheels, not a replacement private Python. Set the following **non-secret selectors** to values from the existing approved host inventory: `NANA_QUALIFIED_IMAGE` (full digest), `NANA_RUN_UID` and `NANA_RUN_GID` (numeric). Never guess a tag, infer UID from an account display name, or modify old AstrBot permissions.

Make only the new candidate and a new scratch directory writable by that numeric owner, then install in isolation:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /opt/nana-core/runtime/bin/python3 \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-408,dst=/candidate \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /candidate/bootstrap.py install
```

Do not omit `--entrypoint`: the ordinary production image entrypoint must not start a live Core during this check. Mount no live Subject, data, Vault, auth or Docker socket. Do not chown the existing data tree.

For actual installed validation, set `NANA_CHECKS_DIR` to the absolute downloaded `server-408` directory and `NANA_SCRATCH_DIR` to a fresh private writable scratch directory. Candidate is now read-only; only scratch is writable:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /candidate/.venv/bin/python \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-408,dst=/candidate,readonly \
  --mount "type=bind,src=$NANA_CHECKS_DIR,dst=/checks,readonly" \
  --mount "type=bind,src=$NANA_SCRATCH_DIR,dst=/tmp/nana-check" \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /checks/verify-dev.py --bundle /candidate --work /tmp/nana-check/probe --output /tmp/nana-check/result.json --check-memory-notes
```

This verification intentionally creates a fresh **DEV** identity in scratch, exercises loopback BFF and original Core, and stops only those test processes. It is not canonical Genesis, private migration or production recovery. Short container scratch paths prevent Unix-socket length failures. Do not pass `-O`; qualification assertions must execute.

Through the same image/SDK entrypoint, confirm `ssl`, `sqlite3`, `pydantic` and source commit. The development installation used Python3.12.14/SQLite3.53.1/OpenSSL3.5.8. The cloud's private3.51.3/3.5.7 combination needs its actual operator receipt; this document does not claim that host was tested.

Web tar contains the separate `nana-space-web/` static root. Keep it in a candidate location; do not overwrite active Web. Register source/root/interpreter/integrity only through the original sealed Supervisor/Host Operator path. Core and Gateway must select the same registered release; the updated bootstrap follows Supervisor state before credentials/Subject startup. Preserve canonical home, roles, existing HTTPS, Vault, old slots and rollback. Activation, live restart, live routing and host permission changes follow existing production authorization.

## Recorded evidence and scope

408 retains the existing source-bound note/UNKNOWN and native G/needs/Fish mechanisms. New explicit connection-only PROJECT retention keeps PERSONAL per-message. Stable mobile send/options targets no longer move when focus changes. Current scoped validation:59 frontend tests,12 responsive request/lifecycle/UNKNOWN checks,50 final relationship/context/person tests. Same153-row synthetic corpus preserves preferences/boundaries/shared event that were previously buried; final200k alternating benchmark original P9561.77→49.24ms. A slower six-scan first attempt and initial browser failures are preserved in source evidence, not reported as success.

Final source f712136:279-file archive built twice byte-identically. The actual archive was extracted with the supplied bounded checker and installed offline in fresh /tmp/n408-installed. Original BFF/ten views/chat/notes/correction/restart/withdrawal/backup/stop passed. The same DEV Subject and lineage then completed INTERPRET+RENDER using a loopback fixture with a current note. No repository PYTHONPATH, real provider calls, live cloud, physical phone, human naturalness or cross-day qualification. The full historical edd170f suite1933pass/1 document failure/12skip and subsequent bounded-header repair belong to that historical source; no full-suite pass is claimed for408. See source docs/nana_next_experience/evidence/chat408 and RELATIONSHIP_RETENTION.md.

For the additional note-context check, keep verify-dev.py beside verify-note-recall.py, and use the same qualified interpreter/container and fresh DEV scratch:

```sh
/candidate/.venv/bin/python -I -B /checks/verify-note-recall.py --bundle /candidate --work /tmp/nana-check/recall --output /tmp/nana-check/recall.json
```

Do not reuse a production home for either checker. The server remains a candidate until the operator follows the existing authorization and stopped-upgrade/backup/fencing path. No active Store hot downgrade, no canonical Genesis, no private history import and no old474MB release rebuild.
