# 许可证与来源（E 线）

> 分级：【实测】【源码确认】【文档】【推断】【未知】。**不简化 AGPL 义务，不擅自决定原创代码许可。**

## 一、代码三类划分

### A. 奈奈原创代码（Nana Core）
- `src/bili_agent/*`（除上游派生外）、`src/c5v/*`、`src/plugins/astrbot_plugin_nana_*`、`bridge/*`、`docs/*`、`PROJECT_BRAIN/*`、`patches/*`、`materials/bili_agent/login/*`
- 许可：**待定** → 由**姐姐最终决定**（本文件不预设）。
- 来源：【实测】本机生成/采集。

### B. 修改过的第三方代码（派生作品，保留原许可）
| 对象 | 上游 | 上游许可 | 本地存放 |
|---|---|---|---|
| AstrBot qqofficial 补丁（3 处） | `AstrBotDevs/AstrBot` v4.28.0 | **AGPL-3.0-or-later** | `patches/astrbot/` |
| Iris 定制（14 处） | `Leafliber/astrbot_plugin_iris_chat_memory` 0.3.0 | **AGPL-3.0** | `materials/iris_customizations/`（隔离，附 AGPL 全文） |

> AGPL 义务依**代码关系与使用方式**判断；**不**等于"入库即整仓变 AGPL"。
> 上述两类为**衍生作品**，其所在目录保留 AGPL；**不**改写为自有许可。

### C. 未修改的第三方依赖（不随仓库分发）
- 见 `requirements.txt`。均为 pip/npm 生态包，**不复制源码入仓**。
- AstrBot 4.28.0（AGPL-3.0-or-later）、bilibili-api-python、curl_cffi、openai、faiss-cpu、numpy、quart、Pillow、httpx、pytest 等。

## 二、上传白名单/排除
- 上传：上述 A/B 类中**已通过敏感扫描**的文件。
- 排除：真实凭据、Cookie、数据库、日志、备份、聊天记录、含真实事件 ID/UID 的测试脚本（见 `materials/bili_agent/EXCLUSIONS.md`）。

## 三、待姐姐决策
1. Nana Core **原创代码**采用何种许可证（默认：暂不添加根 LICENSE，保持待定）。
2. 是否允许 Iris AGPL 派生材料（14 处补丁）存于主仓库 `materials/`（当前为**隔离 + 附 AGPL**方案）。
