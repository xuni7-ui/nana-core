# 正确的live构建输入与依赖元数据

基线8bec062/Brain253，A统一交付范围的真实兼容/复现修复，不抢B的产品研发。Runtime/Core业务源码本批不改，源API/冻结63标准/单主体与原C-D-G不变。

## 两个真实差额

重建草稿从旧70项生产输入清单复制时，漏掉已提交的.env.live。TS/Vite成功不代表入口正确，缺该公共开关会走演示入口；因此未发布该草稿。该文件只有VITE_NANA_DELIVERY=live，SHA58743d208a51ed698148af2d22d0cb6723e40d2212347687d48d2b0eef13cd66；不是密钥、不从本地私有dotenv取得。旧9a Web42文件与原B合并构建目录全SHA相同，其.env.live也与固定Git源一致，故不把本次复制错误误判为旧9a包源不匹配。旧70清单缺这一输入证明，本次补齐。

锁文件@types/deep-eql/parse-entities/through2的version误标4.0.3，原resolved URL、integrity对应包及实际安装均4.0.2。只纠正三条标签，不换包/地址/完整性摘要、不改应用版本4.0.3或任何依赖选择。离线新安装因旧cache缺包ENOTCACHED保留，随后标准registry新npm ci --ignore-scripts --no-audit --no-fund成功279包/6秒；逐包package.json版本与新锁文件279匹配。

新增原发行工具目录内web_inputs.py，只接受固定40位提交和新目录，从Git提交复制生产src/public/配置及契约，显式验证这一个已知非密钥live开关；不复制工作区dotenv、Store、缓存、node_modules、Android签名或历史配置。73输入=71前端（原70+公共配置）及2契约；不包含测试目录。编译与npm操作仍是明确的调用步骤，不造第二发行服务/治理权威。后继快照可用同一小工具，避免靠临时目录猜测输入。

## 实测

corrected-live-build.txt：干净279依赖下TS/Vite通过；final100.txt：13文件100单测/4.73s。最初复制生产输入后缺vitest.config、再缺tests/，两次未执行单测的失败分别保留；按原vitest配置补原测试输入/有限Java XML公开源后才运行100，不改测试配置或放宽断言，未运行Gradle/Java/手机。

live-input-and-output-proof.json：修正公共输入后新编译42个静态文件逐字节等于原9a合格Web；可以复用其既有受控浏览器资格，不冒称新跑168浏览器或新设备。旧cc8独立client100单测/168浏览器属于同前端代码原CI；本批新运行的只有上述100/编译。

Core草稿8bec两次302文件构建SHA d1d1de6a96bfb17073f57b90d37ef983757abe2fc88b0cb08081a093b06233df、n8b首槽离线安装已完成。draft-core-installed49：49passed12.22s，157实际Core模块全从安装槽，Pydantic/crypto/Pillow亦安装依赖，非仓库PYTHONPATH；包含原G晚资格后续交流、C新愿望/原BUSY投递门/重启、巩固D、H1时间与UNKNOWN、原平台连续性。draft-core-gateway：实际安装BFF/反馈幂等/十投影/纠错重启撤回/隔离备份通过，Python3.12.14/SQLite3.53.1，不冒称云端3.51.3。

stopped三回执：同一新合成DEV Store，原G17 ACTIVE lesson、原私人计划与当前SOCIAL_INTERACTION pending，在关闭owner后8bec→9a→8bec；身份/lineage/私计划record-revision-state-正文摘要/课题状态与counts完全相同，cycles2/requests0/actions0/jobs0/goals0。旧9a因已知16窗口缺陷不选该方法，回新版恢复true→false→true，这是功能回退而非数据丢失；未在旧版执行任何待办，不是266或生产兼容验收。

## 交付边界

这些8bec结果是封签前的真实受控草稿资格，未发布候选/选择CURRENT。版本标签修正与新工具提交后统一以新提交重新封签Core/Web，复用已验证的不变Core代码与42文件Web，补最终实际安装/下载/回退回执；不把草稿标最终安装，不重打APK或474MB旧V4。

没有新模型/数据表/运行时资源成本/外部付费/实际账号或用户设备。新npm缓存和构建在/tmp，旧cache/node_modules未删。回退只需本锚package-lock及删除新增工具（源码层面，不动任何Store）；所有运行已实现的C/G成果保留。CURRENT266+409不动，真实模型/自然度/手机/生产/跨日长期与全部原A–H仍未总完成。
