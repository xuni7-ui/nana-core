#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codex_bridge.py — 奈奈 ↔ Codex 自动协作桥（最小可验证闭环）
================================================================
定位：**奈奈负责统筹与验收，Codex 负责编码**。本文件只做「调度 + 隔离 + 采集 + 边界校验」，
**不含**任何业务代码，也**不**替代奈奈做验收判断。

最小闭环（4 步，缺一不可）
--------------------------
    TaskSpec  →  隔离克隆（scratch）  →  Runner 执行  →  差异采集 + 边界校验 + 回执

安全纪律（对齐 AGENTS.md §4 / PROJECT_BRAIN D-015 / D-019）
----------------------------------------------------------
1. **永不原地改**：一律 `git clone` 到 `bridge/scratch/<task_id>/`，源仓只读。
2. **边界白名单**：改动落到 `allow_paths` 之外 → 立即判违规，回执 `applied=False`，
   **且不把该改动并入结果**（人工/奈奈复核）。
3. **不发外网**：本文件自身零网络调用；是否出网由**注入的 Runner 决定**。
4. **Runner 可插拔**：默认 `StubRunner`（离线，测试用）；`CodexRunner` 只在
   `codex` 二进制存在时才可用，否则**明确报错**，不假装成功。
5. **预算硬上限**：单任务墙钟超时；超时即杀进程并如实记录。
6. **回执留痕**：每次执行写 `bridge/receipts/<task_id>.json`（含 diff、测试输出、判定）。

用法（离线自检）
----------------
    python3 codex_bridge.py --selftest          # 用 StubRunner 跑通闭环
    python3 codex_bridge.py --spec spec.json    # 用真实 CodexRunner（需已安装 codex）
