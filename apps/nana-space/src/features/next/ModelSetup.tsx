import { useState } from "react";
import { newProviderDraft, type ProviderDraft } from "../../data/provider-center";
const presets = [{name:"DeepSeek",url:"https://api.deepseek.com",model:"deepseek-chat"},{name:"OpenAI",url:"https://api.openai.com/v1",model:""},{name:"自定义 OpenAI-compatible",url:"",model:""}];
export function ModelSetup({disabled,onSetup}:{disabled:boolean;onSetup:(d:ProviderDraft,status:(s:string)=>void)=>Promise<void>}) {
 const [draft,setDraft]=useState<ProviderDraft>({...newProviderDraft(),displayName:presets[0].name,baseUrl:presets[0].url,modelId:presets[0].model});
 const [status,setStatus]=useState("");
 return <section className="next-setup v3-card"><span className="v3-eyebrow">MAKE IT YOURS</span><h2>把你喜欢的模型，带给奈奈</h2><p>选择服务商，填写模型名称。内部配置由向导完成，密钥通过手机安全输入框存到服务器。</p>
 <form onSubmit={e=>{e.preventDefault();void onSetup(draft,setStatus);}}><label>服务商<select disabled={disabled} onChange={e=>{const p=presets[Number(e.target.value)];setDraft({...newProviderDraft(),displayName:p.name,baseUrl:p.url,modelId:p.model});}}>{presets.map((p,i)=><option key={p.name} value={i}>{p.name}</option>)}</select></label>
 <label>API 地址<input required disabled={disabled} type="url" value={draft.baseUrl} onChange={e=>setDraft({...draft,baseUrl:e.target.value})}/></label>
 <label>模型名称<input required disabled={disabled} value={draft.modelId} placeholder="填写服务商提供的模型名称" onChange={e=>setDraft({...draft,modelId:e.target.value})}/></label>
 <button className="v3-button primary" disabled={disabled}>保存并设为对话模型</button></form><p role="status">{status}</p><small>不会自动调用付费模型。更多能力、备用模型和高级参数仍在下方。</small></section>;
}
