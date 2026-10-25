export type Maturity =
  | "DEMO"
  | "PLANNED"
  | "BACKEND_AVAILABLE"
  | "CONNECTED"
  | "DISABLED"
  | "BLOCKED"
  | "ERROR"
  | "UNKNOWN";
export type Scenario =
  | "evening"
  | "offline"
  | "blocked"
  | "conflict"
  | "restart"
  | "quiet"
  | "partial"
  | "model-unavailable"
  | "slow"
  | "error";
export type Route =
  | "home"
  | "chat"
  | "memories"
  | "goals"
  | "journal"
  | "world"
  | "growth"
  | "devices"
  | "runtime"
  | "settings";
export interface Source {
  label: string;
  ref: string;
  confidence: number;
  privacy: "PUBLIC" | "PROJECT";
}
export interface Memory {
  id: string;
  title: string;
  summary: string;
  date: string;
  kind: "共同经历" | "发现" | "约定" | "成长";
  state: "ACTIVE" | "CORRECTED" | "WITHDRAWN";
  source: Source;
  correction?: string;
  tags: string[];
}
export interface Goal {
  id: string;
  title: string;
  description: string;
  origin: "NANA" | "USER" | "SHARED";
  state: "ACTIVE" | "PAUSED" | "BLOCKED" | "DECLINED" | "VERIFIED" | "UNKNOWN";
  progress: number;
  reason: string;
  next: string;
  dependencies: string[];
  steps: string[];
  evidence: string;
}
export interface Activity {
  id: string;
  time: string;
  title: string;
  summary: string;
  kind: "发现" | "学习" | "共同生活" | "恢复" | "休息" | "行动";
  state: string;
  source: Source;
}
export interface Research {
  id: string;
  title: string;
  summary: string;
  state: "EXPLORING" | "CONFLICT" | "SUPPORTED" | "UNKNOWN";
  tags: string[];
  sources: { title: string; detail: string; stance: string }[];
  conclusion: string;
}
export interface Skill {
  id: string;
  title: string;
  description: string;
  state: "QUALIFIED" | "LEARNING" | "FAILED" | "PAUSED" | "RETIRED" | "PLANNED";
  tests: string;
  reuse: string;
  scope: string;
}
export interface Device {
  id: string;
  title: string;
  kind:
    "phone" | "desktop" | "browser" | "platform" | "audio" | "avatar" | "game";
  state: Maturity;
  description: string;
  observe: string[];
  act: string[];
  lastSeen: string;
  limitation: string;
}
export interface MessageAttachment {
  name: string;
  type: string;
  size: number;
  url?: string;
}
export interface Message {
  id: string;
  role: "nana" | "user" | "system";
  text: string;
  time: string;
  status: "SENT" | "SENDING" | "FAILED" | "UNKNOWN";
  attachments?: MessageAttachment[];
  proactive?: boolean;
}
export interface SpaceSnapshot {
  contract: "nana-space/v1";
  mode: "demo";
  identityId: string;
  asOf: string;
  scenario: Scenario;
  presence: {
    state: string;
    label: string;
    focus: string;
    share: string;
    expression: string;
  };
  memories: Memory[];
  goals: Goal[];
  activities: Activity[];
  research: Research[];
  skills: Skill[];
  devices: Device[];
  messages: Message[];
  runtime: {
    status: string;
    epoch: number;
    queue: number;
    provider: string;
    recovery: string;
    lastVerified: string;
  };
  partial: string[];
}
export interface NanaAdapter {
  kind: "demo";
  load(scenario: Scenario, signal?: AbortSignal): Promise<SpaceSnapshot>;
  send(
    text: string,
    scenario: Scenario,
    onChunk: (text: string) => void,
    signal?: AbortSignal,
  ): Promise<string>;
}
export interface InspectorItem {
  category: string;
  reference: string;
  state: string;
  record_id: string | null;
  as_of_us: number | null;
  source_memory_ids: string[];
}
export interface InspectorSnapshot {
  schema_version: 1;
  derived: true;
  read_only: true;
  identity_id: string;
  as_of_us: number;
  coverage: "BOUNDED_METADATA_ONLY";
  governance_visibility: "LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE";
  sections: Record<string, InspectorItem[]>;
  resources: Record<string, number> | null;
  execution_authority: false;
}
export const scenarioLabels: Record<Scenario, string> = {
  evening: "月光下的日常",
  offline: "连接中断",
  blocked: "愿望与权限",
  conflict: "来源相互矛盾",
  restart: "运行时恢复",
  quiet: "安静的几天",
  partial: "部分投影缺失",
  "model-unavailable": "模型资源不可用",
  slow: "慢速网络",
  error: "加载错误",
};
