# 独立 Nana 开发体验（A7 / D8 / C9）

无需 AstrBot、QQ、Iris、设备或真实模型凭据。当前可完整体验离线工作与恢复；
真实自然语言质量尚未验收。新建的是开发 Subject，不导入生产奈奈或私人记忆。

## 最短启动

在仓库根目录，Python3.12+。已有开发环境直接使用下面命令。
全新环境先 `python3 -m venv .venv`，再 `.venv/bin/python -m pip install -e .`；
运行依赖仅现有 pydantic。测试依赖不是启动必需，不会安装 AstrBot。

```bash
.venv/bin/python -m nana_core.life init \
  --home /tmp/my-nana-life --project "$PWD" --demo-materials --allow-local-artifacts
.venv/bin/python -m nana_core.life run --home /tmp/my-nana-life
```

`init`只创建一次。重复启动只执行`run`，保持相同 home 和 identity_id。
默认前台运行最多一小时；Ctrl-C/SIGTERM 或 `/quit` 保存退出。
文件与 SQLite 都在私有 home，报告在 home/reports；输入仓库不被修改。
`--demo-materials`明确批准本仓库两份真实 Python 源码和三份独立训练材料，
不扫描目录。可用 `--source ... --practice ... --heldout ... --transfer ...`
替换为你明确批准的非隐私 Python 文件（每份<=6144字节、最多16份）。
源码不执行，只提取声明/行号并经独立编译器符号表核验。

不要输入也可观察：可用材料机会→原 C 自主考虑→F/Kernel 真实处理→不完整方法
失败→C 反思→G 独立验证/选定已有方法→完成报告→处理第二份未见材料。活动不是
模型一直生成 token，也不会自动发消息。初始无兴趣/关系历史的开发主体，只考虑
宿主批准的有限材料机会；不宣称已形成真实人格或开放式自主学习课程。

## 直接输入普通句子，或使用控制命令

* `今天只是吐槽一下。`：离线字面基线识别后由 C 决定回应候选，不另开研究。
* `/topic closed 别再研究这件事`：明确边界；同 topic 后续任务会受约束。
* `/status` / `/activities`：身份、当前活动、工作/学习结果和共享资源预算。
* `/sources`：批准材料、来源记忆 ID、有效/撤回状态。
* `/pause` / `/resume`：暂停/恢复后台机会和工作；保留游标，仍能交互/维护租约。
* `/work recurrence.py`：向 C 提供已批准材料机会，不强制采用、提权或重跑已完成任务。
* `/busy` / `/available`：明确声明短期可交流状态；不推断好感或社交需要。
* `/forget <memory-id>`：原 Memory 删除闭包撤回来源，后续不得复活或继续依赖。
* `/revoke`：撤销本地执行 Grant；resume/restart 都不会偷偷重授。
* `/quit`：退出。`/help`可随时查看上述命令。

后台候选仅显示为本地活动，不向任何社交平台投递。普通对话原文只在内存中使用；
持久化的是受隐私限制的归一化意义/明确边界元数据，不能恢复整段聊天。
导出的报告是你持有的副本，Core 忘记来源不会擅自删除你的文件；它们也不会成为
第二事实来源。受支持的源码定位会在来源删除后失效。

脚本模式在命令后加`--json`；无人输入持续演练用`run --headless --seconds 30`。
只读健康检查：`.venv/bin/python -m nana_core.life status --home /tmp/my-nana-life`。
不要让两个进程使用同一个 home；第二 writer 会被拒绝。不要把生产 Store 指向这里。

## 模型槽与真实语义边界

默认 `OFFLINE_LIMITED`，无外网/凭据读取、模型安装或付费请求。离线解释只是小型
字面规则；不理解的表达会澄清，不能把它当成真人自然语言质量通过。

原 ProviderRegistry / CapabilityRouter / RuntimeProviderFactory / JSON transport /
CognitionSession / ContextAssembler 直接复用。home/providers.json 是原 typed host-local
配置（非 Subject 记忆）；支持现有 primary/fallback、secret_ref、privacy/预算和 UNKNOWN
边界。文本 COGNITION 是本轮接入，Vision/ASR/TTS 等继续沿现有能力端口扩展，未启动。

真实调用需要**另行明确授权**。授权后由宿主通过原 ProviderConfigService 的 CAS 命令
配置 provider/model/COGNITION route，并显式设置 life.json 的 provider_hosts、remote_privacy、
正数 provider_cost_ceiling_micro/calls 和有限 timeout。没有这些条件不能读凭据或 dispatch。
CLI 支持显式 `--live-provider-authorized --secret-fd <宿主预先提供的FD> --secret-ref <引用>`；
只读这个显式 FD，绝不搜索环境变量/文件/历史，退出清理内存，不保存 key。
更完整的宿主也可直接提供 SecretResolver 和原 CapabilityRouter，无需更换主体。

模型只提出意义和措辞；当前 C 判断、Manager/Grant/Privacy 不由模型改变。
输出有相关 request/revision/epoch/source，低置信或无效结果降级；模型独自认为用户
拒绝时只影响当前周期，不能伪造明确长期边界。模型候选无法创建 goal/Grant/relationship。
回复阶段获得受过滤的真实报告事实和 C 已提交的判断；措辞仍是未验收草稿，不能把
JSON effect_status 当成任意自然语言绝对真实的证明。真实质量/自然度需单独检查。
超时 UNKNOWN 不自动 fallback、重试或继续调用渲染；重启也不重放私密原文。

## 资源与故障

单 Runtime owner，无本地大模型/持续视频。run 配置默认512MiB地址空间上限、最多4个
可用 CPU affinity（仍受宿主 cgroup quota 限制），有限队列/材料/调用字节成本预算。UTC活动时段限制新材料机会，已采用工作可继续；需要立即让后台让路用 /pause。
四核不是性能宣传；实测报告同时列宿主 quota 和实际 CPU/RSS。成本单位是保守预留，
不是 provider 实际账单。默认真实调用0。

缺 Grant/过期/撤销：查看状态，保持阻塞；不靠 `/resume` 重授。默认初始 Grant 有效1小时。
UNKNOWN：保留动作/请求历史等待原 Verify 或人工复核，不新建相同动作。输入摘要变化：
拒绝旧 manifest，显式更新批准材料后再考虑，不能无声改写旧任务。配置损坏/不匹配：
失败关闭，不重置成另一个主体。报告半写入：UNKNOWN，不盲重试。

独立进程可复现旅程（新临时目录，约35秒）：

```bash
.venv/bin/python -m tools.nana_independent_life.qualify \
  --repo "$PWD" --root /tmp/a7-qualification-fresh \
  --output /tmp/a7-qualification.json --seconds 30
```

它先在真实学习阶段 SIGKILL，再启动新进程；未提供任何用户输入时自动完成两份
真实源码工作/有限学习复用，随后交互、暂停/恢复、退出，检查身份/Grant/效果未重复。
所有交互示例匿名、provider 关闭。它不把离线会话升级为真实自然语言体验。
