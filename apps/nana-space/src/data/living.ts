import type { Turn } from "../features/v3/ChatPane";
import type { MemoryUseSource } from "./feedback";

const record = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : null;

/** A reviewed input is not assistant speech. Link replies only to the original
 * Core's bounded source IDs, even when independent receipts arrive reversed.
 */
export function messageReceiptTurns(id:string,value:unknown,turns:Turn[]):Turn[] {
  const data=record(value)||{},result=record(data.result)||{};
  const safeId=(v:unknown):v is string=>typeof v==='string' && /^[A-Za-z0-9._:-]{1,128}$/.test(v);
  const mid=safeId(result.message_memory_id)?result.message_memory_id:undefined;
  const refs=Array.isArray(result.respond_to_memory_ids)?result.respond_to_memory_ids:undefined;
  const bound=data.receipt_id===id;
  const validRefs=!!(mid && refs && refs.length<=4 && new Set(refs).size===refs.length
    && refs.every(safeId) && refs.includes(mid));
  const deferred=result.state==='SHADOW_INPUT_REVIEWED_NO_REPLY';
  const validDeferred=bound && data.state==='VERIFIED' && mid
    && result.render_state==='DEFERRED_TO_CONTINUATION' && result.text===null
    && result.raw_body_persisted===false && result.exchange_record_id==null
    && Array.isArray(refs) && refs.length===0 && result.external_delivery===false
    && result.completion_kind==='SUBJECT_REVIEW_NOT_SOCIAL_DELIVERY';
  const malformed=(deferred && !validDeferred) || (!deferred
    && 'respond_to_memory_ids' in result && (!bound || !validRefs));
  const wording=data.state==='VERIFIED' && !malformed && result.render_state==='UNVERIFIED_MODEL_WORDING'
    && typeof result.text==='string' && !!result.text.trim() && validRefs && safeId(result.reply_response_id);
  let next=turns.map((turn):Turn=>{
    if(turn.id!==id)return turn;
    if(result.state==='BODY_WITHHELD_SOURCE_CHANGED')return {id,input:'',state:'SOURCE_WITHHELD'};
    const route=record(result.route);
    const model=typeof route?.returned_model_id==='string' && route.returned_model_id
      ? route.returned_model_id:typeof route?.remote_model_id==='string'?route.remote_model_id:undefined;
    const common={...turn,state:typeof data.state==='string'?data.state:'',provisional:undefined,phase:undefined,
      error:typeof data.error==='string'?data.error:undefined,remembered:data.state==='VERIFIED' && result.raw_body_persisted===true,
      exchangeId:typeof result.exchange_record_id==='string'?result.exchange_record_id:undefined,
      restored:turn.pendingReceipt?false:turn.restored,model,
      reply:data.state==='VERIFIED' && typeof result.text==='string'?result.text:undefined,
      provider:typeof result.provider_state==='string'?result.provider_state:undefined,
      messageMemoryId:mid,replyToMemoryIds:wording?refs as string[]:undefined};
    if(malformed)return {...common,state:'UNKNOWN',reply:undefined,error:'CONTINUATION_REPLY_BINDING_INVALID'};
    if(validDeferred){
      const covered=turns.some(t=>t.id!==id && t.state==='VERIFIED' && t.reply?.trim()
        && t.replyToMemoryIds?.includes(mid!));
      return {...common,state:covered?'GROUPED':'DEFERRED_REPLY',reply:undefined};
    }
    return common;
  });
  if(wording)next=next.map(t=>t.id!==id && t.state==='DEFERRED_REPLY'
    && t.messageMemoryId && refs!.includes(t.messageMemoryId)
    ? {...t,state:'GROUPED',reply:undefined,provisional:undefined,phase:undefined}:t);
  return next;
}

/** Python's existing IPC uses ASCII-escaped JSON; reserve4096bytes for its
 * typed metadata. This estimate only chooses unsent grouping, never admission.
 */
export function sequenceTextWireBytes(texts: string[]): number {
  return JSON.stringify(texts).replace(/[\u007f-\uffff]/g, c=>"\\u"+c.charCodeAt(0).toString(16).padStart(4,"0")).length;
}

