# b196f5d 同源联合候选（不是 CURRENT 或生产）

固定 Core/BFF 源码 `b196f5d44e032fe6f18dcc5db59760286170cdb7` / Brain277。312包文件、263Core源码，19依赖（含显式可选 NANALINK）。两次构建完全一致：Core SHA256 `6f7d309f03ab87c6c44b7acfd120ec8847a244bd79bddb072dfa4fa498a40bb9`。NANALINK只补可选运行依赖闭包，不启用账号/侧车/真实发送。Pillow/密码库依赖随功能分层，最小Core仍不必装这些可选项。

Web SHA256 `5963d5948fa51823541f4692f529efbbba4345b9ac075bef7af2abbd9de21243`，原B24固定3598ebb已完成TS/Vite及desktop/390浏览器；本源237 tracked app输入逐字节/全SHA一致，所以复用编译，只按本源epoch两次确定性归档，既有根nana-space-web。不是两次Vite新构建，没有新APK；既有409不能冒充本候选Android资格。

## 本候选实际证明的联合行为

首槽 ni277 实际离线19依赖/pip check，全部263运行文件与固定Git一致。一个显式DEV主体 d917be4a-892f-4424-85d5-148f846c2620 连续执行：

1. 原Gateway/Core/BFF：聊天、反馈幂等、十投影、笔记纠错/重启/撤回和隔离备份。
2. 原journey.setup全部原断言：真实读取owned合成文件→一个loopback解释→原世界冲突/纠正→原Concern→C自主EXPLORE，撤回后UNKNOWN且原请求回放不新增调用；原C形成私人创作、默认不公开；拒聊不禁止内在认知；Manager约束执行而不改原判断。只运行setup函数，不称30分钟residency。
3. 原G笔记方法：BASELINE未召回→独立EVALUATE/TRANSFER通过→重启后未见ALTAIR笔记进入后续实际RENDER；撤回训练来源后方法失效，下一轮不再使用该方法。INTERPRET/原C/流式RENDER仍在，实际前缀早于终止事件。这个阶段恰好6 fixture调用，原setup已有1；原账本保留，临时总额度7，finally恢复配置。不称已学会一般沟通、情感或任意检索。
4. 同主体原C巩固改变后续上下文，虚拟72h重启仍召回，原来源撤回清除影响；冷副本实际回读。不是实际跨日生活、主库物理驱逐/总磁盘回收或异机DR。
5. 同一私人创作记录、内容摘要指纹和表达边界经过以上步骤保持；学习源撤回不抹掉无关私人兴趣。停机 reader b196f5d→00d643b→b196f5d，三次语义视图相同：1身份、17原C周期、7请求、0动作/Goal，没有再调用模型或执行待办。仅这两个兼容reader的DEV资格，不证明任意旧版266或真实数据回退。

另在安装槽运行原S3短/长倾向49虚拟h消融、真实反馈→原D→下一选择、G已验方法→私人兴趣、跨平台记忆/持久化及本轮事实上下文反例，共28项32.20s；158业务模块均来自安装槽，外置pytest依赖和3原公开factory不是第二Core。它们各自的测试DEV不能冒称上述一个整合Subject；两类证据分别保留。源206相关136.07s属于0110b31，b196与其263Core逐文件不变，未称全仓重跑。

此前275联合setup真实失败（无关临时回执污染事实解释）、276联合G末次工具额度失败、276CI节点路径检查失败均保留在开发分支证据。没有放宽来源/隐私/Core预算或原结果断言。

## 下载、校验、离线安装与复现

先从可信渠道独立确认摘要，不能只信同一下载目录的SHA文件。目的槽及DEV work必须不存在。以下只创建明确隔离的合成DEV，不授权生产切换/正式genesis。

```sh
sha256sum -c SHA256SUMS
python3 nana-unpack.py nana-core-b196f5d-portable.tar.gz --sha256 6f7d309f03ab87c6c44b7acfd120ec8847a244bd79bddb072dfa4fa498a40bb9 --destination /tmp/nana-b196-local
/tmp/nana-b196-local/install.sh /absolute/path/to/qualified-python3.12
/tmp/nana-b196-local/.venv/bin/python -I -B installed_gateway_probe.py --bundle /tmp/nana-b196-local --work /tmp/nana-b196-dev --output /tmp/nana-b196-gateway.json --check-memory-notes
/tmp/nana-b196-local/.venv/bin/python -I -B integrated_setup_probe.py --bundle /tmp/nana-b196-local --work /tmp/nana-b196-dev --gateway /tmp/nana-b196-gateway.json --output /tmp/nana-b196-setup.json
/tmp/nana-b196-local/.venv/bin/python -I -B installed_note_recall_probe.py --bundle /tmp/nana-b196-local --work /tmp/nana-b196-dev --continue-gateway-result /tmp/nana-b196-gateway.json --output /tmp/nana-b196-growth.json --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage
/tmp/nana-b196-local/.venv/bin/python -I -B installed_living_memory_probe.py --bundle /tmp/nana-b196-local --work /tmp/nana-b196-dev --prior /tmp/nana-b196-growth.json --output /tmp/nana-b196-living.json
```

宿主Linux x86_64、glibc>=2.34、CPython3.12，实际绑定SQLite>=3.51.3、ssl/ctypes/JSON/FTS5/venv；本地是Python3.12.14/SQLite3.53.1，不冒称云端ABI。原bwrap不资格时技能/媒体隔离仍BLOCKED，不降级exec，不改系统库/LD_PRELOAD。pytest不是普通安装依赖。外部qualification目录仅固定原fixture，运行时Core来源均核对安装槽；不要加源码仓库PYTHONPATH。所有模型为有界本地fixture，usage不是实际账单或自然度。

## 升级与回退边界

真实宿主先按原合同停唯一writer、做原备份并核实reader合同；没有生产授权不得执行切换。安装新槽不覆盖旧槽，保存旧配置和Store。不得把init用作恢复，不补发UNKNOWN或pending动作。上面的DEV reader返回只核验00d643b与b196f5d；检查采用原LifeApplication、同原identity/lineage、原clock high-water，不调用step。

```sh
NANA_OLD_SLOT=/absolute/path/to/verified-compatible-00d643b-slot
NANA_NEW_SLOT=/absolute/path/to/b196f5d-slot
NANA_SHARED_HOME=/absolute/path/to/verified-compatible-owned-dev-home
"$NANA_OLD_SLOT/nana" stop --home "$NANA_SHARED_HOME"
"$NANA_NEW_SLOT/nana" inspect --home "$NANA_SHARED_HOME"
# 只有原正式配置、Provider和授权均满足才按原宿主合同start。
# 回退前先停止新writer，并验证旧reader/新来源契约。
"$NANA_NEW_SLOT/nana" stop --home "$NANA_SHARED_HOME"
"$NANA_OLD_SLOT/nana" inspect --home "$NANA_SHARED_HOME"
```

DEV临时Gateway配置没有正式Provider/应用绑定，正式preflight仍应START_BLOCKED；不能为通过而删门禁。独立远端下载/第二安装由后继事实账本给出实测回执，MANIFEST记录归档时状态，不预填成功。此包未全仓发行回归；真实模型、手机、QQ/B站账号、自然度、实际长期和生产均未新增资格。CURRENT仍266272a+409，S3长期因果、S8/S10、PR22正式适配、私QQ/私Bili、物理存储/完整Token和原A–H继续，不是总工程完成。
