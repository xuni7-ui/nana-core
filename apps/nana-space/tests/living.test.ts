import { expect, test } from "vitest";
import { bilibiliReadings, credentialProfiles, mergeRetainedTurns, retainedTurns, pendingReceiptTurns, sharedCandidates, vaultMetadata } from "../src/data/living";

test("retained history restores only valid sourced rows and withdrawal removes stale restored bodies", () => {
  const saved = retainedTurns({items: [{exchange_record_id: "exchange-1", user_text: "PROJECT common task", reply_text: "Sourced reply", created_at_us: 10}]});
  expect(saved[0]).toMatchObject({remembered: true, restored: true, state: "VERIFIED"});
  expect(mergeRetainedTurns(saved, saved)).toEqual(saved);
  const unknown = {id: "original-request", input: "", state: "UNKNOWN"};
  expect(mergeRetainedTurns([], [...saved, unknown])).toEqual([unknown]);
  expect(retainedTurns({items: [{...saved[0], exchange_record_id: "../../other", created_at_us: 10}]})).toEqual([]);
});

test("pending receipts restore only original verification IDs, never body or a fake completion", () => {
  const unknown = pendingReceiptTurns({pending_receipts: [{receipt_id: "original-request", state: "REQUESTED", text: "DO_NOT_RESTORE"}]});
  expect(unknown).toEqual([{id: "original-request", input: "", state: "UNKNOWN", restored: true, pendingReceipt: true}]);
  expect(pendingReceiptTurns({pending_receipts: [{receipt_id: "../other", state: "UNKNOWN"}]})).toEqual([]);
  const current = {id: "original-request", input: "", state: "UNKNOWN"};
  expect(mergeRetainedTurns(unknown, [current])).toEqual([current]);
});

test("current retained receipt deduplicates restored history without copying transient turns into history", () => {
  const saved = retainedTurns({items: [{exchange_record_id: "saved", user_text: "source", reply_text: "reply", created_at_us: 10}]});
  const current = {id: "request", exchangeId: "saved", input: "source", state: "VERIFIED", remembered: true};
  expect(mergeRetainedTurns(saved, [current])).toEqual([current]);
  expect(mergeRetainedTurns([], [current])).toEqual([]);
  const transient = {id: "transient-request", input: "only this window", state: "VERIFIED", remembered: false};
  expect(mergeRetainedTurns([], [current, transient])).toEqual([transient]);
});

test("Bilibili evidence preserves source limits and cannot turn a title into watching", () => {
  const rows = bilibiliReadings({items: [{source_memory_id: "memory-1", bvid: "BV1t55v6DE2v", title: "Public source", observed_at_us: 123,
    coverage: "METADATA_ONLY_NOT_WATCHED", subtitle_segments: [], comment_samples: 2, visual_frames: 0,
    source_origin: "REAL_PLATFORM_HTTP", watched: true, grant: "ignore"}]});
  expect(rows[0]).toMatchObject({coverage: "只读到视频信息", subtitles: 0, comments: 2, frames: 0, interpreted: false});
  expect(JSON.stringify(rows)).not.toMatch(/watched|grant|ignore/);
  expect(bilibiliReadings({items: [{...rows[0], bvid: "javascript:alert(1)"}]})).toEqual([]);
  expect(bilibiliReadings({items: [{source_memory_id: "memory-1", bvid: "BV1t55v6DE2v", title: "source", observed_at_us: -1}]})).toEqual([]);
});

test("vault metadata cannot copy unknown credential fields into its presentation", () => {
  expect(vaultMetadata({vault: {revision: 3, configured: true, persistence: "HOST_LOCAL_AES_256_GCM", state: "READY", credential: "TEST_ONLY_NOT_SECRET"}}))
    .toEqual({revision: 3, configured: true, persistent: true, state: "READY"});
  expect(vaultMetadata({vault: {revision: -1}})).toBeNull();
  expect(credentialProfiles({profiles: [{provider_profile_id: "provider.a", secret_state: "AVAILABLE", credential: "IGNORE_UNKNOWN_FIELD"}]}))
    .toEqual([{id: "provider.a", state: "AVAILABLE"}]);
  expect(credentialProfiles({profiles: [{provider_profile_id: "provider.a", secret_state: "UNVERIFIED"}]})).toEqual([]);
});

test("shared life shows only original approved non-delivered metadata, never a fabricated message or permission", () => {
  const item = {candidate_record_id: "candidate-1", cycle_id: "cycle-1", topic: "experience.sourced", state: "DEFER_BUSY", delivery: "NONE",
    source_record_ids: ["record-1"], source_memory_ids: ["memory-1"], text: "DO_NOT_RENDER", grant: "IGNORE"};
  const projection = {coverage: "ORIGINAL_C_APPROVED_CANDIDATES_ONLY", external_delivery: false, items: [item]};
  const candidates = sharedCandidates(projection);
  expect(candidates).toEqual([{id: "candidate-1", cycleId: "cycle-1", topic: "experience.sourced", state: "DEFER_BUSY", records: ["record-1"], memories: ["memory-1"]}]);
  expect(JSON.stringify(candidates)).not.toMatch(/DO_NOT_RENDER|grant|IGNORE/);
  expect(sharedCandidates({...projection, external_delivery: true})).toEqual([]);
  expect(sharedCandidates({...projection, items: [{...item, delivery: "DELIVERED"}]})).toEqual([]);
  expect(sharedCandidates({...projection, items: [{...item, source_record_ids: []}]})).toEqual([]);
});