/** Display the original receipt's child/source bindings, never invent a reply
 * for a deferred input or recover unretained user wording after reload.
 */
export function sequenceReceiptTurns(id: string,value: unknown,turns: Turn[]): Turn[] | null {
  const data=record(value),result=record(data?.result);
  const members=turns.filter(t=>t.receiptId===id);
  if(!members.length && data?.operation!=="MESSAGE_SEQUENCE" && result?.state!=="SUBJECT_SEQUENCE_REVIEWED")return null;
  const pending=(error?:string)=>turns.map(t=>(t.receiptId===id || t.id===id)
    ? {...t,state:t.id===id?"UNKNOWN":"GROUP_PENDING",provisional:undefined,phase:undefined,reply:undefined,error,receiptId:id}:t);
  if(data?.receipt_id!==id)return pending("SEQUENCE_REPLY_BINDING_INVALID");
  if(data.state!=="VERIFIED"){
    if(data.state==="REJECTED")return turns.map(t=>(t.receiptId===id || t.id===id)
      ? {...t,state:"REJECTED",provisional:undefined,phase:undefined,reply:undefined,
        error:typeof data.error==="string"?data.error:undefined,receiptId:id}:t);
    return pending(typeof data.error==="string"?data.error:undefined);
  }
  if(result?.state==="BODY_WITHHELD_SOURCE_CHANGED")return turns.map(t=>(t.receiptId===id || t.id===id)
    ? {id:t.id,input:"",state:"SOURCE_WITHHELD",receiptId:id}:t);
  if(result && !Object.keys(result).length)return turns.map(t=>(t.receiptId===id || t.id===id)
    ? {...t,state:"REPLY_UNAVAILABLE",reply:undefined,provisional:undefined,phase:undefined,receiptId:id}:t);
  if(result?.state!=="SUBJECT_SEQUENCE_REVIEWED" || result.external_delivery!==false
    || !Array.isArray(result.results) || result.results.length<2 || result.results.length>4)
    return pending("SEQUENCE_REPLY_BINDING_INVALID");
  const rows=result.results.map(record),safeId=(v:unknown,max=128)=>typeof v==="string" && new RegExp(`^[A-Za-z0-9._:-]{1,${max}}$`).test(v);
  if(rows.some(r=>!r || !safeId(r.client_message_id,96) || r.external_delivery!==false))return pending("SEQUENCE_REPLY_BINDING_INVALID");
  const checked=rows as Record<string,unknown>[],ids=checked.map(r=>String(r.client_message_id));
  const mids=checked.filter(r=>safeId(r.message_memory_id)).map(r=>String(r.message_memory_id));
  const restored=!members.length && turns.some(t=>t.id===id && t.pendingReceipt);
  if(new Set(ids).size!==ids.length || new Set(mids).size!==mids.length
    || (!restored && (members.length!==ids.length || members.some(t=>!ids.includes(t.id)))))
    return pending("SEQUENCE_REPLY_BINDING_INVALID");
  if(checked.some(r=>!Array.isArray(r.respond_to_memory_ids) || r.respond_to_memory_ids.length>4
    || r.respond_to_memory_ids.some(mid=>!safeId(mid) || !mids.includes(String(mid)))
    || (r.text!==undefined && r.text!==null && (typeof r.text!=="string" || [...r.text].length>16384))
    || (typeof r.text==="string" && r.text.length>0 && (!safeId(r.message_memory_id)
      || !r.respond_to_memory_ids.includes(r.message_memory_id)))))return pending("SEQUENCE_REPLY_BINDING_INVALID");
  const displayed=checked.map((row,index):Turn=>{
    const turn=members.find(t=>t.id===row.client_message_id) || {id:String(row.client_message_id),input:"",state:"UNKNOWN"};
    const route=record(row.route),model=route?.returned_model_id || route?.remote_model_id;
    const common={...turn,receiptId:id,provisional:undefined,phase:undefined,error:undefined,
      remembered:row.raw_body_persisted===true,
      exchangeId:safeId(row.exchange_record_id)?String(row.exchange_record_id):undefined,
      provider:typeof row.provider_state==="string" && row.provider_state.length<=128?row.provider_state:undefined,
      model:typeof model==="string" && model.length<=128?model:undefined};
    if(typeof row.text==="string" && row.text.length)return {...common,state:"VERIFIED",reply:row.text,pendingReceipt:false};
    if(row.render_state==="DEFERRED_TO_CONTINUATION" && checked.slice(index+1).some(later=>
      typeof later.text==="string" && later.text.length>0 && (later.respond_to_memory_ids as unknown[]).includes(row.message_memory_id)))
      return {...common,state:"GROUPED",reply:undefined};
    if(["ALREADY_REVIEWED_NO_REPLAY","ALREADY_REVIEWED_SOURCE_RETIRED"].includes(String(row.state)))
      return {...common,state:"ALREADY_REVIEWED",reply:undefined};
    return {...common,state:turn.id===id?"UNKNOWN":"GROUP_PENDING",reply:undefined,error:"SEQUENCE_REPLY_BINDING_INVALID"};
  });
  if(displayed.some(t=>t.error==="SEQUENCE_REPLY_BINDING_INVALID"))return pending("SEQUENCE_REPLY_BINDING_INVALID");
  if(restored){
    const replies=displayed.filter(t=>Boolean(t.reply));
    return [...turns.filter(t=>t.id!==id),...(replies.length?replies:[{id,input:"",state:"ALREADY_REVIEWED",receiptId:id}])].slice(-32);
  }
  return turns.map(t=>displayed.find(row=>row.id===t.id) || t);
}

