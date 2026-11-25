# 合入 NanaLink 手机连接器状态恢复

S7 与跨端交付。从原 A `81680f3c` 快进到固定交接 `2c0ed15a`。操作回执不明时用最新管理版本显式确认暂停；写入回执丢失后，连接器控制等待一次成功读取，刷新只走查询。未引入新 API、权限、依赖或原生路由。

本地复用锁定依赖，TypeScript/Vite 和 105 项单测通过。Playwright 默认下载域本次返回 403，改用现有系统 Chromium 151，在 390 px 视口跑通全部七项 NanaLink 场景。另核对交接源码的 GitHub CI 成功。 [固定 PR](https://github.com/xuni7-ui/nana-core/pull/36) [独立 CI](https://github.com/xuni7-ui/nana-core/actions/runs/45576079263)

浏览器使用原合成 API。真机、真实平台和生产待验。固定 `5ed149d` 制品早于此交接。
