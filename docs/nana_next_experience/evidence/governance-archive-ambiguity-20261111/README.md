# Delivery archive ambiguity — Codex B governance

[实测，2026-11-11 Asia/Shanghai] 在独立完整 Git 副本上继承现役源码，复用原 `verify_delivery.py` 与 `test_delivery_consistency.py`。这是一项交付证据校验修复，归属 S7 / Governance axis；不修改固定 Foundation criteria、Core、客户端、权限或 selector。

## 问题与最小修复

原 ZIP `getinfo()` 与 tar `getmember()` 均默取最后一个同名条目。在合成归档中先放过期内容、后放匹配内容，重新计算 manifest/selector 摘要后，普通 manifest 与 CURRENT 两个入口仍返回组件一致。新增五个反例在原验证器上全部失败（未拒绝重复项），原十二项通过。

现验证器拒绝 APK `assets/public/` 下重复的文件条目，并要求每个被检查的 Core archive 恰有一份 `nana-first-life-portable-v1/runtime.json`。普通入口复用已有 `runtime_metadata()`，CURRENT 的原始 Core 与 server patch 都受同一检查。未尝试比较或删除 APK 额外桥接文件；固定409 APK合法保留 `cordova.js`、`cordova_plugins.js`。

现有治理 PR workflow 增加该验证器/测试的路径触发和原交付测试入口；pytest 版本直接读取已有 `requirements-core-dev.lock`，不新增运行依赖或另一套测试框架。CI 结果以实际 PR 回执为准，本地结果不代替 CI。

## 验证与限制

- 修复后原交付测试合计17项通过，含五个重算摘要的重复条目反例；便携导入标准库测试2项通过。
- 修改验证器后从固定交付提交 `5b4f589fec8ecf5deb4dc5fafd2f4193c96569b8` 提取 selector、两个 manifest 及其所列文件，只读运行原 `verify_current()`，仍通过，42个APK/Web文件相同，Core契约保留。结果见 `current-result.json`。
- 该结果只证明固定 Git 快照的组件一致性；未解包执行 Core、安装、启动服务、访问生产/私人数据/模型或更新 CURRENT。远端 Actions candidate 的下载403及其摘要对照仍独立开放。本修复不证明全部归档安全、APK签名、来源真实性或语义兼容。
- 集成时以 A 最新现役两份账本为底，只追加治理记录；完整保留其原文。不覆盖 A 的主体语义和交流行为工作。

回退：撤销本批独立治理提交中的验证器、定向测试及 workflow 改动；保留历史验证记录。不需要数据迁移、生产操作或 selector 回退。
