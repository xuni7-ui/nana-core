"""总闸关 = 与三道闸 v1 逐字节一致：负向回归（防复发）。

覆盖复核报告点名的两条「隐性差异」：

1. **修#11·乙**：软确认文案算不算「有记忆」——
   - 总闸开：用真检索结果判（`l2_results`）→ 软确认文案 **不再** 触发稀薄告警
   - 总闸关：用 v1 判据（`l2_text` 非空即算有记忆）→ 与 v1 同
2. **裁决日志**：总闸关时一个字节都不写（即便 `decision_log_enable` 是开的）。
3. **孤词专线**：必须挂在总闸下（`if sg_enable and lone_v1:`），不许裸早退。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from iris_memory.core import decision_log as dl
from iris_memory.core.llm_request_hook import preprocess_llm_request

_SOFT_CONFIRM_TEXT = (
    "## 相关记忆\n（本轮姐姐只发来一个极短孤词/唤醒词，且没有可用上文。"
    "已按纪律跳过向量检索。）"
)

_GET_CONFIG = "iris_memory.config.get_config"
_COLLECT_L1 = "iris_memory.core.llm_request_hook._collect_l1_context"
_COLLECT_PROFILE = "iris_memory.core.llm_request_hook._collect_user_profile"
_COLLECT_L2 = "iris_memory.core.llm_request_hook._collect_l2_memory"
_COLLECT_L3 = "iris_memory.core.llm_request_hook._collect_l3_knowledge_graph"
_PARSE_IMAGES = "iris_memory.core.llm_request_hook._parse_images_if_related_mode"
_LOG_FINAL = "iris_memory.core.llm_request_hook._log_final_context"
_GET_ADAPTER = "iris_memory.platform.get_adapter"

WARN_MARK = "上下文稀薄告警"


def _cfg(gate: bool, log: bool = False, threshold: int = 6) -> MagicMock:
    """最小可用的配置替身：只认这几把旋钮。"""
    values = {
        "l2_memory.semantic_gate_enable": gate,
        "l2_memory.semantic_gate_time_calibration": True,
        "l2_memory.decision_log_enable": log,
        "l1_buffer.thin_context_warn_enable": True,
        "l1_buffer.thin_context_warn_threshold": threshold,
        "l1_buffer.inject_queue_length": 50,
        "l1_inject_max_content_chars": 200,
    }
    cfg = MagicMock()
    cfg.get.side_effect = lambda key, default=None: values.get(key, default)
    cfg.data_dir = None
    return cfg


def _text_of(req) -> str:
    parts = getattr(req, "extra_user_content_parts", []) or []
    return "\n".join(getattr(p, "text", "") or str(p) for p in parts)


async def _run_preprocess(
    gate: bool,
    l2_text: str,
    l2_results,
    l3_text: str,
    l1_text: str = "L1 稀薄上下文",
    l1_count: int = 1,
):
    """跑一遍完整 preprocess：L1 稀薄，L2/L3 给指定产物。"""
    req = MagicMock()
    req.extra_user_content_parts = []
    req.system_prompt = "system"
    req._l1_context_count = l1_count
    event = MagicMock()
    event.message_str = "妹妹"
    event.get_message_str = lambda: "妹妹"
    cm = MagicMock()

    with (
        patch(_GET_CONFIG, return_value=_cfg(gate=gate)),
        patch(_GET_ADAPTER, return_value=MagicMock()),
        patch(_COLLECT_L1, new_callable=AsyncMock, return_value=l1_text),
        patch(_COLLECT_PROFILE, new_callable=AsyncMock, return_value=""),
        patch(_COLLECT_L2, new_callable=AsyncMock, return_value=(l2_text, l2_results)),
        patch(_COLLECT_L3, new_callable=AsyncMock, return_value=l3_text),
        patch(_PARSE_IMAGES, new_callable=AsyncMock, return_value=None),
        patch(_LOG_FINAL),
    ):
        await preprocess_llm_request(event, req, cm)
    return _text_of(req)


class TestThinWarnGate11:
    """修#11 的甲/乙口径：只有开闸才换判据。"""

    @pytest.mark.asyncio
    async def test_gate_off_soft_confirm_counts_as_memory(self):
        """总闸关：软确认文案＝v1 眼里的「有记忆」→ 告警照开（与 v1 一致）。"""
        text = await _run_preprocess(
            gate=False, l2_text=_SOFT_CONFIRM_TEXT, l2_results=[], l3_text="",
            l1_text="",
        )
        assert WARN_MARK in text

    @pytest.mark.asyncio
    async def test_gate_on_soft_confirm_is_not_memory(self):
        """总闸开：软确认文案不算记忆 → 没有可误用的东西 → 告警闭嘴（修#11）。"""
        text = await _run_preprocess(
            gate=True, l2_text=_SOFT_CONFIRM_TEXT, l2_results=[], l3_text="",
            l1_text="",
        )
        assert WARN_MARK not in text

    @pytest.mark.asyncio
    async def test_gate_on_real_hits_keep_warn_awake(self):
        """总闸开：真有命中 → 有东西可误用 → 告警开口。"""
        text = await _run_preprocess(
            gate=True, l2_text="## 相关记忆\n（命中）", l2_results=[object()],
            l3_text="",
        )
        assert WARN_MARK in text

    @pytest.mark.asyncio
    async def test_gate_on_l3_alone_keeps_warn_awake(self):
        """总闸开：只有 L3 图谱 → 也算「有记忆」。"""
        text = await _run_preprocess(
            gate=True, l2_text=_SOFT_CONFIRM_TEXT, l2_results=[],
            l3_text="<iris:l3_kg>奈奈：…</iris:l3_kg>", l1_text="",
        )
        assert WARN_MARK in text

    @pytest.mark.asyncio
    async def test_both_empty_arms_stay_silent(self):
        """两边都没东西可误用 → 告警保持沉默（设计如此）。"""
        text = await _run_preprocess(
            gate=False, l2_text="", l2_results=[], l3_text="", l1_text=""
        )
        assert WARN_MARK not in text

    @pytest.mark.asyncio
    async def test_thick_l1_never_warns(self):
        """L1 够厚 → 不管有没有记忆都不报警。"""
        text = await _run_preprocess(
            gate=True, l2_text="", l2_results=[], l3_text="",
            l1_text="L1 很厚", l1_count=9,
        )
        assert WARN_MARK not in text


