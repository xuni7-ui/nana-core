# Iris 定制文件指纹（sha256）

> 【实测】2026-10-10 对生产插件目录采集。用于校验补丁应用结果。

## 7 处修改
| 文件 | sha256 |
|---|---|
| `_conf_schema.json` | `c8711d7b09c684132dad2d1558f949918a2a12b8f97bbe35fddf6adf91ee9ec0` |
| `iris_memory/config/defaults.py` | `4175a4bd9fe1cf5aca52edbb64a28cc36e450caf2c11cad7dd807e963a6a0384` |
| `iris_memory/core/llm_request_hook.py` | `180724304cb5a45c3f4a6783adc38e2d386d7f6cff791d7b5e382b71b0b4f420` |
| `iris_memory/core/llm_response_hook.py` | `f776ee5d22ea15e21a0dfe942bc97b4a00aefeac435b26da97ab995fc4af6d33` |
| `iris_memory/core/message_hook.py` | `cf54e3b0efcc6713d7e7b27c43e60a943176965d8ea24b4cbbe07157339862a9` |
| `iris_memory/l1_buffer/buffer.py` | `306da9d37b0718585e4a00c006e5edf940f361c1963c115daaf6b8b194f1d8db` |
| `iris_memory/utils/__init__.py` | `820ec4a818d0b768cf0ef2745588c3a6d2286bf72d1a556100430167cd8a7590` |

> 新增 7 文件（sha256 见仓库本轮 commit 或 `git hash-object`）逐字节备份于 `NEW_FILES/`。
