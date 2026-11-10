# B站发送动作可靠性 · C.2（v1）

> 目标：不再发生「发送回包不明确 → 盲重发 → 12051 刷屏」的事故。

## 一、状态机

```
precheck → send → result → verify → record
```

| 状态 | 含义 | 处置 |
|---|---|---|
| `PRE_EXIST` | 发前已存在同文评论（幂等命中） | 视为成功，**不发送** |
| `VERIFIED` | B站 上已确认存在（拿到 rpid） | 成功 |
| `RETRYABLE` | 服务端明确答复失败 + verify 未见 + 确认无副作用 | 可安全重试 |
| `PENDING_VERIFY` | 状态不明（回包残缺 / **读不到 code** / 网络异常 / 12051 但查不到） | **禁止自动重试**，需复核 |
| `DRY_RUN` | 空跑 | 不发送、不写账 |

退出码：`0`=成功/幂等命中 · `1`=可重试 · `2`=状态不明 · `3`=空跑

## 二、核心判据（代码里的硬闸门）

1. **真相源是 B站，不是本地记账。** precheck 直接查评论列表 → 天然解决「重启后重复执行」。
2. **回包不明确 ≠ 失败。** `code=0` 但读不到 rpid / 网络超时 → 一律先去 verify。
3. **12051 是「疑似已存在」而不是「失败」** → 必须核实到 rpid 才算 VERIFIED。
4. **query_ok=False 不能推断「不存在」。** 查询本身失败 → PENDING_VERIFY。
5. **mid 类型不稳定**（B站 有时回 str 有时回 int）→ 一律按字符串比。 *这是 12051 事故的真正根因。*
6. **读不到 code = 结果未知，不是「明确失败」。** `code is None`（回包残缺/结构变动）一律并入 `PENDING_VERIFY`，绝不可落到 `RETRYABLE`。  *(v1.1 补洞，2026-10-07)*

## 三、用法

```bash
python3 bili_send_comment.py <BVID> "<正文>" [--dry]         # 顶层评论
python3 bili_reply_comment.py <BVID> <ROOT_RPID> "<正文>" [--dry]  # 楼中楼回复
python3 test_c2_state_machine.py                             # 离线 11 项自测（mock，不碰真站）
```

## 四、账本接线（复用现有，不另造）

| 账本 | 角色 | 落点 |
|---|---|---|
| `bili_comment_log.jsonl` | 流水（发生过什么） | 每次发送追加一行，含 `status` |
| Action Ledger `bili_comment_last_action` | 当前状态 | 最近一次动作的最终状态 |
| Action Ledger `bili_comment_pending_verify` | 未决队列 | 仅 PENDING_VERIFY 时写；VERIFIED 后置 `none` |

写序：**先记 INTENT → 再发送 → 回填最终状态**。

## 五、已知边界

- precheck 只取评论列表**第一页**（顶层 20 条 / 子评论 20 条）。热门视频顶层评论刷得很快时，久远评论可能滑出首页 → 漏判。缓解：文本指纹 + verify 二次确认；暂不翻页（避免请求放大）。
- 顶层评论 `send` 回包**长期残缺**（真机实测：`code=None`、读不到 rpid），因此 `VERIFIED` 快路径基本走不到，**verify（查评论列表）才是唯一真相源**。代价：每次真发多一次列表查询。
- **历史痕迹（不改）**：`bili_comment_log.jsonl` 末尾那行真实发送记录（rpid=316313011233）由**修复前**旧代码写入，note 文案为「明确返回失败 code=None」——措辞误导，但属真实证据原样留档，不回改。

## 六、C.2 收口状态（2026-10-07）

| 环节 | 状态 |
|---|---|
| 源码修改 | ✅ `bili_send_core.py` 补 `code is None → PENDING_VERIFY`（+2 行，主流程未动） |
| 离线测试 | ✅ T1–T11 全绿（删 9 项 + 新 T10/T11 补洞回归） |
| 真站只读 | ✅ precheck 命中既有评论（316307987585 / 316309369569） |
| 真站真实发送 | ✅ BV1t55v6DE2v rpid=316313011233（code=None → verify → VERIFIED） |
| Verify | ✅ 独立第三方查询 rpid 完全一致（双向印证） |
| Record | ✅ 流水末行 + `bili_comment_last_action=VERIFIED`，pending_verify=none |
| 独立复核 | ✅ 静态穷举：全活跃文件 `RETRYABLE` 仅 1 处赋值，已带 `code is None` 守卫 |

**C.2 收口，不再扩大。** 下一步 C.1（BiliAgent 最小闭环）。
