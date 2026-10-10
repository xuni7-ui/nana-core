"""
语意裁决闸 v3.2 —— 「L1 上下文为主，L2/L3 为辅，时间做校准」

姐姐 2026-10-05 定：裁决范围从「孤词」扩大到「所有消息」。
姐姐 2026-10-06 定：孤词走「专线」——只看「是不是孤词」这一条，
                     不再等 verdict 分级，也不再拿近窗去兜底。

固定处理顺序：
    ① 孤词专线：是孤词 → 不叫醒 L2/L3，只依据最近 2～4 轮上文接话
       （有还悬着的事就顺一句轻软地接；没有就当作新对话自然开场）
    ② 非孤词：先看 L1 上下文，判断这句话冷不冷（能不能自解释）
    ③ 冷（依赖上文 / 指代）→ 才去叫醒 L2/L3；热（自足）→ 只做轻检索（半量）
    ④ 兜底：指代但无上文 → 近窗（默认 3 天）兜一次，兜到接语义，兜不到才软确认
    ⑤ 全程带时间思考与校准：时间锚点始终注入（含「距上次对话」）、
       按记忆时龄降权、当下时态词 vs 全旧记忆冲突时告警

三档语义裁决（Verdict.tier）：

| tier            | 含义                             | 检索档位      | 查询词拼法            |
|-----------------|----------------------------------|---------------|-----------------------|
| self_contained  | 自身信息完整，不依赖上文         | light（半量） | 当前句为主 + 1 条上文 |
| needs_context   | 靠 L1 上文才能懂                 | normal        | 最近 N 轮 + 当前句    |
| frail           | 上文也补不出（指代无上文等）     | last_resort   | 1 条上文 + 当前词     |

设计约束：
- 纯函数、零副作用、零网络调用，方便单测
- 不 import llm_request_hook（避免循环依赖）；清洗工具在这里定义，hook 反过来复用它
- 任何异常都不能让主链路挂掉：调用方一律 try/except 包住

v3.2 相对 v3.1 图纸的差异（奈奈补刀 #12，见方案文档）：
- `time_anchor_line()` 的注入开关建议跟随总闸（`semantic_gate_enable`），
  否则「总闸关 = 行为与 v1 逐字节一致」这句承诺不成立。
  本文件只提供函数，开关裁决留给接线处（8.3 已按「跟随总闸」写好）。

v3.3 相对 v3.2 的差异（2026-10-06 二审修订，改动清单 F）：
- 【升④ 落地】孤词专线窗口与「检索词轮数」彻底解耦：
  新增独立键 `l2_memory.lone_thread_window_turns`（默认 4），
  并提供 `resolve_lone_window()` / `lone_window_recent()` 两个纯函数。
  从此姐姐把 `retrieval_query_context_turns` 拧到 6，孤词窗口仍守在「最近二到四轮」。
- 其余逻辑一行未动：`arbitrate` / `policy_for` / 时间校准 / 孤词文案 与 v3.2 逐字节一致。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, List, Optional, Sequence, Tuple
import re

# ============================================================================
# 一、文本清洗（唯一真源：hook 复用本模块，不再各写一份）
# ============================================================================

_WAKE_NOISE_RE = re.compile(r"\[At:[^\]]*\]")
_PUNCT_ONLY_RE = re.compile(
    r"[\s，。！？!?~～,.;；:：、…—\-—_\"'“”‘’（）()\[\]【】<>《》]+"
)


def clean_text(text: Optional[str]) -> str:
    """洗掉 @占位符与标点，只留实词。"""
    if not text:
        return ""
    return _PUNCT_ONLY_RE.sub("", _WAKE_NOISE_RE.sub("", text)).strip()


def is_lone(text: Optional[str], max_chars: int = 3) -> bool:
    """是否为孤词/唤醒词（清洗后长度不超过阈值）。"""
    cleaned = clean_text(text)
    if not cleaned:
        return True
    return len(cleaned) <= max(1, int(max_chars))


def has_context(recent_utterances: Optional[Sequence[str]]) -> bool:
    """上方到底有没有可接的东西。

    修#7：口径统一为「有任一条洗出实词」，与 arbitrate 内部判据同源，
    不再出现 hook 用 `not recent`、闸内用 `clean_text` 两套标准。
    """
    return any(clean_text(u) for u in (recent_utterances or []))


# ============================================================================
# 二、语意信号词表
# ============================================================================

# 承上/指代词：命中即说明「必须靠上文才能懂」
# 修#6：去掉裸单字（此 / 该 / 它 / 其），避免「因此 / 应该 / 其它 / 其实」被误伤
_REFERENCE_WORDS: Tuple[str, ...] = (
    "这个", "那个", "这些", "那些", "这样", "那样", "它们", "此方案", "该方案",
    "上面", "上述", "前述", "前面", "前一条", "那条", "这条",
    "接下来", "然后", "接着", "继续", "还有吗", "下一个", "同样", "也是",
    "一样", "三个", "两个", "几个", "哪些", "哪条", "第一种", "第二种",
    "上次", "之前", "那个方案", "那件事", "这题", "那条消息", "刚才那个",
)

# 单字指代：只有紧贴名词时才认（此方案 / 该条 / 它个…），裸「此」「该」「它」不认
_SINGLE_REF_RE = re.compile(r"([此该它其])(?:方案|条|个|些|项|种|件事|题|消息)")

# 当下时态词：说话人把锚点钉在「今天/现在」，旧记忆不该被当成今天的事
_PRESENT_MARKERS: Tuple[str, ...] = (
    "今天", "今晚", "今早", "现在", "刚刚", "刚才", "这会儿", "马上",
    "待会", "这两天", "这周", "本周", "目前",
)


# ============================================================================
# 三、裁决结果
# ============================================================================


@dataclass
class Verdict:
    """一句话的语意裁决结果。"""

    tier: str  # self_contained | needs_context | frail
    clean_len: int = 0
    references: List[str] = field(default_factory=list)
    present_marker: Optional[str] = None
    reason: str = ""

    @property
    def retrieval_tier(self) -> str:
        """检索档位：light / normal / last_resort。"""
        return {
            "self_contained": "light",
            "needs_context": "normal",
            "frail": "last_resort",
        }.get(self.tier, "normal")

    @property
    def need_retrieval(self) -> bool:
        """self_contained 允许轻检索；其余两档属于「必须叫醒」或「兜底」。"""
        return self.tier != "self_contained"

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "clean_len": self.clean_len,
            "references": list(self.references),
            "present_marker": self.present_marker,
            "reason": self.reason,
            "retrieval_tier": self.retrieval_tier,
        }


def detect_references(text: str) -> List[str]:
    """捡出指代/承上词（含「单字＋名词」的合法单字指代）。"""
    cleaned = clean_text(text)
    hits = [w for w in _REFERENCE_WORDS if w in cleaned]
    for m in _SINGLE_REF_RE.finditer(cleaned):
        if m.group(0) not in hits:
            hits.append(m.group(0))
    return hits


def detect_present_marker(text: str) -> Optional[str]:
    """捡出当下时态词（今天/现在/刚才…）。"""
    cleaned = clean_text(text)
    for w in _PRESENT_MARKERS:
        if w in cleaned:
            return w
    return None


def arbitrate(
    current_text: Optional[str],
    recent_utterances: Optional[Sequence[str]] = None,
    lone_max: int = 3,
) -> Verdict:
    """核心裁决：先判「这句话离了上文能不能懂」。

    注意：孤词在接线层已由「孤词专线」提前拦走；本函数仍保留孤词分支，
    是为了「专线开关关掉」或「被别处单独调用」时行为依旧自洽。

    Args:
        current_text: 姐姐这一轮的原话
        recent_utterances: 从 L1 捞到的最近若干条「用户实质发言」（旧→新）
        lone_max: 孤词阈值（清洗后字数）

    Returns:
        Verdict
    """
    cleaned = clean_text(current_text)
    refs = detect_references(cleaned)
    present = detect_present_marker(cleaned)
    has_recent = has_context(recent_utterances)

    if not cleaned:
        verdict = Verdict("frail", 0, refs, present, "空消息/纯符号")
    elif is_lone(cleaned, lone_max):
        if has_recent:
            verdict = Verdict(
                "needs_context", len(cleaned), refs, present,
                f"孤词·有上文（{len(cleaned)}字）",
            )
        else:
            verdict = Verdict(
                "frail", len(cleaned), refs, present,
                f"孤词·无上文（{len(cleaned)}字）",
            )
    elif refs and not has_recent:
        verdict = Verdict(
            "frail", len(cleaned), refs, present,
            "指代词但无上文：" + "/".join(refs[:3]),
        )
    elif refs:
        verdict = Verdict(
            "needs_context", len(cleaned), refs, present,
            "依赖上文：" + "/".join(refs[:3]),
        )
    else:
        verdict = Verdict("self_contained", len(cleaned), refs, present, "自身信息完整")

    return verdict


# ============================================================================
# 四、检索策略（按档位决定「叫不叫醒 L2/L3」「用多狠的阈值」）
# ============================================================================


@dataclass
class RetrievalPolicy:
    top_k: int
    min_score: float
    max_age_days: Optional[float]  # None = 不限时龄
    soft_confirm_on_miss: bool      # 修#8：接线层必须真的读这个字段

    def to_dict(self) -> dict:
        return {
            "top_k": self.top_k,
            "min_score": self.min_score,
            "max_age_days": self.max_age_days,
            "soft_confirm_on_miss": self.soft_confirm_on_miss,
        }


def policy_for(
    verdict: Verdict,
    base_top_k: int = 10,
    base_threshold: float = 0.3,
    recent_days: float = 3.0,
) -> RetrievalPolicy:
    """按裁决档位生成检索策略。"""
    base_top_k = max(1, int(base_top_k))
    if verdict.tier == "self_contained":
        return RetrievalPolicy(
            top_k=max(3, base_top_k // 2),
            min_score=base_threshold,
            max_age_days=None,
            soft_confirm_on_miss=False,
        )
    if verdict.tier == "needs_context":
        return RetrievalPolicy(
            top_k=base_top_k,
            min_score=base_threshold,
            max_age_days=None,
            soft_confirm_on_miss=False,
        )
    # frail：兜底档，只在近期里找，阈值抬一点，找不到就软确认
    return RetrievalPolicy(
        top_k=base_top_k,
        min_score=max(base_threshold, 0.35),
        max_age_days=max(1.0, float(recent_days)),
        soft_confirm_on_miss=True,
    )


def build_retrieval_query(
    verdict: Verdict,
    current_text: Optional[str],
    recent_utterances: Optional[Sequence[str]] = None,
    max_turns: int = 4,
) -> str:
    """按档位拼检索词（旧→新，当前句排在最后）。"""
    turns = max(1, int(max_turns))
    recent = [u.strip() for u in (recent_utterances or []) if clean_text(u)]
    recent = recent[-turns:]
    cur = (current_text or "").strip()

    if verdict.tier == "self_contained":
        parts = recent[-1:] + [cur] if recent else [cur]
    elif verdict.tier == "needs_context":
        parts = recent + [cur]
    else:  # frail：上文补不出东西，只押当前词 + 1 条上文试运气
        parts = recent[-1:] + [cur]

    return " ".join(p for p in parts if p and p.strip())


# ============================================================================
# 五、时间思考与校准
# ============================================================================


def to_cst(dt: datetime) -> datetime:
    """把「容器本地时钟」的 naive 时间换算成北京时间（naive）。

    补差动态算：shift = 8h - 本地相对 UTC 的偏移。
    将来容器时区改成 CST，也不会重复叠加 8 小时。
    """
    try:
        import time as _time

        shift = 8 * 3600 - int(_time.localtime().tm_gmtoff)
    except Exception:
        shift = 0
    return dt + timedelta(seconds=shift)


def now_cst() -> datetime:
    """当前北京时间（naive）。"""
    return to_cst(datetime.now())


def gap_phrase(last_ts: Optional[datetime], now: Optional[datetime] = None) -> str:
    """「距上次对话」分档文案（修#5）。"""
    if last_ts is None:
        return "距上次对话：时间未知"
    sec = max(0.0, ((now or now_cst()) - to_cst(last_ts)).total_seconds())
    if sec < 120:
        return "距上次对话：刚刚"
    if sec < 3600:
        return f"距上次对话：{int(sec // 60)} 分钟前"
    if sec < 86400:
        return f"距上次对话：{int(sec // 3600)} 小时前"
    return f"距上次对话：{int(sec // 86400)} 天前"


