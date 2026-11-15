import {describe,it,expect} from 'vitest';
import {linkHealth,healthWords,capabilityWords} from '../src/data/nanalink';

describe('NanaLink phone health',()=>{
  it('distinguishes expired login from receipt health and names unsupported media',()=>{
    const data={nanalink:{schema_version:1,sessions:[{platform:'qq',channel_id:'primary',
      health:{connection:'DEGRADED',login:'REQUIRED',receive:'NOT_OBSERVED'},
      capabilities:[{name:'message.image.send.via_core',available:false}]}]}};
    const health=linkHealth(data,'qq','primary');
    expect(healthWords(health)).toContain('需要重新登录或更新授权');
    expect(healthWords(health)).toContain('还未收到事件');
    expect(capabilityWords(health!.capabilities[0].name)).toBe('经奈奈发送图片');
    expect(health!.capabilities[0].available).toBe(false);
  });
});
