# Server-only daily defaults and original retrieval growth, compatible with408

Runtime source: `f03fcbbb6e8c7d0aa490d71aa89dfa128374dda7`. Existing408 APK/Web remains source f712136. No phone reinstall, no new474MB V4 release, no new subject or schema. Use this replacement candidate Core archive rather than editing files inside a sealed older candidate. Original408 artifact set stays historical and unchanged.

Download/keep both the original matched408 manifest files and this server patch. The current checker verifies their hashes, actual source pins and retained runtime features; it does not authorize activation. From that complete downloaded delivery root:

```sh
python3 server-408-retrieval-growth/verify-current.py --root . --current CURRENT-DELIVERY.json
(cd server-408-retrieval-growth && sha256sum -c SHA256SUMS)
python3 server-408-retrieval-growth/nana-unpack.py server-408-retrieval-growth/nana-core-f03fcbb-portable.tar.gz --sha256 ce518a23e3ec431b22f1b2a4e7441c84f57770ea2f65a133d9ac100c738ff25e --destination /srv/nana-core/candidates/next-408-wire-f03fcbb
```

The parent must be an existing private operator-owned directory. Unpacker rejects an existing destination, links, traversal and oversized archives. If the destination exists, stop and inspect; do not erase it. No Subject is created during extraction. Check `runtime.json` source against the commit above; bootstrap verifies the280-file bundle. Hashes are integrity evidence, not production approval.

Reuse the already qualified Debian13 image/private SDK. Preserve `/srv/nana-core/runtime` → `/opt/nana-core/runtime` read-only. The source package supplies locked offline wheels, not a replacement private Python. Set the following **non-secret selectors** to values from the existing approved host inventory: `NANA_QUALIFIED_IMAGE` (full digest), `NANA_RUN_UID` and `NANA_RUN_GID` (numeric). Never guess a tag, infer UID from an account display name, or modify old AstrBot permissions.

Make only the new candidate and a new scratch directory writable by that numeric owner, then install in isolation:

```sh
docker run --rm --network none --env NO_PROXY=127.0.0.1,localhost --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /opt/nana-core/runtime/bin/python3 \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-408-wire-f03fcbb,dst=/candidate \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /candidate/bootstrap.py install
```

Do not omit `--entrypoint`: the ordinary production image entrypoint must not start a live Core during this check. Mount no live Subject, data, Vault, auth or Docker socket. Do not chown the existing data tree.

For actual installed validation, set `NANA_CHECKS_DIR` to the absolute downloaded `server-408-retrieval-growth` directory and `NANA_SCRATCH_DIR` to a fresh private writable scratch directory. Candidate is now read-only; only scratch is writable:

```sh
docker run --rm --network none --env NO_PROXY=127.0.0.1,localhost --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /candidate/.venv/bin/python \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-408-wire-f03fcbb,dst=/candidate,readonly \
  --mount "type=bind,src=$NANA_CHECKS_DIR,dst=/checks,readonly" \
  --mount "type=bind,src=$NANA_SCRATCH_DIR,dst=/tmp/nana-check" \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /checks/verify-note-recall.py --bundle /candidate --work /tmp/nana-check/probe --output /tmp/nana-check/result.json --check-wire-reservations --check-retrieval-growth
```

This verification intentionally creates a fresh **DEV** identity in scratch, exercises loopback BFF and original Core, and stops only those test processes. It is not canonical Genesis, private migration or production recovery. Short container scratch paths prevent Unix-socket length failures. Do not pass `-O`; qualification assertions must execute.

Through the same image/SDK entrypoint, confirm `ssl`, `sqlite3`, `pydantic` and source commit. The development installation used Python3.12.14/SQLite3.53.1/OpenSSL3.5.8. The cloud's private3.51.3/3.5.7 combination needs its actual operator receipt; this document does not claim that host was tested.

Web tar contains the separate `nana-space-web/` static root. Keep it in a candidate location; do not overwrite active Web. Register source/root/interpreter/integrity only through the original sealed Supervisor/Host Operator path. Core and Gateway must select the same registered release; the updated bootstrap follows Supervisor state before credentials/Subject startup. Preserve canonical home, roles, existing HTTPS, Vault, old slots and rollback. Activation, live restart, live routing and host permission changes follow existing production authorization.

## Actually run, and limits

Runtimef03fcbb, tool-source edfd685. Two280-file builds equal,15001321bytes/SHAce518a23e3ec431b22f1b2a4e7441c84f57770ea2f65a133d9ac100c738ff25e. Actual final archive extracted/installed offline, original BFF/ten views/chat/notes/correction/withdrawal/backup/stop and same DEV identity+lineage restart passed. Independent installed study then original G plus a different later note in actual HTTP RENDER and source withdrawal passed. Six local fixture calls, real Provider0.139 related checks passed in three bounded groups; original failures retained, no full-suite PASS claim. Original exact-byte reservation and source/privacy/UNKNOWN rules inherited.

New-host presets128/day,64/hour,128/provider, inside original128 ceiling; fee defaults0, existing configurations are NOT rewritten. Plain Chinese operational notices retain structured states and UNKNOWN/no resend. Existing408 client works unchanged.

Optional learned note normalization is limited to16 retained PUBLIC/PROJECT notes and wordlike queries, with independent practice/evaluation/transfer and original C approval. More notes preserve original literal lookup and defer this narrow fallback. PERSONAL/unretained conversation is not study input. Original G remains the only learning authority; original C can watch/rest, no new timer or mandatory provider call. A checked counterexample suspends a method; source withdrawal removes support. This is controlled DEV retrieval learning, not broad semantic/human/long-life qualification.

The original control surfaces/Subject/Store/permissions/schema remain. No production activation/private migration/live vector/phone/human/cross-day proof is asserted. Current host resource/ABI/profile and live operator receipt are still required; do not edit sealed files, copy live credentials into checks, or create a second formal identity. Full model-token framing and real streaming remain separate unfinished product work. This is the same continuous task, not a new release line.
