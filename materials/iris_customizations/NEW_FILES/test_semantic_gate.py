"""语意裁决闸 semantic_gate 单元测试（v3.3 · 改动清单 B）

落盘目标：`tests/core/test_semantic_gate.py`
跑法：`python -m pytest tests/core/test_semantic_gate.py -q`（在插件根目录）

覆盖 §12 验收清单里的边界：
    三档裁决 / 单字指代误伤(修#6) / 锚点含「距上次对话」(修#5)
    / 冲突告警两向(修#3·#9) / 未知时间不冒充(修#4)
    / 孤词专线窗口解耦(改动清单 F：独立键 + 夹逼)
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import json
import os

from iris_memory.core import decision_log as dl
from iris_memory.core import semantic_gate as sg


# --------------------------------------------------------------------------
# 造数小工具
# --------------------------------------------------------------------------

def _mem(age_days, score=0.6):
    """造一条「N 天前写入」的记忆结果对象。

    刻意不给 `entry` 属性，让 getattr(r, "entry", r) 落回对象本身。
    """
    local_now = datetime.now()
    raw = (local_now - timedelta(days=age_days)).replace(microsecond=0).isoformat()
    return SimpleNamespace(timestamp=raw, score=score, content=f"第{age_days}天前的记忆")


# --------------------------------------------------------------------------
# 一、文本清洗 / 孤词判定
# --------------------------------------------------------------------------

class TestCleanAndLone:
    def test_clean_text_strips_at_placeholder_and_punct(self):
        assert sg.clean_text("[At:qq_official] 妹妹，！！！") == "妹妹"

    def test_clean_text_none_and_empty(self):
        assert sg.clean_text(None) == ""
        assert sg.clean_text("") == ""
        assert sg.clean_text("……——") == ""

    def test_is_lone_true_for_short_word(self):
        assert sg.is_lone("妹妹") is True
        assert sg.is_lone("嗯") is True

    def test_is_lone_respects_max_chars(self):
        assert sg.is_lone("姐姐帮帮我", max_chars=3) is False
        assert sg.is_lone("姐姐帮帮我", max_chars=5) is True

    def test_has_context_ignores_blank_entries(self):
        assert sg.has_context(["", "  ", "[At:x] 。。。"]) is False
        assert sg.has_context(["上次那道题"]) is True
        assert sg.has_context(None) is False


# --------------------------------------------------------------------------
# 二、指代词 / 时态词（修#6、修#9 的地基）
# --------------------------------------------------------------------------

class TestSignals:
    def test_hits_plain_reference_words(self):
        assert "这个" in sg.detect_references("这个怎么办")
        assert "上次" in sg.detect_references("上次那个方案呢")

    def test_single_char_does_not_break_common_words(self):
        """修#6：裸单字不再触发误伤（『因此 / 应该 / 这些词本身』不算指代）。"""
        assert sg.detect_references("因此我们应该先备份") == []
        assert sg.detect_references("其实我们应该早点动手") == []

    def test_single_char_reference_needs_noun(self):
        """『此方案 / 该条』这类才认。"""
        assert "此方案" in sg.detect_references("此方案可行")
        assert sg.detect_references("此可行") == []

    def test_known_imperfection_single_char_after_other(self):
        """已知微瑕 #13（登记备查，本次不改逻辑）：『其它方案』会被认成「它+方案」。

        影响面：仅在**无上文**时把自足句降到 frail 兜底档，功能不破。
        改正则要加负向断言，属姐姐拍板项，故此处只固化现状。
        """
        assert sg.detect_references("其它方案都可以") == ["它方案"]

    def test_present_marker(self):
        assert sg.detect_present_marker("今天好累呀") == "今天"
        assert sg.detect_present_marker("刚才说的那个") == "刚才"
        assert sg.detect_present_marker("明天再说明天") is None


# --------------------------------------------------------------------------
# 三、三档裁决（核心）
# --------------------------------------------------------------------------

