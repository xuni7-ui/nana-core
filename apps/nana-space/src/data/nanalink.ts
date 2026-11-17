export interface LinkHealth {
  connection: string; login: string; receive: string; error?: string;
  reconnects: number; capabilities: {name: string; available: boolean}[];
}
const object = (v:unknown):Record<string,unknown>|null => v!==null && typeof v==='object' && !Array.isArray(v) ? v as Record<string,unknown> : null;
const states = new Set(['DISABLED','DISCONNECTED','CONNECTING','CONNECTED','DEGRADED']);
export function linkHealth(data:unknown,platform:string,channel:string):LinkHealth|null {
  const root=object(data), link=object(root?.nanalink);
  if(link?.schema_version!==1 || !Array.isArray(link.sessions) || link.sessions.length>16)return null;
  const row=link.sessions.map(object).find(r=>r?.platform===platform && r?.channel_id===channel), health=object(row?.health);
  if(!health || !states.has(String(health.connection)) || !['UNKNOWN','AUTHENTICATED','REQUIRED'].includes(String(health.login))
    || !['NOT_OBSERVED','HEALTHY','STALE','BACKPRESSURE'].includes(String(health.receive)))return null;
  const caps=Array.isArray(row?.capabilities) && row.capabilities.length<=32 ? row.capabilities : [];
  return {connection:String(health.connection),login:String(health.login),receive:String(health.receive),
    reconnects:typeof health.reconnects==='number' && Number.isSafeInteger(health.reconnects) && health.reconnects>=0?health.reconnects:0,
    error:typeof health.error==='string' && /^[A-Z_]{1,96}$/.test(health.error)?health.error:undefined,
    capabilities:caps.flatMap(v=>{const c=object(v);return c && typeof c.name==='string' && /^[a-z][a-z0-9._-]{0,95}$/.test(c.name)
      && typeof c.available==='boolean'?[{name:c.name,available:c.available}]:[];})};
}
export function healthWords(health:LinkHealth|null):string {
  if(!health)return '连接状态尚未观测';
  const connection:Record<string,string>={DISABLED:'连接已暂停',DISCONNECTED:'连接已断开',CONNECTING:'正在恢复连接',CONNECTED:'会话已连接',DEGRADED:'连接需要检查'};
  const receive:Record<string,string>={NOT_OBSERVED:'还未收到事件',HEALTHY:'事件接收正常',STALE:'心跳过期，请检查客户端',BACKPRESSURE:'接收繁忙，部分事件未入队'};
  const errors:Record<string,string>={ACCOUNT_MISMATCH:'账号不匹配，请检查连接账号',CREDENTIAL_UNAVAILABLE:'连接凭据不可用，请重新绑定',CREDENTIAL_REJECTED:'连接凭据未获接受或权限不足，请检查绑定',SIDECAR_UNAVAILABLE:'连接服务暂不可达，请检查服务状态'};
  const hint=health.error && errors[health.error] ? ` · ${errors[health.error]}` : '';
  return `${connection[health.connection]}${health.login==='REQUIRED'?' · 需要重新登录或更新授权':''} · ${receive[health.receive]}${hint}`;
}

export function capabilityWords(name:string):string {
  const labels:Record<string,string>={
    'message.receive':'接收消息','message.text.send.via_core':'经奈奈发送文字',
    'message.readback':'独立核实送达','delivery.independent_readback':'独立核实送达',
    'media.reference':'接收媒体引用','message.image.send.via_core':'经奈奈发送图片',
    'message.face.send.via_core':'经奈奈发送表情','login.qr':'二维码登录',
    'login.external_session':'使用已有授权会话','message.edit':'编辑消息',
  };
  return labels[name] || name;
}
