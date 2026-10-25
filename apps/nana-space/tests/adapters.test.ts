import { describe, expect, it, vi } from 'vitest';
import { demoAdapter } from '../src/data/demo';
import { createDemoSnapshot, DEMO_IDENTITY } from '../src/data/fixtures';
import { parseInspectorSnapshot, MAX_INSPECTOR_BYTES } from '../src/data/inspector';
import { plannedGateway, validateGatewayConfiguration, validateGatewayProjection } from '../src/data/gateway';
import { contractRegistry } from '../src/data/registry';
import type { Scenario } from '../src/data/contracts';
const inspector = () => ({ schema_version:1, derived:true, read_only:true, identity_id:'subject-1', as_of_us:1792841350875917, coverage:'BOUNDED_METADATA_ONLY', governance_visibility:'LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE', execution_authority:false, sections:{runtime:[{category:'LEASE_EPOCH',reference:'4',state:'ACTIVE',record_id:null,as_of_us:null,source_memory_ids:[]}]}, resources:{VmRSS:42000,Threads:1} });
describe('fictional Demo data and transitions', () => {
  it('covers life, evidence and authority states with fictional identity', () => {
    const value=createDemoSnapshot('evening'); expect(value.identityId).toBe(DEMO_IDENTITY);
    expect(value.memories.length).toBeGreaterThanOrEqual(4); expect(value.goals.length).toBeGreaterThanOrEqual(6); expect(value.activities.length).toBeGreaterThanOrEqual(6); expect(value.research.length).toBeGreaterThanOrEqual(3); expect(value.skills.length).toBeGreaterThanOrEqual(6); expect(value.devices.length).toBeGreaterThanOrEqual(10); expect(value.messages.length).toBeGreaterThanOrEqual(10);
    expect(value.goals.find(g=>g.state==='DECLINED')?.reason).not.toContain('缺少权限'); expect(value.goals.some(g=>g.state==='BLOCKED')).toBe(true); expect(value.goals.some(g=>g.state==='UNKNOWN')).toBe(true); expect(value.memories.some(m=>m.state==='WITHDRAWN')).toBe(true); expect(value.memories.some(m=>m.state==='CORRECTED')).toBe(true); expect(value.devices.every(d=>d.state!=='CONNECTED'&&d.act.length===0)).toBe(true);
    value.goals[0].title='local mutation'; expect(createDemoSnapshot('evening').goals[0].title).not.toBe('local mutation');
  });
  it('preserves identity across recovery and every scenario', () => {
    const scenarios:Scenario[]=['evening','offline','blocked','conflict','restart','quiet','partial','model-unavailable','slow','error']; for(const s of scenarios) expect(createDemoSnapshot(s).identityId).toBe(DEMO_IDENTITY);
    expect(createDemoSnapshot('restart').runtime.epoch).toBe(5); expect(createDemoSnapshot('partial').memories).toEqual([]); expect(createDemoSnapshot('quiet').messages.some(m=>m.proactive)).toBe(false); expect(createDemoSnapshot('model-unavailable').runtime.status).toBe('DEGRADED');
  });
  it('cancels slow loading without resolving stale fixtures', async () => {
    const controller=new AbortController(); const pending=demoAdapter.load('slow',controller.signal); controller.abort(); await expect(pending).rejects.toMatchObject({name:'AbortError'}); await expect(demoAdapter.load('evening',controller.signal)).rejects.toMatchObject({name:'AbortError'});
  });
  it('has explicit failure and UNKNOWN semantics without retries', async () => {
    const chunks=vi.fn(); await expect(demoAdapter.send('看看星空','offline',chunks)).rejects.toMatchObject({code:'OFFLINE'}); await expect(demoAdapter.send('看看星空','model-unavailable',chunks)).rejects.toMatchObject({code:'RESOURCE_UNAVAILABLE'}); await expect(demoAdapter.send('看看星空','restart',chunks)).rejects.toMatchObject({code:'UNKNOWN'}); await expect(demoAdapter.send('看看星空','error',chunks)).rejects.toMatchObject({code:'SEND_FAILED'}); expect(chunks).not.toHaveBeenCalled();
  });
  it('streams cumulative local text and cancels mid-stream', async () => {
    const controller=new AbortController(); const chunks:string[]=[]; await expect(demoAdapter.send('观星','evening',chunk=>{chunks.push(chunk);controller.abort();},controller.signal)).rejects.toMatchObject({name:'AbortError'}); expect(chunks).toHaveLength(1);
    const complete:string[]=[]; const text=await demoAdapter.send('观星','evening',chunk=>complete.push(chunk)); expect(complete.length).toBeGreaterThan(2); expect(complete.at(-1)).toBe(text); expect(text).toContain('没有调用 Nana Core');
  });
  it('surfaces a load error instead of returning usable-looking data',async()=>{await expect(demoAdapter.load('error')).rejects.toMatchObject({code:'DEMO_LOAD_FAILED'});});
});
describe('Core Inspector boundary',()=>{
  it('accepts existing v1 and discards undeclared private objects',()=>{
    const input={...inspector(),self_view:{secret:'do not retain'},advanced_life:{thoughts:'do not retain'},sections:{...inspector().sections,arbitrary:[{text:'private'}]},resources:{...inspector().resources,process_path:9000}};
    const output=parseInspectorSnapshot(JSON.stringify(input),'subject-1'); expect(output.identity_id).toBe('subject-1');expect(output.sections.runtime[0].state).toBe('ACTIVE'); expect(output).not.toHaveProperty('self_view');expect(output).not.toHaveProperty('advanced_life');expect(output.sections).not.toHaveProperty('arbitrary');expect(output.resources).not.toHaveProperty('process_path');
  });
  it('rejects schema, authority, lineage and missing governance boundary',()=>{
    expect(()=>parseInspectorSnapshot({...inspector(),schema_version:2})).toThrow(); expect(()=>parseInspectorSnapshot({...inspector(),execution_authority:true})).toThrow(); expect(()=>parseInspectorSnapshot({...inspector(),read_only:false})).toThrow(); expect(()=>parseInspectorSnapshot({...inspector(),governance_visibility:'PUBLIC'})).toThrow(); expect(()=>parseInspectorSnapshot(inspector(),'other')).toThrow(); expect(()=>parseInspectorSnapshot({state:'UNKNOWN',read_only:true})).toThrow();
  });
  it('bounds bytes, arrays, tokens, integers and resource values',()=>{
    expect(()=>parseInspectorSnapshot(' '.repeat(MAX_INSPECTOR_BYTES+1))).toThrow(); expect(()=>parseInspectorSnapshot({...inspector(),as_of_us:Number.MAX_SAFE_INTEGER+1})).toThrow(); expect(()=>parseInspectorSnapshot({...inspector(),sections:{runtime:Array(33).fill(inspector().sections.runtime[0])}})).toThrow(); expect(()=>parseInspectorSnapshot({...inspector(),sections:{runtime:[{...inspector().sections.runtime[0],reference:'x'.repeat(257)}]}})).toThrow();expect(()=>parseInspectorSnapshot({...inspector(),resources:{Threads:-1}})).toThrow();expect(()=>parseInspectorSnapshot('{bad json')).toThrow();
  });
});
describe('planned gateway preparation',()=>{
  const config=()=>({contract:'nana-space-gateway/v1',path:'/api/nana-space/v1/inspector',expectedIdentity:'subject-1',credentials:'same-origin',readOnly:true});
  it('only permits same-origin sessions without credential fields',()=>{
    expect(validateGatewayConfiguration(config(),'https://nana.example').credentials).toBe('same-origin');expect(()=>validateGatewayConfiguration({...config(),secret:'forbidden'},'https://nana.example')).toThrow();expect(()=>validateGatewayConfiguration({...config(),path:'https://other.example/api'},'https://nana.example')).toThrow();expect(()=>validateGatewayConfiguration({...config(),path:'//other.example/api'},'https://nana.example')).toThrow();expect(()=>validateGatewayConfiguration({...config(),credentials:'include'},'https://nana.example')).toThrow();expect(()=>validateGatewayConfiguration({...config(),path:'/api/nana-space/v1?token=unsafe'},'https://nana.example')).toThrow();
  });
  it('requires matching identity, version and read-only projection',()=>{
    const envelope={contract:'nana-space-gateway/v1',subject_id:'subject-1',projection:'INSPECTOR',execution_authority:false,data:inspector()};expect(validateGatewayProjection(envelope,'subject-1').data.identity_id).toBe('subject-1');expect(()=>validateGatewayProjection(envelope,'other')).toThrow();expect(()=>validateGatewayProjection({...envelope,contract:'v2'},'subject-1')).toThrow();expect(()=>validateGatewayProjection({...envelope,projection:'EXECUTE'},'subject-1')).toThrow();expect(()=>validateGatewayProjection({...envelope,execution_authority:true},'subject-1')).toThrow();
  });
  it('remains disabled and never requests the network',async()=>{
    const network=vi.fn();vi.stubGlobal('fetch',network);await expect(plannedGateway.load()).rejects.toMatchObject({code:'GATEWAY_NOT_IMPLEMENTED'});expect(plannedGateway.enabled).toBe(false);expect(network).not.toHaveBeenCalled();vi.unstubAllGlobals(); expect(contractRegistry.find(c=>c.id==='gateway')?.maturity).toBe('PLANNED');expect(contractRegistry.find(c=>c.id==='inspector')?.maturity).toBe('BACKEND_AVAILABLE');
  });
});
