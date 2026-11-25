import { AdapterManagement } from "./AdapterManagement";
import { PlatformLogin } from "./PlatformLogin";
import { NanaLinkSetup } from "./NanaLinkSetup";
import { linkHealth, healthWords, capabilityWords, capabilityStatusWords } from "../../data/nanalink";
import { useEffect, useState } from "react";
import { V2Client, object, writeBase, isNative } from "../../data/v2";
import type { Envelope } from "../../data/v2.generated";
import { V3Card } from "./LifeViews";
import { platformChannels, type PlatformChannel } from "../../data/living";

/** Original owner status + finite host configuration. No credentials or claims
 * of successful delivery from a toggle; uncertain commands are not resent. */
export function PlatformPanel({client, canManage}: {client: V2Client; canManage: boolean}) {
  const [status, setStatus] = useState<Envelope | null>(null);
  const [message, setMessage] = useState("");
  const [statusReadFailed, setStatusReadFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    setBusy(true);
    try { setStatus(await client.platformStatus()); setStatusReadFailed(false); }
    catch { setStatusReadFailed(true); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    let live = true;
    client.platformStatus().then(value => { if (live) setStatus(value); })
      .catch(() => { if (live) setMessage("当前版本尚未提供平台连接状态，或主体暂未就绪。"); });
    return () => { live = false; };
  }, [client]);
  const data = status ? object(status.data) : {};
  const rows = platformChannels(data);
  const optionalObject=(value:unknown):Record<string,unknown> => value && typeof value==='object' && !Array.isArray(value) ? value as Record<string,unknown> : {};
  const sessionViews=optionalObject(data.nanalink).sessions;
  const managed=(channel:string)=>optionalObject((Array.isArray(sessionViews)?sessionViews:[]).map(optionalObject).find(v=>v.platform==='qq'&&v.channel_id===channel)?.management);
  const toggle = async (row: PlatformChannel) => {
    if (!status || busy || !canManage) return;
    setBusy(true); setMessage("");
    try {
      const reply = await client.configurePlatform({...writeBase(status, crypto.randomUUID()),
        platform: row.platform, channel_id: row.channel_id, enabled: !row.enabled,
        configuration_revision: data.configuration_revision});
      const result = object(reply.data);
      setMessage(result.state === "VERIFIED" ? "设置已保存。启用通道仍需原有授权和安全凭据；不会重发旧消息。"
        : result.state === "UNKNOWN" ? "设置回执尚不确定，请刷新核对；不要重复提交。"
        : "设置未生效，请检查管理权限或刷新版本后再操作。");
      setStatus(await client.platformStatus());
    } catch { setMessage("未确认设置结果，请先刷新核对；不会自动重试。"); }
    finally { setBusy(false); }
  };
  const credential = async (row: PlatformChannel, slot: "AUTH" | "COOKIE" | "CSRF", revoke = false) => {
    if (!status || busy || !canManage || !isNative()) return;
    setBusy(true); setMessage("");
    const body = {...writeBase(status, crypto.randomUUID()), platform: row.platform, channel_id: row.channel_id,
      slot, configuration_revision: data.configuration_revision, expected_vault_revision: data.vault_revision ?? null, action: "BIND"};
    try {
      if (revoke) await client.revokePlatformCredential(body);
      else await client.bindPlatformCredential(body, data.vault_persistent === true);
      setMessage(revoke ? "凭据已撤销，相关通道已停用。" : "凭据已安全绑定；重新启动已授权的服务后生效，不会自动发送消息。");
      setStatus(await client.platformStatus());
    } catch { setMessage("未确认凭据变更。请刷新核对；需要支持此功能的 Android 版本及管理权限。"); }
    finally { setBusy(false); }
  };
  return <V3Card title="NanaLink · 平台连接" eyebrow="ONE CORE · LIVE CHANNELS">
    <p className="v3-muted">每个入口都回到同一个主体。连接设置、读取许可与发送授权分别核验。</p>
    <NanaLinkSetup client={client} status={status} canManage={canManage} onSaved={refresh}/>
    <details><summary>平台能做什么</summary>
      <p>QQ：授权后可接收和发送文字；图片、表情的自主发送尚未接通。官方 Bot 回执不能单独证明送达。</p>
      <p>哔哩哔哩：可按授权接收评论和通知，观看支持的公开视频资料；动态来源和视频帧需宿主另行启用。</p>
      <p>是否参与或回应由主体决定，现实行动仍须相应授权；连接成功不会自动授予发送权限。</p>
    </details>
    {!rows.length && <p className="v3-muted">还没有平台连接。可以先保存账号与会话配置，再完成对应平台授权。</p>}
    {rows.map(row => <article className="v3-card" key={`${row.platform}.${row.channel_id}`}>
      <h3>{row.platform === "qq" ? "QQ" : "哔哩哔哩"} · {row.account_label || String(row.channel_id)}{row.conversation_kind ? " · " + (({private:"私聊",group:"群聊",dm:"私信",comment:"评论"} as Record<string,string>)[row.conversation_kind] || "") : ""}</h3>
      <p>{row.enabled ? "通道已启用" : "通道已暂停"} · {row.secret_state === "AVAILABLE" ? "凭据已绑定" : "等待宿主安全凭据"}</p>
      <p>{healthWords(linkHealth(data,row.platform,row.channel_id))}</p>
      {linkHealth(data,row.platform,row.channel_id)?.capabilities.length ? <details><summary>此连接支持的能力</summary><ul>
        {linkHealth(data,row.platform,row.channel_id)!.capabilities.map(c=><li key={c.name}>{capabilityWords(c.name)} · {capabilityStatusWords(c)}</li>)}
      </ul></details> : null}
      {!row.read_authorized && <p className="v3-muted">等待账号与读取范围授权。请在对应平台完成登录，并由宿主绑定授权；保存配置不会自动读取。</p>}
      <p className="v3-muted">{row.state === "SUCCEEDED" ? "最近一次投递已核实" : row.state === "UNKNOWN" ? "最近投递待核实，不会重发"
        : row.state === "PLATFORM_MESSAGE_PREEXISTED_NO_SEND" ? "平台已有相同内容，本次未发送"
        : row.state === "ORIGINAL_CONFIRMATION_NOT_AVAILABLE" ? "最近投递缺少有效确认，不会重发"
        : row.state === "NOT_OBSERVED" ? "尚无本次运行的投递记录" : "最近状态待核对"}</p>
      <button className="v3-button soft" disabled={busy || !canManage || row.read_authorized !== true}
        onClick={() => void toggle(row)}>{row.enabled ? "暂停入口" : "启用已授权入口"}</button>
      {canManage && row.platform==='qq' && status && typeof managed(row.channel_id).revision==='number' &&
        <AdapterManagement client={client} status={status} channel={row.channel_id} readAuthorized={row.read_authorized} view={managed(row.channel_id)} onSaved={refresh}/>}
      {canManage && row.platform==='bilibili' && !row.enabled && optionalObject(data.login).bilibili_qr===true && status &&
        <PlatformLogin client={client} status={status} channel={row.channel_id} onSaved={refresh}/>}
      {canManage && isNative() && <div className="v3-inline">
        {(row.platform === "qq" ? ["AUTH"] as const : ["COOKIE", "CSRF"] as const).map(slot => <span key={slot}>
          <button className="v3-button soft" disabled={busy} onClick={() => void credential(row, slot)}>
            安全绑定 {slot === "AUTH" ? "连接凭据" : slot === "COOKIE" ? "账号会话" : "请求校验值"}</button>
          <button className="v3-button soft" disabled={busy} onClick={() => void credential(row, slot, true)}>撤销</button>
        </span>)}
      </div>}
    </article>)}
    <button className="v3-button soft" disabled={busy} onClick={() => void refresh()}>刷新连接状态</button>
    {statusReadFailed && <p role="status" className="v3-muted">暂时读不到平台状态，请检查运行进程是否已启动。不会自动发送或重试消息。</p>}
    {message && <p role="status" className="v3-muted">{message}</p>}
    {!canManage && <p className="v3-muted">当前设备可查看状态；更改通道需要已授权的管理设备。</p>}
  </V3Card>;
}
