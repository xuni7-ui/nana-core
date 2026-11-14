# Portable Cloud Runtime V1

Ubuntu/Debian-like x86_64 Linux, CPython **3.12**, SQLite>=**3.51.3**
with JSON and FTS5 in that Python's actual binding. This preserves Store's WAL-reset
corruption-fix requirement. The installer checks both itself and the target venv;
preflight never passes an older SQLite merely because JSON/FTS5 work.
The glibc minimum depends on the built features: the base bundle declares
**glibc>=2.17**, while a bundle with **HOST_VAULT requires glibc>=2.34**.
Use `supported_platform` and `features` in that verified bundle's `runtime.json`,
not the base minimum, when selecting a host. Metadata review does not replace
the actual installer and preflight checks.
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
3. `cd nana`; inspect the platform metadata shown below, then run
   `./install.sh /path/to/python3.12` (entirely offline, hashed wheels).
4. `./nana preflight` checks the host without creating a Subject.
5. Choose **one** explicit mode:
   - New test identity: `./nana init --fresh` prints **NEW SUBJECT CREATED**.
   - Same identity: follow MIGRATION.md; never use init as a restore fallback.
6. `./nana start --seconds 3600` runs the original foreground Runtime.
7. Another SSH terminal: `./nana health`, `./nana inspect`, `./nana chat`.
8. `./nana stop`; restart with `./nana start` or `./nana restart`.

Before invoking `install.sh` in step 3, inspect the extracted, checksum-verified
bundle from that directory without starting Core or creating a Subject:

```sh
python3 -I -c 'import json; m=json.load(open("runtime.json")); print(m["supported_platform"]); print("features:", ", ".join(m["features"]))'
```

Run the remaining commands from this same bundle directory. If the declared
platform is unsupported, use a matching host; this guide does not authorize
replacing system libraries or weakening the original checks.

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


## 开发版后台模型资源

新版本的模型运行预算页可显式选择“后台按需使用模型”。默认关闭；开启后，在下一次明确重启时才绑定原有路由和预算。保存配置本身不调用模型，后台请求与聊天共用原额度，不提供额外费用授权。缺少已授权的模型路由时保持未绑定；主体的原轻量生活机制继续运行。

这是宿主 life.json 的 provider_background_cognition 资源选项，不是主体人格或思想许可；主体包不携带它。旧客户端只改预算时保留当前选项。改变后台选项会重置本页的计费同意，需要明确选择后再保存；重启前仍使用原运行设置。

返回不识别此选项的旧软件前，先在当前版本关闭该选项并保存（关闭值从 life.json 中省略），再停机并按原回退流程返回旧包。不要把仍含开启字段的配置直接交给旧的严格配置读取器。该开发入口不表示 CURRENT 或生产已经升级，实际安装、手机及真实模型资格分别核对。