class TestArbitrate:
    RECENT = ["妹妹帮我看下电磁感应", "嗯，先画受力分析"]

    def test_empty_message_is_frail(self):
        assert sg.arbitrate("", self.RECENT).tier == "frail"
        assert sg.arbitrate("。。。", self.RECENT).tier == "frail"

    def test_self_contained(self):
        v = sg.arbitrate("姐姐帮我讲讲电磁感应", self.RECENT)
        assert v.tier == "self_contained"
        assert v.retrieval_tier == "light"
        assert v.need_retrieval is False

    def test_needs_context_when_reference_with_context(self):
        v = sg.arbitrate("那个再讲一遍", self.RECENT)
        assert v.tier == "needs_context"
        assert v.retrieval_tier == "normal"
        assert v.references

    def test_frail_when_reference_without_context(self):
        v = sg.arbitrate("那个再讲一遍", [])
        assert v.tier == "frail"
        assert v.retrieval_tier == "last_resort"
        assert "无上文" in v.reason

    def test_lone_branch_still_self_consistent(self):
        """专线在接线层拦走，但 arbitrate 单独调用时仍要自洽。"""
        assert sg.arbitrate("妹妹", self.RECENT).tier == "needs_context"
        assert sg.arbitrate("妹妹", []).tier == "frail"

    def test_verdict_to_dict_roundtrip(self):
        d = sg.arbitrate("那个再讲一遍", self.RECENT).to_dict()
        assert d["tier"] == "needs_context" and d["retrieval_tier"] == "normal"


# --------------------------------------------------------------------------
# 四、检索策略
# --------------------------------------------------------------------------

class TestPolicy:
    def test_light_is_half_dose(self):
        p = sg.policy_for(sg.Verdict("self_contained"), base_top_k=10, base_threshold=0.3)
        assert p.top_k == 5 and p.min_score == 0.3
        assert p.max_age_days is None
        assert p.soft_confirm_on_miss is False  # 修#8：这个字段必须被真的读

    def test_normal_keeps_base(self):
        p = sg.policy_for(sg.Verdict("needs_context"), base_top_k=10, base_threshold=0.3)
        assert p.top_k == 10 and p.max_age_days is None and p.soft_confirm_on_miss is False

    def test_last_resort_raises_threshold_and_limits_age(self):
        p = sg.policy_for(sg.Verdict("frail"), base_top_k=10, base_threshold=0.3)
        assert p.min_score >= 0.35
        assert p.max_age_days == 3.0
        assert p.soft_confirm_on_miss is True

    def test_top_k_never_below_three_in_light(self):
        p = sg.policy_for(sg.Verdict("self_contained"), base_top_k=4)
        assert p.top_k == 3

    def test_build_retrieval_query_orders(self):
        recent = ["一", "二", "三", "四"]
        q = sg.build_retrieval_query(sg.Verdict("needs_context"), "现在这句", recent, 4)
        assert q == "一 二 三 四 现在这句"
        q2 = sg.build_retrieval_query(sg.Verdict("self_contained"), "现在这句", recent, 4)
        assert q2 == "四 现在这句"


# --------------------------------------------------------------------------
# 五、时间校准（修#3 / #4 / #5 / #9）
# --------------------------------------------------------------------------

