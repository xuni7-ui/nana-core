# Unified First-Life Release · 最终 V3 交接

此文件取代本目录先前 Core-only/de899/V2 Web 部署指引；其历史证据和镜像保留。
继续同一个任务及分支，不另建 Release。完整可执行交接位于仓库根
[CLOUD_DEPLOY_HANDOFF/README.md](../../CLOUD_DEPLOY_HANDOFF/README.md)，包含全部镜像
分片、Core、V3 Web、APK、新封条、原plan引用及独立安装工具，不要求宿主先有源码分支。

Core运行源码3665d39完整继承9217e3f/7a1bce9/a07e906与ea1e225完整前端。最终镜像
sha256:6581d9e0cb7e686511aa704f77546cae508fc2911792753ed3a9bd3bf3cdb18b；
Debian13/CPython3.12.14/SQLite3.51.3/OpenSSL3.5.7/UID999。镜像gzip SHA256
6974cec541039290d6ddf100be1834b6a51d3dec5299adc52331a33a1de80923，11片307509301bytes。

新版先进入 /srv/nana-core/slots/<source>/runtime，容器内仍是
/opt/nana-core/runtime；旧/srv/runtime与旧6565封条不替换。新完整封条8149项。
默认Compose无启用服务、verify/no-restart；不执行Genesis/激活。受控安装器已实际
完成独立提取、树核验、数字所有权/权限恢复及只读挂载后验证。

Host Operator 修复工具在同一最终镜像/提取runtime执行私有.venv Python；检查
实际_ssl/loader/RUNPATH、libssl/libcrypto与pydantic。宿主Python仅运行标准库适配器，
不加载不匹配的私有_ssl；不改宿主OpenSSL，不用LD_PRELOAD，不修改旧sealed SDK。
互斥模式只保留dry-run或verify-only之一。真实原checker/源码目前未提供，因此
原13/13为NOT_RUN；合成解析器及ABI实测不能替代该结果。见OPERATOR_ENTRY.md。

最终镜像实际通过隔离DEV安装/十页API/V3 Web/原C离线chat/自动重启/重建同ID/
备份/B8恢复/旧源fence/撤Grant。新Web真实Core配置回执、revision冲突、角色及
backup/status已验证；Android3.0.1实际构建/签名/原生单元通过，保持原appId。
来源、命令、失败历史和等级见evidence/final与FINAL_STATUS.md。没有真实模型、
实体手机/私有HTTPS、真实宿主部署或生产资格。First-Life NOT_READY、Beta NO。
