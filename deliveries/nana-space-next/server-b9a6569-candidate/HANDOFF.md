# Nana Core b9a6569 同源集成候选

固定源码 `b9a6569daf57ed84a323b5dbe84235ff5697b2c2`。Core/BFF 两次构建的 313 个文件一致，Web 两次打包摘要一致，APK 内 42 项 Web 静态资源逐字节匹配。NanaLink 侧车独立构建和安装，18 项回环测试通过。新候选包含 #28/#30/#31、原索引恢复和反思积压中的可归因反馈修复。

原 Gateway、BFF、记忆纠错撤回、私人创作、独立学习及虚拟 72 小时受控演练通过。同一合成 DEV 主体停机回退至 `0b03734` 后返回，身份、谱系、私人状态和请求计数一致。新槽额外验证原索引重建中断和进程被 SIGKILL，重开后保留原完整索引并可重试。真实模型调用为 0。

## 安装和回退演练

`PYTHON312` 使用 SQLite 3.51.3 或更新版本，并启用 FTS5 的 CPython 3.12。使用新的临时槽和隔离 DEV 工作目录。

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-b9a6569-portable.tar.gz --sha256 40daf7374f70f725cbbfd510c5b6346b2a4c1058d0beeae78e3862204bb5fee4 --destination /tmp/n316slot
/tmp/n316slot/install.sh "$PYTHON312"
```

从固定交付提交 `fa7c929e80463e6d2325262db8b8c7e5dae49b0f` 的 `server-0b03734-candidate` 获取并核对旧 Core，安装至另一临时槽 `/tmp/n316old`。运行下列命令时，原探针在停机后的相同 DEV 工作目录依次读取新槽、旧槽和新槽。

```sh
bash rehearse.sh "$PWD" /tmp/n316slot /tmp/n316dev /tmp/n316reports /tmp/n316old
"$PYTHON312" -m venv /tmp/n316side
/tmp/n316side/bin/python -m pip install --no-index --find-links=/tmp/n316slot/wheelhouse -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
/tmp/n316side/bin/python -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault /tmp/n316side/unused-adapter-vault --check
```

## Android 与正式选择

APK 为 `life.nana.space.dev`，版本码 409，min SDK 23，target SDK 35，v2 签名验证通过。本次独立调试证书与历史 c79297c 调试证书不同，该旧包无法被本包原地升级。正式选择仍为 Core 266272a 与 Android 409。真机、真实模型及账号、生产、自然度与实际跨日仍待验证。
