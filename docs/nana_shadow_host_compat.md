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

The new archive was built from clean committed support `cd2e8a302a6dc53ee1bb4449a04aa5a739d58cf7`. It reuses the same original binary and private dependency files, revising runtime/support metadata only. Old bundle SHA256 `22ae38de7d2c751717a4ef351d0dc8f75491f2274a1bfea11e0a2e38c251b149` remains intact.

| Delivery item | Value |
|---|---|
| File | `nana-shadow-bootstrap-host3123-cd2e8a302a6d.tar.gz` |
| Bytes | 3,270,530 |
| Archive SHA256 | `c793991badd5efeaaa4676730278c2cdf3f2e01ee5ccafd1626edc4819b49c88` |
| Core SHA | `ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513` |
| Support SHA | `cd2e8a302a6dc53ee1bb4449a04aa5a739d58cf7` |
| Runtime content-map SHA256 | `95c7215bc78d43cae809e99fcc65c1572cd611c87ae273afb80138b61c01e6ec` |
| Runtime bytes including updated manifest | 8,537,337 |
| Verified Python releases | 3.12.3 and3.12.14 |
| Required SOABI | `cpython-312-x86_64-linux-gnu` |
| Minimum glibc | 2.34; actual3.12.3 environment2.39 |

Final full regression **each**:318 passed/0 failed/0 errors/1 skipped(E12). Actual extracted archive processes **both**:preflight/probe/restart-check/SIGKILL(-9)/UNKNOWN rollback/recovery/rollback/collect/tamper-block PASS. Each arm restores the same identity, one unique probe/Evidence/candidate/draft Plan/Decision; all proposed external calls SHADOW_BLOCKED; Action/Grant/production budget/messages zero. These are development-equivalent engineering measurements, not live AstrBot integration or semantic model acceptance.

The generated single archive is saved at `artifacts/shadow-bootstrap/` on the private development branch after per-entry/path/hash/credential/license checks. This narrow generated-delivery exception is recorded in upload_whitelist; no third-party upstream source repository is mirrored, and no runtime data/DB/secrets are included. No .github workflow exists or paid artifact service is invoked. The final GitHub download URL and remote byte verification receipt are recorded after that asset commit/push; the archive is not confined to /workspace.

Production changes/private memory/secret values/external messages/real model calls are zero. E12 remains NOT_RUN. Actual AstrBot stream, Iris extraction, execution/memory handoff and real-host re-run are outside this task.


## Smallest operator sequence

Download the one reviewed private GitHub archive, upload through the already available panel, and use a **new** independent extraction directory. No Python upgrade, pip, API key or environment variable is needed. This task does not perform these host operations.

```bash
set -eu
printf '%s  %s\n' 'c793991badd5efeaaa4676730278c2cdf3f2e01ee5ccafd1626edc4819b49c88' 'nana-shadow-bootstrap-host3123-cd2e8a302a6d.tar.gz' | sha256sum -c -
test ! -e nana-shadow-bootstrap-host3123-cd2e8a302a6d
tar -xzf nana-shadow-bootstrap-host3123-cd2e8a302a6d.tar.gz
cd nana-shadow-bootstrap-host3123-cd2e8a302a6d
./run_shadow.sh preflight
```

Only when `adapter_local_probe_ready=true`:

```bash
./run_shadow.sh probe
./run_shadow.sh restart-check
./run_shadow.sh rollback
./run_shadow.sh collect
```

A preflight overall UNKNOWN for unverified AstrBot/hook metadata does not negate a true adapter-local readiness, and does not establish actual host-hook binding. If readiness is false, the reason now identifies the failing condition; no bypass or host repair is prescribed. Readability/stop remains available through `./stop_shadow.sh` for the bounded foreground probe, and all scripts support --dry-run.

Evidence: `nana_shadow_host_compat_evidence/compatibility_matrix.json`, `final_delivery.json`, `final_3123_junit.xml`, `final_31214_junit.xml`, `bundle_validation_3123.json`, `bundle_validation_31214.json`, `new_bundle.json`. Archive Core55 source fingerprint stays original; no new Core SQL table/runtime dependency/full interpreter. Future live host re-run, message hook/Iris/semantic E12 remain separate unverified boundaries.
