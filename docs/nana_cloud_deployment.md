# Deployment preparation — NOT DEPLOYED

优先同宿主、同进程、单Core Store writer，串行bounded observer；不在4GB服务器长期启动第二完整自治Runtime。代码包readonly，shadow数据库新目录，与Iris SQLite/JSON/FAISS及生产账本分离。开发工程能力模块不在production hook实例化；默认reading ActionKernel也不在ShadowBridge实例化。

配置示例（不是已应用生产配置）：
```json
{"enabled":false,"mode":"SHADOW","external_execute":false,"production_budget_enabled":false,
 "package_path":"<reviewed-readonly-package>","shadow_db":"<approved-shadow-dir>/nana-shadow.db",
 "backup_path":"<approved-local-backup-dir>","iris_snapshot":"<operator-frozen-copy>",
 "export_mode":"hash-only","allowed_conversations":[["<platform>","<probe-conversation>"]],
 "max_events":1,"expires_at_us":"<operator-set-UTC-microseconds>","expected_identity_id":"<persisted-Core-id>"}
```
变量名可选：NANA_CLOUD_SHADOW_ENABLED、NANA_CLOUD_SHADOW_DB、NANA_CLOUD_PACKAGE_PATH、NANA_CLOUD_SNAPSHOT_PATH、NANA_CLOUD_SHADOW_EXPIRES_AT_US。**当前API由operator直接传参，无自动dotenv/secret加载**；这些变量是未来hook配置输入，不宣称已有完整配置loader。真实模型未来只使用既有NANA_S5_DEV_*绑定，不在这里写值或复用生产key。

Startup：metadata preflight→版本/包hash→只读snapshot→Store(identity check)→Bridge/session bounded allowlist→最后register observer。停机：先unregister→停止接收新事件→close Store。升级：unregister旧hook→保留DB与artifact→审核新包hash/schema→兼容测试→再注册；SQL v1没有自动migrate。Rollback：unregister+close，去掉包引用，纯legacy仍运行；不能把重建backup quarantine当可执行runtime。

Failure modes：Python/SQLite不兼容BLOCKED；锁冲突RUNTIME_ALREADY_ACTIVE；源snapshot WAL未合并BLOCKED；超限拒绝；时间UNKNOWN；重复source冲突拒绝不覆盖；同身份不一致拒绝；hook未知/热加载不可用则不启用、不重启服务；公网与模型不可用只限制真实语义，不让shadow取得动作权。实际部署、资源常驻开销、热加载API、真实Iris/live runtime版本皆未运行验收。
