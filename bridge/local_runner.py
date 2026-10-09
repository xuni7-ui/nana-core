#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
local_runner.py — 「本地编码 Runner」：用**已配置的 OpenAI 兼容端点**驱动一个模型改代码
=========================================================================================
用途：作为 `codex_bridge` 的一种 Runner 实现，让协作桥在**不安装任何新依赖**的前提下
具备真实的编码能力（复用环境里已装的 `openai` SDK 与已在用的模型端点）。

与 CodexRunner 的关系（两者可互换，桥不关心）
---------------------------------------------
| Runner        | 依赖           | 需要新授权 | 说明 |
|---------------|----------------|-----------|------|
| StubRunner    | 无             | 否        | 离线确定性，测试用 |
| LocalLLMRunner| openai SDK（已装）| **是（出网）** | 本文件；端点由调用方注入 |
| CodexRunner   | codex 二进制   | **是（安装+凭据）** | 未安装 |

安全纪律
--------
1. `client=None` → **明确报错**，绝不偷偷联网。
2. 只把 `allow_paths` 内的文本文件喂给模型；**硬黑名单内容永不进入提示词**。
3. 模型返回的每个编辑路径都要过白名单/黑名单校验，**越界即整体拒绝**（不写盘）。
4. 单文件与上下文有体积上限；不处理二进制。
5. 只写 scratch 工作目录内的相对路径；拒绝绝对路径与 `..`。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from codex_bridge import HARD_DENY, RunnerResult, TaskSpec, _matches

_BASE_URL_ENV = "NANA_BRIDGE_BASE_URL"
_API_KEY_ENV = "NANA_BRIDGE_API_KEY"
_MODEL_ENV = "NANA_BRIDGE_MODEL"

SYSTEM_PROMPT = (
    "你是一个严谨的工程编码助手。你的输出必须是**一个 JSON 对象**，不得包含任何解释性文字或代码围栏。\n"
    "格式：{\"edits\":[{\"path\":\"相对路径\",\"content\":\"该文件修改后的完整内容\"}],\"notes\":\"一句话说明\"}\n"
    "规则：\n"
    "1. 只允许修改被列出的、允许改动的文件；不要新增无关文件。\n"
    "2. content 必须是**整份文件**的新内容，不是 diff。\n"
    "3. 改动最小化；不确定时不要改。\n"
    "4. 无法完成时，输出 {\"edits\":[],\"notes\":\"原因\"}。\n"
)


@dataclass
class Edit:
    path: str
    content: str


def parse_edits(text: str) -> Tuple[List[Edit], str]:
    """从模型回复中解析 edits。失败返回 ([], 原因)。"""
    if not isinstance(text, str) or not text.strip():
        return [], "模型回复为空"
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j <= i:
        return [], "回复中找不到 JSON 对象"
    try:
        obj = json.loads(s[i:j + 1])
    except Exception as e:
        return [], "JSON 解析失败：%s" % e
    if not isinstance(obj, dict) or not isinstance(obj.get("edits"), list):
        return [], "缺少 edits 数组"
    out: List[Edit] = []
    for e in obj["edits"]:
        if not isinstance(e, dict):
            return [], "edits 项不是对象"
        p, c = e.get("path"), e.get("content")
        if not isinstance(p, str) or not isinstance(c, str):
            return [], "edits 项缺 path/content 或类型错误"
        out.append(Edit(p, c))
    return out, ""


