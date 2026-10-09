#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_local_runner.py — 本地编码 Runner · 全离线测试（T1–T9）

运行：python3 test_local_runner.py
关键点：**T4 用本机 127.0.0.1 的假 OpenAI 端点**打真实 HTTP 链路 —— 全程不出公网。
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import codex_bridge as B          # noqa: E402
import local_runner as L          # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("✅" if cond else "❌", name, ("  — " + str(detail)) if not cond else ""))


def git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def make_repo(path):
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    git(["init", "--quiet"], path)
    git(["config", "user.email", "n@l"], path)
    git(["config", "user.name", "n"], path)
    with open(os.path.join(path, "calc.py"), "w", encoding="utf-8") as fh:
        fh.write("def add(a, b):\n    return a - b\n")
    with open(os.path.join(path, ".env"), "w", encoding="utf-8") as fh:
        fh.write("TOPSECRET_LEAK_CANARY=1\n")
    with open(os.path.join(path, "secret_key.txt"), "w", encoding="utf-8") as fh:
        fh.write("TOPSECRET_LEAK_CANARY=2\n")
    git(["add", "-A"], path)
    git(["commit", "-qm", "init"], path)
    return path


# ---------- 假客户端 ----------
class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Usage:
    prompt_tokens = 11
    completion_tokens = 22
    total_tokens = 33


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class _Completions:
    def __init__(self, outer):
        self.outer = outer

    def create(self, **kw):
        self.outer.calls.append(kw)
        return _Resp(self.outer.payload)


class _FakeChat:
    def __init__(self, outer):
        self.completions = _Completions(outer)


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.chat = _FakeChat(self)


def good_payload():
    return json.dumps({"edits": [{"path": "calc.py",
                                  "content": "def add(a, b):\n    return a + b\n"}],
                       "notes": "把减法改成加法"}, ensure_ascii=False)