/** Only source-validated, explicitly retained server exchanges are restored.
 * A client cache is never the memory authority. Uncertain requests are not replayed.
 */
export function retainedTurns(value: unknown): Turn[] {
  const data = record(value);
  if (!data || !Array.isArray(data.items) || data.items.length > 64) return [];
  return data.items.flatMap((value): Turn[] => {
    const row = record(value);
    if (!row || typeof row.exchange_record_id !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/.test(row.exchange_record_id)
      || typeof row.user_text !== "string" || typeof row.reply_text !== "string"
      || row.user_text.length > 4096 || [...row.reply_text].length > 16384
      || typeof row.created_at_us !== "number" || !Number.isSafeInteger(row.created_at_us)
      || row.created_at_us < 0) return [];
    const memoryUseSources: MemoryUseSource[] = row.memory_use_delivery_proven === false
      && Array.isArray(row.memory_use_sources) && row.memory_use_sources.length <= 8
      ? row.memory_use_sources.flatMap(value => {
        const source = record(value);
        return source && typeof source.memory_id === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(source.memory_id)
          && typeof source.excerpt === "string" && source.excerpt.length > 0 && source.excerpt.length <= 160
          ? [{memory_id: source.memory_id, excerpt: source.excerpt}] : [];
      }) : [];
    return [{id: row.exchange_record_id, input: row.user_text, reply: row.reply_text,
      state: "VERIFIED", remembered: true, restored: true,
      exchangeId: row.exchange_record_id,
      memoryUseSources,
      ...(typeof row.model === "string" && row.model.length <= 128 ? {model: row.model} : {})}];
  }).slice(-32);
}

/** Original body-free server receipts restore verification handles only. */
export function pendingReceiptTurns(value: unknown): Turn[] {
  const data = record(value);
  if (!data || !Array.isArray(data.pending_receipts) || data.pending_receipts.length > 32) return [];
  return data.pending_receipts.flatMap((value): Turn[] => {
    const row = record(value);
    if (!row || typeof row.receipt_id !== "string" || !/^[A-Za-z0-9._:-]{1,96}$/.test(row.receipt_id)
      || !["UNKNOWN", "REQUESTED"].includes(String(row.state))) return [];
    return [{id: row.receipt_id, input: "", state: "UNKNOWN", restored: true, pendingReceipt: true}];
  });
}

