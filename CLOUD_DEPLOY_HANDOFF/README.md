# Nana Unified First-Life V3 · 云端部署交接

延续 First-Life Android V2/rev3 的唯一 Unified Release。Core 完整继承
9217e3f / 7a1bce9 / a07e906，已合入 ea1e225 的完整 V3 分支。
运行源码固定为 3665d39fe0aeff9831721d4bfd1bfba0b8386a2b；后续提交只提供
交接工具、测试及账本。每项文件摘要见 SHA256SUMS，镜像分片见 image/image.json。

## 实际资格

[实测] Debian13/linux-amd64、数字 UID/GID999、私有 CPython3.12.14、SQLite3.51.3、
OpenSSL3.5.7、pydantic2.13.4。最终镜像及其独立提取/逐项核验的 runtime 都完成
原前缀挂载检查。最终镜像完成 DEV 单主体启动、十页 API、V3 Web、原 C 离线
聊天、BFF SIGKILL 自动恢复、容器重建同身份 epoch2→3→4、备份/B8 恢复、旧源
fence、旧 Grant 撤销。配置 API/版本冲突/回执及 Web/native 固定操作有独立测试。

[未运行] 真实云端安装、原 Operator 的完整13项、实体手机/私有 HTTPS 配对、真实
Provider、真人自然度、正式 Genesis/激活。历史 Provider UNKNOWN 保留；不重试。
First-Life NOT_READY、Beta NO。bwrap/Code Skills 仍 BLOCKED，其余已授权能力不收回。
旧 SDK/6565 项封条保持不变；新版独立封条 runtime-tree.json 为8149项。

## 0 · 收件核验（在 Ubuntu 宿主执行，不在 AstrBot 容器）

收齐本目录全部文件及11个分片；不得只复制一份旧 Core zip。目录可位于任意非敏感
交接路径。先从最终交付报告/Git可信记录取得 SHA256SUMS 自身摘要，再执行：

```sh
cd CLOUD_DEPLOY_HANDOFF
python3 tools/check_delivery.py --handoff . --manifest-sha256 <交付报告中的SHA256SUMS摘要>
```

这是宿主标准库脚本，不导入宿主 ssl/sqlite3/pydantic。Docker 操作固定指向本机
unix:///var/run/docker.sock，忽略其他 Docker context。若当前是容器/rootfs 或无
正确宿主通道，停止该步骤；容器 root 不代表宿主 root。确认宿主 Docker29、
linux/amd64、/srv/nana-core 根为 root 所有且不可被组/其他写入。

## 1 · 载入最终镜像，不启动服务

```sh
nana_image_manifest_sha=$(python3 -c 'import json; print(json.load(open("release.json"))["image_manifest_sha256"])')
python3 tools/receive.py --image-dir image --manifest-sha256 "$nana_image_manifest_sha" --load
nana_image_id=$(python3 -c 'import json; print(json.load(open("release.json"))["image_id"])')
nana_source_pin=$(python3 -c 'import json; print(json.load(open("release.json"))["core_source"])')
```

receive 先核全部分片、gzip/tar摘要，再 docker load，最后核 image ID/架构/UID。
没有 build、pull、重编译、服务重启或身份初始化。新的镜像 ID 是 release.json 中
的6581d9e0…；0d842676…与de899852…是保留的历史版本，不再作为本次安装目标。

## 2 · 新版本槽位，消除空 runtime 遮挡

通过已授权的宿主 Operator/root 执行以下**准备**命令。非 root 会明确拒绝，不自行
扩大权限。/srv/nana-core/{runtime,data,logs,backups} 及旧封条均不覆盖。

```sh
python3 tools/stage.py --handoff "$PWD" --root /srv/nana-core
nana_runtime_slot="/srv/nana-core/slots/$nana_source_pin/runtime"
python3 tools/operator_check.py --image "$nana_image_id" --source "$nana_source_pin" \
  --runtime "$nana_runtime_slot" --mode abi
```

stage 从已加载镜像创建一个**不启动**的临时容器，导出完整 runtime，复用原原子
安装器逐项校验哈希/链接/模式/数字UID。新建 slots/<source>/runtime，根0555，
Core 私有 release999:999，保留绝对前缀 /opt/nana-core/runtime。不接受已有槽位；
失败保留该新槽位及错误，不能盲目覆盖或改用旧/空 runtime。没有创建 Subject。

compose.env 已指向这个新槽位。compose.yaml 默认没有启用的服务，command=verify、
restart=no；不会因普通 compose up 意外开始生活或重启循环。实际只读部署检查：

```sh
docker compose --env-file compose.env -f compose.yaml \
  --profile after-explicit-activation-approval run --rm --no-deps core verify
```

该检查运行最终部署入口；不发布端口、不打开身份。数据三卷必须已是数字999:999、
0700且持久化；不要依赖显示的账户名（宿主 UID999 可能显示为其他账户）。

## 3 · 原 Host Operator 的最小修复

