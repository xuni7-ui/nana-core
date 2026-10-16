# Letta / Letta Code — 按当前与archive分别审查

当前`letta-ai/letta @ 5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a`只保留入口文档，README明确历史API server在archive。
额外固定archive `56ba9c25552605eec89de8ed3dc6394b625c1993`，不把它当当前production实现。
当前Letta Code `1297870b0aa6662d6c70729d273f5073c1bcbdea`，TypeScript，Apache-2.0；包含local/server/backend接口和filesystem memory。

## Core/external/filesystem

archive [letta/schemas/memory.py](https://github.com/letta-ai/letta/blob/56ba9c25552605eec89de8ed3dc6394b625c1993/letta/schemas/memory.py#L68)：blocks属于in-context memory；git-enabled只渲染system/，其它blocks/files按需。ContextWindowOverview明确system/core/summary/messages/external metadata的token分类。
Code [src/agent/memory-filesystem.ts](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/src/agent/memory-filesystem.ts#L29) 有system目录、bounded tree与初始化。不能把“system路径”理解为不可篡改身份，也不能把目录layout当privacy policy。
当前backend/context具体编译由各backend提供，研究没有证明每个provider active streaming都能瞬间应用memory edit。

## memory edit与context recompilation

[src/agent/subagents/memory-worker.ts](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/src/agent/subagents/memory-worker.ts#L68)：worker运行私有worktree；cancel丢弃；成功merge后sync/recompile；冲突保留branch并报告，不猜覆盖。prompt refresh失败不伪装成memory write失败。
[src/agent/memory-operation.ts](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/src/agent/memory-operation.ts#L15) 跨进程checkout lease基于PID/start，仅持有者死亡才reap；**主agent own edits不走这把锁**，依靠prompt等待和Git冲突降级。这不是Nana单writer transaction/CAS的替代。
[src/agent/memory-conflict-repair.ts](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/src/agent/memory-conflict-repair.ts#L161) 根据冲突signature+token/PID/start防止同一失败状态每turn重复repair；进程确实死亡可重试未启动worker。借signature/ack阶段分离，不让模型自行merge权威记忆。

## Reflection / heartbeat / cron

[src/cli/helpers/post-turn-reflection.ts](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/src/cli/helpers/post-turn-reflection.ts#L22) 在transcript delta后检查off/compaction-event/step-count，满足才launch。background worker是work resource，不是独立人格判决者。
archive letta_agent `_decide_continuation` 的request_heartbeat用于工具步骤继续，不等于墙钟生活心跳；workflow heartbeat、resource health、Subject wake三者不可混用。
[src/cron/scheduler.ts](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/src/cron/scheduler.ts#L1) listener进程scheduler lease、60s scan、queue pump；是scheduled prompt机会，不保证每task一定应该做。不借cron命令→强制服从。

## Procedural / skills

当前`src/skills/builtin/`与skill tests有memory initialization/curation/creator等显式说明与脚本。技能内容只是procedure候选，工具权限/副作用需另审；不能把“skill已安装”当已验证可执行authority。
已读worker与prompt integration测试；后者明确API key gating，未运行。没有真实模型/endpoint调用。

## NANA_MEMORY_TEMPERATURE_MAP — DESIGN_ONLY

| 温度 | 例子 | 读取与失效规则 |
|---|---|---|
| HOT | canonical identity最小头、当前scope约束、当前task、必要承诺 | bounded mandatory；每次freshness/privacy/source验证 |
| WARM | current SelfFrame、有关关系facet、active项目、近期experience | source-linked projection；支持消失立刻失效 |
| COOL | relevant episodic/semantic/conflict bundles | 按需检索，多样性，保留完整矛盾包 |
| COLD | 不相关历史/合规原始证据/归档 | 用户与scope授权后取回；非默认进云 |

PROCEDURAL是**用途轴**，不是真正温度：活跃skill可WARM，不相关可COLD；它没有更高authority。PUBLIC/PERSONAL/SECRET仍是独立privacy轴。温度影响加载成本，不影响真假、保留权利或删除。
不新增Memory文件authority，不把整个关系profile永远塞到prompt。

VERDICT：BORROW_PATTERN。Nana已有ContextAssembler/manifest/CAS/delete closure；缺的是有评测的tier placement、可中断慢工作和检查UX。不要引入多agent记忆作者与第二Store。
