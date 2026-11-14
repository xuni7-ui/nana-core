# NanaLink · 受控开发验收

[实测，2026-11-14 Asia/Shanghai] 基线87c32b3；最终业务源码8669d64。阶段/下一项仍以PROJECT_BRAIN/09_STATE C段为准。[机器可读口径](qualification.json)。

- [105项Python相关测试](python-tests.txt)，51.08s；含真实owned HTTP/WS/reverse-WS、原单主体QQ+Bili组合、重启去重/UNKNOWN不重发、C.4原owner接线与权限拒绝、真正RSS/Atom HTTP条件读取、原手机CAS/CSRF/回执。
- [93项原客户端测试](client-tests.txt)、[TS/Vite构建](client-build.txt)、[12项四视口浏览器场景](browser-tests.txt)、[390px截图](phone-390.png)。浏览器是合成HTTP fixture，不是真实Android账号登录/实机投递。
- [wheel双构建](wheel.json)：固定SOURCE_DATE_EPOCH、937655bytes、SHA81dd604d…211dbed，两次相同；真实无索引安装及[插件发现/工厂、包内C.4导入](installed-plugin-check.txt)通过。不是最终Core便携发行选择。
- [容器](container.json)：固定镜像a57ac3…344538，UID999、0 capabilities、NoNewPrivileges、只读rootfs、独立合成vault、network-none内loopback status通过。可重复[探针](container-smoke.py)只含fixture值，未挂Core DB/真实vault，未提权Core。
- [合成成本测量](benchmark.json)：2000入队+2000重复，约0.207s/CPU0.103ms每入队事件；Linux进程峰值RSS26700KiB；同8MiB两次传入只保留8MiB、范围取64KiB。模型/真实网络/外发0。这不是并发峰值、长期RSS或有效认知/实际Token节省证明。

复现命令见上级README；Python集合与CI `.github/workflows/nanalink-source.yml`一致。Ruff E9/F、规范schema重建、C.4原函数快照及git diff空白检查通过；未做昂贵全仓重跑。

原失败包括403错误包502、Feed结果字段、缺测试依赖、代理TLS CA、缺构建backend及首次错cwd未采集浏览器测试；均已定位修复，不把这些首次尝试写成通过。最终日志在本目录，完整临时调试留work/不纳入项目事实源。

明确开放：QQ官方Bot统一Core路径（原AstrBot/补丁保留）；完整控制台二维码会话/适配器包管理；原QQ文字之外的受控媒体发送；更广B站动态源。真实账号/实际对外发送/实机/生产/长期成本NOT_RUN，不能称NanaLink总工程完成。

## 最小契约增量说明（供A/B集成评估）

先建立了独立WS→原HTTP兼容侧车，不修改A的主体选择。原owner仅新增metadata `bilibili-notifications(channel_id)`；复用原worker/Store预算/原Bili工作流，channel/private-read/activation默认拒绝。Bili传输只增加两个已从锁定17.4.2 SDK核对的C.4只读路径。QQ入站metadata允许标准负消息ID，与既有get_msg/send回读一致。

BFF新增`platform/setup`只写暂停配置（原CAS/ledger），不授予读/发/Grant；host `nanalink_observers`及`nanalink_bilibili_sources`默认空且序列化省略。新配置给旧BFF回退时恢复原host配置；保留原Core所有UNKNOWN/预算/来源，不能通过回滚重派。Master/Matrix、SubjectLoop/认知/记忆/Manager/Grant的权威语义未改。
