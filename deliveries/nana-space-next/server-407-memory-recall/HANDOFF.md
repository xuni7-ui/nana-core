# Server-only memory recall patch, compatible with407

Core source: e7c28e7f899bde7fa1787a2cdc9804ab5b7b4dce. Android/Web407 remain pinned to edd170f; this is an explicit compatible server patch, not a falsely matching new three-component release. HTTPv2, pairing, appId, signature and native operation contracts are unchanged. No new APK installation needed if407 is installed. Original MANIFEST-407/ZIP and all old artifacts are unchanged. Do not download the old474MB release again.

Adds original-Store note selection through existing INTERPRET/RENDER with no extra model call, ephemeral hints, current-source/privacy checks and explicit statement/non-lived-event attribution. Original C/autonomy/relationship/S8/Manager/Grant/UNKNOWN remain. Known partial index preserves100ms, rejects substituted DDL and rebuilds through existing official portability rules. Pinned evidence blocks are byte-equal while discarded raw reads decrease.

Download this folder from the pinned delivery commit. From the parent downloaded deliveries/nana-space-next directory, paths below refer to actual files. MANIFEST.json in this patch folder records every file, source and SHA256.

## Operator steps: isolated candidate, no live changes

From the downloaded delivery directory:

```sh
(cd server-407-memory-recall && sha256sum -c SHA256SUMS)
python3 server-407-memory-recall/nana-unpack.py server-407-memory-recall/nana-core-e7c28e7-portable.tar.gz --sha256 e5dc0365e056eaa71458d551ba16701fb773988b5b604aacd694fe5683cc612c --destination /srv/nana-core/candidates/next-407-recall-e7c28e7
```

The parent must be an existing private operator-owned directory. Unpacker rejects an existing destination, links, traversal and oversized archives. If the destination exists, stop and inspect; do not erase it. No Subject is created during extraction. Check `runtime.json` source against the commit above; bootstrap verifies the279-file bundle. Hashes are integrity evidence, not production approval.

Reuse the already qualified Debian13 image/private SDK. Preserve `/srv/nana-core/runtime` → `/opt/nana-core/runtime` read-only. The source package supplies locked offline wheels, not a replacement private Python. Set the following **non-secret selectors** to values from the existing approved host inventory: `NANA_QUALIFIED_IMAGE` (full digest), `NANA_RUN_UID` and `NANA_RUN_GID` (numeric). Never guess a tag, infer UID from an account display name, or modify old AstrBot permissions.

Make only the new candidate and a new scratch directory writable by that numeric owner, then install in isolation:

```sh
docker run --rm --network none --env NO_PROXY=127.0.0.1,localhost --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /opt/nana-core/runtime/bin/python3 \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-407-recall-e7c28e7,dst=/candidate \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /candidate/bootstrap.py install
```

Do not omit `--entrypoint`: the ordinary production image entrypoint must not start a live Core during this check. Mount no live Subject, data, Vault, auth or Docker socket. Do not chown the existing data tree.

For actual installed validation, set `NANA_CHECKS_DIR` to the absolute downloaded `server-407-memory-recall` directory and `NANA_SCRATCH_DIR` to a fresh private writable scratch directory. Candidate is now read-only; only scratch is writable:

```sh
docker run --rm --network none --env NO_PROXY=127.0.0.1,localhost --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /candidate/.venv/bin/python \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-407-recall-e7c28e7,dst=/candidate,readonly \
  --mount "type=bind,src=$NANA_CHECKS_DIR,dst=/checks,readonly" \
  --mount "type=bind,src=$NANA_SCRATCH_DIR,dst=/tmp/nana-check" \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /checks/verify-note-recall.py --bundle /candidate --work /tmp/nana-check/probe --output /tmp/nana-check/result.json
```

This verification intentionally creates a fresh **DEV** identity in scratch, exercises loopback BFF and original Core, and stops only those test processes. It is not canonical Genesis, private migration or production recovery. Short container scratch paths prevent Unix-socket length failures. Do not pass `-O`; qualification assertions must execute.

Through the same image/SDK entrypoint, confirm `ssl`, `sqlite3`, `pydantic` and source commit. The development installation used Python3.12.14/SQLite3.53.1/OpenSSL3.5.8. The cloud's private3.51.3/3.5.7 combination needs its actual operator receipt; this document does not claim that host was tested.

Web tar contains the separate `nana-space-web/` static root. Keep it in a candidate location; do not overwrite active Web. Register source/root/interpreter/integrity only through the original sealed Supervisor/Host Operator path. Core and Gateway must select the same registered release; the updated bootstrap follows Supervisor state before credentials/Subject startup. Preserve canonical home, roles, existing HTTPS, Vault, old slots and rollback. Activation, live restart, live routing and host permission changes follow existing production authorization.


## Evidence and boundaries

Two exact-source offline builds byte-identical,279 bundle files. Actual local Python3.12.14/SQLite3.53.1/OpenSSL3.5.8 installation passed. Installed BFF/Core ten-page/chat/notes correction/search/withdrawal/backup/same DEV identity restart passed. Then the SAME stopped DEV identity completed INTERPRET→sourced note context→original C→RENDER through two actual local fixture HTTP calls, with same identity AND lineage verified. Real provider calls0; fixture wording is not real-model/naturalness qualification. verify-note-recall.py must remain beside verify-dev.py; use a fresh owned scratch only and do not use -O.

Affected116 tests passed54.22s; original S8/concern/H1 regression12passed5.15s; index/package32passed8.85s plus final index/fallback/substitution4passed0.46s. The historical complete edd170f run1933pass/1 project-header failure/12skip and its successful header repair remain accurately recorded; no new-source complete whole-suite success is claimed.

Actual cloud SDK3.51.3/3.5.7, physical phone, real provider/human/cross-day memory and live vector mapping are NOT_RUN here. Run the isolated tools in the existing approved container/SDK, then use the original sealed registry/Supervisor upgrade and rollback procedure. No live home/Vault/private data mounted by these checks. Do not hot-downgrade an active Store; original stopped/export/restore compatibility and single-owner fences remain.

This does not approve or execute production activation, real sends, private-history migration, fees, another canonical Subject or unqualified bwrap.
