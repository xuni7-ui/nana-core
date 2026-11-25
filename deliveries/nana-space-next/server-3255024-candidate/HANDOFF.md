# Nana Core 3255024 受控候选

固定源码 `325502482afd18f1e3137ea183d3927c2c02bce4`。包含原 Core/BFF、同源 Web 与 NanaLink 独立 wheel。Core 双构建与 Web 的两棵 dist 一致。原 Gateway、BFF、独立学习、笔记撤回和虚拟 72 小时已在隔离 DEV 运行，停机 `3255024→5ed149d→3255024` 保留原身份、谱系、私念及请求计数。FrameService 两项回归实际从离线安装代码执行。NanaLink 独立离线安装且本地回环 36 项通过。

## 离线安装与回退

使用带 SQLite 3.51.3+ 和 FTS5 的 CPython 3.12。在新槽安装当前候选，复用已校验的旧候选作为回退槽。 [固定旧候选](https://github.com/xuni7-ui/nana-core/tree/d09afd2298412d97989c1679f5b4d2925f41a4e3/deliveries/nana-space-next/server-5ed149d-candidate)

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-3255024-portable.tar.gz --sha256 bc6e56147df8557097ff9eb5573a15f3d019295f9c1aef42eb54d475562b20ea --destination /tmp/n328slot
/tmp/n328slot/install.sh "$PYTHON312"
bash rehearse.sh "$PWD" /tmp/n328slot /tmp/n328dev /tmp/n328report /tmp/n321slot
"$PYTHON312" -m venv /tmp/n328side
/tmp/n328side/bin/python -m pip install --no-index --find-links=/tmp/n328slot/wheelhouse -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
/tmp/n328side/bin/python -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault /tmp/n328side/unused-vault --check
```

本次 Web 行为已经变化，匹配 Android 包待构建。本候选不携带旧 APK 作为匹配包。正式选择 266272a/409。真实平台账号、受授权发送、真机、真实模型、实际跨日和生产仍待验收。
