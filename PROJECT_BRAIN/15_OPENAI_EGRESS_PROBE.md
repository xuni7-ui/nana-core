# 15 · OpenAI 官方出口可达性 · 只读体检（R5）

> 时刻：**2026-10-10 03:3x CST** ｜ 执行人：奈奈 ｜ 来源：`[实测]`
> 授权依据：姐姐追加指令「先只读检查是否存在可靠、可用的 OpenAI 网络出口，以及官方 ChatGPT 登录是否可以完成」
> 边界：**只读**。未安装、未登录、未部署代理、未改生产、未动桥。

---

## 一、结论（一句话）

**无可靠 OpenAI 出口。官方 ChatGPT 登录无法在本机完成。** 阻塞在**网络层**，非软件层。

---

## 二、实测数据

### 2.1 DNS 解析（本机 Docker 内置 resolver `127.0.0.11`）

| 域名 | 本机解析结果 | 判定 |
|---|---|---|
| `chatgpt.com` | **199.59.150.40** | ❌ 非 Cloudflare 边缘 → 典型污染结果，TCP 不可达 |
| `api.openai.com` | **184.72.1.148** | ❌ 非预期边缘 IP，TCP 不可达 |
| `auth.openai.com` | **104.18.41.241 / 172.64.146.15** | ✅ 真实 Cloudflare 边缘 |
| `openai.com` | 104.18.33.45 / 172.64.154.211 | ✅ 真实 Cloudflare 边缘 |

### 2.2 裸 TCP 连通性（绕开 DNS，直接连 IP）

| 目标 | 结果 |
|---|---|
| `104.18.32.47:443`（Cloudflare，chatgpt.com 真实边缘） | ✅ TCP 可连 |
| `104.18.41.241:443`（auth.openai.com 边缘） | ✅ TCP 可连 |
| `199.59.150.40:443`（本机解析出的 chatgpt.com） | ❌ 超时 |
| `184.72.1.148:443`（本机解析出的 api.openai.com） | ❌ 超时 |

### 2.3 HTTPS 行为（关键证据）

| 请求 | 结果 | 解读 |
|---|---|---|
| `https://chatgpt.com/` | `code=000`，timeout **6.0s** | 解析 IP 不可达 |
| `https://chatgpt.com/`（**强制 --resolve 到真实 CF 边缘 172.64.146.15**） | `code=000`，**0.079s 立刻失败** | ⚠️ TCP 能连、TLS/SNI 立刻被重置 → **SNI 层阻断** |
| `https://api.openai.com/v1/models` | `code=000`，timeout 6.0s | 不可达 |
| `https://auth.openai.com/` | **`code=403`**，0.23s | ✅ TCP+TLS 通（TLS1.3，证书 CN=auth.openai.com 有效）→ **边缘层拒绝**（HTML 为阻断页） |

### 2.4 对照组（证明本机出网本身正常）

| 目标 | 结果 |
|---|---|
| `https://www.baidu.com/` | ✅ 200（0.06s） |
| `https://github.com/` | ✅ 200（0.65s） |
| `https://api.github.com/` | ✅ 200（0.31s） |
| `https://registry.npmjs.org/` | ✅ 200（0.57s） |
| `https://api.deepseek.com/` | ✅ 401（0.08s，端点活着，只是没带钥匙） |
| `https://dns.google/resolve?...` | ❌ 超时（DoH 出口亦被限） |

### 2.5 本机是否存在现成代理

- 监听端口扫描（`ss -ltnp`）：**无输出** → 本命名空间未观察到任何本地代理端口。
- 环境变量：仅 `no_proxy=localhost,127.0.0.1,::1`，**无** `http_proxy/https_proxy/all_proxy`。

---

## 三、阻塞点定性

| # | 阻塞 | 层面 | 本机可否自行解决 |
|---|---|---|---|
| B1 | `chatgpt.com` DNS 被污染 + 真实边缘 **SNI 阻断** | 网络出口 | ❌ 否 |
| B2 | `api.openai.com` 解析污染 + 不可达 | 网络出口 | ❌ 否 |
| B3 | `auth.openai.com` TLS 通但 **403 边缘拒绝** | 服务地区/网络策略 | ❌ 否 |
| B4 | 无本地代理可用 | 环境 | ❌ 否（且**部署代理已被姐姐明令禁止**） |

**推论**：Codex CLI 的两种官方登录路径（`chatgpt.com` 网页授权、`auth.openai.com` device-auth）在本机**都不可能完成**。
R3 已实测 `login --device-auth` → **403**，本次体检**复现同一结论**，故**按姐姐指令停止，不再重试登录**。

---

## 四、Codex CLI 现状（复用，未重装）

| 项 | 值 |
|---|---|
| 包 | `@openai/codex@0.162.0`（官方 npm，Apache-2.0） |
| 可执行 | `/opt/nana_codex/node_modules/.bin/codex` → `bin/codex.js` |
| HOME | `/opt/nana_codex/home/`（owner `nobody:nogroup`） |
| 现有配置 | `config.toml` 已含自定义 provider（指向 DeepSeek 兼容端点，**凭据运行期注入、不落盘**） |
| 当前可用性 | ✅ **CLI + DeepSeek 路径可用**（R4 已实测：真实写文件 + 真实跑测试 rc=0） |
| 官方 OpenAI 路径 | ❌ 被 B1–B3 阻断 |

---

## 五、替代路径评估：GitHub 仓库 + Codex Cloud

| 维度 | 评估 |
|---|---|
| Codex Cloud 入口 | 位于 `chatgpt.com/codex` → **本机不可达**（B1） |
| 是否可能 | ✅ **可能，但必须由姐姐在自己的设备/浏览器完成**（走姐姐本地网络，与本服务器出口无关） |
| 对服务器侧的要求 | 需要一个 **GitHub 远端仓库** + push 能力 |
| 当前状态 | ❌ 副本 `git` **无 remote**；**GitHub 首次上传/push 未授权**（T-44） |
| 结论 | **代码同步链路可替代；模型执行链路仍在姐姐设备侧**，服务器无法直接调用 Cloud 算力 |

---

## 六、本轮未做（合规声明）

- ❌ 未安装任何依赖、未 `npm install`
- ❌ 未执行任何登录 / 未索取密码、验证码、令牌
- ❌ 未部署、未配置任何代理或隧道
- ❌ 未修改生产、未重启服务、未 push、未创建凭据

---

## 七、待姐姐裁决（合并为一次）

> **现役方案保留**：Codex CLI + 自定义 Provider（DeepSeek）——已实测可真实执行代码任务，作为**备用/主力开发 Runner**。
> **官方 OpenAI Codex**：网络层不可达，**在本服务器上无法落地**。
>
> 若姐姐希望走官方 Codex 算力，唯一可行形态是：
> **姐姐本地浏览器 → Codex Cloud / ChatGPT → 连接 GitHub 仓库**，
> 而服务器侧只需具备 **git remote + push 授权** 即可同步代码。