def time_anchor_line(
    now: Optional[datetime] = None,
    last_message_ts: Optional[datetime] = None,
) -> str:
    """钉一行「当前对话时间」锚点（修#5：带「距上次对话」，由接线层始终注入）。"""
    n = now or now_cst()
    weekday = "一二三四五六日"[n.weekday()]
    return (
        f"[时间锚] 现在 {n.strftime('%Y-%m-%d %H:%M')}（北京时间，周{weekday}）"
        f"· {gap_phrase(last_message_ts, n)}。"
        "记忆自带「写入时间 · 距今多久」，请据此判断新旧，"
        "不要把旧条目当成今天发生的事。"
    )


def entry_age_days(entry: Any, now: Optional[datetime] = None) -> Optional[float]:
    """一条记忆距今天数；没有可信时间戳时返回 None（不猜，修#4）。"""
    if entry is None:
        return None
    raw = getattr(entry, "timestamp", None)
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw))
    except Exception:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    shown = to_cst(dt)
    return ((now or now_cst()) - shown).total_seconds() / 86400.0


_DECAY_TABLE: Tuple[Tuple[float, float], ...] = (
    (1.0, 1.0),     # 今天/昨天
    (3.0, 0.92),
    (7.0, 0.85),
    (30.0, 0.65),
    (3650.0, 0.45),
)


