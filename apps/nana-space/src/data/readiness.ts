/** User-facing explanation of server observations; never synthesizes readiness. */
export function readinessLabel(code: unknown): string {
  const labels: Record<string, string> = {
    READY_LOCAL_GATES: "模型配置与额度检查已就绪，等待真实回复确认",
    PROVIDER_UNCONFIGURED: "还没有配置聊天模型",
    RUNTIME_PROVIDER_UNBOUND: "配置已保存，运行中的凭据或授权尚未绑定",
    SECRET_UNAVAILABLE: "模型凭据尚未安全绑定",
    CAPABILITY_ROUTE_UNAVAILABLE: "请为文本交流选择默认模型",
    PROFILE_DISABLED: "当前模型或供应商已暂停",
    PRIVACY_DENIED: "当前内容的隐私范围不允许发送给此模型",
    PROVIDER_HOURLY_BUDGET: "本小时调用额度已用完",
    PROVIDER_DAILY_BUDGET: "今日调用额度已用完",
    PROVIDER_PROFILE_DAILY_BUDGET: "此供应商今日额度已用完",
    PROVIDER_TOTAL_CALL_BUDGET: "本次授权的调用次数已用完",
    PROVIDER_TOTAL_RESERVED_COST_BUDGET: "本次授权的费用预留不足",
    UNRESOLVED_PROVIDER_CALL_NO_RETRY: "上一笔模型请求仍待核实，暂不重复调用",
    PRE_DISPATCH_UNAVAILABLE: "当前宿主尚未授权此供应商或不支持此协议",
    UNAVAILABLE_CORE_STOPPED: "连接入口在线，主体运行进程尚未就绪",
    LIVE_PROVIDER_NOT_AUTHORIZED_OR_BUDGETED: "真实模型调用尚未授权或缺少额度",
    PROVIDER_READINESS_UNAVAILABLE: "暂时无法核实模型状态，请检查连接",
    SECRET_INPUT_CANCELLED: "已取消，没有提交凭据",
    CONTINUATION_REPLY_BINDING_INVALID: "接续回执的来源尚未核实，未把草稿当成已发回复",
    PROVIDER_EMPTY_DRAFT: "这次模型没有返回可用的回复",
  };
  return typeof code === "string" && labels[code] ? labels[code] : "状态尚未核实";
}