宿主 Ubuntu 的 OpenSSL3.0.13 不能装载只复制过来的 Debian 私有 _ssl；不要执行
那个私有 Python 的宿主路径，不升级全局 libcrypto、不用 LD_PRELOAD。上面 abi
和下方原 checker 均通过新镜像中的私有 .venv Python 执行、使用容器匹配动态库。

保留真实 Operator 的授权/plan/home/approval 参数，仅替换 genesis.dryrun 调用：

```sh
python3 tools/operator_check.py --image "$nana_image_id" --source "$nana_source_pin" \
  --runtime "$nana_runtime_slot" --mode dry-run \
  --read-root <原checker及批准输入所在的明确窄目录> \
  --script <真实原checker绝对路径> --script-sha256 <经核准的原checkerSHA256> \
  -- <原plan/home/approval参数，逐项保留>
```

尖括号项必须来自真实宿主 Operator，当前交接包**不假定其脚本名称或命令**。
最多4个明确只读根，路径在容器中保持相同；文件必须原本就对选定数字用户可读，
不为测试复制私人库或放宽权限。adapter 去掉 --dry-run/--verify-only 后仅加入
--dry-run，拒绝执行模式；原 checker 的输出及退出码原样返回。适配器不是新的
13项检查器。已有宿主源码若确实采用同一字面 argv 列表，可先生成一次性评审补丁：

```sh
python3 tools/patch_operator_flags.py --help
```

该工具要求原源码摘要，只输出全新评审文件，不修改/执行原 Operator；仅删除同时
出现的 verify-only 标志，保持授权参数。未知源码形状明确拒绝，不能猜改。
原13/13仍需云端按原检查器实测；本地 ABI通过不替代它。此包没有正式执行 Genesis
的命令，不能把镜像 entrypoint 当成 genesis CLI。

## 4 · Host config / Android V3 接线准备

已有正式 Genesis 成功、身份/lineage及原生产激活凭证有效之后，才能准备真实
host config。不要用 DEV UUID、shadow会话或本地恢复测试的身份。若尚无现有
host.json，本工具停止，**不会发明binding或创建主体**。

```sh
python3 tools/propose_config.py --handoff "$PWD" \
  --config <明确现有私有host.json> --config-sha256 <原文件SHA256> \
  --output <全新私有提案文件> --enable-provider-settings
```

提案经镜像中的原 HostConfiguration DTO/Release 完整性核验，保留 home、identity、
lineage、roles、activation、origin、port 和 active slot alias，只更换固定源码/Python/
Web路径；文件0600，O_EXCL，不安装、不启动。原配置必须保留供回退。若已有运行时
曾切换 active_release，应先在原受控停机流程核对 Supervisor 状态与提案 alias，
不能编辑持久化状态绕过。配置开关只允许已具 HOST_ADMIN 的客户端管理配置，
不新增角色、不授予模型付费/数据发送权限、不接收任何 Provider Key。

V3 APK在 artifacts/nana-space-3.0.1-debug.apk，life.nana.space.dev，versionCode301，
沿用原调试签名/Keystore升级路径。Web为 artifacts/nana-space-v3-web.tar.gz，完整
匹配镜像内Web。手机继续使用原一次性配对、设备Keystore、绑定校验及撤销流程，
连接现有 tailnet 私有 HTTPS8443→宿主127.0.0.1:18765→容器18766；不改6199，不开
Funnel，不在此开发会话更改Serve。实际 hostname/证书/ACL由宿主原daemon核实。

模型中心已接 providers/commands；备份页已接 backup/status。UNKNOWN仅查询回执，
不重发；配置revision冲突保留草稿。供应商Key不进入APK/JS/localStorage。缺少安全
Resolver或live授权时明确未就绪，不以保存路由冒充模型资格。语音/媒体/私人迁移及
B1的PC投递/恢复未经实际观察时仍明确待接通/NOT_OBSERVED。

## 5 · 后续激活与回退（本轮不执行）

必须先核原 C-only一次性Genesis授权、plan双摘要、单一identity、旧writer fence、
首份B1真实加密异机备份/恢复及独立生产激活批准。reference/保持原plan与摘要，
不是新批准。C-only不授权切换QQ/Iris、付费或启用生产生活。

获批后才由宿主Operator受控停机/备份，保留原host config，安装经核准的新提案
为原data/host/host.json（999:999/0600），核旧owner已退出、计划合同/UNKNOWN与
fencing。使用同一Compose项目名，旧服务必须已停止，避免两个BFF/SubjectLoop。
activation.override.yaml只提供未来command=serve/restart=unless-stopped的具体差异；
该文件本身不是批准。本轮不要运行它。首次会话口令仅通过既有安全FD/pipe绑定，
此包没有口令、Provider Key或长期token。

失败时保留错误与UNKNOWN，不初始化、不重试旧消息、不更换身份。正式版本回退
同样先受控停机、备份/版本兼容检查，恢复原host config+原镜像+原runtime映射，
保持单owner。禁止活跃Precision计划热降级、盲目覆盖更新的Store/lineage或旧源复活。
没有单独批准，不运行 docker compose down/up、原writer切换或正式restore。