def time_decay(age_days: Optional[float]) -> float:
    """时龄衰减系数。时间不明的记忆给中性偏低分，不冒充新的。"""
    if age_days is None:
        return 0.8
    age = max(0.0, float(age_days))
    for days, factor in _DECAY_TABLE:
        if age <= days:
            return factor
    return 0.4


def rerank_by_time(
    results: Optional[Iterable[Any]], now: Optional[datetime] = None
) -> List[Any]:
    """按 score × 时龄衰减 重排（不改原对象，同分保持原序）。"""
    scored: List[Tuple[float, int, Any]] = []
    for idx, r in enumerate(list(results or [])):
        try:
            score = float(getattr(r, "score", 0.0) or 0.0)
        except Exception:
            score = 0.0
        entry = getattr(r, "entry", r)
        scored.append((score * time_decay(entry_age_days(entry, now)), idx, r))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]


def time_conflict_warn(
    results: Optional[Iterable[Any]],
    verdict: Verdict,
    now: Optional[datetime] = None,
    stale_days: float = 7.0,
) -> str:
    """当下时态词 vs 旧记忆冲突时，返回一行校准告警；不冲突则返回空串。

    修#3：原判据用 max(known)（最旧）——方向写反，导致只要有一条旧账就告警；
          文案本身写的是「最新的一条也已经是 N 天前」，应与 min(known) 一致。
    修#9：原在 frail 时把 marker 硬兜成「刚才」，等于往上下文里塞姐姐没说过的词；
          现在没有 marker 就不开口。
    """
    results = list(results or [])
    if not results:
        return ""
    ages = [entry_age_days(getattr(r, "entry", r), now) for r in results]
    known = [a for a in ages if a is not None]
    if not known or min(known) <= stale_days:
        return ""

    marker = verdict.present_marker
    if not marker:
        return ""

    return (
        f"⚠️【时间校准】姐姐这句带着「{marker}」这类当下时态，"
        f"但捞回的记忆里最新的一条也已经是 {int(min(known))} 天前。"
        "不要把这些旧账当成今天发生的事；不确定就先温柔问一句。"
    )


