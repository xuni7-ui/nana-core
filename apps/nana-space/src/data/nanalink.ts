export interface LinkCapability {name: string; available: boolean; reason?: string}
export interface LinkHealth {
  connection: string; login: string; receive: string; error?: string;
  reconnects: number; capabilities: LinkCapability[];
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
      && typeof c.available==='boolean'?[{name:c.name,available:c.available,
        reason:typeof c.reason==='string' && /^[A-Z_]{1,96}$/.test(c.reason)?c.reason:undefined}]:[];})};
}
export function healthWords(health:LinkHealth|null):string {
  if(!health)return '连接状态尚未观测';
  const connection:Record<string,string>={DISABLED:'连接已暂停',DISCONNECTED:'连接已断开',CONNECTING:'正在恢复连接',CONNECTED:'会话已连接',DEGRADED:'连接需要检查'};
  const receive:Record<string,string>={NOT_OBSERVED:'还未收到事件',HEALTHY:'事件接收正常',STALE:'心跳过期，请检查客户端',BACKPRESSURE:'接收繁忙，部分事件未入队'};
  const errors:Record<string,string>={ACCOUNT_MISMATCH:'账号不匹配，请检查连接账号',CREDENTIAL_UNAVAILABLE:'连接凭据不可用，请重新绑定',CREDENTIAL_REJECTED:'连接凭据未获接受或权限不足，请检查绑定',SIDECAR_UNAVAILABLE:'连接服务暂不可达，请检查服务状态',RECALL_NOT_WITHDRAWN:'检测到消息撤回，相关记忆如已保存不会自动撤销，请检查',EVENT_ID_COLLISION_DROPPED:'检测到消息编号冲突，已跳过异常消息，请检查连接器',EVENT_ACCOUNT_MISMATCH:'连接器事件账号不符，已拒绝该事件',ADAPTER_RECEIVE_FAILED:'连接器接收出错，正在重试，请检查连接器',INVALID_EVENT_DROPPED:'连接器收到无效事件，已跳过该事件'};
  if(health.error==='PLATFORM_SESSION_OFFLINE')return `${connection[health.connection]} · QQ 账号已离线，请在连接器中重新登录 · ${receive[health.receive]}`;
  const hint=health.error && errors[health.error] ? ` · ${errors[health.error]}` : '';
  return `${connection[health.connection]}${health.login==='REQUIRED'?' · 需要重新登录或更新授权':''} · ${receive[health.receive]}${hint}`;
}

export function capabilityWords(name:string):string {
  const labels:Record<string,string>={
    'message.receive':'接收消息','message.text.send':'发送文字','message.text.send.via_core':'发送文字',
    'message.readback':'独立核实送达','delivery.independent_readback':'独立核实送达',
    'media.reference':'接收媒体引用','message.image.send.via_core':'发送图片',
    'message.face.send.via_core':'发送表情','login.qr':'二维码登录',
    'login.external_session':'使用已有授权会话','message.edit':'编辑消息',
    'video.metadata':'读取公开视频资料','video.subtitles':'读取视频字幕',
    'video.frames':'读取视频故事板帧','notification.reply':'接收回复通知',
    'dynamic.publish':'发布动态','feed.receive':'接收订阅更新','message.send':'发送消息',
  };
  return labels[name] || '其他能力';
}

export function capabilityStatusWords(capability:LinkCapability):string {
  if(capability.available) return capability.reason==='ORIGINAL_C_GRANT_AND_SOURCE_REQUIRED'
    ? '可由主体选择，仍需来源和授权' : '可用';
  const reasons:Record<string,string>={
    READ_AUTHORIZATION_OR_CHANNEL_DISABLED:'需启用通道并完成所需读取授权',
    SEND_AUTHORIZATION_OR_CHANNEL_DISABLED:'需启用通道并完成发送授权',
    PRIVATE_READ_OR_CHANNEL_DISABLED:'需启用通道并授权读取私人通知',
    ORIGINAL_VIDEO_NOT_CONFIGURED_OR_AUTHORIZED:'需配置并授权公开视频读取',
    ORIGINAL_VIDEO_FRAMES_NOT_CONFIGURED_OR_AUTHORIZED:'需配置并授权视频帧读取',
    FRAME_DECODER_UNAVAILABLE:'宿主缺少图像解码组件',
    ORIGINAL_MEDIA_ACTION_NOT_WIRED:'当前版本尚未接通',
    NO_EXISTING_GOVERNED_PORT:'当前版本尚未接通',
    C2C_GROUP_API_NOT_AVAILABLE:'当前接口不支持独立核实',
    PLATFORM_UNSUPPORTED:'平台暂不支持',
    NOT_IN_MINIMUM_PROTOCOL:'当前连接协议暂不支持',
    EXTERNAL_CLIENT_LOGIN:'请在对应客户端登录',
    READ_ONLY_SOURCE:'此来源只支持读取',
  };
  return (capability.reason && reasons[capability.reason]) || '未就绪或暂不支持';
}
