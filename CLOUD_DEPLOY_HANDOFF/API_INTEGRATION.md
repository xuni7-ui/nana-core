# V3 / 原 Core v2 API 接线

完整ea1e225已作为真实Git父线合入；保留UI/主题/Keystore/appId/登录配对/CSRF/
撤销/会话恢复/UNKNOWN。没有重做CotEX界面或另建主体。Android仅versionCode301/
versionName3.0.1和有限原生操作映射升级，签名与原版本一致。

| 操作 | 原API | 当前接通与边界 |
|---|---|---|
| Provider/Model/Route/enable/disable | POST /api/nana-space/v2/providers/commands | HOST_ADMIN+显式host opt-in；原typed ProviderConfigurationRequest；gateway revision/owner/generation与独立config expected_revision均校验；VERIFIED才显示成功 |
| 配置读取 | GET views/settings | 原ProviderSettings；缺失配置明确configured=false/revision0，读取不创建文件；损坏fail closed |
| 回执 | GET receipts/<key> | UNKNOWN仅查询，不重新提交或换模型；冲突REJECTED保留草稿 |
| 备份 | GET backup/status | 当前调用者的原安全备份回执投影；未观察PC投递/恢复为NOT_OBSERVED，非异机DR |
| 原生有限映射 | providers.command / backup.status | 静态路径/方法，延续原Keystore签名与角色；无任意URL/任意HTTP旁路 |
| 媒体/语音/私人迁移 | 原既有边界 | 无真实授权/端点时明确待支持，不伪造模型测试或迁移完成 |

原operation枚举没有换成第二套taxonomy。供应商preset不等于协议资格；新增注册只
声明用户配置。OpenAI-compatible现有路径可写；未适配协议仅本地草稿。secret_ref
不在当前前端编辑器收集，Key从不入APK/JS/localStorage。写配置network_calls=0，
live_permission_granted=false，既不证明模型资格，也不授予付费或Privacy权限。

Schema由原tools/nana_first_life_android_v2/schema.py生成，增加原既有
ProviderConfigurationRequest与两路径；V2既有字段和端点保留。生成TS/OpenAPI见
contracts/nana-space-live-v2及apps/nana-space/src/data/v2.generated.ts。无Store/schema迁移。
Embedding变更继续原缓存/重建机制，UNKNOWN成本不因保存配置变成已知。

实际Web验证使用真实原Core/BFF，4种视口（desktop/360/390/412）4PASS；原V2
登录/撤销等浏览器3PASS；前端单元44PASS/TS构建通过，APK构建与原生1test通过。
页面测试使用开发自签证书ignoreHTTPSErrors，不能证明手机信任真实Tailnet HTTPS。