export function mergeRetainedTurns(restored: Turn[], current: Turn[]): Turn[] {
  const supported = new Set(restored.filter(x => x.exchangeId).map(x => x.exchangeId));
  const local = current.filter(x => !x.restored && !(x.remembered && x.exchangeId && !supported.has(x.exchangeId)))
    .map(x => {
      const sources = x.exchangeId && x.remembered
        ? restored.find(row => row.exchangeId === x.exchangeId)?.memoryUseSources : undefined;
      return x.memoryUseSources || sources?.length ? {...x, memoryUseSources: sources ?? []} : x;
    });
  const known = new Set(local.filter(x => x.exchangeId).map(x => x.exchangeId));
  const localIds = new Set(local.map(x => x.id));
  // Restored rows are replaced on each projection, so a withdrawn source cannot
  // survive in a stale browser history after the server removes it.
  return [...restored.filter(x => !localIds.has(x.id) && !known.has(x.exchangeId)), ...local].slice(-32);
}

export interface SharedCandidate {
  id: string; cycleId: string; topic: string; state: string; records: string[]; memories: string[];
}
/** Original C-approved metadata only; no candidate is promoted into a delivered message. */
export function sharedCandidates(value: unknown): SharedCandidate[] {
  const data = record(value);
  if (!data || data.external_delivery !== false || data.coverage !== "ORIGINAL_C_APPROVED_CANDIDATES_ONLY"
    || !Array.isArray(data.items) || data.items.length > 64) return [];
  const refs = (value: unknown) => Array.isArray(value) && value.length <= 32
    && value.every(x => typeof x === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(x)) ? value as string[] : null;
  return data.items.flatMap((value): SharedCandidate[] => {
    const row = record(value);
    if (!row || row.delivery !== "NONE" || typeof row.candidate_record_id !== "string"
      || !/^[A-Za-z0-9._:-]{1,128}$/.test(row.candidate_record_id)
      || typeof row.cycle_id !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/.test(row.cycle_id)
      || typeof row.state !== "string" || !/^[A-Z_]{1,96}$/.test(row.state)
      || (row.topic !== null && row.topic !== undefined && (typeof row.topic !== "string" || row.topic.length > 128))) return [];
    const records = refs(row.source_record_ids), memories = refs(row.source_memory_ids);
    if (!records || !records.length || !memories) return [];
    return [{id: row.candidate_record_id, cycleId: row.cycle_id, topic: typeof row.topic === "string" ? row.topic : "",
      state: row.state, records, memories}];
  }).slice(0, 16);
}

export function credentialProfiles(value: unknown) {
  const data = record(value);
  if (!data || !Array.isArray(data.profiles) || data.profiles.length > 64) return [];
  return data.profiles.flatMap(value => {
    const row = record(value);
    return row && typeof row.provider_profile_id === "string" && /^[A-Za-z0-9._-]{1,128}$/.test(row.provider_profile_id)
      && ["AVAILABLE", "MISSING", "UNCONFIGURED"].includes(String(row.secret_state))
      ? [{id: row.provider_profile_id, state: String(row.secret_state)}] : [];
  });
}

export function vaultMetadata(value: unknown) {
  const data = record(value), vault = record(data?.vault);
  if (!vault || typeof vault.revision !== "number" || !Number.isSafeInteger(vault.revision) || vault.revision < 0) return null;
  return {revision: vault.revision, configured: vault.configured === true,
    persistent: vault.persistence === "HOST_LOCAL_AES_256_GCM" || vault.storage === "HOST_LOCAL_AES_256_GCM",
    state: typeof vault.state === "string" && /^[A-Z_]{1,64}$/.test(vault.state) ? vault.state : "UNKNOWN"};
}