def frail_miss_soft_confirm(verdict: Verdict, hit_count: int = 0) -> str:
    """真孤词/指代无上文 + L2/L3 也没兜到 → 软确认文案（修#8 由接线层调用）。"""
    if verdict.tier != "frail" or hit_count > 0:
        return ""
    return (
        "## 相关记忆\n（本轮姐姐只发来一个极短词，上文也接不上，"
        "近期记忆里没有能对上号的东西。已按纪律不硬猜，"
        "请先用一句话温柔确认她想聊什么，不要翻旧账。）"
    )


# ============================================================================
# 六、孤词专线（姐姐 2026-10-06 定：孤词不检索，只接最近 2～4 轮上文）
# ============================================================================


def lone_thread_notice(has_thread: bool) -> str:
    """孤词专线的提示文案。

    Args:
        has_thread: 最近 2～4 轮里有没有还悬着的事/没回的问题
                    （由接线层用 has_context() 判，判不出就交给模型软判）
    """
    if has_thread:
        return (
            "## 相关记忆\n（本轮是极短孤词。按纪律**不检索长期记忆**，"
            "只依据上方【近期对话记录】里最近 2～4 轮接话："
            "若有还悬着的事/没回的问题，就顺着一句轻软地接；"
            "若没有悬着的东西，就当作新对话自然开场，不要翻旧账。）"
        )
    return (
        "## 相关记忆\n（本轮是极短孤词，最近几轮也没有可接的线索。"
        "按纪律不检索长期记忆，请当作新对话自然开场，不要翻旧账。）"
    )


