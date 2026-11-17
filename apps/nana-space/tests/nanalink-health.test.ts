import {describe,it,expect} from 'vitest';
import {linkHealth,healthWords,capabilityWords,capabilityStatusWords} from '../src/data/nanalink';

describe('NanaLink phone health',()=>{
  it('distinguishes expired login from receipt health and names unsupported media',()=>{
    const data={nanalink:{schema_version:1,sessions:[{platform:'qq',channel_id:'primary',
      health:{connection:'DEGRADED',login:'REQUIRED',receive:'NOT_OBSERVED'},
      capabilities:[{name:'message.image.send.via_core',available:false}]}]}};
    const health=linkHealth(data,'qq','primary');
    expect(healthWords(health)).toContain('需要重新登录或更新授权');
    expect(healthWords(health)).toContain('还未收到事件');
    expect(capabilityWords(health!.capabilities[0].name)).toBe('发送图片');
    expect(health!.capabilities[0].available).toBe(false);
  });
  it('describes actual Bilibili and QQ capability readiness without exposing unknown reasons',()=>{
    const data={nanalink:{schema_version:1,sessions:[{platform:'bilibili',channel_id:'main',
      health:{connection:'CONNECTED',login:'AUTHENTICATED',receive:'HEALTHY'},capabilities:[
        {name:'video.frames',available:true,reason:'ORIGINAL_C_GRANT_AND_SOURCE_REQUIRED'},
        {name:'notification.reply',available:false,reason:'PRIVATE_READ_OR_CHANNEL_DISABLED'},
        {name:'message.text.send',available:false,reason:'SEND_AUTHORIZATION_OR_CHANNEL_DISABLED'},
        {name:'dynamic.publish',available:false,reason:'NO_EXISTING_GOVERNED_PORT'},
        {name:'future.capability',available:false,reason:'UNRECOGNIZED_INTERNAL_REASON'},
        {name:'video.subtitles',available:false,reason:'ORIGINAL_C_GRANT_AND_SOURCE_REQUIRED'},
      ]}]}};
    const caps=linkHealth(data,'bilibili','main')!.capabilities;
    expect(caps.map(c=>[capabilityWords(c.name),capabilityStatusWords(c)])).toEqual([
      ['读取视频故事板帧','可由主体选择，仍需来源和授权'],
      ['接收回复通知','需启用通道并授权读取私人通知'],
      ['发送文字','需启用通道并完成发送授权'],
      ['发布动态','当前版本尚未接通'],
      ['其他能力','未就绪或暂不支持'],
      ['读取视频字幕','未就绪或暂不支持'],
    ]);
  });
  it('explains safe diagnostics without displaying unrecognized server text',()=>{
    const base={connection:'DISCONNECTED',login:'UNKNOWN',receive:'NOT_OBSERVED',reconnects:0,capabilities:[]};
    expect(healthWords({...base,error:'ACCOUNT_MISMATCH'})).toContain('账号不匹配');
    expect(healthWords({...base,error:'CREDENTIAL_UNAVAILABLE'})).toContain('连接凭据不可用');
    expect(healthWords({...base,error:'CREDENTIAL_REJECTED'})).toContain('连接凭据未获接受');
    expect(healthWords({...base,error:'SIDECAR_UNAVAILABLE'})).toContain('连接服务暂不可达');
    expect(healthWords({...base,error:'UNEXPECTED_DETAIL'})).not.toContain('UNEXPECTED_DETAIL');
  });
});
