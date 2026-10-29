import type { LivePage } from "../../data/v2";

/** UI destinations reuse finite v2 views; they never add native/API operations. */
export const destinations = {
  home: ["生活空间", "home"],
  chat: ["和奈奈聊聊", "chat"],
  memories: ["记忆与我们", "memories"],
  models: ["模型中心", "settings"],
  room: ["奈奈的小房间", "home"],
  journal: ["生活动态", "journal"],
  goals: ["小小计划", "goals"],
  world: ["世界探索", "world"],
  bilibili: ["B站与看世界", "world"],
  growth: ["成长足迹", "growth"],
  notifications: ["通知信箱", "journal"],
  devices: ["设备与连接", "devices"],
  backup: ["备份与连续性", "runtime"],
  runtime: ["运行与边界", "runtime"],
  settings: ["设置中心", "settings"],
} as const satisfies Record<string, readonly [string, LivePage]>;
export type Destination = keyof typeof destinations;
export const destinationKeys = Object.keys(destinations) as Destination[];
export function destination(value: string): Destination {
  return Object.hasOwn(destinations, value) ? (value as Destination) : "home";
}
export const sourcePage = (page: Destination): LivePage =>
  destinations[page][1];