class TestTimeCalibration:
    def test_gap_phrase_buckets(self):
        """口径提醒：`now` 是**北京时间**，`last_ts` 是**容器本地时钟**（函数内部会换算）。

        生产路径 `time_anchor_line()` 正是这么喂的，所以测试也照这个口径喂。
        """
        now = sg.now_cst()
        local = datetime.now()          # 容器本地，等价于「刚刚」
        assert "刚刚" in sg.gap_phrase(local - timedelta(seconds=30), now)
        assert "分钟前" in sg.gap_phrase(local - timedelta(minutes=10), now)
        assert "小时前" in sg.gap_phrase(local - timedelta(hours=5), now)
        assert "天前" in sg.gap_phrase(local - timedelta(days=3), now)
        assert "未知" in sg.gap_phrase(None, now)

    def test_time_anchor_line_has_gap_and_weekday(self):
        line = sg.time_anchor_line(datetime(2026, 10, 6, 2, 0, 0))
        assert line.startswith("[时间锚]")
        assert "距上次对话" in line
        assert "北京时间" in line and "周" in line

    def test_entry_age_days_unknown_returns_none(self):
        """修#4：没时间戳不许猜成今天。"""
        assert sg.entry_age_days(SimpleNamespace()) is None
        assert sg.entry_age_days(SimpleNamespace(timestamp="不是时间")) is None
        assert sg.entry_age_days(None) is None

    def test_entry_age_days_normal(self):
        age = sg.entry_age_days(_mem(2))
        assert 1.9 < age < 2.1

    def test_time_decay_monotonic(self):
        assert sg.time_decay(0.5) == 1.0
        assert sg.time_decay(5) == 0.85
        assert sg.time_decay(None) == 0.8
        assert sg.time_decay(99999) == 0.4

    def test_rerank_by_time_promotes_fresh_memory(self):
        old = _mem(400, score=0.80)
        fresh = _mem(0.2, score=0.60)
        ranked = sg.rerank_by_time([old, fresh])
        assert ranked[0] is fresh  # 0.60×1.0 > 0.80×0.45

    def test_rerank_keeps_original_order_on_tie(self):
        a, b = _mem(0.2, 0.5), _mem(0.2, 0.5)
        assert sg.rerank_by_time([a, b]) == [a, b]

    def test_conflict_warn_fires_when_all_stale(self):
        """修#3：判据是 min(known)，全部旧账才告警。"""
        v = sg.arbitrate("今天那道题", ["上文"], )
        warn = sg.time_conflict_warn([_mem(30), _mem(60)], v)
        assert "时间校准" in warn and "今天" in warn

    def test_conflict_warn_silent_when_something_recent(self):
        v = sg.arbitrate("今天那道题", ["上文"])
        assert sg.time_conflict_warn([_mem(30), _mem(0.5)], v) == ""

    def test_conflict_warn_silent_without_present_marker(self):
        """修#9：姐姐没提『今天/刚才』，就不许自己加戏。"""
        v = sg.arbitrate("那道题", ["上文"])
        assert v.present_marker is None
        assert sg.time_conflict_warn([_mem(30)], v) == ""

    def test_conflict_warn_silent_when_no_results(self):
        v = sg.arbitrate("今天那道题", ["上文"])
        assert sg.time_conflict_warn([], v) == ""


# --------------------------------------------------------------------------
# 六、兜底软确认（修#8）
# --------------------------------------------------------------------------

class TestSoftConfirm:
    def test_soft_confirm_only_on_frail_miss(self):
        frail = sg.arbitrate("那个", [])
        assert sg.frail_miss_soft_confirm(frail, 0) != ""
        assert sg.frail_miss_soft_confirm(frail, 1) == ""
        assert sg.frail_miss_soft_confirm(sg.arbitrate("姐姐帮我讲讲电磁感应", []), 0) == ""

    def test_soft_confirm_text_forbids_guessing(self):
        txt = sg.frail_miss_soft_confirm(sg.arbitrate("那个", []), 0)
        assert "不硬猜" in txt and "不要翻旧账" in txt


# --------------------------------------------------------------------------
# 七、孤词专线（v3.3 · 改动清单 F）
# --------------------------------------------------------------------------

class TestLoneThread:
    RECENT = ["第一轮话", "第二轮话", "第三轮话", "第四轮话", "第五轮话"]

    def test_notice_has_both_branches(self):
        a = sg.lone_thread_notice(True)
        b = sg.lone_thread_notice(False)
        assert a != b
        assert "【近期对话记录】" in a  # 修#5：锚点标题与线上 L1 块一致
        assert "新对话" in b and "新对话" in a

    def test_resolve_lone_window_default_is_four(self):
        assert sg.resolve_lone_window(None) == 4
        assert sg.resolve_lone_window("坏值") == 4

    def test_resolve_lone_window_clamps(self):
        """F 的核心：姐姐把窗口拧到 6，孤词这边也只认 4。"""
        assert sg.resolve_lone_window(6) == 4
        assert sg.resolve_lone_window(1) == 2
        assert sg.resolve_lone_window(3) == 3

    def test_lone_window_recent_takes_tail(self):
        assert sg.lone_window_recent(self.RECENT, 2) == ["第四轮话", "第五轮话"]
        assert sg.lone_window_recent(self.RECENT, 4) == [
            "第二轮话", "第三轮话", "第四轮话", "第五轮话",
        ]

    def test_lone_window_recent_drops_blank(self):
        assert sg.lone_window_recent(["", "   ", "真话"], 4) == ["真话"]

    def test_lone_window_decoupled_from_retrieval_turns(self):
        """检索词用 6 轮，孤词窗口仍是 4 —— 两件事不许再串。"""
        all_recent = [f"第{i}轮话" for i in range(1, 7)]
        retrieval_query = sg.build_retrieval_query(
            sg.Verdict("needs_context"), "现在", all_recent, 6
        )
        assert len(retrieval_query.split()) == 7           # 6 轮 + 当前句
        assert sg.lone_window_recent(all_recent, sg.resolve_lone_window(None)) == [
            "第3轮话", "第4轮话", "第5轮话", "第6轮话",
        ]                                                  # 只有 4 轮

    def test_lone_thread_payload_returns_all_three(self):
        notice, has_thread, used = sg.lone_thread_payload(self.RECENT, 4)
        assert has_thread is True
        assert len(used) == 4
        assert "极短孤词" in notice
        notice2, has_thread2, used2 = sg.lone_thread_payload([], 4)
        assert has_thread2 is False and used2 == []
        assert "极短孤词" in notice2


