"""奈奈收束锚点插件
维护对话/排查的根目标锚点，防止自由联想发散跑题。

命令（姐姐在消息里写即可）：
  - 设锚：XXX  /  锚点=XXX  /  记锚 XXX        -> 设置/更新当前根目标
  - 收束 / 拉回 / 回到正题 / 别跑题 / 跑偏了  -> 触发一次强收束提醒
  - 清锚 / 结束锚点 / 清除锚点                -> 清除当前根目标
"""
import os
import re
import time
import json

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, StarTools
from astrbot.api.provider import ProviderRequest
from astrbot.api import logger, AstrBotConfig


class NanaAnchor(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        data_dir = StarTools.get_data_dir()
        self.state_file = os.path.join(str(data_dir), "nana_anchor_state.json")
        self.state = self._load_state()

    # ---------- 状态读写 ----------
    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[NanaAnchor] 状态加载失败: {e}")
        return {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[NanaAnchor] 状态保存失败: {e}")

    def _get_sid(self, event: AstrMessageEvent) -> str:
        try:
            return event.get_session_id() or "default"
        except Exception:
            return "default"

    @staticmethod
    def _clean_text(text):
        # 洗掉 [At:xxx] 等平台噪声
        return re.sub(r"\[At:[^\]]*\]\s*", "", text or "").strip()

    def _parse_command(self, text: str):
        """返回 (cmd, anchor)。cmd in {set, pull, clear, None}"""
        m = re.search(r"(?:设锚|记锚|锚点)\s*[:：=]\s*(.+)", text)
        if m:
            return "set", m.group(1).strip()
        m = re.search(r"(?:我们的目标|根目标|要解决的根本问题)\s*[是：:]\s*(.+)", text)
        if m:
            return "set", m.group(1).strip()
        if re.search(r"(收束|拉回|回到正题|别跑题|跑偏了|拉回来)", text):
            return "pull", ""
        if re.search(r"(清锚|结束锚点|清除锚点|取消锚点)", text):
            return "clear", ""
        return None, ""

    # ---------- 命令处理 ----------
    @filter.on_waiting_llm_request(priority=200)
    async def on_command(self, event: AstrMessageEvent):
        if not self.config.get("enabled", True):
            return
        text = self._clean_text(event.message_str)
        if not text:
            return
        cmd, anchor = self._parse_command(text)
        if cmd is None:
            return
        sid = self._get_sid(event)
        entry = self.state.setdefault(sid, {"anchor": "", "updated_at": 0})
        if cmd == "set" and anchor:
            max_len = int(self.config.get("max_anchor_len", 200))
            entry["anchor"] = anchor[:max_len]
            entry["updated_at"] = time.time()
            self._save_state()
            logger.debug(f"[NanaAnchor] 设置锚点: {anchor[:max_len]}")
        elif cmd == "clear":
            entry["anchor"] = ""
            self._save_state()
            logger.debug("[NanaAnchor] 清除锚点")

    # ---------- 锚点注入 ----------
    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        if not self.config.get("enabled", True):
            return
        sid = self._get_sid(event)
        entry = self.state.get(sid)
        anchor = (entry or {}).get("anchor", "")
        if not anchor:
            return
        text = self._clean_text(event.message_str)
        pulled = bool(re.search(r"(收束|拉回|回到正题|别跑题|跑偏了|拉回来)", text))
        if pulled:
            block = (
                "\n\n【收束指令·最高优先】"
                "姐姐刚提醒我们跑偏了，请立刻停止当前发散。"
                f"本次要解决的根目标是：{anchor}。"
                "请用一句话确认已收束，然后只围绕这个根目标继续，不要延伸新话题。"
            )
        else:
            block = (
                "\n\n【收束锚点】"
                f"本次要解决的根目标是：{anchor}。"
                "奈奈请时刻锚定它：先紧扣根目标回答，再谈延伸；"
                "一旦发现话题越走越远，主动拉回并提醒姐姐。"
            )
        req.system_prompt = (req.system_prompt or "") + block
