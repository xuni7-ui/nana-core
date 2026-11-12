import { useState } from "react";
import { newProviderDraft, modelSetupPresets, type ProviderDraft } from "../../data/provider-center";
export type ModelSetupPhase="NEW"|"RESUME"|"VERIFY"|"SAVED"|"BINDING_UNKNOWN";
export function ModelSetup({disabled,canBindCredential=false,phase="NEW",savedDraft,onNew,onSetup}:{disabled:boolean;canBindCredential?:boolean;phase?:ModelSetupPhase;savedDraft?:ProviderDraft;onNew?:()=>void;onSetup:(d:ProviderDraft,status:(s:string)=>void)=>Promise<void>}) {
 const [draft,setDraft]=useState<ProviderDraft>(savedDraft || newProviderDraft("deepseek"));
 const [status,setStatus]=useState("");
 const locked=disabled || phase!=="NEW";
 return <section className="next-setup v3-card"><span className="v3-eyebrow">MAKE IT YOURS</span><h2>配置对话模型</h2><p>选择服务商，填写模型名称。{canBindCredential ? "接着在手机安全输入框绑定密钥，再设置默认模型。" : "先保存配置；凭据需在已授权手机上绑定，当前默认模型不会改变。"}</p>
 <form onSubmit={e=>{e.preventDefault();void onSetup(draft,setStatus);}}><label>服务商<select value={draft.preset} disabled={locked} onChange={e=>{setDraft(newProviderDraft(e.target.value));setStatus("");}}>{modelSetupPresets.map(p=><option key={p.id} value={p.id}>{p.id==="compatible"?"自定义 OpenAI-compatible":p.name}</option>)}</select></label>
 <label>API 地址<input required disabled={locked} type="url" value={draft.baseUrl} placeholder="填写当前服务地域的 HTTPS API 地址" onChange={e=>setDraft({...draft,baseUrl:e.target.value})}/></label>
 <label>模型名称<input required disabled={locked} value={draft.modelId} placeholder="填写服务商提供的模型名称" onChange={e=>setDraft({...draft,modelId:e.target.value})}/></label>
 <button className="v3-button primary" disabled={disabled || phase==="SAVED" || phase==="BINDING_UNKNOWN"}>{phase==="VERIFY"?"核验并继续配置":phase==="RESUME"?"继续配置":phase==="SAVED"?"模型配置已保存":phase==="BINDING_UNKNOWN"?"凭据结果待核验":canBindCredential?"连接并设为对话模型":"保存模型配置"}</button></form>{(phase==="SAVED" || phase==="RESUME") && onNew && <button className="v3-button" disabled={disabled} onClick={onNew}>新建另一组配置</button>}<p role="status">{status}</p><small>续配进度仅保留在当前连接，不保存到设备。不会自动调用付费模型。更多能力、备用模型和高级参数仍在下方。</small></section>;
}
