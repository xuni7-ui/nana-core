// Network-independent contract checks: node tests/feedback.node.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { languageFeedbackSample, memoryUseModes, reviewableResponse } from "../src/data/feedback.ts";
import { mergeRetainedTurns, retainedTurns } from "../src/data/living.ts";

const row = {exchange_record_id: "retained-exchange", user_text: "SYNTHETIC question", reply_text: "SYNTHETIC reply",
  created_at_us: 1, memory_use_delivery_proven: false,
  memory_use_sources: [{memory_id: "source-note", excerpt: "SYNTHETIC retained note"}]};

test("all four memory preferences bind the selected retained source without rating fact truth or verbosity", () => {
  const turn = retainedTurns({items: [row]})[0];
  for (const [mode] of memoryUseModes) {
    const sample = languageFeedbackSample(turn, "sample", {memory_id: "source-note", mode}, 10);
    assert.deepEqual(sample.memory_use, {memory_id: "source-note", mode});
    assert.equal(sample.review_target, row.exchange_record_id);
    assert.equal(sample.human_judgment, "PARTIAL");
    assert.deepEqual(sample.reason_tags, []);
    assert.equal(sample.provenance, "USER_PROVIDED_REVIEW");
  }
  const expression = languageFeedbackSample(turn, "expression", "TOO_VERBOSE", 10);
  assert.equal(expression.memory_use, undefined);
  assert.deepEqual(expression.reason_tags, ["TOO_VERBOSE"]);
});

test("foreign, withdrawn, unretained and malformed targets cannot form memory feedback", () => {
  const turn = retainedTurns({items: [row]})[0];
  const choice = {memory_id: "source-note", mode: "DO_NOT_MENTION" as const};
  assert.throws(() => languageFeedbackSample(turn, "foreign", {...choice, memory_id: "other-person"}, 10));
  assert.throws(() => languageFeedbackSample({...turn, state: "UNKNOWN"}, "unknown", choice, 10));
  assert.throws(() => languageFeedbackSample({...turn, exchangeId: undefined}, "transient", choice, 10));
  const longReply="x".repeat(2049);
  assert.equal(reviewableResponse(longReply), false); // Old server has no long-feedback capability.
  assert.equal(reviewableResponse(longReply, true), true);
  assert.equal(languageFeedbackSample({...turn,reply:longReply}, "long", choice, 10).candidate_response, "DEPENDENT_RECORD_BODY");
  assert.throws(() => languageFeedbackSample({...turn, reply: "x".repeat(16385)}, "oversized", choice, 10));
  for (const source of [{memory_id: "../wrong", excerpt: "SYNTHETIC"}, {memory_id: "source-note", excerpt: "x".repeat(161)}])
    assert.deepEqual(retainedTurns({items: [{...row, memory_use_sources: [source]}]})[0].memoryUseSources, []);
  assert.deepEqual(retainedTurns({items: [{...row, memory_use_delivery_proven: true}]})[0].memoryUseSources, []);
});

test("fresh history attaches choices to a live turn and removes stale choices on a later projection", () => {
  const local = {id: "request", input: row.user_text, reply: row.reply_text, state: "VERIFIED",
    exchangeId: row.exchange_record_id, remembered: true};
  const merged = mergeRetainedTurns(retainedTurns({items: [row]}), [local]);
  assert.deepEqual(merged[0].memoryUseSources, row.memory_use_sources);
  const cleared = mergeRetainedTurns(retainedTurns({items: [{...row, memory_use_sources: []}]}), merged);
  assert.deepEqual(cleared[0].memoryUseSources, []);
  assert.throws(() => languageFeedbackSample(cleared[0], "stale", {memory_id: "source-note", mode: "DO_NOT_MENTION"}, 10));
  assert.deepEqual(mergeRetainedTurns([], merged), []);
});
