# Portable Cloud Runtime V1

Ubuntu/Debian-like x86_64 Linux, CPython **3.12**, glibc>=2.17, SQLite>=3.35
with JSON and FTS5. Use a non-root account, >=512MiB memory, >=128 FDs and >=64MiB
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
