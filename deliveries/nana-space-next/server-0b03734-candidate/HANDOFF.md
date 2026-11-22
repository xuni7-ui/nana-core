# Nana Core 0b03734 集成候选

Core/BFF 与独立 NanaLink / OneBot 侧车同源 `0b03734567ccb7c9313dd1eaa9d94f7a06ecbfd5`。Core 两次构建一致，SHA256 `aa61c967c930913d3ca775772fd3a544d33b8aacc931a95ad7b9400081a6f79d`，33 项离线安装定向验证通过。Web 逐件核对 73 项固定构建输入后沿用 c79297c 的 42 项静态文件，SHA256 `59ebf034b0da1b7c9160367459f931093b3c165fa0e60c1e0fa5cb1b27ae10be`。侧车 wheel SHA256 `812abc102185bd33ea723fc7f1a70bb38c8d678c25876392eeccaf18e9fcadc5`，在独立环境安装并运行 18 项回环测试。

运行原 Gateway、BFF、私人创作、独立学习、虚拟72小时召回以及笔记撤回后，在同一合成 DEV 中停机读取 `0b03734→c79297c→0b03734`，身份、谱系、私人状态、撤回状态与请求计数一致。核对 61 项 Android 构建输入相同后沿用 debug APK SHA256 `622b287e2a6638b7f54edab2dadd14c5005288bd07c490d6dbf7d2b94c1ebe11`，以隔离开发密钥通过签名校验。正式 Android 选择为 409，未用于覆盖正式应用或真机验证。

## Core 离线安装与验证

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-0b03734-portable.tar.gz --sha256 aa61c967c930913d3ca775772fd3a544d33b8aacc931a95ad7b9400081a6f79d --destination /tmp/n310bslot
/tmp/n310bslot/install.sh "$PYTHON312"
/tmp/n310bslot/.venv/bin/python -I -B installed_gateway_probe.py --bundle /tmp/n310bslot --work /tmp/n310bdev --output /tmp/n310b-gateway.json --check-memory-notes
/tmp/n310bslot/.venv/bin/python -I -B integrated_setup_probe.py --bundle /tmp/n310bslot --work /tmp/n310bdev --gateway /tmp/n310b-gateway.json --output /tmp/n310b-setup.json
/tmp/n310bslot/.venv/bin/python -I -B installed_note_recall_probe.py --bundle /tmp/n310bslot --work /tmp/n310bdev --continue-gateway-result /tmp/n310b-gateway.json --output /tmp/n310b-growth.json --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage
/tmp/n310bslot/.venv/bin/python -I -B installed_living_memory_probe.py --bundle /tmp/n310bslot --work /tmp/n310bdev --prior /tmp/n310b-growth.json --output /tmp/n310b-living.json
```

参考固定旧槽 `c79297c`。对同一合成 DEV 分别用两槽的 Python 运行 `continuity-reader.py --bundle SLOT --work /tmp/n310bdev --gateway /tmp/n310b-gateway.json --setup /tmp/n310b-setup.json --output REPORT`，在停机状态比较输出，时钟字段可以变化。

## 侧车离线安装与检查

```sh
"$PYTHON312" -m venv /tmp/n310bside
/tmp/n310bside/bin/python -m pip install --no-index --find-links=/tmp/n310bslot/wheelhouse -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
/tmp/n310bside/bin/python -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault /tmp/n310bside/unused-adapter-vault --check
```

候选使用合成 DEV 和本地回环。Core 正式选择为 266272a。生产、真实平台账号、真实 Provider、真机、自然交流和实际跨日仍待验收。
