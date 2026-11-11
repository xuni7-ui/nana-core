import { useState } from "react";
import type { ProviderRuntimeBudgetRequest } from "../../data/v2.generated";

export type RuntimeBudgetInput = Omit<ProviderRuntimeBudgetRequest,
  "client_request_id" | "idempotency_key" | "expected_revision" | "run_generation" | "owner_epoch">;
const object = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
const positive = (value: unknown, fallback: number) =>
  typeof value === "number" && Number.isSafeInteger(value) && value > 0 ? value : fallback;

export function ProviderRuntimeSettings({data,disabled,onSave}:{data:unknown;disabled:boolean;onSave:(input:RuntimeBudgetInput)=>Promise<void>}) {
  const settings=object(data),limits=object(settings.limits);
  const profiles=Array.isArray(settings.profiles) && settings.profiles.length<=64
    ? settings.profiles.map(object).filter(p=>p.enabled===true && p.locality==="REMOTE" && p.protocol==="OPENAI_COMPATIBLE_CHAT"
      && typeof p.provider_profile_id==="string" && typeof p.profile_revision==="number" && typeof p.host==="string") : [];
  const [providerId,setProviderId]=useState(String(profiles[0]?.provider_profile_id || ""));
  const profile=profiles.find(p=>p.provider_profile_id===providerId);
  const [day,setDay]=useState(positive(limits.calls_per_day,12));
  const [hour,setHour]=useState(positive(limits.calls_per_hour,24));
  const [perProvider,setPerProvider]=useState(positive(limits.per_provider_calls_per_day,24));
  const [output,setOutput]=useState(positive(settings.output_tokens,1024));
  const [context,setContext]=useState(positive(settings.context_tokens,8192));
  const [reserve,setReserve]=useState(positive(limits.per_call_reserved_cost_micro,positive(profile?.per_call_reserved_cost_micro,1000)));
  const [consent,setConsent]=useState(false);
  const ready=settings.can_configure===true && typeof settings.configuration_revision==="number" && Boolean(profile);
  const privacy=Array.isArray(settings.remote_privacy) ? [...new Set([...settings.remote_privacy,"PUBLIC","PROJECT"])] : ["PUBLIC","PROJECT"];
  const privacyLabels:Record<string,string>={PUBLIC:"公开",PROJECT:"项目",PERSONAL:"已有私人授权"};
  return <section className="v3-card" aria-label="模型运行预算">
    <span className="v3-eyebrow">READY WHEN YOU CHOOSE</span><h2>运行预算与服务商连接</h2>
    <p>为已保存的服务商开放连接，并设置所有已授权模型共用的调用预算。保存后需明确重启应用；这一步不会调用模型。一次对话可能包含多次模型请求，按请求分别计入预算。</p>
    <p className="v3-muted">连接后按现有路由权限使用内容：{privacy.map(p=>privacyLabels[String(p)] || String(p)).join("、")}。已有总量限制继续生效，实际费用以服务商账单为准。</p>
    {!ready && <p role="status">等待已启用的供应商与宿主运行设置授权。</p>}
    <form onSubmit={event=>{
      event.preventDefault();if(disabled || !ready || !consent || !profile)return;
      void onSave({provider_profile_id:providerId,profile_revision:Number(profile.profile_revision),
        configuration_revision:Number(settings.configuration_revision),calls_per_day:day,calls_per_hour:hour,
        per_provider_calls_per_day:perProvider,output_tokens:output,context_tokens:context,
        per_call_reserved_cost_micro:reserve,consent:true}).catch(()=>{});
    }}>
      <div className="v3-form-grid">
        <label>连接服务商<select aria-label="连接服务商" disabled={disabled || !ready} value={providerId} onChange={event=>{
          setProviderId(event.target.value);setConsent(false);
          const selected=profiles.find(p=>p.provider_profile_id===event.target.value);
          setReserve(positive(limits.per_call_reserved_cost_micro,positive(selected?.per_call_reserved_cost_micro,1000)));
        }}>{profiles.map(p=><option key={String(p.provider_profile_id)} value={String(p.provider_profile_id)}>{String(p.display_name)} · {String(p.host)}</option>)}</select></label>
        <label>每日请求上限<input required type="number" min={1} max={128} disabled={disabled} value={day} onChange={e=>setDay(Number(e.target.value))}/></label>
        <label>每小时请求上限<input required type="number" min={1} max={128} disabled={disabled} value={hour} onChange={e=>setHour(Number(e.target.value))}/></label>
        <label>每个服务商每日上限<input required type="number" min={1} max={128} disabled={disabled} value={perProvider} onChange={e=>setPerProvider(Number(e.target.value))}/></label>
        <label>每次输出 Token 上限<input required type="number" min={64} max={4096} disabled={disabled} value={output} onChange={e=>setOutput(Number(e.target.value))}/></label>
        <label>上下文 Token 上限<input required type="number" min={1024} max={65536} disabled={disabled} value={context} onChange={e=>setContext(Number(e.target.value))}/></label>
      </div>
      <details className="v3-technical"><summary>高级资源预留</summary><label>单次预留上限（内部单位）<input required type="number" min={1} max={100000} disabled={disabled} value={reserve} onChange={e=>setReserve(Number(e.target.value))}/></label><p>用于服务器资源预算核算，实际账单由服务商提供。</p></details>
      <label className="v3-check"><input type="checkbox" checked={consent} disabled={disabled || !ready} onChange={e=>setConsent(e.target.checked)}/>我允许向 {String(profile?.host || "所选服务商")} 及其他已授权模型发起计费请求，接受服务商实际计费。</label>
      <button className="v3-button primary" type="submit" disabled={disabled || !ready || !consent}>保存运行预算</button>
    </form>
  </section>;
}
