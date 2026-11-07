import {test,expect,vi,afterEach} from "vitest";
import {V2Client} from "../src/data/v2";
const identity={contract:"nana-space-live/v2",realm:"OWNED_DEVELOPMENT_ONLY",execution_authority:false,
 subject_id:"synthetic-subject",lineage_binding:"a".repeat(64),owner_epoch:1,as_of_us:1,revision:0,
 session_generation:1,run_generation:"b".repeat(32),coverage:"CURRENT",privacy_scope:["PROJECT"],source_refs:[],capabilities:{},data:{}};
const body={client_request_id:"stream-message",idempotency_key:"stream-message",expected_revision:0,
 run_generation:"b".repeat(32),owner_epoch:1,text:"SYNTHETIC",topic:"daily",thread_id:"space",privacy_class:"PROJECT" as const};
const progress=(text:string,sequence=1)=>({event:"progress",message_id:body.client_request_id,sequence,
 data:{...identity,data:{state:"PROVISIONAL_MODEL_DRAFT",text}}});
const final=()=>({event:"receipt",message_id:body.client_request_id,data:{...identity,data:{receipt_id:body.idempotency_key,
 client_request_id:body.client_request_id,operation:"MESSAGE",state:"VERIFIED",dispatch_happened:true,no_retry:true,result:{text:"SYNTHETIC complete"}}}});
const encode=(x:unknown)=>new TextEncoder().encode(JSON.stringify(x)+"\n");
afterEach(()=>vi.unstubAllGlobals());
async function client(){vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify(identity))));const c=new V2Client();await c.bootstrap();return c;}

test("actual received prefix is visible before final receipt, one POST only",async()=>{
 const c=await client();let controller!:ReadableStreamDefaultController<Uint8Array>;
 const stream=new ReadableStream<Uint8Array>({start(value){controller=value;}});
 const fetch=vi.fn(async()=>new Response(stream,{headers:{"Content-Type":"application/x-ndjson"}}));vi.stubGlobal("fetch",fetch);
 const events:unknown[]=[];let complete=false;
 const result=c.streamMessage(body,x=>events.push(x)).then(x=>{complete=true;return x;});
 controller.enqueue(encode(progress("你好，奈奈🌙")));
 await vi.waitFor(()=>expect(events).toHaveLength(1));expect(complete).toBe(false);
 controller.enqueue(encode(final()));
 expect((await result).data.result).toEqual({text:"SYNTHETIC complete"});expect(fetch).toHaveBeenCalledTimes(1);
 expect(fetch.mock.calls[0][0]).toBe("/api/nana-space/v2/messages/stream");
});

test("lost stream yields verify-only and never retries/falls back to buffered POST",async()=>{
 const c=await client();const fetch=vi.fn(async()=>new Response(new ReadableStream({start(x){x.enqueue(encode(progress("partial")));x.close();}}),{headers:{"Content-Type":"application/x-ndjson"}}));vi.stubGlobal("fetch",fetch);
 await expect(c.streamMessage(body,()=>{})).rejects.toMatchObject({code:"STREAM_INTERRUPTED_VERIFY_ONLY"});expect(fetch).toHaveBeenCalledTimes(1);
});

test.each(["identity","generation","id","sequence"])("rejects mismatched %s before presenting text",async(kind)=>{
 const c=await client();const frame=progress("MUST_NOT_SHOW");
 if(kind==="identity")frame.data.subject_id="different";
 if(kind==="generation")frame.data.run_generation="c".repeat(32);
 if(kind==="id")frame.message_id="another-request";
 if(kind==="sequence")frame.sequence=0;
 vi.stubGlobal("fetch",vi.fn(async()=>new Response(new ReadableStream({start(x){x.enqueue(encode(frame));x.close();}}),{headers:{"Content-Type":"application/x-ndjson"}})));
 const show=vi.fn();await expect(c.streamMessage(body,show)).rejects.toBeInstanceOf(Error);expect(show).not.toHaveBeenCalled();
});

test("logout suppresses late chunks instead of re-binding a prior identity",async()=>{
 const c=await client();let controller!:ReadableStreamDefaultController<Uint8Array>;
 vi.stubGlobal("fetch",vi.fn(async()=>new Response(new ReadableStream({start(x){controller=x;}}),{headers:{"Content-Type":"application/x-ndjson"}})));
 const show=vi.fn();const request=c.streamMessage(body,show);c.clear();controller.enqueue(encode(progress("MUST_NOT_SHOW")));
 await expect(request).rejects.toMatchObject({code:"SESSION_REVOKED"});expect(show).not.toHaveBeenCalled();
});
