# Original C may withdraw an ongoing goal under attention load

DOMAIN S6/S3 Advanced, autonomy D/E: cognitive load is legitimate evidence about whether to continue work. The lifecycle C branch incorrectly gave HIGH load priority over an independently source-bound WITHDRAW option, changing abandonment into suspension. GoalReviewRef/source qualification still belongs to the original Subject/agency; this change adds no permission.

Frozen parent821426e test: LOW/OCCUPIED2 passed, HIGH failed (REST instead of WITHDRAW), log `/tmp/nana-withdraw-baseline.log`. New code only prioritizes source-supported withdrawal in the existing lifecycle branch; load continues to defer continuation and optional new work. New3 cases create original ongoing goal, restart, present source-bound GoalReviewRef, require WITHDRAW→ABANDONED, then restart again: single identity/goal, no actions. Existing REST/pause/resume/withdraw plan-reference and PrecisionV2 assertions unchanged.

Command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:$PWD/src" /workspace/nana-test-env/bin/python -m pytest -q tests/open_life/test_long_goals.py tests/controlled_world/test_project_presence.py tests/open_autonomy/test_planning.py tests/precision/test_planning.py tests/precision/test_recovery.py --basetemp=/tmp/nana-withdraw-fixed`

22 passed14.94s; raw `/tmp/nana-withdraw-fixed.log`. Source change still needs successor full CI and matching installed qualification. Other high-load gates are unmodified and require their own A–E reasoning, not blanket deletion. Original full acdd2153/12 and installed817 evidence remain earlier-source qualifications. No provider/account/APK/CURRENT/production changes.
