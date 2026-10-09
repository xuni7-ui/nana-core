# 13 · Codex CLI 安装 / 登录 / 执行 探针（真 Codex 验证）

- 时间：2026-10-10 03:0x CST
- 授权：姐姐同意安装官方 @openai/codex + 一次 ChatGPT 账号登录验证
- 范围：隔离探针目录 `/root/nana_dev/codex_probe/`（不进 git、不装全局、不碰生产）
- 生产改动：**0** ｜ 全局 npm 变动：**0** ｜ push：**无**（无 remote）

## 结论
**真 Codex CLI 安装成功；但登录与执行均被外网阻断 → 阻塞（网络+账号），非本机可修复。**

## 证据
1. 环境：Node v24.20.0 / npm 11.19.0 / Debian 13.0.0 / 40G 盘（20.1GiB 空闲）
2. 来源：`registry.npmjs.org`（官方源）HTTP 200
3. 安装：`@openai/codex@0.162.0` + `@openai/codex-linux-x64` 原生二进制（musl），added 2 packages
4. 可执行：`codex --version` → **`codex-cli 0.162.0`** ✅
5. 登录：`codex login --device-auth` → **`device code request failed with status 403 Forbidden`** ❌
6. 端点探测（curl）：
   - `auth.openai.com/api/accounts/deviceauth/usercode` → **403**
   - `chatgpt.com/backend-api/codex/responses` → **000（超时）**
   - `api.openai.com/v1/me` → **000（超时）**
   - DNS：`api.openai.com`→124.11.210.175、`chatgpt.com`→107.181.166.244（IPv6 含 `face:b00c`，疑似污染）
7. `codex doctor`：`✗ auth`（无凭据）/ `⚠ websocket`（超时）/ `✗ reachability`（provider 端点不可达）
8. `codex exec "..."` → 超时 `rc=124`（Runner 不可用）
9. 污染检查：全局 `/usr/lib/node_modules` 仅 `corepack,npm`；`~/.codex` 已生成但**无 `auth.json`（零凭据）**；源仓 git 干净（HEAD `5ceddb6`）；生产 `/AstrBot` mtime 未变

## 判定
- `is_codex_cli`：可置 true（CLI 确实存在且可执行）
- `codex runner able`：**false**（登录/执行不通）
- 阻塞类型：外网链路（GFW/区域封锁），**不是**本机配置问题
- 官方替代安装：npm 已是官方方式；登录无可用替代（ChatGPT 账号必须走 OpenAI 域名）
- 唯一可行的官方替代运行方式：**自定义 model provider**（config.toml `model_providers` 指向国内可达的 OpenAI 兼容端点，API-key 模式）→ 属 L3，需姐姐授权

## 未做
- 未装全局、未改生产、未 push、未创建/读取任何密钥、未大规模改造服务器
