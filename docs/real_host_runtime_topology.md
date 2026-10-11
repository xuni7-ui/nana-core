# Real Host Runtime Topology — AstrBot Shadow Bind R01

- 采集时间：2026-10-11 (CST)
- 执行者：奈奈（宿主侧执行者，in-container shell）
- 授权范围：只读 host/runtime metadata + 非敏感程序源码；**无 restart / 无 secret / 无私人正文 / 无消息外发**
- 证据等级：全部来自当前真实运行态实测（非历史假设）

## 一、运行链（VERIFIED）

```
HOST (外部宿主，不可见)
  └─ container runtime (Docker/containerd, overlayfs)
       └─ container  dae88a85…(redacted)
            └─ PID1: python main.py            ← AstrBot 本体进程
                 └─ /AstrBot                    ← AstrBot 根
                      └─ data/ (volume /dev/vda2 ext4)
                           └─ plugins/          ← 插件目录
                                └─ astrbot_plugin_iris_chat_memory  ← Iris
```

**结论：AstrBot execution location = CONTAINER（就在奈奈所在的同一个容器内）。**

## 二、逐项核实

| 项目 | 实测值 | 方式 | 状态 |
|---|---|---|---|
| container id | `dae88a85…`（redacted） | hostname | VERIFIED |
| 是否容器内 | 是 | `/.dockerenv` 存在；`/proc/1/cgroup`=`0::/` | VERIFIED |
| PID1 | `python main.py` | /proc/1/cmdline | VERIFIED |
| AstrBot root | `/AstrBot` | ls / pyproject | VERIFIED |
| AstrBot version | **4.28.0** | pyproject.toml + `pip show AstrBot` | VERIFIED |
| Python version | **3.12.14** | `python3 --version` | VERIFIED |
| plugin dir | `/AstrBot/data/plugins` | source: `get_astrbot_plugin_path()` | VERIFIED |
| reserved plugin dir | `/AstrBot/astrbot/builtin_stars` | star_manager.py:207 | VERIFIED |
| plugin config dir | `/AstrBot/data/config` | source: `get_astrbot_config_path()` | VERIFIED |
| Iris path | `/AstrBot/data/plugins/astrbot_plugin_iris_chat_memory` | ls | VERIFIED |
| Iris version | 0.3.0（display: Iris 聊天陪伴记忆） | metadata.yaml | VERIFIED |
| data volume | `/AstrBot/data` ← `/dev/vda2` ext4 (rw) | /proc/mounts | VERIFIED |
| docker CLI | **不存在**（容器内无 docker） | command -v | VERIFIED |
| image / container name | — | 无 docker/inspect | **UNKNOWN** |

## 三、未取到 / UNKNOWN

- container image、container name、read-only mount 全量元数据：容器内 **无 docker CLI**，且无 inspect 通道 → **UNKNOWN**（未从目录名猜测）。
- host 侧其它容器（nana_keeper 等）：无法枚举 → **UNKNOWN**。

## 四、Drift 记录

1. **仓库分支 drift**：任务书基线为 `dev/nana-core-v1-shadow-host-compat @ c3ada9b`；本地开发副本 `/root/nana_dev/nana-core` 仅 `master @ 18bc736`（+ `origin/main`），**未见目标分支与 c3ada9b 提交**。→ 需姐姐确认是 fetch 远程还是基线另指。
2. **AstrBot 版本**：实测 4.28.0，与仓库 R15 记述的 “AstrBot 补丁(v4.28.0, a4121464)” **一致**，无 drift。

## 五、零漂移声明（本轮）

| 项 | 值 |
|---|---|
| existing production files modified | **0** |
| existing Iris files modified | **0** |
| existing config modified | **0** |
| AstrBot restarted | **false** |
| external messages | **0** |
| secret reads | **0** |
| private message plaintext reads | **0** |
| new plugin directory created | 0（本轮未创建任何插件目录） |
