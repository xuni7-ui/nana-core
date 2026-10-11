# Real host ABI compatibility correction

Baseline `99098b21c6d48948807fd2052f808e6c9e1aba6b`; old bundle support `3aba4eb4253cb30f27141831a4c983d714594e3a`; approved Core remains `ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513` with 55 original files unchanged.

## Blocker and fact source

[User provided] Host Ubuntu24.04/x86_64/glibc2.39/CPython3.12.3 at `/usr/bin/python3.12`, SOABI `cpython-312-x86_64-linux-gnu`, extension suffix `.cpython-312-x86_64-linux-gnu.so`, old preflight BLOCKED_RUNTIME_ABI. This task does not log in or touch that host.

[Measured source and development runtime] Old `bootstrap_entry.runtime` rejects `platform.python_version()!=3.12.14` before any private extension load. Actual Ubuntu CPython3.12.3 reproduces this old failure. Therefore it is a patch-string rejection, not evidence of extension ABI incompatibility.

## Actual equivalent environment

Docker development image uses pinned Ubuntu24.04 base digest `sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55`. Development image ID `sha256:351dd13f5f7c094b59ceba151ae5e5d703569db9ae835f168e4cbbcaffbf932c`. Actual distro Python `3.12.3-1ubuntu0.17`, libc `2.39-0ubuntu8.9`; executable `/usr/bin/python3.12`, SOABI and suffix match the supplied host. Packages/version/image identity are recorded; this is not a claim of bit-identical host distro revision/kernel. Containers run without external network, as UID1000, no capabilities, no-new-privileges. No production path or credential is mounted. Apt installs are confined to the development image, never the host.

Official CPython3.12.3 source was downloaded as a fallback input, but not built: the real Ubuntu3.12.3 interpreter was directly available. Download receipt is retained; do not claim source-build evidence.

The existing extension SHA256 `c18e64abba400c9c1ee91327680ce388dd51b4fb090b52ad829257ba19d82705` loads actual SQLite3.51.3, and existing private wheels import actual Pydantic2.13.5. Full original-runtime comparison:306 passed/0 failed/0 errors/1 skipped(E12). Actual WAL/backup probe and205 connection create/close cycles keep Connection class refcount53 ->53. These bounded measurements do not prove absence of every possible future refcount defect. Full tests include the existing real SIGKILL, replay/import/owner/Kernel/dedup/shadow/backup invariants. Initial comparison failed4/errored6 because Git was missing from the test image; corrected the image, retained failure logs, changed no assertion.

## Corrected policy and scope

Require CPython, Python major/minor3.12, normal build ABI, Linux x86_64, exact SOABI/suffix above, glibc>=2.34 and successful loading of pinned private SQLite/Pydantic. Do not compare patch strings as ABI conditions. Regression coverage is3.12.3 and3.12.14; other3.12.x remain UNTESTED even if they match the ABI shape. Preflight explicitly exposes this coverage distinction.

Failure classification distinguishes implementation/minor/build/OS/architecture/SOABI/suffix/glibc/extension load/dependency load/runtime version. Failure report preserves only non-sensitive HOST_GLOBAL_ENV/SHADOW_RUNTIME_ENV and sets adapter_local_probe_ready=false. Success reports native host metadata and actual private SQLite/Pydantic/extension build vs ABI target. Startup remains-I -B -S. TLS/SQLite reliability/shadow barriers are not relaxed.

Repackage the original runtime unchanged using `--runtime-from` the integrity-checked old bundle. Binaries/private dependency contents keep runtime content-map hash `95c7215bc78d43cae809e99fcc65c1572cd611c87ae273afb80138b61c01e6ec`; only runtime metadata is revised. No full isolated Python is shipped, no system install or environment variables are needed by the operator. P4 rebuild is NOT_NEEDED.

## Delivery status

New archive and final validation are pending the committed support checkpoint. The old archive remains intact. The final single archive will also be saved as a reviewed generated deployment asset on the private development branch; it is not a third-party source mirror or a production deployment. Archive entry/path/hash/license/credential-pattern checks precede upload. No workflow/paid artifact service is triggered.

Production changes/private memory/secret values/external messages/real model calls are zero. E12 remains NOT_RUN. Actual AstrBot stream, Iris extraction, execution/memory handoff and real-host re-run are outside this task.
