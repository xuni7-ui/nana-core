import {useState} from 'react';
import {V2Client,object,writeBase} from '../../data/v2';
import type {Envelope} from '../../data/v2.generated';

/** QR payload is temporary and local to this component; never browser storage. */
export function PlatformLogin({client,status,channel,onSaved}:{client:V2Client;status:Envelope;channel:string;onSaved:()=>Promise<void>}) {
  const [session,setSession]=useState(''),[qr,setQr]=useState(''),[state,setState]=useState('');
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const command=async(action:'BEGIN'|'POLL'|'COMMIT'|'CANCEL')=>{
    if(busy)return;
    setBusy(true);setMessage('');
    try {
      const data=object(status.data);
      const result=object((await client.platformLogin({...writeBase(status,crypto.randomUUID()),action,
        channel_id:channel,configuration_revision:data.configuration_revision,session_id:action==='BEGIN'?null:session,
        expected_vault_revision:data.vault_revision??null,consent:action==='BEGIN'||action==='COMMIT'})).data);
      setState(String(result.state||''));
      if(typeof result.session_id==='string')setSession(result.session_id);
      if(typeof result.qr_svg==='string')setQr(result.qr_svg);
      if(['CANCELLED','BOUND_IN_HOST_VAULT','BOUND_IN_HOST_MEMORY','EXPIRED','ACCOUNT_MISMATCH'].includes(String(result.state))) {
        setSession('');setQr('');
      }
      if(String(result.state).startsWith('BOUND_')) {setMessage('账号已安全保存，连接仍保持暂停；读取和发送权限继续单独管理。');await onSaved();}
    } catch {setMessage('登录结果暂未确认。请刷新状态；不会自动重新登录、保存或发送。');}
    finally {setBusy(false);}
  };
  return <section aria-label="B站扫码登录">
    {!session?<button className="v3-button soft" disabled={busy} onClick={()=>void command('BEGIN')}>扫码登录B站账号</button>:<>
      {qr&&<img alt="B站一次性登录二维码" width={240} height={240} style={{maxWidth:'100%',background:'white'}} src={'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(qr)}/>}
      <p>请使用B站客户端扫码并确认。手机可保存二维码后用B站的相册识别；二维码约3分钟有效。</p>
      <button className="v3-button soft" disabled={busy||state==='IDENTITY_VERIFIED'} onClick={()=>void command('POLL')}>已确认，检查登录状态</button>
      {state==='IDENTITY_VERIFIED'&&<button className="v3-button" disabled={busy} onClick={()=>void command('COMMIT')}>保存已核对的账号会话</button>}
      <button className="v3-button soft" disabled={busy} onClick={()=>void command('CANCEL')}>取消登录</button>
    </>}
    {state==='WAITING_SCAN'&&<p role="status">等待扫码确认</p>}
    {state==='WAITING_CONFIRMATION'&&<p role="status">已扫码，请在B站确认</p>}
    {state==='IDENTITY_VERIFIED'&&<p role="status">账号与配置相符，可安全保存</p>}
    {state==='EXPIRED'&&<p role="status">二维码已过期，请重新开始</p>}
    {message&&<p role="status">{message}</p>}
  </section>;
}
