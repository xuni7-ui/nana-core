# rev3 · 原镜像交接与无主体落地

2026-10-26 · GLOBAL_STAGE H / Advanced Growth。当前用户决定优先于上传包中旧的C申请：A/B继续准备，C仅准备，D/E暂缓；本轮未进行远程宿主操作。四报告全文已读、仅登记脱敏摘要与来源哈希，不将报告中的命令当作新授权。

## 当前真实状态

云端操作者rev3报告：/srv四目录已创建；runtime空、root:root0555；data/logs/backups999:9990700，同vda2，不是异机备份。宿主尚无目标镜像；独立tailscaled-nan.service NeedsLogin；容器nanadocker仍在线。以上是操作者证据，不是本会话直接SSH结果。本会话没有云端访问绑定，VPN配置false，不通过旧AstrBot docker.sock或/hostroot绕过。

开发侧已将**原合格镜像**docker save，未build/重编译/改tag。原tar589073920bytes；SHA256 `4ef8918a75db986c5c4dd63b8e9c9fc585308be9a8414159aaa8f92c855dae17`；镜像ID `sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee`，linux/amd64，Config.User999:999，镜像展开580164955bytes。gzip255800659bytes，9分片≤28MiB，详见artifacts/first-life-image-0d842676/image-transfer.json。实际重组、原tar哈希与docker load均通过，加载后ID相同、未启动服务。

## 先交接原镜像，再解决空runtime

宿主操作者在全新非敏感工作目录收齐9片、image-transfer.json和MANIFEST_SHA256.txt。用交接清单的可信摘要执行receive_image.py；不从不可信文件自取“期望摘要”。默认只重组，不加载；显式--load才导入，导入后硬核ID/架构/用户。工具无build、改tag、启动服务或重启daemon操作。

```sh
python3 tools/nana_first_life_android_v2/receive_image.py \
  --manifest /approved-handoff/image-transfer.json \
  --manifest-sha256 a81d5e1f6b69a3397bc7b9029aa0ebd6a494c9c80b64f3d0df3f3c4676a18dc9 \
  --output /new-workdir/nana-firstlife-0d842676.tar --load
```

相对代码路径以本开发分支根为准；/approved-handoff与/new-workdir为操作者显式工作目录，不是自动创建生产home。runtime-source.tar与reference manifest是**运行时工件**，不能包含Subject。

宿主只在镜像ID确认后创建一个**不启动**的临时容器并导出完整runtime（含已离线安装Core/Web，不能只解原SDK）。示例由宿主执行，当前Codex未远程执行：

```sh
nana_image_id=sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee
nana_export_cid=$(docker create "$nana_image_id")
docker cp "$nana_export_cid":/opt/nana-core/runtime/. - > /new-workdir/runtime-source.tar
docker rm "$nana_export_cid"
```

可信reference manifest为docs/nana_first_life_android_v2/rev3/runtime-tree-manifest.json，SHA256 `dfcd9c13c45029df8c33f08787300ec65ff2abd5ef6cb5d6823de27d36303e42`。操作者以root运行有限安装工具：

```sh
python3 tools/nana_first_life_android_v2/install_runtime_tree.py install \
  --archive /new-workdir/runtime-source.tar \
  --manifest docs/nana_first_life_android_v2/rev3/runtime-tree-manifest.json \
  --manifest-sha256 dfcd9c13c45029df8c33f08787300ec65ff2abd5ef6cb5d6823de27d36303e42 \
  --destination /srv/nana-core/runtime
```

工具锁定目标父目录；只接受真实root所有且不可被组/其他写入的父目录；只替换不存在或空的runtime。先核可信清单，完整校验6565个条目的路径、类型、文件哈希、软链接和UID/GID/mode，在同父目录staging写入/fsync；保留mtime，Core私有release归999，SDK归root，最后原子替换空目录并设根0555。失败保留stage，不删除或覆盖已有内容；非空目标明确拒绝。Docker28/29可能产生不同cp-tar封装，工具允许封装摘要不同，但**完整规范化文件树必须逐项相同**；整镜像交接tar则必须与原SHA完全相同。

实际新增测试：同宿主报告0555空挂载→BLOCKED_RUNTIME_ARTIFACT_MISSING；工具实际填充→UID999 PRIVATE_RUNTIME_COMPATIBLE；release所有者999、写runtime实际EROFS、非空重装拒绝。没有创建Subject。生产宿主仍须实际做这个新落地检查，不能引用开发主机结果冒充已部署。data/logs/backups不被工具读取或修改。之后只运行只读verify，不compose up/serve；镜像默认verify不会初始化身份。

