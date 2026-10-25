import type { Maturity } from "./contracts";
export interface ContractRegistration {
  id: string;
  title: string;
  maturity: Maturity;
  version: string;
  transport: string;
  source: string;
  description: string;
  executionAuthority: false;
}
export const contractRegistry: ContractRegistration[] = [
  {
    id: "demo",
    title: "Nana Space 产品演示",
    maturity: "DEMO",
    version: "nana-space/v1",
    transport: "Local fixtures",
    source: "src/data/demo.ts",
    description: "虚构生活故事与复杂状态，数据仅用于当前产品演示。",
    executionAuthority: false,
  },
  {
    id: "inspector",
    title: "Core Inspector 只读快照",
    maturity: "BACKEND_AVAILABLE",
    version: "schema_version: 1",
    transport: "Python / CLI → 用户选择 JSON",
    source: "src/nana_core/life/inspector.py",
    description:
      "现有有界元数据投影。可本地导入；LOCAL_METADATA 不等于接收者公开许可或实时连接。",
    executionAuthority: false,
  },
  {
    id: "frontend",
    title: "FrontendSession 投影",
    maturity: "BACKEND_AVAILABLE",
    version: "FrontendProjection / derived",
    transport: "Python in-process",
    source: "src/nana_core/continuity/application.py",
    description:
      "已有真实前端 facade；scope、entity、privacy 与 commands 由主机绑定。没有通用 HTTP 服务。",
    executionAuthority: false,
  },
  {
    id: "providers",
    title: "Provider / Models / Routing",
    maturity: "BACKEND_AVAILABLE",
    version: "schema_version: 1",
    transport: "Python projection / typed CAS",
    source: "docs/nana_provider_capability_routing_v1_frontend_contract.md",
    description:
      "设置投影与 expected_revision 已有。secret_state 可展示，凭据不进入浏览器。Nana Space 未连接修改命令。",
    executionAuthority: false,
  },
  {
    id: "perception",
    title: "Perception 设置与状态",
    maturity: "BACKEND_AVAILABLE",
    version: "schema_version: 1",
    transport: "Python projection / typed CAS",
    source: "docs/nana_h2_perception_ingress_v1_frontend_contract.md",
    description:
      "状态、来源修订与独立权限已有；启用不等于授权，REQUESTED 不等于采集完成。",
    executionAuthority: false,
  },
  {
    id: "screen",
    title: "受控屏幕扩展投影",
    maturity: "BACKEND_AVAILABLE",
    version: "B10 / H2 controlled screen",
    transport: "Host-bound metadata",
    source: "docs/nana_h2_live_real_screen_v1_frontend_contract.md",
    description:
      "资格仅为自建受控 OS 窗口；不代表用户桌面或 Android 屏幕已接入。",
    executionAuthority: false,
  },
  {
    id: "continuity",
    title: "多界面连续性",
    maturity: "BACKEND_AVAILABLE",
    version: "SurfaceEnvelope schema_version: 1",
    transport: "Python / source-filtered views",
    source: "src/nana_core/continuity/surfaces.py",
    description:
      "同一 subject_id 的 L0/L1/L2 有界派生投影，沿用原权威数据与来源生命周期。",
    executionAuthority: false,
  },
  {
    id: "runtime",
    title: "Runtime / Journal / Open Autonomy",
    maturity: "BACKEND_AVAILABLE",
    version: "Existing Python DTOs",
    transport: "Python in-process",
    source: "src/nana_core/presence/projections.py",
    description:
      "原 Runtime 的健康、目标、学习、技能与活动投影；没有额外 SubjectLoop。",
    executionAuthority: false,
  },
  {
    id: "gateway",
    title: "Nana Space 浏览器 Gateway",
    maturity: "PLANNED",
    version: "nana-space-gateway/v1 · proposed",
    transport: "Planned same-origin session HTTP",
    source: "src/data/gateway.ts",
    description:
      "仅版本与边界校验准备。默认禁用、不联网；身份认证、接收者授权与 Core owner 装配待接线。",
    executionAuthority: false,
  },
  {
    id: "streaming",
    title: "聊天流与异步事件",
    maturity: "PLANNED",
    version: "Not yet defined",
    transport: "Future authenticated streaming",
    source: "docs/CORE_INTEGRATION.md",
    description:
      "目前仅 DemoAdapter 本地分段显示。真实流式响应、订阅恢复和回执尚未接入。",
    executionAuthority: false,
  },
  {
    id: "avatar",
    title: "Live2D / Voice / Lip Sync",
    maturity: "PLANNED",
    version: "Avatar renderer extension",
    transport: "Future host-authorized renderer",
    source: "src/avatar",
    description:
      "可展示静态角色。没有 Live2D 模型或语音驱动，不由前端推测内在情绪。",
    executionAuthority: false,
  },
];
