import type { NanaAdapter, Scenario, SpaceSnapshot } from './contracts';
import { createDemoSnapshot } from './fixtures';
import { AdapterError, assertActive, delay } from './errors';

/** An isolated fixture renderer, not a SubjectLoop, memory engine or model. */
export class DemoAdapter implements NanaAdapter {
  readonly kind = 'demo' as const;
  async load(scenario: Scenario, signal?: AbortSignal): Promise<SpaceSnapshot> {
    await delay(scenario === 'slow' ? 2200 : 180, signal);
    if (scenario === 'error') throw new AdapterError('DEMO_LOAD_FAILED', '演示投影加载失败。可以重新加载或切换场景。');
    assertActive(signal);
    return createDemoSnapshot(scenario);
  }
  async send(text: string, scenario: Scenario, onChunk: (text: string) => void, signal?: AbortSignal): Promise<string> {
    assertActive(signal);
    if (!text.trim() || text.length > 8000) throw new AdapterError('MESSAGE_INVALID', '请输入 1–8000 个字符。');
    if (scenario === 'offline') throw new AdapterError('OFFLINE', '演示连接已断开，消息没有发送。');
    if (scenario === 'model-unavailable') throw new AdapterError('RESOURCE_UNAVAILABLE', '模型资源不可用，未产生回复。');
    await delay(scenario === 'slow' ? 900 : 220, signal);
    if (scenario === 'error') throw new AdapterError('SEND_FAILED', '演示发送失败，可以由你明确重试。');
    if (scenario === 'restart') throw new AdapterError('UNKNOWN', '演示连接在发送后中断，结果未知。请先核验，不要盲目重试。');
    const response = scenario === 'conflict'
      ? '演示回复：这次先保留两份来源的分歧。可以打开「世界与研究」查看更新时间、证据和仍未确认的部分。没有充分依据时，结论保持不确定。'
      : scenario === 'blocked'
        ? '演示回复：想看看窗外的云，但目前没有摄像头连接与授权。这个想法仍保留，当前不会发生采集。你可以在「愿望与计划」查看条件，也可以继续讨论其他办法。'
        : /星|夜空|天气/.test(text)
          ? '演示回复：可以接着看我们的观星小计划。星图已整理，云量还有两份不同的资料。先把不确定的地方放在桌面上，再一起挑一个舒服的夜晚。\n\n这是本地预设的演示文本，没有调用 Nana Core 或模型，也没有新增真实记忆。'
          : '演示回复：你的消息已进入当前页面的演示对话。可以继续聊小房间、观星，或打开共同记忆看看这段产品故事。\n\n当前回复来自本地预设文本；没有调用 Nana Core 或模型，没有写入主体记忆，也没有执行外部动作。';
    let accumulated = '';
    for (let index = 0; index < response.length; index += 5) {
      await delay(scenario === 'slow' ? 75 : 16, signal);
      accumulated = response.slice(0, index + 5);
      onChunk(accumulated);
    }
    return accumulated;
  }
}
export const demoAdapter = new DemoAdapter();
