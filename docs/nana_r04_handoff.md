# R04 Codex → Nana development handoff

Sole base89385e98118da81bae751311fb6149f048b772a8; branchdev/nana-core-v1-r04-single-message-shadow-codex. R04 code IMPLEMENTED/TESTED. Real load NOT_RUN, dispatcher NOT_VERIFIED, real one-shot NOT_RUN, host_binding UNVERIFIED, FIRST_REAL_ASTRBOT_SHADOW BLOCKED, E12 NOT_RUN. No Codex real-host operation/private memory/production secret/message/model call.

Full latest470pass/0fail/0errors/1E12skip in cli_sealed_full.xml;66 R04 cases. New SQL tables0/dependencies0. D-045 preserved; D-046 receipt authority recorded. Scans/file hashes/package checks PASS.

Download final private-repo archive: https://github.com/xuni7-ui/nana-core/raw/b332df16701e56f07224ba633016d6ba28e4bcee/artifacts/r04/nana-r04-one-shot-3675a13a7bd7-delivery.tar.gz

Bytes3,325,221; SHA256faf85677f7625836cf0cffba36a044190333f35e0295edce1059c7a5efb9b6a4. Source support3675a13a7bd74b4501b1da7c777336b695a0c7af; fixed Coreddabfc4e49221b45a9f9600dd2ab8cb7f66ec513,55 bytes verified; original private runtime95c721… unchanged. Intermediate d025/095a archives are superseded, not current deliverables. Native running-AstrBot SQLite gate remains >=3.51.3, do not inject the private CLI binding into that process.

R03 repository already has one historical preflight version-line difference vsddab; R04 changed zeroCore files relative toR03. Repository full regression and approved55 package harness are separate scopes; do not claim full470 against a different source tree.

## Minimal next host steps — Nana/human only, not executed
1. Nana verifies native runtime/support-path/hook API/registry/plugin_set and baseline metadata/health. Stop the affected binding path if dependency gate fails; do not alter host deps or create a second permanent Runtime.
2. Independently review a genuine store-bound one-shot authorization receipt and onboard genuine production trust/source pin under explicit human authorization. Current pinsEMPTY; the package cannot arm real receipt until this is done. Do not pin fixture hashes.
3. Human manually Dashboard uploads the dormant pluginZIP, enables/sets plugin_set. Nana reads registry. Package does not auto-install/auto-arm and must not overwrite existing plugin.
4. Arm exact reviewed scope<=600sec/1use, bind using verified operator factory and reviewed adapter. Human sends exactly one approved test message with result-path traversal. Nana proves actual dispatcher/callback/Core links/replay/barrier/Shadow-attributed side effects, never reads body/result/prompt.
5. Unbind/close before CLI writer operations, disarm if unconsumed, human unloads, Nana proves registryabsence/health/zero drift/unchanged authorities. Keep sanitized DB/proof locally. Real runtime proof needs independent evidence pin; fixture verdict is not real PASS.

Detailed tools and checklists: docs/nana_r04_package/OPERATOR_RUNBOOK.md. Changes: docs/nana_r04_evidence/changed_files.json. No next Memory Shadow/E12 auto-start.

## Integration order
Preferred: fetch/merge this branch only into Nana development branch based onR03, preserve both append-onlyBrain tails. Never old10581/652/c3ada as base, never main/production merge. If cherry-picking, use exact oldest-first commits below; later doc-only receipt commit can follow. No history rewrite/force push. Tests/scans retained, no old assertions weakened.

```
8f2eee7e8d1405278f4757ada1ced342fd9d8624 R04-C0: verify sole R03 bundle baseline and approved-runtime regression
09313bcc18d1b0eaeb97a71d51ca86e6c7c92d0b R04-C1: strict store-bound one-shot receipt and separated empty production trust
f02b207156e72b04183a51d855febe0e0b37c1be R04-C2-C5: Atomic receipt and D-045 ingress/proof; 42 targeted passed, five actual SIGKILL boundaries; R03 pre-existing preflight drift disclosed
e6e6a7c38bb253e41713d2099beaca0393a5bd32 R04-C6-C8: Fail-closed operator CLI, 65 targeted passes, dormant message-only plugin and gated package/runbook
6327d3d9fe4c62caf3d56e8afff25c389cb03450 R04-C8-HARDEN: Dormant plugin blocks fixture trust and empty pins; 62 R04 targeted passed; earlier 65 count corrected to62
3b7f5ec147549b78914c40584262ac2126203d07 R04-C8-SEAL: Exact UTC microseconds, non-remintable permit and single-writer rollback instructions; 63 targeted passed
d025636c2682f84c36be12007f1a4058ffaf5b2e R04-C8-INTEGRITY: Stdlib hash gate before package execution and fixed proof diagnostics; 64 targeted passed, full468 passed one E12 skip
b9aec4e616b179b2e676a4ecfd835519167f5632 R04-RELEASE: Reviewed downloadable archive and extracted-package validation; full468 passed, one E12 skip, zero production operations
095a5fab00dde27a2015dcdf1cb744a9ae62db71 R04-FINAL-TYPE-SEAL: Require actual ReceiptLedger at sanitizer permit gate; full469 passed, one E12 skip, 65 R04 cases
f637cc2035b58b6b01c25a3a11599148fc8f9a4a R04-FINAL-DELIVERY: Sealed support archive and extracted-package proof; JUnit469 passed one E12 skip, all65 R04 cases
3675a13a7bd74b4501b1da7c777336b695a0c7af R04-FINAL-CLI-SEAL: Redact invalid CLI arguments with fixed diagnostics; full470 passed one E12 skip, 66 R04 cases
b332df16701e56f07224ba633016d6ba28e4bcee R04-FINAL-PACKAGE: Final CLI-redacted asset verified, full470 passed one E12 skip, package55ddab exact, zero host operations
```
