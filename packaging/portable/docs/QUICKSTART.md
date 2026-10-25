# Portable Cloud Runtime V1

Ubuntu/Debian-like x86_64 Linux, CPython **3.12**, glibc>=2.17, SQLite>=**3.51.3**
with JSON and FTS5 in that Python's actual binding. This preserves Store's WAL-reset
corruption-fix requirement. The installer checks both itself and the target venv;
preflight never passes an older SQLite merely because JSON/FTS5 work.
Required stdlib/native modules also include ctypes,ssl,zlib,sqlite3,resource,
termios and venv. A partially built Python can initialize a Store yet lack the
ctypes process-isolation primitive; this is now refused before install/identity.
The private-source recipe builds libffi explicitly. Optional bz2/lzma/curses/Tk
are not required by this runtime; the source-build host must support its input
archive compression and provide OpenSSL/zlib/toolchain headers.
Use a non-root account, >=512MiB memory, >=128 FDs and >=64MiB
free runtime space (additional install space required). Python and python3.12-venv
must already be installed by the host operator. No apt/root/systemd install occurs.
No ffmpeg/ffprobe is required for this text/Inspector runtime; capture/audio are off.

1. Upload the archive, its separately checked SHA256 and nana-unpack.py.
2. Safe extraction (destination must not exist):
   `python3 nana-unpack.py nana-first-life-portable-v1.tar.gz --sha256 <published-sha256> --destination ./nana`
3. `cd nana && ./install.sh /path/to/python3.12` (entirely offline, hashed wheels).
4. `./nana preflight` checks the host without creating a Subject.
5. Choose **one** explicit mode:
   - New test identity: `./nana init --fresh` prints **NEW SUBJECT CREATED**.
   - Same identity: follow MIGRATION.md; never use init as a restore fallback.
6. `./nana start --seconds 3600` runs the original foreground Runtime.
7. Another SSH terminal: `./nana health`, `./nana inspect`, `./nana chat`.
8. `./nana stop`; restart with `./nana start` or `./nana restart`.

Default home is bundle-relative `var/subject`; every command supports
`--home /absolute/private/path`. No dependency on a repository checkout, cwd,
Codex, username, developer venv, paid provider, AstrBot or social account.
Do not put the home under materials/. Private directories require0700/files0600.
Start never invents an identity; occupied init/restore destinations are rejected.

The initial runtime is paused, offline, no execution Grants. `./nana resume`
permits reconsideration, never grants effects or paid calls. The bounded local
example portfolio is disabled by default. Chat is explicitly limited offline
until you configure a separately authorized provider. Human naturalness remains
NOT_RUN. Do not label fresh Subject as the current Nana or this bundle production.

First-run checklist: published archive checksum; install/pip check; preflight;
explicit mode; inspect canonical identity; start/health; private chat; stop; backup;
record source commit from runtime.json. Keep first-live budgets separately approved.


## Optional isolation and host paths (Engineering Quality V2)

`preflight.optional_capabilities.generated_python_skill` independently reports
AVAILABLE/UNAVAILABLE/BLOCKED after an actual same-policy bwrap probe, not just
executable lookup. Missing bwrap or denied user namespaces do not prevent paused
base Runtime/chat/Inspector, but generated Python skills cannot run. There is no
unsandboxed fallback. Optional skills require bubblewrap, Linux user/mount/PID/
network/IPC/UTS namespaces, system `/usr/bin/python3`, resource limits and the exact
read-only system mounts. No workspace/home/root/DB/credential is mounted. Host
operators provide system packages/policy; this installer never uses apt/sudo.

Every filesystem Unix socket path is checked in **encoded bytes**, max107 on
Linux, before creating a control-enabled Subject/owned service. Choose an explicit
short private home when needed; Core never relocates/copies an identity for you.
A foreign path/symlink,live or uncertain owner,permissions error and long path are
separate refusals. Only the original writer lock/lease permits stale socket cleanup.
Dev startup readiness deadlines do not change Action/lease/Verify deadlines.

A distro Python3.12 may still link SQLite3.45 and is correctly rejected. Use a
qualified host Python, or the separate developer `build_private_python` recipe
with verified official source archives in a fresh user-owned prefix. SQLite is
linked through that Python's private RUNPATH, not LD_PRELOAD, sqlite3 monkeypatch,
system Python replacement or an alternate Store. Rebuild the host dependency on
a new machine; it is not Subject identity or part of SubjectPackage.