# --------------------------------------------------------------------------
# 八、决策日志护栏（改动清单 C）
# --------------------------------------------------------------------------

class TestDecisionLog:
    def test_make_record_shape_and_clip(self):
        rec = dl.make_record(
            tier="frail", reason="指代无上文：" + "长" * 400, query="那个",
            top_k=10, hits=0, route="last_resort", soft_confirm=True, window=4,
        )
        assert rec["tier"] == "frail" and rec["route"] == "last_resort"
        assert rec["soft_confirm"] is True and rec["window"] == "4"
        assert len(rec["reason"]) <= dl.MAX_FIELD_CHARS + 1   # 截断留一个省略号

    def test_write_appends_jsonl(self, tmp_path):
        for i in range(3):
            p = dl.write_decision(dl.make_record(tier="lone", hits=i), tmp_path)
        assert p is not None and p.name.endswith(".jsonl")
        lines = p.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        assert json.loads(lines[0])["tier"] == "lone"

    def test_no_data_dir_means_no_write(self):
        assert dl.write_decision(dl.make_record(tier="lone"), None) is None
        assert dl.write_decision({}, "/tmp") is None

    def test_rotation_happens_only_once(self, tmp_path):
        """超 5MB 滚一次；当天再超就放弃写（宁可丢日志）。"""
        assert dl.write_decision(dl.make_record(tier="a"), tmp_path, max_bytes=1) is not None
        assert dl.write_decision(dl.make_record(tier="b"), tmp_path, max_bytes=1) is not None
        rolled = list(tmp_path.glob("decision_log/*.1.jsonl"))
        assert len(rolled) == 1
        assert dl.write_decision(dl.make_record(tier="c"), tmp_path, max_bytes=1) is None

    def test_prune_old_files(self, tmp_path):
        d = dl.log_dir(tmp_path)
        old = d / "20260101.jsonl"
        old.write_text("{}", encoding="utf-8")
        stale = (datetime.now() - timedelta(days=30)).timestamp()
        os.utime(old, (stale, stale))
        dl.write_decision(dl.make_record(tier="lone"), tmp_path)
        assert not old.exists()

    def test_prune_overflow_files(self, tmp_path):
        d = dl.log_dir(tmp_path)
        for i in range(12):
            f = d / f"202601{i:02d}.jsonl"
            f.write_text("{}", encoding="utf-8")
        dl.write_decision(dl.make_record(tier="lone"), tmp_path)
        assert len(list(d.glob("*.jsonl"))) <= dl.MAX_FILES

    def test_should_log_defaults_off(self):
        assert dl.should_log({}) is False
        assert dl.should_log(None) is False

    def test_should_log_needs_master_gate(self):
        """口径收紧（姐姐复核四.4）：日志两道门都要开——总闸关时一个字节都不写。

        旧口径「只要 decision_log_enable 开就写」已被推翻：
        总闸关＝回退到 v1，v1 是不写盘的，所以日志也必须闭嘴。
        """
        assert dl.should_log({dl.ENABLE_KEY: True}) is False
        assert dl.should_log({dl.ENABLE_KEY: True, dl.GATE_KEY: True}) is True
        assert dl.should_log({dl.GATE_KEY: True}) is False
