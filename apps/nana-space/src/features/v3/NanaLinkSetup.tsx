import {useState} from 'react';
import {V2Client, object, writeBase} from '../../data/v2';
import type {Envelope} from '../../data/v2.generated';

/** Prepare in original CAS config only. Login and real account authorization
 * cannot be smuggled into this reversible phone setup command. */
export function NanaLinkSetup({client,status,canManage,onSaved}:{client:V2Client;status:Envelope|null;canManage:boolean;onSaved:()=>Promise<void>}) {
  const [open,setOpen]=useState(false),[platform,setPlatform]=useState('qq'),[backend,setBackend]=useState('onebot');
  const [account,setAccount]=useState(''),[peer,setPeer]=useState(''),[sender,setSender]=useState('');
  const [kind,setKind]=useState('private'),[endpoint,setEndpoint]=useState('http://127.0.0.1:18790');
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const choose=(value:string)=>{setPlatform(value);setKind(value==='qq'?'private':'dm');setMessage('');};
  const submit=async()=>{
    if(!status || busy || !canManage)return;
    const origin=object(status.data), source=kind==='group'||kind==='comment'?sender:peer;
    if(![account,peer,source].every(v=>/^[0-9]{1,20}$/.test(v))){setMessage('请填写数字账号和会话对象；群聊或评论还需明确消息发送者。');return;}
    setBusy(true);setMessage('');
    try {
      const result=object((await client.setupPlatform({...writeBase(status,crypto.randomUUID()),
        method:platform==='qq'?'qq.onebot':'bilibili.account',account_id:account,peer_id:peer,sender_id:source,kind,
        endpoint,configuration_revision:origin.configuration_revision})).data);
      setMessage(result.state==='VERIFIED'?'连接配置已保存并保持暂停。下一步由已授权宿主绑定账号会话与读取范围，再启动入口。'
        :result.state==='UNKNOWN'?'保存结果待核对，请刷新查看，勿重复提交。':'配置未保存，请刷新版本并检查管理权限。');
      await onSaved();
    } catch {setMessage('保存回执未确认，请刷新查看；不会自动重试。');}
    finally {setBusy(false);}
  };
  if(!canManage)return null;
  return <section className="nanalink-setup" aria-label="NanaLink连接向导">
    <button className="v3-button soft" onClick={()=>setOpen(!open)} aria-expanded={open}>添加平台连接</button>
    {open && <div className="v3-card">
      <h3>1 · 选择平台和连接方式</h3>
      <label>平台 <select aria-label="连接平台" value={platform} onChange={e=>choose(e.target.value)}>
        <option value="qq">QQ</option><option value="bilibili">哔哩哔哩</option></select></label>
      {platform==='qq' && <label>连接方式 <select aria-label="QQ连接方式" value={backend} onChange={e=>setBackend(e.target.value)}>
        <option value="onebot">OneBot · 外部QQ客户端</option><option value="official">QQ官方Bot · 现有AstrBot宿主</option></select></label>}
      {platform==='qq' && backend==='official' ? <p role="status">官方Bot沿用现有AstrBot适配和补丁。请在官方开发者平台及已部署宿主完成授权；当前向导尚不能创建官方账号连接。</p> : <>
      <h3>2 · 指定账号与会话</h3>
      <label>平台账号 <input aria-label="平台账号" inputMode="numeric" autoComplete="off" value={account} onChange={e=>setAccount(e.target.value)}/></label>
      <label>会话类型 <select aria-label="会话类型" value={kind} onChange={e=>setKind(e.target.value)}>
        {platform==='qq'?<><option value="private">私聊</option><option value="group">群聊</option></>:<><option value="dm">私信</option><option value="comment">视频评论</option></>}
      </select></label>
      <label>{kind==='group'?'群号':kind==='comment'?'视频aid':'联系人账号'} <input aria-label="会话对象" inputMode="numeric" autoComplete="off" value={peer} onChange={e=>setPeer(e.target.value)}/></label>
      {(kind==='group'||kind==='comment') && <label>允许接收的发送者账号 <input aria-label="发送者账号" inputMode="numeric" value={sender} onChange={e=>setSender(e.target.value)}/></label>}
      {platform==='qq' && <details><summary>高级连接设置</summary><label>已部署的OneBot服务 <input aria-label="OneBot服务地址" type="url" value={endpoint} onChange={e=>setEndpoint(e.target.value)}/></label>
        <p className="v3-muted">默认使用宿主已部署的NanaLink连接器。多账号由宿主分配独立连接；公网服务需HTTPS。</p></details>}
      <h3>3 · 保存后完成账号授权</h3>
      <p className="v3-muted">登录使用对应客户端的二维码或平台官方流程。这里保存的入口保持暂停，不读取私人消息，也不授予发送权限。账号凭据使用已有Android安全输入。</p>
      <button className="v3-button" disabled={busy||!status} onClick={()=>void submit()}>{busy?'保存中…':'保存连接配置'}</button>
      </>}
      {message && <p role="status">{message}</p>}
    </div>}
  </section>;
}
