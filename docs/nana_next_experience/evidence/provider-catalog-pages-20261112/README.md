# Codex B · 显式模型目录分页与正确协议草稿

[源码/实测，2026-11-12 Asia/Shanghai] 同一 `NEXT_EXPERIENCE_AND_TEN_DOMAIN_REFINEMENT`，B-P 模型配置 P1；DOMAIN S5-C03、S1-C04 / Platform axis 的 Advanced 产品接线，不修改 Foundation 标准。起点 `f7c30787ab8b72ce7e21f0ef21ef9e7b257ff223`；开发中正常快进继承 A 的 `f583f187152c452b9638ff2d6c96b91bd4fe68da`，A 的主体/内心生活源码与账本保留。

实际缺口：原后端报告 native `has_more`，Web 却将整个回执压成 `string[]`，没有不完整提示和下一页；选择目录模型也没有继承供应商协议，旧的 media 草稿可能错误沿用到 native 文字模型。原实现新增两项反例失败，见 `before-2fail.txt`。

实现：原 GET `providers/models` 接可选 `after_id`，仅 Anthropic 使用实际 `limit/after_id/last_id/has_more` 分页形状，每次点击一页。游标按上游顺序，不按 UI 排序；缺失/不前进游标及过大页拒绝。OpenAI-compatible 不臆造分页协议，截断或服务商 `has_more` 仅标记不完整。原 HOST_ADMIN、授权域名、profile revision、Vault、10 秒共享节流、无重定向、读后配置/响应授权复核继续生效。

客户端保留完成状态，绑定供应商 ID/revision，失败保留已读选项，去重合并；重复游标循环停止。每个供应商最多显示 1024 个模型、最多 16 页，达到边界仍诚实显示不完整并允许手填。目录仅在当前组件内存；选择模型按实际供应商协议建立新的文字草稿，不自动写 Provider、Key 或路由，也不推断视觉/流式/context 能力。SDK 与 Android 有限操作映射携带同一游标。

验证：

- `related51.txt`：目录、认证、长响应授权、原持久 Vault 相关 51 通过 / 46.85s。
- 最终目录新增 compatible 截断反例后 `catalog16.txt`：16 通过 / 9.53s；继承 A 后的目录与原 HTTP 集成 28 通过 / 29.25s，见 `after-fast-forward.txt`。
- `client37.txt`：目录状态、revision/循环/数量边界、Web/Native SDK、原命令与模型投影 37 通过 / 1.75s。Native 为 synthetic bridge 合约，不是 Android 编译或手机资格。
- `browser16.txt`：桌面/360/390/412，下一页、429 后保留选项、协议与用途重置、单一模型注册、截断手填、错误供应商拒绝等 16 通过 / 40.4s。浏览器使用明确 HTTP fixture；后端为真实本地认证 BFF/Core、上游 fixture，两者不冒充真实 provider 端到端。
- 最终 `npm run build:live`：TypeScript/Vite 通过，3.58s。首次浏览器精确 label 包含 option 文本而超时，改用原控件精确 accessible role/name 后通过；`browser-first.txt` 保留失败及中断。环境首次命令错写不存在测试路径、后续 Vault 收集缺 cryptography 的日志合入 `prerequisite-failures.txt`；安装原已登记依赖后通过，不削弱断言。

复现（使用项目现有依赖；不调用真实模型）：

```sh
python -m pytest -q tests/first_life_android_v2/test_provider_models.py tests/first_life_android_v2/test_http_integration.py
cd apps/nana-space
npm test -- --run tests/model-catalog.test.ts tests/v2-client.test.ts tests/native-continuation.test.ts tests/provider-commands.test.ts tests/provider-center.test.ts
npm run build:live
npx playwright test --config playwright.v3.config.ts --grep 'model catalog:|native catalog:|catalog completion:'
```

能力/代价：用户可继续选后续页模型，避免错误协议或虚假完整目录；每次显式翻页产生一个有界目录 GET，LLM 调用/Token 为 0，不新增依赖、持久化、Store、主体或调度器。未测 CPU/RSS、真实 provider、Java/手机、最终发行或生产；不把测试耗时当产品性能。原网页 native-only Key 输入与连接推理测试等向导缺口仍在队列。代码为本仓库原创修改，未复制第三方 SDK，许可现状不变。

回退：撤销本批接口/客户端/测试提交，无 schema、主体数据、凭据或 CURRENT 迁移。旧客户端可忽略新增响应字段；新客户端对旧后端无分页游标时保留手填。`source-sha256.json` 只覆盖本批 12 个源码/测试，不自指；SHA256 锚 `924f4ef2547df6976f7a395118feba2ac241e6c5cb94b74bf8b0fb2bbe1fcf43`。GitHub 集成/CI 以实际后续回执为准。

集成前续核：已正常合入 A `4635690e522f1fd317172368abb8bed8a5c53e4e` 的原内心兴趣成果，完整保留其两份账本，仅合并本批追加。精确分页 HTTP 后续检查 1 passed / 15 deselected，见 `after-a463.txt`；未重复未受影响完整发行。PR #14 已推送但合并被自动审批以缺少 B 合并授权拒绝，仍由 A 评估或等待用户明确授权，不绕过。

2026-11-12 18:00续办：正常合入A 071669b，最新两份A账本全文保留后接B后缀。原分页HTTP补验1通过/15deselected/3.12s（after-a071.txt）；12份业务/测试指纹不变，不重复51回归/发行。PR14仍待A评估，本轮未重试合并。R1研究PR15已按查询感知控制的否定结论关闭，B队列已更新。
