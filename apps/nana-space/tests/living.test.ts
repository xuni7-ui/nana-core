import { expect, test } from "vitest";
import { platformChannels } from "../src/data/living";
import { bilibiliReadings, credentialProfiles, mergeRetainedTurns, retainedTurns, pendingReceiptTurns, sharedCandidates, vaultMetadata, sequenceTextWireBytes, sequenceReceiptTurns, messageReceiptTurns } from "../src/data/living";

const groupMembers=()=>['one','two','parent'].map(id=>({id,input:'SYNTHETIC '+id,state:'REQUESTED',receiptId:'parent'}));
const groupReceipt=()=>({receipt_id:'parent',operation:'MESSAGE_SEQUENCE',state:'VERIFIED',result:{
  state:'SUBJECT_SEQUENCE_REVIEWED',external_delivery:false,results:['one','two','parent'].map((id,i)=>({
    client_message_id:id,message_memory_id:'memory-'+i,external_delivery:false,
    render_state:i===2?'UNVERIFIED_MODEL_WORDING':'DEFERRED_TO_CONTINUATION',
    text:i===2?'SYNTHETIC one actual reply':null,respond_to_memory_ids:i===2?['memory-0','memory-1','memory-2']:[],
  }))}});
test('sequence receipt shows exactly its source-bound reply without inventing earlier assistant speech',()=>{
  const rows=sequenceReceiptTurns('parent',groupReceipt(),groupMembers())!;
  expect(rows.map(r=>r.state)).toEqual(['GROUPED','GROUPED','VERIFIED']);
  expect(rows.filter(r=>r.reply).map(r=>r.reply)).toEqual(['SYNTHETIC one actual reply']);
  expect(rows.map(r=>r.input)).toEqual(['SYNTHETIC one','SYNTHETIC two','SYNTHETIC parent']);
  expect(rows.every(r=>r.receiptId==='parent')).toBe(true);
});
test('sequence UNKNOWN retains one parent verification handle and never promotes visible wording',()=>{
  const value={...groupReceipt(),state:'UNKNOWN'};
  const rows=sequenceReceiptTurns('parent',value,groupMembers())!;
  expect(rows.map(r=>r.state)).toEqual(['GROUP_PENDING','GROUP_PENDING','UNKNOWN']);
  expect(rows.some(r=>r.reply)).toBe(false);
  const invalid=groupReceipt();invalid.result.results[2].respond_to_memory_ids.push('foreign-private-source');
  expect(sequenceReceiptTurns('parent',invalid,groupMembers())!.some(r=>r.reply)).toBe(false);
});
test('withdrawal clears the whole sequence body while preserving unrelated dialogue',()=>{
  const other={id:'unrelated',input:'SYNTHETIC other scope',state:'VERIFIED',reply:'other reply'};
  const rows=sequenceReceiptTurns('parent',{receipt_id:'parent',operation:'MESSAGE_SEQUENCE',state:'VERIFIED',
    result:{state:'BODY_WITHHELD_SOURCE_CHANGED'}},[other,...groupMembers()])!;
  expect(rows[0]).toEqual(other);
  expect(rows.slice(1).every(r=>r.input==='' && !r.reply && r.state==='SOURCE_WITHHELD')).toBe(true);
});
test('manual sequence verification after reload restores only actual replies and no unretained question',()=>{
  const pending=pendingReceiptTurns({pending_receipts:[{receipt_id:'parent',state:'UNKNOWN'}]});
  const rows=sequenceReceiptTurns('parent',groupReceipt(),pending)!;
  expect(rows).toHaveLength(1);expect(rows[0]).toMatchObject({input:'',reply:'SYNTHETIC one actual reply',receiptId:'parent'});
});
test('verified sequence metadata without a cached body does not become a fake reply or uncertain execution',()=>{
  const rows=sequenceReceiptTurns('parent',{receipt_id:'parent',operation:'MESSAGE_SEQUENCE',state:'VERIFIED',result:{}},groupMembers())!;
  expect(rows.every(r=>r.state==='REPLY_UNAVAILABLE' && !r.reply)).toBe(true);
});
test('sequence pre-dispatch grouping measures ASCII-escaped IPC text including Unicode surrogate pairs',()=>{
  expect(sequenceTextWireBytes(['月','🌙'])).toBe(25);
  expect(sequenceTextWireBytes(['月'.repeat(2048),'月'.repeat(2048)])).toBeGreaterThan(12288);
  expect(sequenceTextWireBytes(['one','two'])).toBeLessThan(12288);
});

test("retained history restores only valid sourced rows and withdrawal removes stale restored bodies", () => {
  const saved = retainedTurns({items: [{exchange_record_id: "exchange-1", user_text: "PROJECT common task", reply_text: "Sourced reply", created_at_us: 10}]});
  expect(saved[0]).toMatchObject({remembered: true, restored: true, state: "VERIFIED"});
  expect(mergeRetainedTurns(saved, saved)).toEqual(saved);
  const unknown = {id: "original-request", input: "", state: "UNKNOWN"};
  expect(mergeRetainedTurns([], [...saved, unknown])).toEqual([unknown]);
  expect(retainedTurns({items: [{...saved[0], exchange_record_id: "../../other", created_at_us: 10}]})).toEqual([]);
});

