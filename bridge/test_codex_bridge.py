#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_codex_bridge.py — 协作桥最小闭环 · 全离线测试（T1–T8）

运行：python3 test_codex_bridge.py
纪律：**零网络**；一律用 StubRunner；重点验证「源仓只读」与「边界拒绝」两个安全不变式。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import codex_bridge as B                      # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("✅" if cond else "❌", name, ("  — " + str(detail)) if not cond else ""))


def git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def make_repo(path: str) -> str:
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    git(["init", "--quiet"], path)
    git(["config", "user.email", "n@l"], path)
    git(["config", "user.name", "n"], path)
    with open(os.path.join(path, "lib.py"), "w", encoding="utf-8") as fh:
        fh.write("def mul(a, b):\n    return a + b\n")
    os.makedirs(os.path.join(path, "docs"), exist_ok=True)
    with open(os.path.join(path, "docs", "guide.md"), "w", encoding="utf-8") as fh:
        fh.write("# guide\n")
    with open(os.path.join(path, "keep.txt"), "w", encoding="utf-8") as fh:
        fh.write("不可改动\n")
    git(["add", "-A"], path)
    git(["commit", "-qm", "init"], path)
    return path


def tree_hash(root: str) -> str:
    h = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in sorted(files):
            p = os.path.join(base, f)
            h.update(os.path.relpath(p, root).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


def main() -> int:
    root = os.path.join(HERE, "scratch", "_test")
    repo = make_repo(os.path.join(root, "src_repo"))
    before = tree_hash(repo)

    TEST = ("python3 -c \"import lib,sys; sys.exit(0 if lib.mul(3,4)==12 else 1)\"")

    # T1 正常闭环
    spec = B.TaskSpec(task_id="t1_happy", goal="修复 mul", repo=repo,
                      allow_paths=["*.py"], test_command=TEST)
    r1 = B.execute_task(spec, B.StubRunner({"lib.py": "def mul(a, b):\n    return a * b\n"}))
    check("T1 正常路径：applied + 测试通过 + 采集到改动",
          r1.ok and r1.applied and r1.test_ok is True and r1.changed_files == ["lib.py"],
          json.dumps(r1.to_dict(), ensure_ascii=False)[:400])

    # T2 白名单外（非硬黑名单）→ 拒绝
    spec2 = B.TaskSpec(task_id="t2_outside", goal="越界改文档", repo=repo, allow_paths=["*.py"])
    r2 = B.execute_task(spec2, B.StubRunner({"docs/guide.md": "# 被改了\n"}))
    check("T2 白名单外改动被拒绝且 applied=False",
          (not r2.ok) and (not r2.applied) and r2.violations == ["docs/guide.md"],
          json.dumps(r2.to_dict(), ensure_ascii=False)[:400])

    # T3 硬黑名单（凭据类）→ 拒绝
    spec3 = B.TaskSpec(task_id="t3_secret", goal="碰凭据", repo=repo, allow_paths=["**"])
    r3 = B.execute_task(spec3, B.StubRunner({"cfg/nana_secret_key.txt": "leak"}))
    check("T3 硬黑名单路径被拒绝", (not r3.applied) and r3.violations,
          json.dumps(r3.to_dict(), ensure_ascii=False)[:300])

    # T4 Runner 失败 → 不 applied
    spec4 = B.TaskSpec(task_id="t4_fail", goal="失败任务", repo=repo, allow_paths=["*.py"],
                       test_command=TEST)
    r4 = B.execute_task(spec4, B.StubRunner({"lib.py": "def mul(a,b):\n    return 0\n"}, fail=True))
    check("T4 Runner 失败时不 applied", (not r4.ok) and (not r4.applied))

    # T5 验收命令失败 → 不 applied
    spec5 = B.TaskSpec(task_id="t5_testfail", goal="测试不过", repo=repo, allow_paths=["*.py"],
                       test_command=TEST)
    r5 = B.execute_task(spec5, B.StubRunner({"lib.py": "def mul(a,b):\n    return 99\n"}))
    check("T5 验收命令失败时不 applied", (not r5.ok) and (not r5.applied) and r5.test_ok is False)

    # T6 源仓只读（核心安全不变式）
    after = tree_hash(repo)
    check("T6 源仓逐字节未被修改", before == after, "%s != %s" % (before[:12], after[:12]))

    # T7 回执落盘可解析
    rp = os.path.join(B.RECEIPT_ROOT, "t1_happy.json")
    ok7 = False
    try:
        with open(rp, encoding="utf-8") as fh:
            d = json.load(fh)
        ok7 = d.get("task_id") == "t1_happy" and "diff" in d
    except Exception as e:
        ok7 = False
    check("T7 回执 JSON 落盘且可解析", ok7, rp)

    # T8 Runner 异常/超时 → 被吞并如实记录
    class BoomRunner:
        name = "boom"
        def run(self, spec, workdir, prompt):
            raise TimeoutError("模拟卡死")

    r8 = B.execute_task(B.TaskSpec(task_id="t8_boom", goal="炸", repo=repo,
                                   allow_paths=["*.py"]), BoomRunner())
    check("T8 Runner 异常被吞并如实记录",
          (not r8.ok) and "抛异常" in r8.reason, r8.reason)

    # T9 codex 未安装 → 明确报错，不假装成功
    cr = B.CodexRunner(binary="definitely-not-a-real-binary-xyz")
    raised = False
    try:
        cr.build_command(B.TaskSpec(task_id="x", goal="g", repo=repo), "/tmp", "p")
    except FileNotFoundError:
        raised = True
    check("T9 codex 缺失时明确报错（不假成功）", (not cr.is_available()) and raised)

    shutil.rmtree(root, ignore_errors=True)
    print("\n===== 结果：%d 通过 / %d 失败 =====" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：", FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
