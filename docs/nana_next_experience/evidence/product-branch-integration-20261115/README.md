# A集成PR14：复用B产品成果，保留较新A契约

唯一主任务。A起点45b3e5718fae5f937b14623edc48c08966d37805/Brain239，B固定d409a55f27f0d0b388d2ea01bde041d31a48038a（PR14）。合并前实际比较前A3eeb与B13ahead59behind，先读B_QUEUE与integration/catalog-wait证据；影响/回退先记IMPACT_AND_ROLLBACK.md。B原分支及所有提交保留，正常双亲merge，不reset/rebase/force。当前用户新增全局兼容/视觉分工正式入task_inputs，A不重写B视觉算法或NanaLink平台工具。

采用：共享供应商预设/已知端点；真实协议继承；目录多批结果合并、去重、revision绑定，失败保留选择/草稿；真实剩余等待倒计时，过期只启用、不自动请求。每批仍原8页/256KiB/10秒/256ID，组件最多1024ID/16批；数据只在当前组件内存。Native读取增加remaining limit，避免一批溢出后跳过未展示ID；服务端忽略limit则只返回诚实部分且无伪cursor。

明确保留A后继：continued_after_id回显及旧Java桥拒绝假续页、CURSOR_INVALID/UNSUPPORTED原错误码、query/HostAdmin/CSRF/Vault/CAS/隐私、原等待时窗。SDK增加B的输入预校验，但不删A的输出核验。服务端路由保留A整文件，因为B同类after_id接线已被A较新实现覆盖；Java相对A已相同，不额外改写。模型ID/分页/绑定数据仍严格；B可选等待提示异常降为未知但保留已读模型，服务端节流仍生效，既不虚构倒计时也不自动重试。C/D/G/Memory/Store/63标准相对A起点无改动。

## 实际资格与首错

- catalog-first.txt：4fail27pass5.76s；3条旧URL期望尚未包含新的Native limit，1条B旧错误码与A现役契约冲突。保留原断言意图，改成更精确的remaining limit/query集合和原A(code,status)严格相等，不放宽边界/删除用例。catalog-second.txt31pass5.81s。
- backend-related.txt：79pass67.81s，实际本地认证BFF/目录/配置/鉴权/响应权限。不是真实Provider或账号。
- TS/Vite两次通过；web-tests-first.txt98pass1fail，为A原严格等待提示与B“可选未知仍保留已读”的不同产品语义。经上述明确取舍采纳B提示降级，原B测试断言不改；web-tests-second.txt99pass4.75s。
- browser-first.txt：28pass47.6s，原有与新增目录/预设场景，桌面1440及360/390/412四视口，无横溢。包括失败保留草稿/已选项、ProtocolNative/用途正确、8页批次后模型不丢、无自动重试、冷却实际剩余、旧桥不回显时仍拒绝。B新测试的有效回复补当前A实际提供的echo/provider/revision字段，并沿原A可访问按钮名选中同一控件；故意缺echo反例保持，不改其断言。

合并冲突初次辅助脚本使用贪婪marker行模式，可能吞多段文本，且误把git merge-file的多个冲突返回码当执行错误；提交前从Git三阶段重建，改成逐行界定并检查完整组件/原断言，未进入任何已提交或安装版本。无Core业务回退/未知WIP覆盖，首merge日志保留。

成本：无新依赖/持久化/推理阶段；只有用户显式目录GET，未付费。前后端均本地fixture；不是手机/真实模型/生产/自然度/长期验收。fee8候选及CURRENT266+409原样，不新APK、不以此merge冒充匹配安装。当前UI编译自准确跟踪的合并文件副本；复用同lock的node_modules，未复制账号资料。

## 候选结局与后续

PR14独有功能随本双亲提交进入A主线；重复的after_id/Java实现由A已有实现替代，B历史证据保留原范围。PR17仍draft30459c54564c3e246d92e1c8e97f2ec2df4b9409，下一读取其18行parse复用、独立回归与冷热/内存证据后作采用或停止的明确决定，不重复已证明无收益的图实验。PR18当前可见6645fd0b01e88018203471c013e2fb0cb50be37f、draft且近期更新，下一按其新来源/撤回/旧reader/最小Runtime清单审阅；不推断另一账号未提交工作，也不擅动真实QQ/B站。B两仓视觉研究及NanaLink平台接入各自负责，A对实际I/O契约做原S5/S2/S3/C/S8消费者接线。原A–H持续，保持一Subject/Store/Loop/Authority。

## 集成末次兼容修正

新增浏览器用例发现B候选把相同兼容协议下用户明确选择的VISION也重置COGNITION。旧A frontend（与45b提交逐文件相同的fee8已编译dist）同一用例1pass3.2s，B合并候选实际1行为失败，最终保留相同协议的明确用途；当前Native不支持视觉路径仍回COGNITION。final16四视口22.3s覆盖新用途保留/Native正确约束/翻页失败保留/旧桥拒假结果，最终TS/Vite通过。旧28视口为之前阶段，不与16重叠相加。首次两条命令因cwd/config路径错误未执行有效用例，first/old-main.txt单独保留，不当行为基线。

B的兼容端“显式还有模型但不能猜通用续页协议”也纳入：少于256条时has_more=true或未知完成标记仍为partial，无伪cursor；标准明确false/缺省保持。初始新增同输入2fail1pass，最终整组目录34pass7.33s，既有79相关为之前阶段、源权限/Native分支不变。目录类型重复定义收敛为兼容类型别名，原ProviderCatalogPage导出仍保留。

因此当前准确资格为：79相关认证BFF、末次34目录、99客户端单测、最终TS/Vite、先前28与末次受影响16浏览器分开报告。没有全仓、真实模型/手机或匹配新包主张。
