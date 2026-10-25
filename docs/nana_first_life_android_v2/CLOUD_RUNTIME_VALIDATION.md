# Supplied cloud runtime — actual isolated qualification, 2026-10-26

GLOBAL_STAGE H / Advanced Growth. This continues Android V2; no new framework,
Subject architecture, production owner, paid Provider call or social delivery.

## Verified inputs and results

Four parts reconstructed the exact113321598-byte ZIP with SHA256
`95617d43deb9678f2dbd7b307df81ff77c849305793b94035523f86ae76428a5`.
All part hashes,15-entry ZIP CRC,13 handoff seals,4766 regular-file hashes and10
relative symlink targets passed. CODEX_HANDOFF was read before running supplied
scripts. The SDK archive SHA256 is
`1dbbcf46f6a16ab41deac96657a43a8fcecbba6ab7dea1d0113a84b2c8285b27`.
Its bytes were reused; Python/SQLite were not rebuilt or replaced.

Actual Debian13 image, fixed UID/GID999, no capabilities, no-new-privileges,
read-only root/SDK,512MiB,1CPU,64PIDs:

- Python3.12.14, prefix `/opt/nana-core/runtime`, loaded private SQLite3.51.3.
- OpenSSL3.5.7, ssl/hashlib/ctypes, WAL/FTS5/JSON/transaction/integrity passed.
- Real public PyPI TLS HTTP200 with certificate and hostname validation. Managed
  proxy/public CA used as a temporary read-only mount, never baked into the image.
  This is not a model request or cloud production-network qualification.
- Supplied verify script7 PASS/0 FAIL in fresh `/tmp` tmpfs. It is not strictly
  read-only: its fixed temporary DB write is confined to that disposable namespace.
  Independent `-I -B` probe asserts prefix, exact SQLite and actual loaded library
  paths; it supplements the supplied script's weaker diagnostic checks.
- Original Core installed offline from its hash-bound243-file archive. No source
  repository PYTHONPATH, new dependency, alternative sqlite binding or model key.

Actual qualified local image:
`sha256:84396a934f15351fc60fd47e9e02e6d89f34c7fbfe989ef125df906a0a067950`.
Core source is `dbfb37ebe5c82edcfba6d50ba4f41a02ab8f358e`; image infrastructure is
the new development commit. Core/Web/APK business bytes are unchanged from the
previous qualified delivery. Docker builds use the pinned Debian base plus
recorded OS packages; the image ID, not a mutable tag, identifies this result.

## Actual defects repaired

1. SDK extraction inherited private umask0077, preventing UID999 access. Explicit
   modes apply only to the new non-sensitive SDK tree; Subject directories remain
   private0700. Tests cover both.
2. Docker published18765 to a BFF listening only on container loopback. A bounded
   infrastructure relay18766→127.0.0.1:18765 now preserves Host/Origin/auth bytes.
   Host publication remains127.0.0.1 only. The original BFF still enforces its
   loopback/Host/Origin/CSRF/auth rules; this relay is no Subject or planner.
3. First boot had no path for its operator password. Optional non-TTY stdin FD0
   reaches only the existing bounded gateway reader; subsequent service starts
   use salted hashes. No plaintext file/env/argv or Provider secret lookup.
4. Image build omitted the required parent for the trusted Core unpacker. It is
   created explicitly; digest/clean-destination checks remain unchanged.
5. Web build is now a digest-bound static release in the same image, with path,
   link, type and decompression bounds. It is the same LIVE build packaged in APK.

All failed attempts are retained in `evidence/cloud-sdk-failure-history.json` and
the external raw qualification directory. Harness corrections did not relax
Core checks: the intentional root303 must target `/index.html?source=live` and
that exact LIVE page must return200; copied private releases must retain UID999.

## Real development lifecycle

Fresh explicitly marked DEV identity, never the cloud's formal Nana:

`four mapped volumes → first password pipe → published host loopback → login →
original START → ten pages → LIVE Web → original C offline PROJECT turn →
quarantined BACKUP → SIGKILL BFF → Docker automatic restart → same identity →
intentional STOP → remove/recreate container with retained volumes → STOP latch →
same identity START → STOP → original B8 export/receive → old-source fence`.

Same subject/lineage, epochs2→3→4, automatic restart1. New restored Store has one
identity, quick_check=ok,0 FK errors,0 Provider requests,0 inherited execution
Grants. SDK write actually failed EROFS. Data/logs/backups each UID999,0700 and
actually writable. Review backup remains quarantined; it was not blindly opened
as a second active Subject. Source was retired before B8 activation.

## Reproduce without touching production

From this checked-out dev branch, use a **new isolated work directory**:

```sh
python tools/nana_first_life_android_v2/prepare_image.py \
  --runtime /path/to/verified/handoff/artifacts/nana-core-runtime-py31214-sqlite35103.tar.gz \
  --destination /path/to/new-isolated-build-context
```

The emitted JSON contains exact argument arrays, runtime/Core/Web digests and
source pin. Use the managed local Docker daemon, preserve proxy settings, and
supply its public CA through the documented BuildKit secret mount. Build target
`qualified-runtime`; default `verify` never opens a Store or creates an identity.
Do not run `compose up` or `serve` on the production host before approval.

Run `runtime_abi_probe.py` with the supplied SDK Python `-I -B` in that read-only
container. `--tls` performs only the fixed public PyPI check. Run
`cloud_docker_probe.py --image <qualified-local-image> --work <new-dev-directory>
--web-sha256 8d55d97d59b6cefef74fe18651092960ac3fd5b3399606ee19b07f098a0fc90c`
for the actual isolated lifecycle. Its seed is explicitly DEV and all Provider
budgets are zero. It never contacts AstrBot, a phone or a model.

## Production preparation and remaining gates

Selected host layout stays `/srv/nana-core/{runtime,data,logs,backups}` → container
`/opt/nana-core/` same four names. Export the image's **complete non-sensitive**
runtime tree, including offline Core and Web releases, to a temporary new staging
directory first. Preserve/restore private Core-release UID999 ownership after
`docker cp` (default copying can change it). Validate hashes and permissions before
an approved install; mount runtime read-only. Do not mask it with an empty volume,
relocate its RUNPATH, copy old overlay data or place Subject files in the handoff.

An operator must prepare the three writable directories as999:999/0700. The
compose artifact refuses automatic host-path creation and has an inactive approval
profile. BFF publication is host127.0.0.1:18765→container18766; only a separately
approved private HTTPS proxy may forward it. Existing6199/Tailscale root routes,
AstrBot, QQ and Iris are unchanged. No public control endpoint or Funnel.

For first login setup, pass the operator's input through a non-TTY stdin pipe to
`serve --password-fd 0` in an approved deployment. Stop that initial setup service,
then run ordinary `serve` with persisted auth hashes, never store plaintext or
leave password-FD mode as an automatic restart command. Initial binding still
requires the separately approved canonical identity/activation receipts.

No safe cloud access is bound here: actual `/srv` preparation/deployment, formal
genesis, private history, old writers, QQ delivery and production cutover remain
NOT_RUN. bwrap stays BLOCKED; no privilege expansion or unsafe execution fallback.
Release signing, physical Android/Keystore/notifications, daily Provider budget,
human naturalness and production canary/72h remain separate gates. Existing debug
APK and unsigned release are delivered; the software-emulator installation failure
remains recorded. FIRST_LIFE=NOT_READY and BETA=NO.
