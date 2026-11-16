# NanaLink video source: old-reader storage qualification

C-owned incremental evidence on A baseline `90a31b6d10118061c55bf7d3821920b22713463c`; the existing source lineage implementation was integrated through PR #20. This is a synthetic storage compatibility check, not a replay of the Manager/Grant/Kernel watch action, a production migration, or a real Bilibili account test. The original watch and H1/World path have separate evidence in `../platform-compat-20261116/README.md` and A's PR #20 integration evidence.

The developer tool constructs a fresh temporary original Store with a source-bound video and sampled frame, closes it, and opens it with a copied, fingerprint-verified old Core reader at `cfd11be158a3f0fa36abf93f42d5e4fde1f55bf0`. It verifies the same subject identity, the video's original source dependency and readability. The current reader then withdraws the parent; the old reader reopens the same Store, finds the dependency and both DELETED tombstones, and cannot read either video or frame. `PRAGMA user_version` remains 13; this alone does not assert that opening a Store performs no other writes. No network or model calls occur. A deliberately altered old source was refused before its code could execute.

Reproduce in an isolated checkout (the old source must be the exact archive, not an arbitrary installed package):

```sh
mkdir -p /tmp/nanalink-old-cfd
git archive cfd11be158a3f0fa36abf93f42d5e4fde1f55bf0 | tar -x -C /tmp/nanalink-old-cfd
PYTHONPATH=src:. python tools/nanalink_video_rollback_qualification.py --old-source /tmp/nanalink-old-cfd
```

The pinned 322-file old `src/nana_core` tree has SHA-256 `0049c39500db44ca2dbcb089bd022502799db44f3aa1a967efae2e469062419d`. On the baseline above the before/after identity and dependency checks passed. Related original video lineage, video history, frame and B coverage prototype tests: `23 passed in 9.04s`. PR #20 head `3d6475c8ad03fad77f1f6b73c67db09f9537b02d` has matching GitHub Actions run `43777369721` succeeded; that result does not qualify later commits.

This does not extend old-reader support to the new private platform provenance type: the previously documented requirement to withdraw it with the new reader before rollback still applies. Real-data backup, matched release, old reader compatibility for unrelated new Core contracts, actual devices and production rollback remain unqualified. A owns the final integrated release and rollback decision. Remove this standalone tool and its evidence to revert this candidate; no runtime consumer or data schema is changed.
