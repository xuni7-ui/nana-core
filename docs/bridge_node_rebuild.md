# Codex Bridge Node/npm 重建说明（D 线）

> 【实测】2026-10-10。目标：让 Bridge 的 Node 侧可在隔离环境重建。

## 1. 版本锁定【实测】
| 组件 | 版本 |
|---|---|
| Node.js | `v24.20.0` |
| npm | `11.19.0` |
| `@openai/codex`（CLI） | `0.162.0` |
| `@openai/codex-linux-x64` | `0.162.0`（平台二进制包） |

## 2. 安装位置与方式【实测】
- 本地安装于 `/opt/nana_codex/node_modules/`（**不在 git 内** → 容器重建需重做）。
- 可执行入口：`/opt/nana_codex/node_modules/.bin/codex`。
- 平台二进制：`@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex`。

## 3. 重建步骤
```bash
mkdir -p /opt/nana_codex && cd /opt/nana_codex
npm init -y
npm install @openai/codex@0.162.0
# 校验
/opt/nana_codex/node_modules/.bin/codex --version   # 期望 0.162.0
```

## 4. Bridge 侧约定（`bridge/codex_bridge.py`）【源码确认】
- 通过 `CODEX_HOME` 与运行期注入的 Provider 配置调用 `codex exec`。
- 降权外部沙箱：`setpriv -> nobody`。
- 关键坑（已修）：`codex 0.162` 在 **stdin 非 TTY** 时会读到 EOF 才继续 → 桥**必须关闭 stdin**，否则 300s 假超时。
- `--strict-config --json -C <dir>`；密钥仅运行期读入内存，**不落盘**。

## 5. 依赖与外部工具
- 无额外 npm 依赖（仅 codex 及其平台包）。
- 宿主需 FFmpeg/FFprobe（视频/字幕处理）。
