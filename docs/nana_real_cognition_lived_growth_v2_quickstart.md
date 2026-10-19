# 独立生活 V2：本地开发体验

这是原 Nana Core 的持续运行入口，不需要 AstrBot、QQ、Iris 或 GUI。
默认没有真实模型；自然聊天和真人适切性尚未通过资格。不要把离线提示当作完整陪伴。

## 启动（仓库根目录，已有开发 venv）

```bash
.venv/bin/python -m nana_core.life init --home /tmp/my-life-v2 --project "$PWD" --demo-materials --document-work --allow-local-artifacts --allow-local-skills
.venv/bin/python -m nana_core.life run --home /tmp/my-life-v2 --seconds 3600
```

使用全新的 private home。初始化参数明确批准：四份特定仓库材料（两份 Python、两份
Markdown）、三份 Python/三份文档评估材料；只读这些文件。报告写到独立 home/reports。
`--allow-local-artifacts` 安装一次有限、一小时的原 Kernel Grant；`--allow-local-skills`
允许原隔离技能生命周期/精确资源上的 world.skill，不允许安装软件、改 Core 或外发。
两项都可以省略；未授权动作会被阻断，不能用重启/恢复重新授权。需要 bwrap 现有 OS
隔离环境；不可用则技能工作 fail closed，不准改为进程内 exec。

无需输入：主体原 D/C/F/G/I 会在有限材料中判断机会，处理工作、失败、学习、技能审核
和后来的新材料；完成后不强制继续学习或聊天。资源/时间受原控制，不是开放环境探索。
静默是正常结果。按 Ctrl-C 或 `/quit` 正常退出；同 home 启动可恢复身份/游标。
真实效果 UNKNOWN 时只核验，绝不盲重试。

## 看见她的生活和控制

- `/life`：身份、两类材料、当前来源、目标、经独立核验的方法、隔离技能、生活 Journal。
- `/status`：原 SelfState、Primary User（若已有合法绑定）、Manager、预算/健康。
- `/sources`：可删除的来源记忆 ID。`/forget <memory-id>` 使用原删除闭包。
- `/pause` / `/resume`：暂停/恢复后台；保留愿望和游标。暂停仍可交互。
- `/busy` / `/available`：显式本地可接待状态，不据联系频率推断感情。
- `/revoke`：撤掉本地执行 Grant；不会把愿望改成“不想做”，重启也不重新授予。
- `/topic <key> <text>`：话题内交流；明确“不研究”保持原 C 的边界语义。
- `/work <已配置文件名>`：提供已有批准材料给原 C，不强制采用。

普通句子直接输入。离线只支持有限明确语句和澄清，不能理解任意自然语言。
真实模型关闭时不会偷偷联网。至多六条临时轮次仅在内存；按话题/隐私/当前来源过滤，
删除来源后去掉相应轮次，退出丢弃。纠错先澄清，不靠一句话改写历史。
报告文件是用户拥有的产物，不是事实库；删除来源撤掉派生支持，不自动删除已导出副本。

## 模型配置：准备可操作，但本任务没有真实调用授权

Provider 是宿主配置，不是人格或身份。先查：

```bash
.venv/bin/python -m nana_core.life provider-status --home /tmp/my-life-v2
```

对照 `docs/nana_provider_capability_routing_v1_frontend_contract.md`，将**单个严格
ProviderCommand** 写入显式 JSON（不含密钥），然后：

```bash
.venv/bin/python -m nana_core.life provider-command --home /tmp/my-life-v2 --document /tmp/provider-command.json
```

按 revision 顺序 UPSERT_PROVIDER、UPSERT_MODEL、SET_CAPABILITY_ROUTE(COGNITION)。
每次只改变 host-local providers.json；CAS 冲突明确报错，不改变 Subject。模型/端点
必须由操作者明确选择和确认，例文中的域名仅占位，绝不执行联网发现。

新 home 的 init 可显式指定 `--provider-host`、`--remote-privacy`（PUBLIC/PROJECT/PERSONAL）
和 `--provider-cost-ceiling-micro`。这些是硬上限配置，**不代替本轮真实调用授权**。
当前路由 timeout 最高3000ms，每日最多24次、默认12次；措辞另算一次，UNKNOWN 停止后续
调用。成本单位是保守预留，不冒充供应商账单。未选定 provider/模型/隐私/显式 FD 凭据
引用/调用和费用上限前，不使用 `--live-provider-authorized`；不搜索旧 key 或环境变量。
经单独授权后，由宿主把内存凭据 FD 与 secret_ref 传入 run 的 `--secret-fd/--secret-ref`；
不在命令行参数、仓库、日志或聊天中传密钥正文。

## 30–60 分钟自由体验与匿名审阅

先完成真实 provider 资格后，才可称自然交流评审。现阶段可以自由看工作/暂停/恢复，
但应记录语言质量 NOT_RUN。真实评审可以自行换顺序和话题：闲聊/吐槽/求助/玩笑/分享、
询问一次真实工作、忙碌、明确拒绝深入、重新开放话题、纠正一条具体说法、退出再恢复。
不要求她每次提研究，不要求每次提报告，也不奖励发言次数。

匿名反馈只保留结构字段（由人填写，不由程序伪造）：

```json
{"case":"VENT","provider_qualified":false,"human_reviewed":false,"fit":"NOT_RUN","unwanted_task":null,"unsupported_claim":null,"boundary_respected":null,"interruption_cost":"UNKNOWN"}
```

不要保存原对话或个人背景；不以该 JSON 的存在宣称通过。真实自然度仍需要真人自由观察。

## 故障和可复现旅程

源 digest 改变/缺失会拒绝启动或暂停原工作，显示具体错误；核对批准清单，不要修改 DB
伪造成功。旧身份/history 留在 home；恢复已审核文件后同 home 继续。无自动目录漫游。
技能 UNKNOWN/拒绝不会自动扩大权限；报告部分落盘只核验，不重复写。并发启动由原租约拒绝。

```bash
.venv/bin/python -m tools.nana_lived_growth.qualify --repo "$PWD" --root /tmp/life-v2-qualification-fresh --output /tmp/life-v2-qualification.json --seconds 90
```

真实 wall-clock 旅程：零用户消息→真实任务失败/学习→技能测试后 SIGKILL→重启审核→新文档
技能调用→暂停/离线交互/恢复→静默驻留→退出。模型0次；不是虚拟时钟或真人自然度评审。
只用新临时开发目录；不触碰生产。无默认 Web 监听、设备读取、QQ 或任何外部发送。