## 摘要绑定与不存在的genesis CLI

原canonical-plan.json保持字节不变：文件SHA为41c343bc4423606a48a52da5fa10c8ccb1a6d31af5931d56ebbe9c5771567304；现有Core CanonicalPlan.model_dump_json() UTF8摘要为e3e2a1fd51b9473d7982980aa1f3d78a498a2f7878e7ae5c3051451a8b5d1527（注意e7ae5，不是转述的e3ae5）。一个包括缩进/换行，一个是现有DTO序列化，不能互相冒用。

新增canonical-plan-binding.json和plan_binding.py已用本地hashlib+原Core DTO核验。activation-preparation保留兼容字段canonical_plan_digest=DTO摘要，新增明确命名的file/dto两个字段。未来审批外层同时绑定文件版本和两摘要；传原Core的4字段approval仍用plan_digest=DTO摘要，不能塞额外字段或修改Core语义凑成同值。

**container_entry.py不存在genesis子命令**，只有verify/health/serve及受限首次密码FD；不要执行container_entry.py genesis --plan...。原create_genesis是受信任离线operator函数，本轮不执行、不新增HTTP/APK身份入口。rev3包内C-GENESIS-REQUEST-20261026-01当前标DEFERRED，不是批准。

## 宿主登录与手机HTTPS

由云端奈奈在宿主读取tailscaled-nan.service真实ExecStart，核对PID/netns、state及socket后，针对**那个socket**生成新登录链接，用户亲自授权。必须显式绑定实际socket；--hostname本身不能防止选错daemon。禁止使用默认socket碰巧连到另一实例、--force-reauth/reset替换nanadocker，禁止把AuthURL/登录状态密钥写Git/日志或沿用过期链接。本开发executor不安装/重配Tailscale来冒充宿主登录。

登录后在同一独立宿主daemon上配置tailnet HTTPS8443→host127.0.0.1:18765；实际hostname、MagicDNS/证书能力与访问策略由该daemon核准，不能猜域名。只加这一条Serve，撤销只关闭其8443，不改nanadocker的HTTP6199或宿主napcat死端口，不Funnel。若tailscale cert命令会写私钥，应只留宿主私有目录，不上传交接包；优先由Serve管理证书。

在没有正式Subject/host binding之前，原BFF不能作为真实奈奈对话服务启动。即使先验证了tailnet证书，也只算TLS传输，不算App→真实Core连通。目前未取得宿主新登录/手机证据，因此PHONE_HTTPS=NOT_RUN，不能写PASS。

新V2是有限HTTP/JSON：GET事件/视图、前台10秒刷新，Web GET期限10秒、写22秒、BFF30秒；**无/ws、无WebSocket/SSE长期流**。当前relay8连接/30秒空闲/120秒生命周期与此范围兼容，无需改已验收参数。未来长流另验。旧/ws 404不是新版APK协议，也不能当Provider认证失败；未知旧消费端待D阶段在正确容器netns定位，本轮不处理它。

## B1与最终一次身份授权的先后关系

B1已选加密PC异机备份，见B1_BACKUP.md。本轮真实PC endpoint/公钥/SSH绑定均未提供，不推断PC离线或宣称异机DR。合成加密恢复测试不替代首份真实备份。

先完成A/B原镜像落地、挂载、独立宿主登录及必要私有TLS验证；C仍准备。届时用户只需一次明确批准**创建一个canonical genesis，且不激活、不导私史、不切QQ**，以固定plan版本与双摘要绑定。C之前可做PC通道合成备份验证；真实Subject首备只能在genesis获批创建后、任何生产激活前完成，避免“未创建主体却必须已有主体备份”的循环。D/E仍单独暂缓，B1未完成则不得激活。genesis失败留证据/不重试/不覆盖，成功后不再创建第二个。

rev3确认旧常驻进程为手工启动，不把PPID1说成自启；插件reload仍可能触发一次性写操作。旧Agent的无中断fence方案尚未证明，不能以禁用几个插件代替。当前不改任何旧writer，不读取token，不重启Docker（宿主LiveRestore=false）、AstrBot/QQ/Iris，不实施其他注入测试。