# ============================================================================
# 七、孤词专线窗口（v3.3 · 改动清单 F／二审「升④」落地）
# ============================================================================

LONE_THREAD_WINDOW_DEFAULT: int = 4   # 姐姐 2026-10-05 17:26 拍板：最近二到四轮，取上界
LONE_THREAD_WINDOW_MIN: int = 2
LONE_THREAD_WINDOW_MAX: int = 4


def resolve_lone_window(raw: Any = None, default: int = LONE_THREAD_WINDOW_DEFAULT) -> int:
    """把配置值收敛到姐姐拍板的「最近二到四轮」区间（纯函数）。

    - 缺配置 / 非法值 → `default`（4）
    - 比下限小 → 抬到 2；比上限大 → 压到 4

    存在的意义：孤词窗口以前直接借用 `retrieval_query_context_turns`，
    姐姐哪天把检索词轮数改成 6，孤词窗口就跟着变 6——那就不再是「最近二到四轮」了。
    独立键 + 这个夹逼函数，把两件事钉死分开。
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = int(default)
    return max(LONE_THREAD_WINDOW_MIN, min(LONE_THREAD_WINDOW_MAX, value))


def lone_window_recent(
    recent_utterances: Optional[Sequence[str]] = None,
    lone_window: Any = LONE_THREAD_WINDOW_DEFAULT,
) -> List[str]:
    """从「已经取出的最近上文」里，切出孤词专线真正要看的那个窗口。

    取尾部最靠近当前的若干条（旧→新列表的末尾 = 最近）。清洗后为空的条目丢掉。
    """
    window = resolve_lone_window(lone_window)
    cleaned = [u for u in (recent_utterances or []) if clean_text(u)]
    return cleaned[-window:]


def lone_thread_payload(
    recent_utterances: Optional[Sequence[str]] = None,
    lone_window: Any = LONE_THREAD_WINDOW_DEFAULT,
) -> Tuple[str, bool, List[str]]:
    """孤词专线一次算全：返回 (提示文案, 有没有可接线索, 用到的窗口原文)。

    接线层只要 `notice, has_thread, window_used = _sg.lone_thread_payload(recent, cfg)` 一行，
    就同时拿到「文案」「是否算有上文」「实际窗口」，方便顺手写进决策日志。
    """
    window_used = lone_window_recent(recent_utterances, lone_window)
    has_thread = has_context(window_used)
    return lone_thread_notice(has_thread), has_thread, window_used
