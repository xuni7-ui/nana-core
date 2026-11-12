/** SDK/native-port contract, synthetic bridge only; no Android device claim. */
import {test,expect,vi,afterEach} from 'vitest';
const bridge=vi.hoisted(()=>({call:vi.fn(),addListener:vi.fn()}));
vi.mock('@capacitor/core',()=>({Capacitor:{isNativePlatform:()=>true},registerPlugin:()=>bridge}));
import {V2Client,V2Error} from '../src/data/v2';
const identity={contract:'nana-space-live/v2',realm:'OWNED_DEVELOPMENT_ONLY',execution_authority:false,
  subject_id:'SYNTHETIC_NATIVE_SUBJECT',lineage_binding:'a'.repeat(64),owner_epoch:1,as_of_us:1,
  revision:0,session_generation:1,run_generation:'b'.repeat(32),coverage:'CURRENT',
  privacy_scope:['PROJECT'],source_refs:[],capabilities:{},data:{}};
const root={client_request_id:'native-root',idempotency_key:'native-root',expected_revision:0,
  run_generation:'b'.repeat(32),owner_epoch:1,text:'SYNTHETIC root',topic:'daily',thread_id:'space',privacy_class:'PROJECT' as const};
afterEach(()=>vi.resetAllMocks());

test.each([false,true])('one native stream permits a bound buffered child; logout=%s suppresses late root',async(logout)=>{
  let finish!:(value:unknown)=>void,progress!:(value:unknown)=>void;
  const remove=vi.fn(async()=>{});
  bridge.addListener.mockImplementation(async(_event:string,listener:(value:unknown)=>void)=>{progress=listener;return {remove};});
  bridge.call.mockImplementation(async({operation,data})=>{
    if(operation==='bootstrap')return identity;
    if(operation==='message.stream')return new Promise(resolve=>{finish=resolve;});
    expect(operation).toBe('message');expect(data.continuation_of).toBe(root.client_request_id);
    return {...identity,data:{receipt_id:data.idempotency_key,client_request_id:data.client_request_id,
      operation:'MESSAGE',no_retry:true,state:'VERIFIED',dispatch_happened:true,result:{text:'SYNTHETIC child wording'}}};
  });
  const client=new V2Client();await client.bootstrap();const display=vi.fn();let done=false;
  const pending=client.streamMessage(root,display).then(value=>{done=true;return {value};},error=>({error}));
  await vi.waitFor(()=>expect(finish).toBeTypeOf('function'));
  progress({event:'progress',message_id:root.client_request_id,sequence:1,
    data:{...identity,data:{state:'INTERPRETING'}}});
  expect(display).toHaveBeenCalledOnce();expect(done).toBe(false);
  const child=await client.write('message',{...root,client_request_id:'native-child',idempotency_key:'native-child',
    text:'SYNTHETIC addition',continuation_of:root.client_request_id});
  expect(child.data.state).toBe('VERIFIED');expect(done).toBe(false);
  if(logout)client.clear();
  finish({...identity,data:{receipt_id:root.idempotency_key,client_request_id:root.client_request_id,
    operation:'MESSAGE',no_retry:true,state:'VERIFIED',dispatch_happened:true,result:{text:null}}});
  expect(await pending).toMatchObject(logout?{error:{code:'SESSION_REVOKED'}}:{value:{data:{state:'VERIFIED'}}});
  expect(remove).toHaveBeenCalledOnce();
  expect(bridge.call.mock.calls.map(([request])=>request.operation)).toEqual(['bootstrap','message.stream','message']);
});

test.each(['CONTINUATION_WINDOW_CLOSED','SESSION_REVOKED','SYNTHETIC verbose failure'])('native rejection %s becomes a bounded typed error without replay',async(message)=>{
  bridge.call.mockResolvedValueOnce(identity).mockRejectedValueOnce(new Error(message));
  const client=new V2Client();await client.bootstrap();
  const error=await client.write('message',{...root,continuation_of:'previous-root'}).catch(error=>error);
  expect(error).toBeInstanceOf(V2Error);
  expect(error.code).toBe(message==='SYNTHETIC verbose failure'?'NETWORK_OR_EXECUTION_UNKNOWN':message);
  expect(bridge.call).toHaveBeenCalledTimes(2);
});
