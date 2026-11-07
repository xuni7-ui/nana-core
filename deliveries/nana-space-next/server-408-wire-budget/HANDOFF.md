# Server-only exact byte-reservation refinement, compatible with408

Runtime source: `de08f8fe003e8188d3e661e5ae134a40fee3bc35`. Existing408 APK/Web remains source f712136. No phone reinstall, no new474MB V4 release, no new subject or schema. Use this replacement candidate Core archive rather than editing files inside a sealed older candidate. Original408 artifact set stays historical and unchanged.

Download/keep both the original matched408 manifest files and this server patch. The current checker verifies their hashes, actual source pins and retained runtime features; it does not authorize activation. From that complete downloaded delivery root:

```sh
python3 server-408-wire-budget/verify-current.py --root . --current CURRENT-DELIVERY.json
(cd server-408-wire-budget && sha256sum -c SHA256SUMS)
python3 server-408-wire-budget/nana-unpack.py server-408-wire-budget/nana-core-de08f8f-portable.tar.gz --sha256 fbfe1399ce882ad5d310427039e47d767749e7a4e87fa5924d2258ebbf86741f --destination /srv/nana-core/candidates/next-408-wire-de08f8f
```

The parent must be an existing private operator-owned directory. Unpacker rejects an existing destination, links, traversal and oversized archives. If the destination exists, stop and inspect; do not erase it. No Subject is created during extraction. Check `runtime.json` source against the commit above; bootstrap verifies the279-file bundle. Hashes are integrity evidence, not production approval.

Reuse the already qualified Debian13 image/private SDK. Preserve `/srv/nana-core/runtime` → `/opt/nana-core/runtime` read-only. The source package supplies locked offline wheels, not a replacement private Python. Set the following **non-secret selectors** to values from the existing approved host inventory: `NANA_QUALIFIED_IMAGE` (full digest), `NANA_RUN_UID` and `NANA_RUN_GID` (numeric). Never guess a tag, infer UID from an account display name, or modify old AstrBot permissions.

Make only the new candidate and a new scratch directory writable by that numeric owner, then install in isolation:

```sh
docker run --rm --network none --env NO_PROXY=127.0.0.1,localhost --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /opt/nana-core/runtime/bin/python3 \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-408-wire-de08f8f,dst=/candidate \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /candidate/bootstrap.py install
```

Do not omit `--entrypoint`: the ordinary production image entrypoint must not start a live Core during this check. Mount no live Subject, data, Vault, auth or Docker socket. Do not chown the existing data tree.

For actual installed validation, set `NANA_CHECKS_DIR` to the absolute downloaded `server-408-wire-budget` directory and `NANA_SCRATCH_DIR` to a fresh private writable scratch directory. Candidate is now read-only; only scratch is writable:

```sh
docker run --rm --network none --env NO_PROXY=127.0.0.1,localhost --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user "$NANA_RUN_UID:$NANA_RUN_GID" \
  --entrypoint /candidate/.venv/bin/python \
  --mount type=bind,src=/srv/nana-core/runtime,dst=/opt/nana-core/runtime,readonly \
  --mount type=bind,src=/srv/nana-core/candidates/next-408-wire-de08f8f,dst=/candidate,readonly \
  --mount "type=bind,src=$NANA_CHECKS_DIR,dst=/checks,readonly" \
  --mount "type=bind,src=$NANA_SCRATCH_DIR,dst=/tmp/nana-check" \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "$NANA_QUALIFIED_IMAGE" -I -B /checks/verify-note-recall.py --bundle /candidate --work /tmp/nana-check/probe --output /tmp/nana-check/result.json --check-wire-reservations
```

This verification intentionally creates a fresh **DEV** identity in scratch, exercises loopback BFF and original Core, and stops only those test processes. It is not canonical Genesis, private migration or production recovery. Short container scratch paths prevent Unix-socket length failures. Do not pass `-O`; qualification assertions must execute.

Through the same image/SDK entrypoint, confirm `ssl`, `sqlite3`, `pydantic` and source commit. The development installation used Python3.12.14/SQLite3.53.1/OpenSSL3.5.8. The cloud's private3.51.3/3.5.7 combination needs its actual operator receipt; this document does not claim that host was tested.

Web tar contains the separate `nana-space-web/` static root. Keep it in a candidate location; do not overwrite active Web. Register source/root/interpreter/integrity only through the original sealed Supervisor/Host Operator path. Core and Gateway must select the same registered release; the updated bootstrap follows Supervisor state before credentials/Subject startup. Preserve canonical home, roles, existing HTTPS, Vault, old slots and rollback. Activation, live restart, live routing and host permission changes follow existing production authorization.

## Actually run, and limits

279files, two byte-identical builds. Final actual archive extracted and installed offline; original BFF/ten views/chat/notes/correction/restart/withdrawal/backup/stop passed, then SAME DEV Subject+lineage completed two loopback fixture model calls. Independent HTTP receiver lengths agree with reservations: INTERPRET19311input+8192response cap+1probe=27504bytes; SOCIAL19741+8192+1=27934. Old408 reservations69388/71608 remain historical, never refunded. All original cost/call/UNKNOWN bounds remain. No provider tokens or cost reduction is inferred from bytes; pure serialization P95 increases from0.19 to1.12ms on a synthetic descriptor. Actual provider/network/model inference latency is not measured by that microbenchmark.

Related tests:18boundaries,12dialogue/byte-budget; broad149passed/1new fixture failure (original background sub-budget), then corrected fixture4passed. No full-suite pass claimed. No real provider, live host, phone, human/cross-day qualification or production activation. Original G/needs/Fish and memory source mechanisms inherited. Full model-token wire budgeting and retrieval-feedback learning remain open, not replaced by these developer changes.
