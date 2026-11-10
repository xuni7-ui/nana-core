import type { LanguageSample, MemoryUseFeedback } from "./v2.generated";
import type { Turn } from "../features/v3/ChatPane";

export type FeedbackTag = "TOO_VERBOSE" | "NATURAL" | "TOO_TERSE";
export type FeedbackChoice = FeedbackTag | MemoryUseFeedback;
export type MemoryUseSource = { memory_id: string; excerpt: string };

export const memoryUseModes = [
  ["EXPLICIT_RECALL", "明确回忆", "需要时清楚说出记得的事"],
  ["NATURAL_REFERENCE", "自然呼应", "聊到相关处再自然提起"],
  ["IMPLICIT_REFERENCE", "放在心里", "理解我的意思就好，不必说出往事"],
  ["DO_NOT_MENTION", "暂不提及", "这条记忆先不要主动提起"],
] as const;

export function reviewableResponse(reply: string, longFeedback = false): boolean {
  const length=Array.from(reply).length;
  return length>0 && length <= (longFeedback ? 16384 : 2048);
}

export async function languageFeedbackResponseBinding(reply: string): Promise<{response_sha256?: string}> {
  if (!reviewableResponse(reply,true)) throw new Error("FEEDBACK_TURN_UNAVAILABLE");
  if (Array.from(reply).length<=2048) return {};
  const hash=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(reply));
  return {response_sha256:Array.from(new Uint8Array(hash),x=>x.toString(16).padStart(2,"0")).join("")};
}

export function languageFeedbackSample(turn: Turn, id: string, choice: FeedbackChoice, observedAt: number): LanguageSample {
  if (turn.state !== "VERIFIED" || !turn.exchangeId || !turn.reply || !reviewableResponse(turn.reply,true))
    throw new Error("FEEDBACK_TURN_UNAVAILABLE");
  const labels = { TOO_VERBOSE: "有点啰嗦", NATURAL: "这样刚好", TOO_TERSE: "想听多一点" };
  const memory = typeof choice !== "string";
  if (memory && (!turn.memoryUseSources?.some(source => source.memory_id === choice.memory_id)
      || !memoryUseModes.some(([mode]) => mode === choice.mode)))
    throw new Error("FEEDBACK_MEMORY_UNAVAILABLE");
  return {
    sample_id: id, review_target: turn.exchangeId, mode: "CASUAL",
    context: turn.input.slice(0, 1024) || "这次交流", candidate_response: Array.from(turn.reply).length<=2048 ? turn.reply : "DEPENDENT_RECORD_BODY",
    human_judgment: memory ? "PARTIAL" : choice === "NATURAL" ? "ACCEPTED" : "REJECTED",
    reason_tags: memory ? [] : [choice],
    exact_feedback: memory ? memoryUseModes.find(([mode]) => mode === choice.mode)![2] : labels[choice],
    provenance: "USER_PROVIDED_REVIEW", observed_at_us: observedAt,
    ...(memory ? { memory_use: choice } : {}),
  };
}
