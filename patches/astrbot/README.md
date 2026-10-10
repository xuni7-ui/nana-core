# AstrBot 4.28.0 主体补丁（D2）

> 结论分级：【实测】=本机命令直接产出；【源码确认】=与上游源码逐字节比对；【文档】=既有报告；【推断】；【未知】

## 1. 目的
生产 AstrBot 宿主 `qqofficial` 平台源码对官方 4.28.0 有 **3 处**本地改动。为让宿主偏离**可审查、可复现**，以补丁形式保存，**不**把整个 AstrBot 目录入库。

## 2. 上游基线（双源交叉确认）【源码确认】
| 来源 | 标识 | 校验 |
|---|---|---|
| GitHub `AstrBotDevs/AstrBot` tag `v4.28.0` | commit `a412146401426c0cdff8bbefb8627a03da519da8` | 两文件 sha256 与生产基线**完全一致** |
| PyPI sdist `astrbot-4.28.0.tar.gz` | sha256 `ea48a4ba8f4d8edfcb757c19818ab22e25d175e28431c1919643709045e9c655` | 解包出的两文件与 GitHub 版一致 |

- 生产版本：`AstrBot 4.28.0`（`importlib.metadata`）【实测】
- 许可证：**AGPL-3.0-or-later**（PyPI 元数据 License 字段）【实测】

## 3. 改动内容（3 处 / +3 −3）【源码确认】
文件 1：`astrbot/core/platform/sources/qqofficial/qqofficial_message_event.py`
- 第 ~432 行：`isinstance(...)` 增加 `botpy.message.C2CMessage` 分支。

文件 2：`astrbot/core/platform/sources/qqofficial/qqofficial_platform_adapter.py`
- 第 ~417 行、第 ~494 行：**主动推送**路径移除 `payload["msg_seq"] = random.randint(1,10000)`（替换为注释说明）。

**修改目的**：QQ 官方机器人主动推送场景下 `msg_seq` 会触发越权/`msg_id` 不可用问题；C2C 私聊同样不应带 `msg_seq`。

## 4. 应用 / 回退
```bash
# 应用（在 AstrBot 4.28.0 源根目录）
git apply patches/astrbot/astrbot-4.28.0-qqofficial-proactive-send.patch
# 回退
git apply -R patches/astrbot/astrbot-4.28.0-qqofficial-proactive-send.patch
```
【实测】补丁对干净基线 `git apply --check` 通过，往返应用后与生产文件**逐字节一致**（sha256 相等）。

## 5. 敏感信息
【实测】补丁仅含 3 行代码改动，无密钥/个人信息/环境数据。

## 6. 边界
- 未修改生产 AstrBot；本补丁仅在隔离环境制作。
- AstrBot 为 AGPL，本补丁属其**衍生作品**，随附 AGPL 义务；**不**并入 Nana Core 原创代码许可决定。