class TestDecisionLogGate:
    """裁决日志：只在总闸开时落盘。"""

    def test_gate_off_blocks_log_even_when_enabled(self):
        assert dl.should_log(_cfg(gate=False, log=True)) is False

    def test_gate_on_and_log_on_allows(self):
        assert dl.should_log(_cfg(gate=True, log=True)) is True

    def test_gate_on_but_log_off_blocks(self):
        assert dl.should_log(_cfg(gate=True, log=False)) is False

    def test_broken_config_means_no_write(self):
        class Boom:
            def get(self, *a, **k):
                raise RuntimeError("配置炸了")

        assert dl.should_log(Boom()) is False

    def test_gate_key_is_the_master_switch(self):
        assert dl.GATE_KEY == "l2_memory.semantic_gate_enable"


class TestLoneLineIsUnderMasterGate:
    """孤词专线必须挂在总闸下（复核第一条：防「总闸关还偷偷早退」）。"""

    def test_lone_line_reads_master_gate(self):
        import inspect

        from iris_memory.core import llm_request_hook as hook

        src = inspect.getsource(hook._collect_l2_memory)
        assert "if sg_enable and lone_v1:" in src

    def test_no_bare_lone_early_return(self):
        import inspect

        from iris_memory.core import llm_request_hook as hook

        src = inspect.getsource(hook._collect_l2_memory)
        # v1 回退分支里的「孤词 + 无上文」软确认是允许的（那是 v1 行为）
        assert "if lone_v1 and not recent:" in src
        # 但不许出现「不受总闸管辖」的裸早退
        assert "\n    if lone_v1:\n" not in src.replace("        ", "    ")
