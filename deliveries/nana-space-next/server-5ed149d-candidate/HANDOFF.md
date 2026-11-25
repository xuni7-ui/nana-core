# Nana Core 5ed149d 受控集成候选

固定源码 `5ed149d167a12cae9de37dbf63ba80cb798658b6`。Core/BFF 双构建、离线安装和原 G 后续反例安装测试通过。NanaLink 独立 wheel 同源构建并离线安装，30 项本地网络回环通过。74 项 Web 构建输入与 Android 原生构建树一致，沿用固定 b9a6569 的 Web/APK。 [客户端与旧回退槽](https://github.com/xuni7-ui/nana-core/tree/4eda4492aea5e6f9c13299f7bdf92d70370bbd31/deliveries/nana-space-next/server-b9a6569-candidate)

隔离 DEV 实际运行原 Gateway、BFF、笔记纠错撤回、独立学习和虚拟 72 小时。停止后依次读取 `5ed149d → b9a6569 → 5ed149d`，保持身份、谱系、私人状态与请求计数。真实 Provider 调用 0。

## 离线安装与回退

选择带 SQLite 3.51.3+ 和 FTS5 的 CPython 3.12。验证 b9a6569 的固定旧包摘要后另装至 `/tmp/n321fallback`。

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-5ed149d-portable.tar.gz --sha256 d56021102865407d7ee560e6cead6776f506d8dc0c1df2ce53e240a95665f75d --destination /tmp/n321slot
/tmp/n321slot/install.sh "$PYTHON312"
bash rehearse.sh "$PWD" /tmp/n321slot /tmp/n321dev /tmp/n321report /tmp/n321fallback
"$PYTHON312" -m venv /tmp/n321side
/tmp/n321side/bin/python -m pip install --no-index --find-links=/tmp/n321slot/wheelhouse -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
/tmp/n321side/bin/python -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault /tmp/n321side/unused-adapter-vault --check
```

正式选择仍为 Core 266272a 与 Android 409。沿用的调试包无法原地覆盖旧 c79297c 调试包。真实模型、账号、真机、实际跨日和生产依原计划验收。
