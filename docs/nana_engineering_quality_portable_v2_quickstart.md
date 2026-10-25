# Engineering Quality & Portable Runtime V2 — reproduce

GLOBAL_STAGE H, OWNED_DEV qualification only. No production/social/private data,
credential discovery, device control or paid Provider call is needed or authorized.

## Choose a qualified Python binding

The actual Runtime interpreter must be Linux x86_64/CPython3.12 with SQLite>=3.51.3,
JSON and FTS5. A system Python with3.46.1 is rejected even if JSON/FTS5 work.
This is the WAL-reset corruption-fix requirement, not a syntax convenience.
The installer separately probes the selected Python and its target venv before
pip/identity creation. Do not monkeypatch sqlite3 or install pysqlite3 as a bypass.

On a host without a qualified binding, use an isolated user-owned Python build.
Obtain archives from official HTTPS origins and verify their published/trusted
digests. This task's source receipt pins the downloaded content; it does not
claim independent release-signature verification.

```sh
python3.12 -m tools.nana_quality.build_private_python \
  --root /absolute/fresh/private-host \
  --sqlite-source /approved/sqlite-autoconf-3510300.tar.gz \
  --sqlite-sha256 81f5be397049b0cae1b167f2225af7646fc0f82e4a9b3c48c9ea3a533e21d77a \
  --python-source /approved/Python-3.12.14.tar.xz \
  --python-sha256 5c8462af5790baf43a321a1559dbe0db06d1be4300fb85fb53c40060668e548a \
  --ffi-source /approved/libffi-3.4.6.tar.gz \
  --ffi-sha256 b0dea9df23c863a7a50e825440f3ebffabd65df1497108e5d437747843895a4e
```

Official sources: https://sqlite.org/2026/sqlite-autoconf-3510300.tar.gz and
https://www.python.org/ftp/python/3.12.14/Python-3.12.14.tar.xz and the
libffi release https://github.com/libffi/libffi/releases/download/v3.4.6/libffi-3.4.6.tar.gz .
The recipe builds private libffi so `_ctypes` is not silently omitted. Both
installer and target venv must have ctypes/ssl/zlib/sqlite3/resource/termios/venv.
Compiler success alone is insufficient; all runtime imports must close. Build needs the
host C toolchain and standard Python build headers (OpenSSL,zlib,libffi,etc),
provided by the host operator. The tool never installs apt packages/uses root or
network. Jobs<=2. Use a fresh prefix without spaces/shell metacharacters. The real
_sqlite3 links private SQLite through RUNPATH; no LD_PRELOAD or system replacement.
The prefix is **host-specific**, not a portable identity or relocatable Python
binary. On another host rebuild dependencies and explicitly bind execution anew.

## Runtime and qualification artifacts are separate

Build from a fixed committed revision and a local wheelhouse matching the exact
five runtime dependency pins (unchanged from the previous release):

```sh
python -m tools.nana_portable_cloud.build --revision <runtime-source-sha> --output <fresh-output> --wheels <approved-wheelhouse>
python -m tools.nana_quality.qualification_package --revision <same-sha> --output <fresh-qualification-output>
```

Build twice in fresh destinations and compare archive SHA256. Runtime source is
selected by `packaging/portable/runtime-files.txt`; missing static import or known
dynamic worker fails the build. `runtime-boundary.json` lists shipped optional
capabilities and assets. Demos/qualification/lab/fake_world do not ship in ordinary
Runtime. Materials are finite public sample data, disabled for autonomous use by
default, never Nana's life history. The separate qualification addon is only an
explicit developer harness; its README explains installed `-I` execution.

Verify archive hash, then use `nana-unpack.py` into a fresh private destination.
`./install.sh /qualified/python3.12` is offline and hash-locked; preflight/imports
do not mutate checksummed source with pyc files. Use a non-root host account.

```sh
./nana preflight
./nana init --fresh                  # NEW test Subject, never a restore shortcut
./nana start --seconds 3600
./nana health                       # another terminal
./nana chat                         # offline until separately authorized Provider
./nana inspect
./nana stop
./nana restart --seconds 3600
```

Same-identity transfer uses `export --retire-source` and `restore` with destination
ID and package SHA; old owner stays fenced and old Grants stay revoked. Backups
are quarantined review copies, never an automatically runnable second Subject.
Pending UNKNOWN is preserved and cannot silently retry. Do not hot-downgrade
extended Precision plans/checkpoints into old executables. Follow official
quiesce/backup/lineage transfer; do not copy a live DB over newer lineage.

## Optional skills, paths and diagnostics

Base Runtime readiness is separate from generated Python Sandbox readiness.
Missing bwrap or denied namespaces gives UNAVAILABLE/BLOCKED, with no fallback
to direct exec. Optional skills need bwrap, system `/usr/bin/python3`, namespaces,
the original AST whitelist/read-only mounts/clearenv/CPU/memory/FD/output/time
limits, independent tests/review and ordinary invocation Grant/Manager/Budget.
Source withdrawal still retires support. Availability is not execution authority.

Use an explicit short private home: final Unix socket path<=107 encoded bytes.
Multibyte characters count by filesystem bytes. Core never silently moves/copies
an identity. Long path,foreign socket/symlink,permission failure and active or
uncertain owner are separate refusals. Only the locked original owner can clean
an old owned socket. Dev readiness15/max30 seconds is not an Action/lease/Verify
timeout change. Missing optional media/provider/device capability stays denied.

## Developer checks

Install pinned `requirements-quality.lock` in an independent dev venv. It is not
a runtime dependency. Run `tools.nana_quality.metrics`, Ruff and the targeted
shared-host-contract mypy check. Global existing C901/unused-import debt is
reported, not hidden with ignores. Reformat only the reviewed hotspot list;
pure formatting commit retains identical AST, separate from behavior changes.

New package installation, actual optimized-mode qualification, minimum-binding
workflow and full source-pinned regression results belong to this task's final
evidence. Historical1528/0/12 and bcb archive remain baseline evidence only.
Human/semantic/model-ablation NOT_RUN, old5h PARTIAL_EXTERNAL_LIMIT, new residency
pending, First-Life NOT_READY/Beta NO remain separate qualifications.
