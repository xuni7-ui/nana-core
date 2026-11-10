# Portable platform guide follows the actual feature manifest

[固定Git产物只读观察，2026-11-11 Asia/Shanghai] CURRENT交付提交`5b4f589`选择的Core266，其实际归档`runtime.json`声明`HOST_VAULT`、`PUBLIC_VIDEO_FRAMES`及`glibc>=2.34`；同包QUICKSTART却统一写`glibc>=2.17`。现役构建器仍按HOST_VAULT与否生成2.34/2.17两个平台要求，包内说明未体现这一区别。这个不一致可能误导宿主选择，不证明现场已安装到不支持的机器或生产有故障。

本修复只将基础/可选feature要求分开，要求安装前读取已校验包内`runtime.json`的`supported_platform`、`features`，保留实际安装和preflight原检查。正式源码地图补一个包内说明入口。没有调整glibc最低门槛、依赖、Core、安装器或任何平台能力。

只从固定归档读取元数据和原说明，在新建metadata-only目录运行文档中的原命令，输出实际`glibc>=2.34`及两个feature；未解包执行Core、安装或创建Subject。详情见`metadata-check.json`。文档不改变旧交付归档或CURRENT；后续源码构建才会携带新说明。

本批受PR9已合并的打包路径规则覆盖；GitHub是否实际启动source qualification仍须读对应运行回执，不用静态命中冒充CI成功。治理PR检查、账本完整性及合并条件仍按原规则；不重跑与文档无关的本地Core测试。

回退仅撤销本批文档和追加记录，无数据、依赖、运行配置、生产或selector迁移。保留A的最新账本全文后追加；不与其FOCUS/UNKNOWN/主体验证工作重叠。