class LocalLLMRunner:
    """用 OpenAI 兼容端点做编码的 Runner。`client` 必须由调用方注入（避免隐式联网）。"""

    name = "local_llm"

    def __init__(self, client: Any = None, model: str = "",
                 *, max_files: int = 8, max_file_bytes: int = 40000,
                 max_total_bytes: int = 120000, temperature: int = 0,
                 max_calls: int = 1):
        self.client = client
        self.model = model or os.environ.get(_MODEL_ENV, "deepseek-flash")
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.temperature = temperature
        self.max_calls = max(1, int(max_calls))   # 费用闸门：单任务最多几次模型请求
        self.calls = 0                            # 实际已发起的请求数（真实计费证据）
        self.last_usage: Optional[Dict[str, Any]] = None
        self.last_prompt: str = ""          # 供测试断言"敏感内容未外泄"

    # ---------- 上下文采集（严格过滤） ----------
    def collect_context(self, workdir: str, spec: TaskSpec) -> List[Edit]:
        picked: List[Edit] = []
        total = 0
        for base, dirs, files in os.walk(workdir):
            dirs[:] = [d for d in dirs if d != ".git"]
            for fn in sorted(files):
                p = os.path.join(base, fn)
                rel = os.path.relpath(p, workdir).replace(os.sep, "/")
                if _matches(rel, HARD_DENY) or _matches(rel, spec.deny_paths or []):
                    continue                                  # 敏感/禁用 → 永不外发
                if not _matches(rel, spec.allow_paths or []):
                    continue
                try:
                    if os.path.getsize(p) > self.max_file_bytes:
                        continue
                    with open(p, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue                                  # 二进制/读不了 → 跳过
                if "\x00" in content[:1024]:
                    continue
                if total + len(content) > self.max_total_bytes:
                    break
                total += len(content)
                picked.append(Edit(rel, content))
                if len(picked) >= self.max_files:
                    return picked
        return picked

    # ---------- 校验模型给的编辑 ----------
    def validate_edits(self, edits: Sequence[Edit], spec: TaskSpec) -> List[str]:
        problems: List[str] = []
        for e in edits:
            p = e.path.replace(os.sep, "/")
            if p.startswith("/") or ".." in p.split("/"):
                problems.append("非法路径：%s" % e.path)
                continue
            if _matches(p, HARD_DENY) or _matches(p, spec.deny_paths or []):
                problems.append("命中硬黑名单：%s" % e.path)
                continue
            if not _matches(p, spec.allow_paths or []):
                problems.append("超出白名单：%s" % e.path)
        return problems

    # ---------- 主入口 ----------
    def run(self, spec: TaskSpec, workdir: str, prompt: str) -> RunnerResult:
        if self.client is None:
            return RunnerResult(ok=False, reason="未注入模型客户端（离线模式，未发起任何请求）")
        if self.calls >= self.max_calls:
            return RunnerResult(ok=False, reason="已触及单任务请求上限（%d 次），拒绝继续外发" % self.max_calls)

        ctx = self.collect_context(workdir, spec)
        files_block = "\n\n".join(
            "### FILE: %s\n```\n%s\n```" % (e.path, e.content) for e in ctx) or "(无可用文件)"
        user = ("%s\n\n## 允许改动的路径\n%s\n\n## 当前文件内容\n%s"
                % (prompt, ", ".join(spec.allow_paths or []), files_block))
        self.last_prompt = user

        try:
            self.calls += 1                   # 计入真实外发次数（在请求前自增，异常也计）
            resp = self.client.chat.completions.create(
                model=self.model, temperature=self.temperature,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user}])
            text = resp.choices[0].message.content or ""
            u = getattr(resp, "usage", None)
            self.last_usage = ({"prompt_tokens": getattr(u, "prompt_tokens", None),
                                "completion_tokens": getattr(u, "completion_tokens", None),
                                "total_tokens": getattr(u, "total_tokens", None)}
                               if u is not None else None)
        except Exception as e:
            return RunnerResult(ok=False, reason="模型调用失败：%s: %s" % (type(e).__name__, e))

        edits, why = parse_edits(text)
        if why:
            return RunnerResult(ok=False, reason="模型输出不合规：%s" % why,
                                stdout=text[:1500], stderr="")
        problems = self.validate_edits(edits, spec)
        if problems:
            return RunnerResult(ok=False, reason="模型编辑越界，已整体拒绝：%s" % "；".join(problems),
                                stdout=text[:1500], stderr="")

        written = []
        for e in edits:
            dst = os.path.join(workdir, e.path)
            os.makedirs(os.path.dirname(dst) or workdir, exist_ok=True)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(e.content)
            written.append(e.path)
        return RunnerResult(ok=True, stdout="已写入：%s" % ", ".join(written),
                            stderr="", exit_code=0)


def from_env() -> Optional[LocalLLMRunner]:
    """按环境变量构造 Runner；缺任一变量 → None（**不联网**）。

    可调闸门：`NANA_BRIDGE_MAX_CALLS`（默认 1）、`NANA_BRIDGE_MAX_FILES`（默认 8）、
    `NANA_BRIDGE_MAX_BYTES`（默认 120000）。
    """
    base = (os.environ.get(_BASE_URL_ENV) or "").strip()
    key = (os.environ.get(_API_KEY_ENV) or "").strip()
    if not base or not key:
        return None
    try:
        import openai
        return LocalLLMRunner(
            openai.OpenAI(api_key=key, base_url=base),
            max_calls=int(os.environ.get("NANA_BRIDGE_MAX_CALLS", "1") or 1),
            max_files=int(os.environ.get("NANA_BRIDGE_MAX_FILES", "8") or 8),
            max_total_bytes=int(os.environ.get("NANA_BRIDGE_MAX_BYTES", "120000") or 120000),
        )
    except Exception:
        return None

