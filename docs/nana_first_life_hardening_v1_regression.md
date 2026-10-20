# Foundation regression map

Use the pinned checkout's environment; Python module selection includes `src`.
`python -m tools.nana_first_life_hardening.regression fast` selects P0 authority,
privacy/deletion, storage, provider UNKNOWN, actual owned-process recovery and
sandbox cases. `... regression full` explicitly runs `pytest tests`, avoiding the
repository's historically narrower default testpaths. Neither enables opt-in live tests.
`--junitxml /tmp/result.xml` emits a disposable machine report.

| Domain / invariant | Targeted suites |
|---|---|
| S1/S10 owner/lineage/recovery | continuous_runtime/test_storage_runtime, portable_subject/test_package |
| S2 erasure/tombstone | continuous_self/test_privacy, cloud_life/test_operations |
| S3 relationship != authority | affective_autonomy/test_relationship_privacy, test_governance |
| S4 bounded cadence / queues | continuous_runtime, first_life/test_durability |
| S5 provider no authority / UNKNOWN | world_loop/test_boundaries, provider_routing/test_router |
| S6 independent C boundaries | foundation_closure/test_scope, test_framing |
| S7 actual effects/UNKNOWN | controlled_hands/test_recovery, test_application |
| S8 optional supported learning | open_autonomy/test_learning, foundation_closure/test_experience_need |
| S9 isolated exact code | open_autonomy/test_code_skills |
| Inspector/privacy/special files/atomic writes | first_life_hardening |

`CHANGE_SUITES` in the runner maps changed paths to recommendations; it never
silently claims an unexecuted suite or replaces full regression. E12/live-screen
skips remain explicit. Dependency `pip check` is consistency only, not a CVE audit;
no new scanner or package installation is authorized by running these suites.
