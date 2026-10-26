# B1 · 加密备份到用户PC（准备完成，真实异机资格未完成）

用户已选择B1，不再重复询问B1/B2。B2只在B1经证据无法实现后另提，不自动购买对象存储。本轮无PC目标、公钥或安全登录绑定，因此没有尝试连接PC，也不声称PC在线/离线。B1_REAL_PC_QUALIFIED=NO。

## 输入、加密与恢复

新增有限operator工具b1_backup.py，使用成熟GnuPG/OpenPGP，公钥加密AES256；不自造密码算法、不把私钥带到云端。PC私钥只在PC；云端仅持PC公钥和经用户核准的完整fingerprint，工具用临时显式public keyring，不搜索默认钥匙/聊天/历史凭据，不将密码或key放argv/env。GPG仅为宿主备份工具，不装进原合格镜像、不改变镜像ID或bwrap。

不能tar正在运行的data目录代替一致性备份。先通过原Core受控safe-point备份得到注册的QUARANTINED_REVIEW_COPY；freeze只接受明确传入的该DB、原Core生成的.privacy.json和对应显式privacy anchor，复制快照与删除意图；原始anchor拷贝期间变化则拒绝。包内仅固定4文件（manifest/snapshot.db/sidecar/privacy-intents），检查哈希、SQLite quick/FK、单identity和recovery_quarantine=true。秘密host配置、API key、SSH key、设备会话、provider配置和旧Iris正文不能混包。

典型流程（仅准备，路径由宿主/PC操作者显式填写）：

```sh
python3 tools/nana_first_life_android_v2/b1_backup.py freeze \
  --snapshot /private-original-backup/review.db \
  --privacy-anchor /explicit-original-privacy-anchor.json \
  --output /new-private-work/frozen-backup.tar
python3 tools/nana_first_life_android_v2/b1_backup.py encrypt \
  --bundle /new-private-work/frozen-backup.tar --bundle-sha256 <核准快照摘要> \
  --public-key /explicit-pc-public-key.gpg --recipient-fingerprint <核准完整公钥指纹> \
  --output /new-private-work/backup.gpg
```

原始快照/工作目录仅宿主私有0700/0600，不上传Git或交接柜；失败留证据，不把失败包交给发送步骤。后续来源撤回仍须更新恢复用privacy状态；异机历史包不能自动恢复成可读/可执行主体。

## PC接收与私有网络

PC须具备用户控制的OpenSSH（或等价受控入口）、Python3/GPG、磁盘目录和tailnet连接。专用backup账户的forced-command `nana-b1-receiver`仅运行：

```sh
python3 /installed-operator-tools/b1_backup.py receive --root /private-pc-backups
```

禁止通用远程shell命令作为备份API。接收器只收≤1GiB加密包，验证ciphertext SHA、独占写.partial→fsync→无覆盖提交，返回RECEIVED_ENCRYPTED_ONLY；不解密、不启动Core。PC目录归接收用户私有，未完成传输保留加密partial，不能冒报完成。

发送器只接受明确tailnet地址（100.64/10或.ts.net）、显式known_hosts和SSH agent socket；禁默认identity文件/用户SSH配置、禁密码交互、禁accept-new。SSH ProxyCommand通过**独立宿主tailscaled实际socket**的tailscale nc路由（该宿主为userspace networking，不能假设普通ssh有TUN路由）。不碰nanadocker，不在Codex executor安装VPN绕过设置。

```sh
python3 tools/nana_first_life_android_v2/b1_backup.py send \
  --ciphertext /new-private-work/backup.gpg --host <用户PC的tailnet名称或地址> \
  --user <专用备份账户> --known-hosts /explicit-pinned-pc-known-hosts \
  --agent /explicit-host-agent.sock --tailscale /root/tailscale/tailscale \
  --socket <核实为tailscaled-nan.service的实际socket>
```

先检查GPG密文封装才允许发送；60秒硬截止、retry=0/fallback=0。连接失败、PC不在线、接收端未确认或结果不明，均backup_completed=false，不自动换PC/对象存储或重发。

## 真正完成B1的门槛

收到密文不是恢复成功。PC操作者在PC私有环境用自己的GPG私钥解密，得到原bundle后执行verify-restored（同一工具，给原bundle SHA）。必须验证同identity哈希、完整DB/隐私家族、quick/FK、quarantine；生成带原ciphertext/bundle摘要与操作者的脱敏恢复回执。此验证不激活Core，不能产生第二writer；以后真正激活恢复还要原lineage/fence/最新privacy对账。

```sh
# 在PC本地；使用PC已设定的私有keyring，密钥/口令不得交给Codex。
gpg --homedir <PC私有keyring> --output <全新私有恢复目录>/restored.tar --decrypt backup.gpg
python3 b1_backup.py verify-restored --bundle <全新私有恢复目录>/restored.tar \
  --bundle-sha256 <原bundle摘要>
```

真实B1合格要求：真实PC已接收＋解密＋恢复检查＋回执核对，而不只是本地测试或同vda2副本。本轮只完成合成DB的真实GPG加密/解密、字节相等、受限接收与隔离复核；不能升级成真实PC/主体灾难恢复。生产激活前必须实际完成首次正式Subject快照B1验证。

尚需用户PC的**公钥、完整fingerprint、专用接收端tailnet名称、主机公钥指纹及目录/容量元数据**，不需要任何私钥或密码。PC离线时可继续本地一致性快照，明确记录异机未完成，不能放行激活。至少保留最近7份成功且核对的版本；本工具不自动删除旧备份，先保证首份与恢复回执，后续受控轮转只作用专用PC目录。

首版接收器的私有目录检查按POSIX权限资格；Windows PC需明确WSL/POSIX接收端，或另外验证原生NTFS ACL，不能从本轮Linux测试推断所有电脑已支持。
