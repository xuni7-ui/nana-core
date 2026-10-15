# L3-C-AFFECT-V1 delivery fields

Exact final SHA is the Git commit containing this report, independently checked
with origin in the final response. It is not embedded into its own content hash.
Source checkpoint09f45244d3d146e5381efb110fc8a89867a0f82e; final commit docs only.

```text
ROADMAP_ID = L3-C-AFFECT-V1
BRANCH = dev/nana-core-affective-autonomy-v1-codex
HEAD_START = 02e68d31d4d15beff141f19aebceb84d592f8a04
HEAD_FINAL = containing Git documentation commit (see final response / git rev-parse HEAD)
REMOTE_SHA = independently verified final origin SHA (see final response)
PUSH_VERIFIED = final origin ls-remote, see final response
COMMITS = 8 (original order; no history rewrite)
SCHEMA_START = C7(default), D8(default)
SCHEMA_FINAL = explicit development9; C7/D8 defaults unchanged
NEW_TABLES = 0
SOURCE_FILES_CHANGED = 34
TEST_FILES_CHANGED = 16 (23 new tests plus shared fixture/qualification code)
DOCS_CHANGED = 17
PROJECT_BRAIN_FILES_CHANGED = 5
CONFIG_FILES_CHANGED = 1 (pytest discovery only; dependencies unchanged)
PROJECT_BRAIN_RECONCILED = YES
R1_NORMATIVE_DISPOSITION = PASS
R1_INTENTION_DISPOSITION = PASS
R1_DISCLOSURE = PASS
R2_MANAGER_NEGATIVE_ONLY = PASS
R2_MANAGER_TRANSPARENT = PASS
R2_MANAGER_REPLAY_SAFE = PASS
R3_RELATIONSHIP_PROJECTION = PASS
R3_DATA_PRIVACY_HARD = PASS
R3_SOCIAL_PRIVACY = PASS
R4_POSITIVE_REQUEST_COMMITMENT = PASS
R4_CALENDAR_RECURRENCE = PASS (typed DAILY / IANA / DST / coalescing / restart)
R5_EXPERIENCE_GATE = PASS
R5_REFLECTION_INTEGRATION = PASS
R6_SCHEMA_REPLAY_DELETE = PASS
GENERIC_SUBJECT_FRAMEWORK = PASS (two independent fictional Subjects)
NANA_SPECIFIC_BEHAVIOR_BRANCHES = 0
SECOND_SUBJECT_LOOP = NO
SECOND_STORE = NO
MANAGER_CAN_CREATE_POSITIVE_DUTY = NO
RELATIONSHIP_CAN_EXPAND_AUTHORITY = NO
DISCLOSURE_CAN_EXPAND_AUTHORITY = NO
MODEL_CAN_WRITE_MANAGER = NO
MODEL_CAN_COMMIT_JUDGMENT = NO
MANAGER_BLOCK_REWRITES_JUDGMENT = NO
ACTION_BLOCKED_DISTINCT_FROM_MANAGER = YES
DATA_PRIVACY_CAN_BE_OVERRIDDEN_BY_RELATIONSHIP = NO
S1_SURPRISE = PASS
S2_TELL_AFTER = PASS
S3_MANAGER_BLOCKED = PASS
S4_ACTION_BLOCKED = PASS
S5_POSITIVE_REQUEST = PASS
S6_RELATIONSHIP_HIGH = PASS
S7_BOUNDARY_VS_MANAGER = PASS
S8_MANAGER_DISAGREEMENT = PASS
S9_CONSTRAINT_REVOCATION = PASS
S10_RELATIONSHIP_COUNTEREVIDENCE = PASS
S11_REPAIR = PASS
S12_DATA_PRIVACY_HARD_DENY = PASS
S13_SOCIAL_PRIVACY_SOFT = PASS
S14_RESTRAINED = PASS
S15_DO_NOTHING = PASS
CRASH_REPLAY_MATRIX = PASS (six actual local SIGKILL/reopen cuts)
V7_TO_FINAL_MIGRATION = PASS
V8_TO_FINAL_MIGRATION = PASS
C_V2_REGRESSION = 32 passed
D_V1_REGRESSION = 11 passed
FULL_REGRESSION = 911 passed / 0 failed / 1 skipped, 93.47 seconds
NEW_TESTS = 23 passed / 0 failed / 0 skipped
SOAK = 60 virtual days PASS
REAL_MODELS = 0
REAL_PRIVATE_DATA = 0
REAL_EXTERNAL_ACTIONS = 0
PRODUCTION_CHANGED = NO
MAIN_CHANGED = NO
R045_CHANGED = NO
FIRST_REAL_ASTRBOT_SHADOW_CHANGED = NO
PRODUCTION_REVIEW_PINS = EMPTY
REAL_RUNTIME_PROOF_PINS = EMPTY
REAL_MEMORY_IMPORT_ENABLED = NO
E12 = NOT_RUN
KNOWN_LIMITATIONS = limitations.txt / implementation section20
ARCHITECTURE_CONFLICTS = NONE
AFFECT_AUTONOMY_V1_OFFLINE_CANDIDATE = READY
NEXT_RECOMMENDED_MILESTONE = independent offline review and development integration;
  do not automatically start production/E/G/real model work
```

Files changed and SHA256 of every changed source/test/document/config are listed
in `manifest.json`. The manifest excludes itself; Git verifies the containing
manifest/report. No executable DB, credentials, package or private data is added.
Existing unrelated untracked `nana-r03-codex-10581aea.bundle` is preserved.

Cherry-pick/integration order (apply the complete dependency chain, not fragments):

1. d865118 — normative/disclosure/schema9
2. 9ee2095 — negative-only governance and fenced fixture handoff
3. 55f9743 — relationship facets/privacy
4. 4ebd09c — request commitment/calendar
5. f513dcc — non-execution experience/reflection
6. 645159e — scenario/generic/soak/migration/crash qualification
7. 09f4524 — late Manager-cancel disclosure provenance fix
8. containing final documentation/evidence commit

No automatic integration into main, R045 or any production branch is performed.