# ---------- 本机假端点 ----------
class _Handler(BaseHTTPRequestHandler):
    payload = good_payload()

    def do_POST(self):                                   # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        body = json.dumps({
            "id": "chatcmpl-local", "object": "chat.completion", "model": "fake",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": _Handler.payload}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):                           # 静音
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main() -> int:
    root = os.path.join(HERE, "scratch", "_test_local")
    repo = make_repo(os.path.join(root, "src_repo"))
    TESTC = "python3 -c \"import calc,sys; sys.exit(0 if calc.add(2,3)==5 else 1)\""

    # T1 假客户端 → 正常闭环
    fc = FakeClient(good_payload())
    spec = B.TaskSpec(task_id="lt1", goal="修复 add", repo=repo, allow_paths=["*.py"],
                      test_command=TESTC)
    r1 = B.execute_task(spec, L.LocalLLMRunner(fc))
    check("T1 本地 Runner 正常闭环（applied + 验收通过）",
          r1.ok and r1.applied and r1.test_ok is True and r1.changed_files == ["calc.py"],
          json.dumps(r1.to_dict(), ensure_ascii=False)[:300])

    # T2 敏感文件内容绝不进入提示词
    prompt = fc.calls[0]["messages"][1]["content"] if fc.calls else ""
    check("T2 提示词不含 .env / 密钥文件内容",
          "TOPSECRET_LEAK_CANARY" not in prompt and "secret_key.txt" not in prompt,
          prompt[:200])

    # T3 模型输出垃圾 → 明确失败
    r3 = B.execute_task(B.TaskSpec(task_id="lt3", goal="垃圾输出", repo=repo,
                                   allow_paths=["*.py"]),
                        L.LocalLLMRunner(FakeClient("我觉得这个代码还行。")))
    check("T3 非 JSON 输出被拒绝", (not r3.ok) and (not r3.applied), r3.reason)

    # T4 模型尝试越界写盘 → 整体拒绝
    bad = json.dumps({"edits": [{"path": "docs/hack.md", "content": "x"}], "notes": ""})
    r4 = B.execute_task(B.TaskSpec(task_id="lt4", goal="越界", repo=repo,
                                   allow_paths=["*.py"]),
                        L.LocalLLMRunner(FakeClient(bad)))
    check("T4 越界编辑被整体拒绝", (not r4.ok) and (not r4.applied), r4.reason)

    # T5 真实 HTTP 链路（本机假端点）
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        import openai
        client = openai.OpenAI(api_key="local-test", base_url="http://127.0.0.1:%d/v1" % port)
        spec5 = B.TaskSpec(task_id="lt5", goal="修复 add（真实 HTTP）", repo=repo,
                           allow_paths=["*.py"], test_command=TESTC)
        r5 = B.execute_task(spec5, L.LocalLLMRunner(client, model="fake-local"))
        check("T5 经真实 HTTP（127.0.0.1）闭环成功",
              r5.ok and r5.applied and r5.test_ok is True,
              json.dumps(r5.to_dict(), ensure_ascii=False)[:300])
    except Exception as e:
        check("T5 经真实 HTTP（127.0.0.1）闭环成功", False, "%s: %s" % (type(e).__name__, e))
    finally:
        srv.shutdown()

    # T6 from_env 无配置 → None（不隐式联网）
    saved = {k: os.environ.pop(k, None) for k in
             ("NANA_BRIDGE_BASE_URL", "NANA_BRIDGE_API_KEY")}
    check("T6 未配置环境变量时 from_env() 返回 None", L.from_env() is None)
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v

    # T7 CLI 子进程 + 本机假端点：回归「脚本运行时 __main__ 与 codex_bridge 两份 RunnerResult」身份 bug
    port2 = free_port()
    srv2 = ThreadingHTTPServer(("127.0.0.1", port2), _Handler)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    try:
        spec_path = os.path.join(root, "t7_spec.json")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(B.TaskSpec(task_id="lt7", goal="修复 add（CLI 路径）", repo=repo,
                                 allow_paths=["*.py"], test_command=TESTC).__dict__,
                      fh, ensure_ascii=False)
        env7 = dict(os.environ, NANA_BRIDGE_BASE_URL="http://127.0.0.1:%d/v1" % port2,
                    NANA_BRIDGE_API_KEY="local-test", NANA_BRIDGE_MODEL="fake-local",
                    NANA_BRIDGE_MAX_CALLS="1")
        p7 = subprocess.run([sys.executable, "codex_bridge.py", "--spec", spec_path,
                             "--runner", "local_llm"],
                            cwd=HERE, env=env7, capture_output=True, text=True, timeout=180)
        out7 = json.loads(p7.stdout)
        ep = out7.get("endpoint") or {}
        check("T7 CLI 路径闭环成功（RunnerResult 身份 bug 回归）",
              bool(out7.get("ok")) and bool(out7.get("applied"))
              and ep.get("is_codex_cli") is False and ep.get("calls") == 1
              and (ep.get("usage") or {}).get("total_tokens") == 2,
              json.dumps(out7, ensure_ascii=False)[:400])
    except Exception as e:
        check("T7 CLI 路径闭环成功（RunnerResult 身份 bug 回归）", False,
              "%s: %s" % (type(e).__name__, e))
    finally:
        srv2.shutdown()

    # T8 请求次数硬闸门：超过 max_calls 拒绝外发
    fc8 = FakeClient(good_payload())
    r8 = L.LocalLLMRunner(fc8, max_calls=1)
    sp8 = B.TaskSpec(task_id="lt8", goal="g", repo=repo, allow_paths=["*.py"])
    a8 = r8.run(sp8, repo, "p")
    b8 = r8.run(sp8, repo, "p")
    check("T8 超请求上限后拒绝外发（费用闸门）",
          a8.ok and (not b8.ok) and r8.calls == 1 and len(fc8.calls) == 1, b8.reason)

    # T9 usage 被如实记录（成本证据）
    check("T9 usage 被记录", (r8.last_usage or {}).get("total_tokens") == 33,
          str(r8.last_usage))

    shutil.rmtree(root, ignore_errors=True)
    print("\n===== 结果：%d 通过 / %d 失败 =====" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：", FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
