# Next Experience 406 — matched phone/Web/Core delivery

Core and frontend source: `cc3dc335cfec6db00ac44850344de2c49df25769`.
Artifact branch: `delivery/nana-space-next-apk`, directory `deliveries/nana-space-next`.
Use `MANIFEST-406.json` and `SHA256SUMS-406` from its pinned delivery commit. Older404/405 remain historical files.

Phone: cover-install `nana-space-4.0.6-next-debug.apk` over `life.nana.space.dev`; same signing certificate and existing Keystore identity. Do not uninstall or clear data. Use the existing approved HTTPS server. Installing the APK does not upgrade that server. Original v2 login/pairing remain; new catalog and older-memory search require the matching BFF. No Key is stored in JS/APK. Real phone qualification remains pending.

This candidate includes original chat-layout improvements, authorized provider catalog, scoped older-memory literal search, selected-release Gateway bootstrap and native concern/rest/presence improvements. It does not claim token streaming, paid provider tests, semantic FAISS qualification, voice/media or cross-day naturalness. No474MB V4.0.3 package or old seal is changed.

## Operator steps: isolated candidate, no live changes

From the downloaded delivery directory:

```sh
sha256sum -c SHA256SUMS-406
python3 server-406/nana-unpack.py server-406/nana-core-cc3dc33-portable.tar.gz --sha256 a921f917676ed34fe6b146652f216bea143b687aaf2d18da981a265c8fea496b --destination /srv/nana-core/candidates/next-406
```

The parent must be an existing private operator-owned directory. Unpacker rejects an existing destination, links, traversal and oversized archives. If the destination exists, stop and inspect; do not erase it. No Subject is created during extraction. Check `runtime.json` source against the commit above; bootstrap verifies the277-file bundle. Hashes are integrity evidence, not production approval.

Reuse the already qualified Debian13 image/private SDK. Preserve `/srv/nana-core/runtime` → `/opt/nana-core/runtime` read-only. The source package supplies locked offline wheels, not a replacement private Python. Set the following **non-secret selectors** to values from the existing approved host inventory: `NANA_QUALIFIED_IMAGE` (full digest), `NANA_RUN_UID` and `NANA_RUN_GID` (numeric). Never guess a tag, infer UID from an account display name, or modify old AstrBot permissions.

Make only the new candidate and a new scratch directory writable by that numeric owner, then install in isolation:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /opt/nana-core/runtime/bin/python3 \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-406,dst=/candidate \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /candidate/bootstrap.py install
```

Do not omit `--entrypoint`: the ordinary production image entrypoint must not start a live Core during this check. Mount no live Subject, data, Vault, auth or Docker socket. Do not chown the existing data tree.

For actual installed validation, set `NANA_CHECKS_DIR` to the absolute downloaded `server-406` directory and `NANA_SCRATCH_DIR` to a fresh private writable scratch directory. Candidate is now read-only; only scratch is writable:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /candidate/.venv/bin/python \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-406,dst=/candidate,readonly \
  --mount "type=bind,src=$NANA_CHECKS_DIR,dst=/checks,readonly" \
  --mount "type=bind,src=$NANA_SCRATCH_DIR,dst=/tmp/nana-check" \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /checks/verify-dev.py --bundle /candidate --work /tmp/nana-check/probe --output /tmp/nana-check/result.json
```

This verification intentionally creates a fresh **DEV** identity in scratch, exercises loopback BFF and original Core, and stops only those test processes. It is not canonical Genesis, private migration or production recovery. Short container scratch paths prevent Unix-socket length failures. Do not pass `-O`; qualification assertions must execute.

Through the same image/SDK entrypoint, confirm `ssl`, `sqlite3`, `pydantic` and source commit. The development installation used Python3.12.14/SQLite3.53.1/OpenSSL3.5.8. The cloud's private3.51.3/3.5.7 combination needs its actual operator receipt; this document does not claim that host was tested.

Web tar contains the separate `nana-space-web/` static root. Keep it in a candidate location; do not overwrite active Web. Register source/root/interpreter/integrity only through the original sealed Supervisor/Host Operator path. Core and Gateway must select the same registered release; the updated bootstrap follows Supervisor state before credentials/Subject startup. Preserve canonical home, roles, existing HTTPS, Vault, old slots and rollback. Activation, live restart, live routing and host permission changes follow existing production authorization.

## Recorded evidence

Installed cc3dc33 DEV bundle: ten API views, original Core offline chat, backup, independent stop and same-ID restart passed (`server-406/installed-dev-result.json`). Core233 related tests plus final Inspector7; responsive browser24 at desktop/360/390/412. Historical complete regression1905/0/12 belongs to6f2a491, not this source. No production update, private migration, real provider call or social send. Human, physical phone, real host and cross-day gates remain open; bwrap code execution remains blocked.
