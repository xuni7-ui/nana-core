import {useState} from 'react';
import {V2Client,object,writeBase} from '../../data/v2';
import type {Envelope} from '../../data/v2.generated';

export function AdapterManagement({client,status,channel,readAuthorized,view,onSaved}:{client:V2Client;status:Envelope;channel:string;readAuthorized:boolean;view:Record<string,unknown>;onSaved:()=>Promise<void>}) {
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[version,setVersion]=useState('');
  const [submittedStatus,setSubmittedStatus]=useState<Envelope|null>(null);
  const statusNeedsRefresh=submittedStatus===status;
  const choices=Array.isArray(view.approved_versions)?view.approved_versions.filter((v):v is string=>typeof v==='string'):[];
  const installed=view.installed===true,enabled=view.enabled===true,uncertain=view.uncertain===true;
  const command=async(operation:string)=>{
    if(busy||statusNeedsRefresh)return;
    setBusy(true);setMessage('');setSubmittedStatus(status);
    try {
      const data=object(status.data);
      const result=object((await client.manageAdapter({...writeBase(status,crypto.randomUUID()),operation,
        channel_id:channel,configuration_revision:data.configuration_revision,management_revision:view.revision,
        version:operation==='INSTALL'||operation==='UPGRADE'?(version||String(view.current)):null})).data);
      setMessage(result.state==='VERIFIED'?'连接器设置已应用。':result.state==='UNKNOWN'?'上次操作回执待核对，以最新连接器状态为准。':'设置未应用，请检查版本或权限。');
    } catch {setMessage('未收到上次操作回执，以最新连接器状态为准。');}
    finally {
      try {await onSaved();}
      finally {setBusy(false);}
    }
  };
  return <details><summary>管理此连接器 · {String(view.current)}</summary>
    {statusNeedsRefresh?<p role="status">{busy?'正在核对连接器状态。':'连接器状态尚未读取，请刷新连接状态。'}</p>:<>
    <p>{installed?'已安装':'已移除'} · {enabled?'运行中':'已暂停'}{uncertain?' · 上次操作待核对':''}</p>
    {view.persistent!==true&&<p className="v3-muted">设置只在本次运行生效；重启后遵循宿主配置。</p>}
    {!uncertain&&choices.length>1&&<label>宿主批准的版本 <select aria-label="连接器版本" value={version||String(view.current)} onChange={e=>setVersion(e.target.value)}>
      {choices.map(v=><option key={v}>{v}</option>)}
    </select></label>}
    {uncertain?<>
      <button className="v3-button soft" disabled={busy} onClick={()=>void command('DISABLE')}>核对并保持暂停</button>
      <p className="v3-muted">确认暂停后，可按授权恢复连接或管理版本。</p>
    </>:installed?<>
      <button className="v3-button soft" disabled={busy||(!enabled&&!readAuthorized)} onClick={()=>void command(enabled?'DISABLE':'ENABLE')}>{enabled?'暂停连接器':'恢复已授权连接器'}</button>
      {!enabled&&choices.length>1&&<button className="v3-button soft" disabled={busy||!version||version===view.current} onClick={()=>void command('UPGRADE')}>使用所选版本</button>}
      {!enabled&&view.previous&&<button className="v3-button soft" disabled={busy} onClick={()=>void command('ROLLBACK')}>回退上一版本</button>}
      {!enabled&&<button className="v3-button soft" disabled={busy} onClick={()=>void command('UNINSTALL')}>移除此连接器</button>}
    </>:<button className="v3-button soft" disabled={busy} onClick={()=>void command('INSTALL')}>安装已批准的连接器</button>}
    <p className="v3-muted">只使用宿主已安装并批准的版本。升级前暂停并排空输入；恢复连接不会授予发送权限。</p>
    </>}
    {message&&<p role="status">{message}</p>}
  </details>;
}
