# R045 First-Real-Shadow Release Candidate (merge-only)

Sole successor of R043 `2d83e6a2acfd07f5e67581543c9b7dff7e6d5cfa`. Created from R043,
then `--no-ff` merged Codex R044 pre-production red-team branch
`dev/nana-core-v1-r044-preprod-redteam-codex` (`1bdf1f07abb02d6610db86153b1cb7b14fe74dc1`).
Common merge-base `a436333d3dceb30773860ff5a3168ca1acdf6682`.

No cherry-pick of scattered fixes: R044 is absorbed as one complete merge so mutually
dependent security fixes are not split. No `main`, no force, no rewrite.

## Why the files did not conflict

R043 (relative to the merge-base) changed only `PROJECT_BRAIN/09|10|11`. R044 never touched
`PROJECT_BRAIN/09|10|11`; its change set is `artifacts/`, `docs/`, `manifests/`,
`src/plugins/astrbot_plugin_nana_shadow_observer/{bridge_client,bridge_wire}.py`,
`tests/nana_shadow/*`, `tools/nana_astrbot_shadow/*`. The two file sets are disjoint, so the
merge is clean and R043's host-readiness facts / D-049 correction / R042 preflight facts are
preserved untouched. R044 is **not** allowed to overwrite R043's field facts.

## R044 fixes mechanically confirmed present in R045

| # | Behaviour | Location |
|---|---|---|
| 1 | result-write failure does not skip cleanup | `bridge_worker.py` independent `finally` boundaries |
| 2 | IPC directory inode/FD fence | `bridge_wire.DirectoryFence` + `bridge_client.py` |
| 3 | capability published LAST | `bridge_worker.py` session.json before client.json |
| 4 | reject dangling symlink / FIFO / special entries | `package.package_members` |
| 5 | reject group/world-writable code/manifest/dirs (the R044 HIGH) | `package.package_members` `st_mode & 0o022` |
| 6 | Git review source rejects symlink blob | `onboarding.source_review` requires `100644 blob` |
| 7 | stale cleanup validates complete capability digest | `bridge_cli.stale_cleanup` `client_config_digest` |
| 8 | atomic publication never exposes nlink=2 | `bridge_wire._publish` renameat2 NOREPLACE |
| 9 | preflight never READY for expired / VERIFY_ONLY | `bridge_cli.preflight` live window + ONE_SHOT seal + production domain |
| 10 | symlink fixed diagnostic contract kept | `package`/`safety` raise `SYMLINK_PATH_BLOCKED` |

Corresponding tests: `test_r044_failures.py`, `test_r044_filesystem.py`,
`test_r044_supply_chain.py`, `test_r044_time_trust.py`, `test_r044_invariants.py`,
`test_r044_crash_matrix.py`, `test_r044_races.py`, `test_r044_privacy.py`,
`test_r044_protocol.py`, `test_r044_recovery.py` (219 new cases total).

## Regression

Approved private runtime CPython 3.12.14 / SQLite 3.51.3 / Pydantic 2.13.5:
**762 passed / 0 failed / 1 skipped (E12)**, 763 collected — identical to the R044
qualification. JUnit: `docs/nana_r045_evidence/full-regression.xml`.

Container caveat: the default `/tmp` here is overlayfs, which deterministically reuses a
just-freed inode for a newly-created object. `test_atomic_write_does_not_follow_symlink_or_
overwrite_foreign_file` needs non-reusing inode allocation; it fails identically on the
**unmodified R044 tree** in this container, so it is an environment artifact, not a product
regression. The qualifying run uses a tmpfs temp directory.

## Package

Rebuilt from the R045 final source; the old R042/R043 packages are superseded (R044 changed
bridge implementation / session journal / integrity gate / package logic / onboarding safety,
so old manifest/SHA must never be mixed with the new code).

- `artifacts/r045/nana-r045-empty-760e5e8-onboarding.tar.gz`
- size 3368374 bytes, SHA256 `05e9765c8a886d65077485d9c9f751f154b7260430ab06a099b9207e4c2bd68c`
- support/source SHA `760e5e829aa67b622b508c3f2c4a4e617528933f`
- production authorization pins EMPTY, runtime-proof pins EMPTY, seal_mode EMPTY
- Approved Core 55 exact (`ddabfc4…`), SQL schema drift 0, dependency drift 0
- dangerous archive entries 0, package permissions PASS, 277 entries
- two rebuilds with identical basename are byte-identical

## Status (unchanged, must not be over-read)

`OFFLINE_RECOVERY_QUALIFIED` is a fixture/offline conclusion and is **not** a real host PASS.
real AstrBot load = NOT_RUN; real dispatcher traversal = NOT_VERIFIED; real bridge = NOT_RUN;
real one-shot = NOT_RUN; host_binding = UNVERIFIED; FIRST_REAL_ASTRBOT_SHADOW = BLOCKED;
E12 = NOT_RUN. Dashboard upload / enable plugin / plugin_set / production authorization /
production seal / arm / real worker / real test message / reload·restart / Iris private read /
model call / push beyond the R045 branch: none performed.
