# Nana Core d3279077 受控联合候选

Core 和独立 NanaLink wheel 来自 `d3279077dfe90bbed926c310d5f04db3bf788868`。Web 与 Android 调试包沿用 `3255024` 的固定制品。Web 全部 74 项构建输入匹配当前源码，APK 内 42 项 Web 内容匹配。设备真机、真实账号、真实模型和生产资格待验。正式交付指针仍为 Core 266272a 和 Android 409。

## 离线安装

使用 CPython 3.12 和 SQLite 3.51.3 或更高版本，需支持 FTS5 和 JSON。下例使用全新的自有 DEV 安装目录。网关配置中的 Web 根目录应指向解压后的 `web/dist`。

```sh
set -eu
sha256sum --check SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
NANA_SLOTS=$(mktemp -d /tmp/nana-check.XXXXXX)
core=nana-core-d3279077-portable.tar.gz
fallback=nana-core-3255024-fallback.tar.gz
"$PYTHON312" nana-unpack.py "$core" --destination "$NANA_SLOTS/core" --sha256 "$(sha256sum "$core" | cut -d' ' -f1)"
"$PYTHON312" nana-unpack.py "$fallback" --destination "$NANA_SLOTS/fallback" --sha256 "$(sha256sum "$fallback" | cut -d' ' -f1)"
"$NANA_SLOTS/core/install.sh" "$PYTHON312"
"$NANA_SLOTS/fallback/install.sh" "$PYTHON312"
"$NANA_SLOTS/core/nana" preflight
"$NANA_SLOTS/fallback/nana" preflight
mkdir "$NANA_SLOTS/web"
tar -xzf nana-web-3255024.tar.gz -C "$NANA_SLOTS/web"
"$PYTHON312" -m venv "$NANA_SLOTS/sidecar"
"$NANA_SLOTS/sidecar/bin/python" -m pip install --no-index --find-links="$NANA_SLOTS/core/wheelhouse" -r nanalink/requirements-nanalink.lock nanalink/nana_core_offline-0.1.0-py3-none-any.whl
"$NANA_SLOTS/sidecar/bin/python" -m nana_core.nanalink --config nanalink/config.example.json --adapter-vault "$NANA_SLOTS/unused-vault" --check
```

## 停机回退核对

通过既有网关停机流程停止 DEV 主体；CLI 独立启动时可用下列命令。回退沿用同一已经存在的 DEV Home 和同一个身份绑定。依次用两个槽读取状态与主体投影。按既有 supervisor 合同切换实际启动版本。

```sh
DEV_HOME=/absolute/path/to/existing-owned-dev-home
"$NANA_SLOTS/core/nana" stop --home "$DEV_HOME"
"$NANA_SLOTS/fallback/nana" preflight --home "$DEV_HOME"
"$NANA_SLOTS/fallback/nana" inspect --home "$DEV_HOME"
"$NANA_SLOTS/core/nana" inspect --home "$DEV_HOME"
```

Android 调试应用标识为 `life.nana.space.dev`。其固定调试签名与此前某些调试制品不同，原地覆盖须以设备上安装证书吻合为准。正式 APK 保持既有签发路径。