test("complete long retained replies restore within the Core character bound", () => {
  const row = {exchange_record_id: "long-speech", user_text: "source", reply_text: "SYNTHETIC "+"explanation. ".repeat(1000), created_at_us: 10};
  expect(retainedTurns({items: [row]})[0]?.reply).toBe(row.reply_text);
  const astral = {...row, reply_text: "🌙".repeat(10000)};
  expect(retainedTurns({items: [astral]})[0]?.reply).toBe(astral.reply_text);
  expect(retainedTurns({items: [{...row, reply_text: "x".repeat(16385)}]})).toEqual([]);
  expect(mergeRetainedTurns([], retainedTurns({items: [astral]}))).toEqual([]);
});

test("platform settings distinguish configured source from authority and filter unknown sensitive fields", () => {
  const channel = {platform: "qq", channel_id: "primary", enabled: true, read_authorized: true,
    send_configured: true, secret_state: "AVAILABLE", state: "NOT_OBSERVED"};
  expect(platformChannels({channels: [{...channel, credential: "TEST_ONLY_NOT_SECRET", grant: "IGNORE"}]})).toEqual([channel]);
  expect(platformChannels({channels: [{...channel, platform: "HOST_ADMIN"}]})).toEqual([]);
  expect(platformChannels({channels: [{...channel, enabled: "false"}]})).toEqual([]);
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

const deferredReceipt=()=>({receipt_id:'root',operation:'MESSAGE',state:'VERIFIED',result:{
  state:'SHADOW_INPUT_REVIEWED_NO_REPLY',render_state:'DEFERRED_TO_CONTINUATION',text:null,
  message_memory_id:'memory.root',respond_to_memory_ids:[] as string[],raw_body_persisted:false,
  exchange_record_id:null,external_delivery:false,completion_kind:'SUBJECT_REVIEW_NOT_SOCIAL_DELIVERY'}});
const combinedReceipt=()=>({receipt_id:'child',operation:'MESSAGE',state:'VERIFIED',result:{
  state:'SHADOW_REPLY_CANDIDATE',render_state:'UNVERIFIED_MODEL_WORDING',text:'SYNTHETIC combined reply',
  message_memory_id:'memory.child',respond_to_memory_ids:['memory.root','memory.child'],reply_response_id:'cycle.child'}});
const independentTurns=()=>[{id:'root',input:'SYNTHETIC original',state:'REQUESTED',provisional:'SYNTHETIC unsent draft'},
  {id:'child',input:'SYNTHETIC continuation',state:'REQUESTED'}];
test('a verified deferred review clears provisional speech and does not pretend a reply or delivery',()=>{
  const rows=messageReceiptTurns('root',deferredReceipt(),independentTurns());
  expect(rows[0]).toMatchObject({state:'DEFERRED_REPLY',messageMemoryId:'memory.root'});
  expect(rows[0].reply).toBeUndefined();expect(rows[0].provisional).toBeUndefined();
  expect(rows[1]).toEqual(independentTurns()[1]);
});
test('independent original receipts display one reply tied to both source inputs',()=>{
  const a=messageReceiptTurns('root',deferredReceipt(),independentTurns());
  const rows=messageReceiptTurns('child',combinedReceipt(),a);
  expect(rows.map(r=>r.state)).toEqual(['GROUPED','VERIFIED']);
  expect(rows.filter(r=>r.reply).map(r=>r.reply)).toEqual(['SYNTHETIC combined reply']);
  expect(rows[0].receiptId).toBeUndefined(); // keep individual verification, not a sequence parent
});
test('reversed completion order still removes the old unsent draft only after its own reviewed receipt',()=>{
  const a=messageReceiptTurns('child',combinedReceipt(),independentTurns());
  expect(a[0].state).toBe('REQUESTED');
  const rows=messageReceiptTurns('root',deferredReceipt(),a);
  expect(rows.map(r=>r.state)).toEqual(['GROUPED','VERIFIED']);expect(rows[0].provisional).toBeUndefined();
});
test('UNKNOWN cannot promote leftover wording or claim it answered a deferred parent',()=>{
  const a=messageReceiptTurns('root',deferredReceipt(),independentTurns());
  const rows=messageReceiptTurns('child',{...combinedReceipt(),state:'UNKNOWN'},a);
  expect(rows.map(r=>r.state)).toEqual(['DEFERRED_REPLY','UNKNOWN']);expect(rows.some(r=>r.reply)).toBe(false);
});
test('malformed reviewed or reply source bindings stay UNKNOWN without invented speech',()=>{
  const wrong=deferredReceipt();wrong.result.respond_to_memory_ids.push('foreign');
  expect(messageReceiptTurns('root',wrong,independentTurns())[0]).toMatchObject({state:'UNKNOWN',error:'CONTINUATION_REPLY_BINDING_INVALID'});
  const a=messageReceiptTurns('root',deferredReceipt(),independentTurns());
  const bad=combinedReceipt();bad.result.respond_to_memory_ids=['memory.root'];
  const rows=messageReceiptTurns('child',bad,a);expect(rows[0].state).toBe('DEFERRED_REPLY');
  expect(rows[1].state).toBe('UNKNOWN');expect(rows[1].reply).toBeUndefined();
});
test('legacy single replies still display and withdrawn bodies clear the input',()=>{
  const turns=independentTurns();
  expect(messageReceiptTurns('root',{state:'VERIFIED',result:{text:'legacy reply'}},turns)[0].reply).toBe('legacy reply');
  const rows=messageReceiptTurns('root',{state:'VERIFIED',result:{state:'BODY_WITHHELD_SOURCE_CHANGED'}},turns);
  expect(rows[0]).toEqual({id:'root',input:'',state:'SOURCE_WITHHELD'});expect(rows[1]).toEqual(turns[1]);
});
