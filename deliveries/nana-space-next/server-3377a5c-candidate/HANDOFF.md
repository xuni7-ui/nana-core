# Nana Core 3377a5c 集成候选

Core、BFF、Web 与独立的 NanaLink 侧车对应固定源码 `3377a5c31fe745ff5867fe0cafe23a264d0045b3`。Core 两次构建一致，313 项文件、264 项原运行路径、19 个锁定依赖，SHA256 `3da5417cb80242bb49f0df0041ea0629edbfeb91a214d37d639ec3092fbb277e`。Web 使用固定 `fe9adb6` 的真实 TS/Vite 构建，237 个构建输入全部与候选 Git blob 一致，两次归档字节一致，SHA256 `84720d1029b00fd48fdd84b6198e8d0cf98654eb2b7906923b52d64beb0819c3`。

Core 离线安装后 46 项通过。在同一隔离 DEV 身份运行 Gateway/BFF、私创作、独立学习、虚拟72小时召回与撤回，停机切旧 `edca3d5` 再回本版的语义快照一致。CPython 3.12.14、SQLite 3.53.1。

侧车 wheel SHA256 `3de15462b83ea2b1e6773d577c0903071911812d1f60fb9b7461e3cc12a46036`。从同源 Python wheel 在分离的离线环境安装，核对 323 个源码文件，配置检查和 18 项本地传输测试通过。由既有 `deployment/nanalink` 部署流程单独启用。侧车配置示例适用于无账号检查。

### Core 离线安装与合成候选验证

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-3377a5c-portable.tar.gz --sha256 3da5417cb80242bb49f0df0041ea0629edbfeb91a214d37d639ec3092fbb277e --destination /tmp/n337bslot
/tmp/n337bslot/install.sh "$PYTHON312"
/tmp/n337bslot/.venv/bin/python -I -B installed_gateway_probe.py --bundle /tmp/n337bslot --work /tmp/n337bdev --output /tmp/n337b-gateway.json --check-memory-notes
/tmp/n337bslot/.venv/bin/python -I -B integrated_setup_probe.py --bundle /tmp/n337bslot --work /tmp/n337bdev --gateway /tmp/n337b-gateway.json --output /tmp/n337b-setup.json
/tmp/n337bslot/.venv/bin/python -I -B installed_note_recall_probe.py --bundle /tmp/n337bslot --work /tmp/n337bdev --continue-gateway-result /tmp/n337b-gateway.json --output /tmp/n337b-growth.json --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage
/tmp/n337bslot/.venv/bin/python -I -B installed_living_memory_probe.py --bundle /tmp/n337bslot --work /tmp/n337bdev --prior /tmp/n337b-growth.json --output /tmp/n337b-living.json
```

停机回退用已实测的固定旧槽 `2864240`。从 [固定 GitHub 交付](https://github.com/xuni7-ui/nana-core/tree/e3afb03019c62c3e3f2c5543946c5950cc1ae611/deliveries/nana-space-next/server-2864240-candidate) 取得旧包，使用该目录的 SHA256SUMS 与离线安装命令。对同一合成 DEV 分别在本版和旧版槽运行 `continuity-reader.py --bundle SLOT --work /tmp/n337bdev --gateway /tmp/n337b-gateway.json --setup /tmp/n337b-setup.json --output REPORT`。回退读取不执行待办，不替代真实宿主备份与升级授权。

### Web 静态文件

校验本目录 SHA256SUMS 后，可用 `mkdir -p /tmp/n337web && tar -xzf nana-web-3377a5c.tar.gz -C /tmp/n337web` 取得 `nana-space-web/`。正式接入复用原认证 BFF 与宿主 HTTPS 配置。

### 侧车独立检查

```sh
"$PYTHON312" -m venv /tmp/n337side
/tmp/n337side/bin/python -m pip install --no-index --find-links=/tmp/n337bslot/wheelhouse -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
/tmp/n337side/bin/python -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault /tmp/n337side/unused-adapter-vault --check
```

侧车、Core 和 Web 分别升级。Android 现有选择仍为 409，Core 选择仍为 266272a。生产、真实模型、平台账号、真机、自然度和实际跨日仍待验收。该候选由隔离开发验证，使用合成入口和本地回环。