"""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH_ROOT = os.path.join(HERE, "scratch")
RECEIPT_ROOT = os.path.join(HERE, "receipts")

DEFAULT_BUDGET_S = 900          # 单任务墙钟上限（15 min）
DEFAULT_TEST_TIMEOUT_S = 300
DEFAULT_TIMEOUT_RUNNER_S = 600

# 任何情况下都不许被改动的路径（硬黑名单，先于 allow_paths 生效）
HARD_DENY = (
    "*.env", "*credential*", "*secret*", "*_secrets/*", "**/.git/**",
    "*cookie*", "*.key", "*token*", "*SESSDATA*",
)


# ============================================================
# 0. 数据结构
# ============================================================
@dataclass
class TaskSpec:
    """一次协作任务的规格。奈奈产出它，Codex 只负责执行。"""
    task_id: str
    goal: str                                   # 目标（自然语言，可自查）
    repo: str                                   # 源仓（**只读**，会被克隆）
    allow_paths: List[str] = field(default_factory=lambda: ["**"])   # 允许改动
    deny_paths: List[str] = field(default_factory=list)              # 额外禁止
    test_command: Optional[str] = None          # 验收命令（在 scratch 内跑）
    test_timeout_s: int = DEFAULT_TEST_TIMEOUT_S
    budget_s: int = DEFAULT_BUDGET_S

    def to_prompt(self) -> str:
        lines = [
            "你是一个工程编码助手。请在**当前工作目录**内完成下述任务。",
            "",
            "## 目标",
            self.goal,
            "",
            "## 硬性约束",
            "1. 只修改下列路径内的文件：%s" % ", ".join(self.allow_paths or ["(无)"]),
            "2. 禁止触碰任何凭据/密钥/环境文件，禁止新建配置文件写死密钥。",
            "3. 不要 git commit、不要 push、不要安装系统级依赖。",
            "4. 改动要最小化；能不改的文件不要改。",
            "5. 若任务无法完成，直接说明原因，**不要**伪造结果。",
        ]
        if self.test_command:
            lines += ["", "## 自检命令", self.test_command,
                      "（请在结束前自行运行一次，并报告真实输出。）"]
        return "\n".join(lines)


@dataclass
class RunnerResult:
    ok: bool = False
    stdout: str = ""
    stderr: str = ""
    reason: str = ""
    exit_code: Optional[int] = None


@dataclass
class Receipt:
    task_id: str
    ok: bool = False
    applied: bool = False           # 是否可并入主线（边界校验通过 + 测试通过）
    reason: str = ""
    runner: str = ""
    duration_s: float = 0.0
    changed_files: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    diff_stat: str = ""
    diff: str = ""
    test_ok: Optional[bool] = None
    test_output: str = ""
    runner_stdout: str = ""
    runner_stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 1. 边界校验
# ============================================================
def _matches(path: str, patterns: Sequence[str]) -> bool:
    p = path.replace(os.sep, "/")
    for pat in patterns:
        if fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(p, pat.rstrip("/") + "/*"):
            return True
        if pat.endswith("/**") and p.startswith(pat[:-3].rstrip("/") + "/"):
            return True
        if pat.startswith("**/") and fnmatch.fnmatch(os.path.basename(p), pat[3:]):
            return True
    return False


def check_boundaries(changed: Sequence[str], spec: TaskSpec) -> List[str]:
    """返回违规路径列表（空 = 通过）。"""
    bad: List[str] = []
    for f in changed:
        f = f.replace(os.sep, "/")
        if _matches(f, HARD_DENY) or _matches(f, spec.deny_paths or []):
            bad.append(f)
            continue
        if not _matches(f, spec.allow_paths or []):
            bad.append(f)
    return sorted(set(bad))


# ============================================================
# 2. Runner（可插拔）
# ============================================================
class StubRunner:
    """离线确定性 Runner：把 `mutations` 写到 scratch 里（测试/自检用）。"""

    name = "stub"

    def __init__(self, mutations: Optional[Dict[str, str]] = None,
                 *, fail: bool = False, sleep_s: float = 0.0):
        self.mutations = mutations or {}
        self.fail = fail
        self.sleep_s = sleep_s

    def run(self, spec: TaskSpec, workdir: str, prompt: str) -> RunnerResult:
        if self.sleep_s:
            time.sleep(self.sleep_s)
        for rel, content in self.mutations.items():
            dst = os.path.join(workdir, rel)
            os.makedirs(os.path.dirname(dst) or workdir, exist_ok=True)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(content)
        return RunnerResult(ok=not self.fail, stdout="stub 执行完毕",
                            stderr="(stub)" if not self.fail else "stub 故意失败",
                            reason="" if not self.fail else "stub fail=True",
                            exit_code=0 if not self.fail else 1)


class CodexRunner:
    """真实 Codex Runner：调用 `codex exec`（非交互）。

    * 二进制不存在 → `is_available()` 为 False，`run()` 抛明确错误（**不假装成功**）；
    * 出网与否、发送到哪个端点，由 `~/.codex/config.toml` 决定 —— 这属于
      **L3（出网·不可逆）**，必须先获得姐姐授权才能启用。
    """

    name = "codex"

    def __init__(self, binary: Optional[str] = None, *, extra_args: Sequence[str] = ()):
        self.binary = binary or os.environ.get("NANA_CODEX_BIN", "codex")
        self.extra_args = list(extra_args)

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def build_command(self, spec: TaskSpec, workdir: str, prompt: str) -> List[str]:
        if not self.is_available():
            raise FileNotFoundError(
                "未找到 codex 可执行文件（%s）。请先安装并完成授权后再启用真实 Runner。"
                % self.binary)
        return [self.binary, "exec", "--cd", workdir, "--skip-git-repo-check",
                *self.extra_args, prompt]

    def run(self, spec: TaskSpec, workdir: str, prompt: str) -> RunnerResult:
        cmd = self.build_command(spec, workdir, prompt)
        timeout = min(spec.budget_s, DEFAULT_TIMEOUT_RUNNER_S)
        try:
            p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                               timeout=max(1, timeout))
        except subprocess.TimeoutExpired:
            return RunnerResult(ok=False, reason="Runner 超时（%ss）" % timeout)
        except Exception as e:
            return RunnerResult(ok=False, reason="Runner 异常：%s: %s" % (type(e).__name__, e))
        return RunnerResult(ok=(p.returncode == 0), stdout=p.stdout[-8000:],
                            stderr=p.stderr[-8000:], exit_code=p.returncode,
                            reason="" if p.returncode == 0 else "codex 退出码 %d" % p.returncode)


# ============================================================
# 3. 编排：隔离 → 执行 → 采集 → 校验 → 回执
# ============================================================
def _git(args: Sequence[str], cwd: str, timeout: int = 120) -> tuple:
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return -1, "", "%s: %s" % (type(e).__name__, e)


def _prepare_scratch(spec: TaskSpec) -> tuple:
    """源仓只读 → 克隆到 scratch。返回 (scratch_dir, error)。"""
    if not os.path.isdir(os.path.join(spec.repo, ".git")):
        return "", "源仓不是 git 仓库：%s" % spec.repo
    os.makedirs(SCRATCH_ROOT, exist_ok=True)
    scratch = os.path.join(SCRATCH_ROOT, spec.task_id)
    shutil.rmtree(scratch, ignore_errors=True)
    rc, out, err = _git(["clone", "--quiet", "--no-hardlinks", spec.repo, scratch], HERE)
    if rc != 0:
        return "", "克隆失败：%s" % (err or out)
    _git(["config", "user.email", "nana@local"], scratch)
    _git(["config", "user.name", "nana"], scratch)
    return scratch, ""


def execute_task(spec: TaskSpec, runner: Any = None) -> Receipt:
    """跑完一次协作任务，返回回执（永不抛）。源仓**绝不被修改**。"""
    runner = runner or CodexRunner()
    t0 = time.time()
    r = Receipt(task_id=spec.task_id, runner=getattr(runner, "name", type(runner).__name__))

    scratch, err = _prepare_scratch(spec)
    if err:
        r.reason = err
        r.duration_s = round(time.time() - t0, 3)
        _write_receipt(r)
        return r

    # 基线（克隆后应为干净）
    rc, base, _ = _git(["rev-parse", "HEAD"], scratch)
    base_head = base.strip()

    # 执行
    try:
        res = runner.run(spec, scratch, spec.to_prompt())
        if not isinstance(res, RunnerResult):
            if all(hasattr(res, x) for x in ("ok", "reason")):
                # 纵深防御：跨模块/跨进程的 RunnerResult 身份不同也不丢结果
                res = RunnerResult(ok=bool(res.ok), stdout=getattr(res, "stdout", ""),
                                   stderr=getattr(res, "stderr", ""), reason=res.reason,
                                   exit_code=getattr(res, "exit_code", None))
            else:
                res = RunnerResult(ok=False, reason="Runner 返回类型异常：%s" % type(res).__name__)
    except Exception as e:
        res = RunnerResult(ok=False, reason="Runner 抛异常：%s: %s" % (type(e).__name__, e))
    r.runner_stdout = (res.stdout or "")[-4000:]
    r.runner_stderr = (res.stderr or "")[-4000:]

    # 采集差异（含新增文件）
    _git(["add", "-A"], scratch)
    _, stat, _ = _git(["diff", "--cached", "--stat"], scratch)
    _, diff, _ = _git(["diff", "--cached"], scratch)
    _, names, _ = _git(["diff", "--cached", "--name-only"], scratch)
    changed = [n.strip() for n in names.splitlines() if n.strip()]
    r.changed_files = changed
    r.diff_stat = stat.strip()
    r.diff = diff[:20000]

    # 边界校验（先于测试，违规直接判否）
    r.violations = check_boundaries(changed, spec)
    if r.violations:
        r.ok = False
        r.applied = False
        r.reason = "边界违规：改动落在白名单之外，已拒绝并入"
        r.duration_s = round(time.time() - t0, 3)
        _write_receipt(r)
        return r

    if not changed:
        r.ok = bool(res.ok)
        r.applied = False
        r.reason = res.reason or "Runner 未产生任何改动"
        r.duration_s = round(time.time() - t0, 3)
        _write_receipt(r)
        return r

    # 验收命令
    if spec.test_command:
        try:
            p = subprocess.run(spec.test_command, cwd=scratch, shell=True,
                               capture_output=True, text=True,
                               timeout=max(1, spec.test_timeout_s))
            r.test_ok = (p.returncode == 0)
            r.test_output = ((p.stdout or "") + "\n" + (p.stderr or ""))[-4000:]
        except subprocess.TimeoutExpired:
            r.test_ok = False
            r.test_output = "验收命令超时（%ss）" % spec.test_timeout_s
        except Exception as e:
            r.test_ok = False
            r.test_output = "验收命令异常：%s: %s" % (type(e).__name__, e)
    else:
        r.test_ok = None

    r.ok = bool(res.ok and (r.test_ok in (True, None)))
    r.applied = bool(r.ok)
    if not r.ok:
        r.reason = res.reason or ("验收命令失败" if r.test_ok is False else "任务未通过")
    else:
        r.reason = "通过：边界合规 + %s" % ("验收命令通过" if r.test_ok else "未配置验收命令")
    r.duration_s = round(time.time() - t0, 3)
    _write_receipt(r)
    return r


def _write_receipt(r: Receipt) -> str:
    os.makedirs(RECEIPT_ROOT, exist_ok=True)
    path = os.path.join(RECEIPT_ROOT, "%s.json" % r.task_id)
    payload = r.to_dict()
    payload["written_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    payload["base_head_note"] = "见 scratch 克隆基线"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return path


# ============================================================
# 4. CLI
# ============================================================
def _selftest() -> int:
    """用 StubRunner 跑通闭环（离线、确定性）。"""
    demo_repo = os.path.join(SCRATCH_ROOT, "_demo_repo")
    shutil.rmtree(demo_repo, ignore_errors=True)
    os.makedirs(demo_repo, exist_ok=True)
    _git(["init", "--quiet"], demo_repo)
    _git(["config", "user.email", "n@l"], demo_repo)
    _git(["config", "user.name", "n"], demo_repo)
    with open(os.path.join(demo_repo, "calc.py"), "w", encoding="utf-8") as fh:
        fh.write("def add(a, b):\n    return a - b\n")
    _git(["add", "-A"], demo_repo)
    _git(["commit", "-qm", "init"], demo_repo)

    spec = TaskSpec(task_id="selftest_happy", goal="修复 add 应为求和",
                    repo=demo_repo, allow_paths=["*.py"],
                    test_command="python3 -c \"import calc,sys; sys.exit(0 if calc.add(2,3)==5 else 1)\"")
    ok_run = StubRunner({"calc.py": "def add(a, b):\n    return a + b\n"})
    r1 = execute_task(spec, ok_run)

    spec2 = TaskSpec(task_id="selftest_violation", goal="越界改动", repo=demo_repo,
                     allow_paths=["*.py"])
    bad_run = StubRunner({"config/secret_token.txt": "oops"})
    r2 = execute_task(spec2, bad_run)

    print(json.dumps({
        "happy": {"ok": r1.ok, "applied": r1.applied, "test_ok": r1.test_ok,
                  "changed": r1.changed_files},
        "violation": {"ok": r2.ok, "applied": r2.applied, "violations": r2.violations},
        "codex_available": CodexRunner().is_available(),
    }, ensure_ascii=False, indent=1))
    good = r1.ok and r1.applied and r1.test_ok and (not r2.ok) and (not r2.applied)
    return 0 if good else 1


def main(argv: Sequence[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="奈奈 ↔ Codex 协作桥（最小闭环）")
    ap.add_argument("--selftest", action="store_true", help="用 StubRunner 离线跑通闭环")
    ap.add_argument("--spec", help="TaskSpec JSON 文件路径（真实 Runner）")
    ap.add_argument("--runner", default="codex", choices=("codex", "local_llm"),
                    help="真实 Runner 选型；默认 codex（未安装则明确报错，不联网）")
    a = ap.parse_args(list(argv))
    if a.selftest:
        return _selftest()
    if not a.spec:
        ap.print_help()
        return 0

    with open(a.spec, encoding="utf-8") as fh:
        raw = json.load(fh)
    spec = TaskSpec(**raw)

    if a.runner == "local_llm":
        # 以脚本方式运行时模块名是 __main__；local_runner 会 `from codex_bridge import ...`，
        # 若不别名就会出现「两份 RunnerResult」→ isinstance 误判（真实跑测抓到的 bug）。
        sys.modules.setdefault("codex_bridge", sys.modules[__name__])
        from local_runner import from_env          # 惰性导入：离线路径不受影响

        runner = from_env()
        if runner is None:
            print(json.dumps({"ok": False, "reason":
                              "未注入 NANA_BRIDGE_BASE_URL / NANA_BRIDGE_API_KEY，"
                              "拒绝联网（本地 Runner 不可用）"}, ensure_ascii=False))
            return 3
    else:
        runner = CodexRunner()
        if not runner.is_available():
            print(json.dumps({"ok": False,
                              "reason": "codex 未安装，真实 Runner 不可用（需姐姐授权 L3）"},
                             ensure_ascii=False))
            return 2

    rec = execute_task(spec, runner)
    out = rec.to_dict()
    out["endpoint"] = {
        "runner": getattr(runner, "name", "?"),
        "model": getattr(runner, "model", None),
        "base_url": (os.environ.get("NANA_BRIDGE_BASE_URL") or "").strip() or None,
        "calls": getattr(runner, "calls", None),
        "max_calls": getattr(runner, "max_calls", None),
        "prompt_bytes": len(getattr(runner, "last_prompt", "") or "") or None,
        "usage": getattr(runner, "last_usage", None),
        "is_codex_cli": getattr(runner, "name", "") == "codex",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0



if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
