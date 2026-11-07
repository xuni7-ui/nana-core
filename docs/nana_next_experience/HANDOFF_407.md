# Next Experience 407 — matched phone/Web/Core delivery

Core and frontend source: `edd170f1971efe0aa592004d2a01b9be9f0cf4f1`.
Artifact branch: `delivery/nana-space-next-apk`, directory `deliveries/nana-space-next`.
Use `MANIFEST-407.json` and `SHA256SUMS-407` from its pinned delivery commit. Older404/405 remain historical files.

Phone: cover-install `nana-space-4.0.7-next-debug.apk` over `life.nana.space.dev`; same signing certificate and existing Keystore identity. Do not uninstall or clear data. Use the existing approved HTTPS server. Installing the APK does not upgrade that server. Original v2 login/pairing remain; new catalog and older-memory search require the matching BFF. No Key is stored in JS/APK. Real phone qualification remains pending.

This candidate includes original chat-layout improvements, authorized provider catalog, scoped older-memory literal search, selected-release Gateway bootstrap and native concern/rest/presence improvements. It does not claim token streaming, paid provider tests, semantic FAISS qualification, voice/media or cross-day naturalness. No474MB V4.0.3 package or old seal is changed.

## Operator steps: isolated candidate, no live changes

From the downloaded delivery directory:

```sh
sha256sum -c SHA256SUMS-407
python3 server-407/verify-delivery.py --root . --manifest MANIFEST-407.json
python3 server-407/nana-unpack.py server-407/nana-core-edd170f-portable.tar.gz --sha256 3ca1e517c23f43bfbce52678fde9d2514973f19d7eabd1dfeee5908b2a318159 --destination /srv/nana-core/candidates/next-407
```

The parent must be an existing private operator-owned directory. Unpacker rejects an existing destination, links, traversal and oversized archives. If the destination exists, stop and inspect; do not erase it. No Subject is created during extraction. Check `runtime.json` source against the commit above; bootstrap verifies the279-file bundle. Hashes are integrity evidence, not production approval.

Reuse the already qualified Debian13 image/private SDK. Preserve `/srv/nana-core/runtime` → `/opt/nana-core/runtime` read-only. The source package supplies locked offline wheels, not a replacement private Python. Set the following **non-secret selectors** to values from the existing approved host inventory: `NANA_QUALIFIED_IMAGE` (full digest), `NANA_RUN_UID` and `NANA_RUN_GID` (numeric). Never guess a tag, infer UID from an account display name, or modify old AstrBot permissions.

Make only the new candidate and a new scratch directory writable by that numeric owner, then install in isolation:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /opt/nana-core/runtime/bin/python3 \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-407,dst=/candidate \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /candidate/bootstrap.py install
```

Do not omit `--entrypoint`: the ordinary production image entrypoint must not start a live Core during this check. Mount no live Subject, data, Vault, auth or Docker socket. Do not chown the existing data tree.

For actual installed validation, set `NANA_CHECKS_DIR` to the absolute downloaded `server-407` directory and `NANA_SCRATCH_DIR` to a fresh private writable scratch directory. Candidate is now read-only; only scratch is writable:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /candidate/.venv/bin/python \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-407,dst=/candidate,readonly \
  --mount "type=bind,src=$NANA_CHECKS_DIR,dst=/checks,readonly" \
  --mount "type=bind,src=$NANA_SCRATCH_DIR,dst=/tmp/nana-check" \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /checks/verify-dev.py --bundle /candidate --work /tmp/nana-check/probe --output /tmp/nana-check/result.json --check-memory-notes
```

This verification intentionally creates a fresh **DEV** identity in scratch, exercises loopback BFF and original Core, and stops only those test processes. It is not canonical Genesis, private migration or production recovery. Short container scratch paths prevent Unix-socket length failures. Do not pass `-O`; qualification assertions must execute.

Through the same image/SDK entrypoint, confirm `ssl`, `sqlite3`, `pydantic` and source commit. The development installation used Python3.12.14/SQLite3.53.1/OpenSSL3.5.8. The cloud's private3.51.3/3.5.7 combination needs its actual operator receipt; this document does not claim that host was tested.

Web tar contains the separate `nana-space-web/` static root. Keep it in a candidate location; do not overwrite active Web. Register source/root/interpreter/integrity only through the original sealed Supervisor/Host Operator path. Core and Gateway must select the same registered release; the updated bootstrap follows Supervisor state before credentials/Subject startup. Preserve canonical home, roles, existing HTTPS, Vault, old slots and rollback. Activation, live restart, live routing and host permission changes follow existing production authorization.

## Recorded evidence

Installed edd170f DEV bundle: ten API views, original Core offline chat, backup, same-ID restart, real original-Store note creation/correction/restart/search/withdrawal passed. New World/semantic/recovery77 tests passed49.97s; frontend59 unit and20 responsive browser plus8 specific admission/UNKNOWN checks passed. Full matching-source run:1933 passed/1 failed/12 skipped604.46s. The sole failure was the repository status header listing9 evidence refs above its fixed8 bound, not a Runtime code failure. The header was compacted without changing the8 bound or deleting history; its existing failed test plus delivery checks then passed5/5 in0.21s. Raw full failure and targeted repair receipts are included; no second whole-suite run is claimed. No production update, private migration, real provider call or social send. Human, physical phone, real host and cross-day gates remain open; bwrap code execution remains blocked.

## New407 memory flow

Memory center now saves explicitly consented user statements and corrects that note family through original Core. Manager/scope/privacy and PERSONAL retention authorization remain required. Old servers without memory_notes capability keep draft-only behavior. Save is verified by independent Store readback. On uncertain transport do not submit again: check the original receipt, which reconciles only when the original source-bound commit proof still supports the request. Withdrawal hides/erases dependent proof and never revives an old correction. Notes are user declarations, not Nana experiences or proven world facts. Saved/retrieved is not proof of automatic conversation recall or human naturalness.

Pure concern reassessment recognizes actual changed World snapshots through the original session while counting the same raw event once. It never replays adopted work or UNKNOWN. Original407 first full run failed and is preserved; this candidate includes the independently verified repair.
