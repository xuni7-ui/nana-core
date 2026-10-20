# Independent review reproduction (offline)

The original63 criteria and Master are pinned to af52371d0201b72ce83b00fdf6e4e1b33cd1d198; audit.json carries criterion-level evidence updates, not a new definition. Core/test files were identical between eece7a4 and af52371, verified by Git diff. No provider or host credential is needed.

- Current tracked focused command and result are recorded in independent_review.json and focused_tests.txt; scope includes60 virtual days, typed owned-method disagreement and learning/REST controls. It passed21 tests.
- `python -m pytest tests/vision_first/test_context_fit.py -q` passed6 tests. The passing old behavior is the observation under review, not proof of conformance to every newly frozen principle.
- `python tools/nana_foundation_audit/probe_topic_scope.py` reproduces topic_scope_probe.json in a temporary synthetic Store with no provider, Grant or Action. It never mutates a real Subject or staging.
- `python tools/nana_foundation_audit/check.py` verifies frozen definitions,63 IDs/denominators, links, source fingerprints, document alignment and manifest; it does not award behavioral qualification.

Historical Relational recheck uses exact Git source a97a8114b7d638d7c9bd1a9895822dbc6efc4e7c, reachable through dev/nana-core-relational-autonomy-v1-codex; it is not an ancestor of current branch. If unavailable locally, explicitly fetch that dev ref before attempting reproduction; never use cached bytecode as source. For each path listed by `git ls-tree -r --name-only <anchor> tests/relational_autonomy`, copy `git show <anchor>:<path>` into a fresh temporary directory, preserving the package layout and checking each SHA256 against relational_snapshot.json. Run the current .venv Python with PYTHONPATH containing current repository src and the temporary root, and pytest the copied directory. This executes current Core, not the historical Core; original test source is unchanged.18 tests passed in106.06s, including90 virtual days and7 actual SIGKILL cuts. No private/production source is used. No directory is restored over the working tree.

This recheck supports the restricted synthetic/process criteria; it is deliberately insufficient for S3-C09, which requires a real controlled experience-to-later-need-change chain rather than manually typed PreferenceSignal or merely sharing an outcome.

Closure revision: topic_scope_probe reproduces the historical defect only with the edda7d08 source/tool snapshot. The current fix intentionally invalidates its old assertion. Current contract: `.venv/bin/python -m pytest tests/foundation_closure/test_scope.py -q`. Original topic_scope_probe.json is retained unchanged.
