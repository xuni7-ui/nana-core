# R041 Codex → Nana handoff (development only)

Base8f9dfab0b7fb008f9f43f02fc361e7001cde37a3; independent branchdev/nana-core-v1-r041-short-lived-host-bridge-codex. No shared/main rewrite. SHORT_LIVED_HOST_BRIDGE IMPLEMENTED/TESTED; real load/bridge/one-shotNOT_RUN, dispatcherNOT_VERIFIED, host_bindingUNVERIFIED, FIRST_REAL_ASTRBOT_SHADOWBLOCKED, E12NOT_RUN. All Codex production/private/secret/message/model/authority operations0.

Full510passed/0failed/0errors/1E12skip,40R041cases; actualCPython3.12.14/privateSQLite3.51.3/Pydantic2.13.5. Actual separateoldSQLite client3.46.1 before/afterimports withCore/privateSQLite/Pydanticimports0. Three trueworkerSIGKILLs beforeconsume/afterconsumecommit/afterEvidence; no receipt/sessionreactivation. 2/10/100concurrentUDSframes exactlyoneCoreingress. SIGTERM, trueharddeadlineexit124, stale/fakepeer/PID/inode/status/body/timeout/cancel/lateconnection tests retained. No newCoreSQLtable/dependency.

## Download
https://github.com/xuni7-ui/nana-core/raw/60894dbdce826f0fff22dd6acb97a744576ccbdc/artifacts/r041/nana-r041-host-bridge-c24833e69ee1-bridge-delivery.tar.gz

Filename nana-r041-host-bridge-c24833e69ee1-bridge-delivery.tar.gz; bytes3,351,586; SHA256fafe82ec73dc2c4d996fb64cb6f2a6bd7402854305b5036e8516797b81c1dc63. Remoteassetbytes freshlyfetchedverified. Supportc24833e69ee181f436eb7ebda75b6a8b58e71004, fixedCoreddab55 exactbytes, unchangedoriginalprivateRuntime95c721… . Old27dfasset is historical candidate, notcurrentrelease. Full regression usesR04repoCore (historicalpreflightdifferencevsddab disclosed); extractedpackageharness separately verifiesapproved55 source andruntime.

## Minimum real-host next actions (Nana/human, NOT Codex)
1. Nana metadata-auditsactualAstrBot4.28result-hook/PID/UID/filesystem/PIDnamespace. ExistinghostSQLite3.46.1 staysuntouched; standaloneworker usesprivate3.51.3 only. Verifypackagehash/isolatedruntimepreflight. NoCore/privateSQLiteimportintoAstrBot.
2. Prepare independentShadowStore and NEW0700shortIPCdirectory. Independentlyreview freshR04receipt/realreviewsourcepin + explicithumanone-messageauthorization; pinscurrentlyEMPTY, no config/fixtureoverride.
3. `bridge preflight`, explicitFOREGROUND `bridge start --seconds60`; no daemon/auto-spawn. Session<=600sec/receiptexpiry, <=5secshutdown grace. SameUID/PIDnamespace required; don'ttunnel/openTCP/changepermissions.
4. HumanDashboard uploads/enablesexactnewpluginZIP/plugin_set; Nana registryinspect andbinds stdlibOneShotBridgeClient(client.json). Human sendsONE authorizedresult-path testmessage. Nana obtains realdispatcher/callback/receipt/Core/barrier/zero-drift evidence. ACK/fixturecannotpromoterealproof.
5. Unbindclient, `bridge stop/status/collect/verify`, humanunload, Nana registryabsence/legacyhealth/zero-drift. Aftercrash explicitexactstale cleanup; no autorestart/retry/re-arm. PreserveDB/reports; noMemoryShadow/E12/handoff auto-start.

Operator commands/checklists/rollback are in docs/nana_r041_package/OPERATOR_RUNBOOK.md. AllCLIcommandsdry-run supported, norealfixture option. Productionverify mayremainUNKNOWN/INCOMPLETE until Nana independentoutside-core/runtime proof.

## Development integration
Prefermerge this branch intoNana developmentclone basedonR04, preserveappend-onlyBrainbothsides. Nevermain/productionmerge. Ifcherry-pick, oldest-first below, finaldocumentationcommit afterwards. Source/runtimechecksandfullregressionbeforefuturehostload.

```
4b1b11d1a86c8759c90e57b7c43544b4eba74657 R041-M1: Bounded stdlib UDS metadata channel, R04 single-writer ingress and foreground session fence; 106 targeted passed
350ded1dcc7e42bc79c255c6bc49af130661c3b0 R041-M2: Old-SQLite client isolation, three actual worker SIGKILLs, PID/socket-fenced stop cleanup and adversarial lifecycle; 126 targeted passed
27df51ef11fc930ba7c7cd4010ca06f842144155 R041-M3: Bridge package/runbook and safe operator session readback; 44 targeted passed, real statuses unchanged
c24833e69ee181f436eb7ebda75b6a8b58e71004 R041-M4-SEAL: Bounded observation and isolated hard-exit grace, no late ingress; full510 passed one E12 skip
60894dbdce826f0fff22dd6acb97a744576ccbdc R041-RELEASE: Sealed-window package validated in fresh directory; full510 passed one E12 skip, no approvedCore or production changes
```