const coverageLabels: Record<string, string> = {
  METADATA_ONLY: "只读到视频信息", METADATA_ONLY_NOT_WATCHED: "只读到视频信息",
  SUBTITLE_EXCERPT: "读过部分字幕", SUBTITLES: "读过字幕",
  SUBTITLE_EXCERPT_NOT_VISUAL_VIEWING: "读过部分字幕 · 未取得画面",
  SOCIAL_CONTEXT_ONLY_NOT_VIDEO_CONTENT: "读过互动上下文 · 未确认视频内容",
  COMMENTS_ONLY: "读过部分评论", DANMAKU_EXCERPT: "读过部分弹幕",
  VISUAL_FRAMES: "有采样画面来源", MULTIMODAL_EXCERPT: "有字幕与采样画面来源",
};
export function coverageLabel(value: unknown): string {
  return typeof value === "string" && coverageLabels[value] ? coverageLabels[value] : "理解范围待核实";
}

export interface BilibiliReading {
  id: string; bvid: string; title: string; coverage: string; interpreted: boolean;
  observedAt: number; subtitles: number; comments: number; danmaku: number; frames: number;
  origin: string; missing: string[];
}
export function bilibiliReadings(value: unknown): BilibiliReading[] {
  const data = record(value);
  if (!data || !Array.isArray(data.items) || data.items.length > 64) return [];
  const count = (v: unknown) => Array.isArray(v) ? v.length : typeof v === "number" && Number.isSafeInteger(v) && v >= 0 ? v : 0;
  return data.items.flatMap((value): BilibiliReading[] => {
    const row = record(value);
    if (!row || typeof row.source_memory_id !== "string" || typeof row.bvid !== "string"
      || !/^BV[A-Za-z0-9]{10}$/.test(row.bvid) || typeof row.title !== "string" || row.title.length > 256
      || typeof row.observed_at_us !== "number" || !Number.isSafeInteger(row.observed_at_us) || row.observed_at_us < 0
      || !/^[A-Za-z0-9._:-]{1,128}$/.test(row.source_memory_id)) return [];
    return [{id: row.source_memory_id, bvid: row.bvid, title: row.title,
      coverage: coverageLabel(row.coverage), interpreted: row.interpreted === true,
      observedAt: row.observed_at_us, subtitles: count(row.subtitle_segments),
      comments: count(row.comment_samples), danmaku: count(row.danmaku_samples), frames: count(row.visual_frames),
      origin: row.source_origin === "REAL_PLATFORM_HTTP" ? "真实平台读取" : row.source_origin === "SYNTHETIC_FIXTURE" ? "合成验证资料" : "来源范围待核实",
      missing: Array.isArray(row.missing_sources) ? row.missing_sources.filter((s): s is string => typeof s === "string").map(s => s.slice(0, 128)).slice(0, 8) : []}];
  }).slice(0, 32);
}

export interface PlatformChannel {
  platform: "qq" | "bilibili"; channel_id: string; enabled: boolean;
  read_authorized: boolean; send_configured: boolean; secret_state: "AVAILABLE" | "MISSING";
  state: string; account_label?: string; conversation_kind?: string;
}
/** Configuration availability is not social authorization or a delivery proof. */
export function platformChannels(value: unknown): PlatformChannel[] {
  const data = record(value);
  if (!data || !Array.isArray(data.channels) || data.channels.length > 32) return [];
  return data.channels.flatMap((value): PlatformChannel[] => {
    const row = record(value);
    if (!row || (row.platform !== "qq" && row.platform !== "bilibili")
      || typeof row.channel_id !== "string" || !/^[a-z][a-z0-9._-]{0,63}$/.test(row.channel_id)
      || typeof row.enabled !== "boolean" || typeof row.read_authorized !== "boolean" || typeof row.send_configured !== "boolean"
      || (row.secret_state !== "AVAILABLE" && row.secret_state !== "MISSING")
      || typeof row.state !== "string" || !/^[A-Z_]{1,96}$/.test(row.state)) return [];
    return [{platform: row.platform, channel_id: row.channel_id, enabled: row.enabled,
      read_authorized: row.read_authorized, send_configured: row.send_configured, secret_state: row.secret_state, state: row.state,
      account_label:typeof row.account_label === "string" && row.account_label.length <= 32?row.account_label:undefined,
      conversation_kind:typeof row.conversation_kind === "string" && ["private","group","dm","comment"].includes(row.conversation_kind)?row.conversation_kind:undefined}];
  });
}
