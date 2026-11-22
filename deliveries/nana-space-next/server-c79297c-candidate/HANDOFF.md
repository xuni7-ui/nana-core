# Nana Core c79297c 集成候选

Core/BFF、Web 与独立 NanaLink / OneBot 侧车同源 `c79297c414d4e4c0225d9abc068d53a4c99f61de`。Core 两次构建一致，SHA256 `f1749e9fd9ec81806017f2dbfb8de9c79801e403b0736ac76fbbe821bd1fe93a`，21 项离线安装定向验证通过。Web 从 73 项固定构建输入编译，42 项静态文件两次归档一致，SHA256 `59ebf034b0da1b7c9160367459f931093b3c165fa0e60c1e0fa5cb1b27ae10be`。侧车 wheel SHA256 `a15dfe50b959a1b8940db57273f6bfbb36e5fd68c4892c07485214997256d67f`，在独立环境安装并运行 18 项回环测试。

运行原 Gateway、BFF、私人创作、独立学习、虚拟72小时召回以及笔记撤回后，在同一合成 DEV 中停机读取 `c79297c→3377a5c→c79297c`，身份、谱系、私人状态、撤回状态与请求计数一致。同源 Android debug APK SHA256 `622b287e2a6638b7f54edab2dadd14c5005288bd07c490d6dbf7d2b94c1ebe11`，以隔离开发密钥通过签名校验。正式 Android 选择为 409，未用于覆盖正式应用或真机验证。

## Core 离线安装与验证

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-c79297c-portable.tar.gz --sha256 f1749e9fd9ec81806017f2dbfb8de9c79801e403b0736ac76fbbe821bd1fe93a --destination /tmp/n306bslot
/tmp/n306bslot/install.sh "$PYTHON312"
/tmp/n306bslot/.venv/bin/python -I -B installed_gateway_probe.py --bundle /tmp/n306bslot --work /tmp/n306bdev --output /tmp/n306b-gateway.json --check-memory-notes
/tmp/n306bslot/.venv/bin/python -I -B integrated_setup_probe.py --bundle /tmp/n306bslot --work /tmp/n306bdev --gateway /tmp/n306b-gateway.json --output /tmp/n306b-setup.json
/tmp/n306bslot/.venv/bin/python -I -B installed_note_recall_probe.py --bundle /tmp/n306bslot --work /tmp/n306bdev --continue-gateway-result /tmp/n306b-gateway.json --output /tmp/n306b-growth.json --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage
/tmp/n306bslot/.venv/bin/python -I -B installed_living_memory_probe.py --bundle /tmp/n306bslot --work /tmp/n306bdev --prior /tmp/n306b-growth.json --output /tmp/n306b-living.json
```

参考固定旧槽 `3377a5c`。对同一合成 DEV 分别用两槽的 Python 运行 `continuity-reader.py --bundle SLOT --work /tmp/n306bdev --gateway /tmp/n306b-gateway.json --setup /tmp/n306b-setup.json --output REPORT`，在停机状态比较输出，时钟字段可以变化。

## 侧车离线安装与检查

```sh
"$PYTHON312" -m venv /tmp/n306bside
/tmp/n306bside/bin/python -m pip install --no-index --find-links=/tmp/n306bslot/wheelhouse -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
/tmp/n306bside/bin/python -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault /tmp/n306bside/unused-adapter-vault --check
```

候选使用合成 DEV 和本地回环。Core 正式选择为 266272a。生产、真实平台账号、真实 Provider、真机、自然交流和实际跨日仍待验收。
