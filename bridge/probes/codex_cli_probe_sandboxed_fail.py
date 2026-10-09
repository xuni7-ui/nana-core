#!/usr/bin/env python3
"""R4 · Codex CLI 自定义 Provider 最小真实验证（一次性 · 有预算上限）

框架：Codex CLI 0.162.0（真 CLI）
模型：DeepSeek deepseek-flash（自定义 model_provider，wire_api=responses）
隔离：CODEX_HOME=/root/nana_dev/codex_probe/home
     沙箱=/root/nana_dev/codex_probe/sandbox/run01（空 git 仓，仅种子 README）
凭据：运行时从生产配置读取，仅注入子进程环境变量，不落盘、不打印、不回执
预算：1 次 codex 会话 · 墙钟 ≤ 300s · 外传内容 = 任务提示 + 空仓种子文件
"""
import json, os, subprocess, sys, time

PROBE = "/root/nana_dev/codex_probe"
HOME = PROBE + "/home"
SANDBOX = PROBE + "/sandbox/run01"
CODEX = PROBE + "/node_modules/.bin/codex"

TASK = (
    "在当前目录完成一个最小可验证任务，不要联网、不要安装任何依赖：\n"
    "1) 创建 calc.py，实现 add(a, b) 返回两数之和；\n"
    "2) 创建 test_calc.py，用 assert 覆盖 正数/负数/零 三种情况，"
    "并带 if __name__ == '__main__' 可直接运行；\n"
    "3) 运行 `python3 test_calc.py` 确认全部通过；\n"
    "4) 用一句话汇报结果。"
)


def load_key():
    cfg = json.load(open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig"))
    for s in cfg["provider_sources"]:
        if s.get("id") == "deepseek":
            k = s.get("key")
            if isinstance(k, list) and k:
                return k[0] if isinstance(k[0], str) else (k[0].get("value") or k[0].get("key"))
    raise SystemExit("no deepseek key")


def main():
    import shutil
    shutil.rmtree(SANDBOX, ignore_errors=True)
    os.makedirs(SANDBOX)
    env_git = dict(os.environ, GIT_AUTHOR_NAME="nana", GIT_AUTHOR_EMAIL="n@n",
                   GIT_COMMITTER_NAME="nana", GIT_COMMITTER_EMAIL="n@n")
    subprocess.run(["git", "init", "-q", "."], cwd=SANDBOX, env=env_git, check=True)
    open(SANDBOX + "/README.md", "w").write("sandbox seed, no sensitive content\n")
    subprocess.run(["git", "add", "-A"], cwd=SANDBOX, env=env_git, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=SANDBOX, env=env_git, check=True)

    key = load_key()
    env = dict(os.environ, CODEX_HOME=HOME, NANA_BRIDGE_API_KEY=key)
    cmd = [CODEX, "exec", "--strict-config", "-s", "workspace-write",
           "-c", 'approval_policy="never"', "-C", SANDBOX, "--json", TASK]
    t0 = time.time()
    p = subprocess.run(cmd, env=env, cwd=SANDBOX, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    dt = time.time() - t0

    out = (p.stdout or "") + "\n---STDERR---\n" + (p.stderr or "")
    # 安全检查：输出里若出现钥匙片段，立刻遮掉（绝不外泄）
    if len(key) > 12 and key[:12] in out:
        out = out.replace(key, "<REDACTED-KEY>")
    print(out[-6000:])
    print("=== exit=%s  wall=%.1fs ===" % (p.returncode, dt))

    print("=== sandbox 文件 ===")
    for root, _, files in os.walk(SANDBOX):
        if ".git" in root:
            continue
        for f in files:
            print("  ", os.path.join(root, f).replace(SANDBOX, "."))
    print("=== 独立验收（奈奈自己跑，不采信模型自述） ===")
    v = subprocess.run(["python3", "test_calc.py"], cwd=SANDBOX, capture_output=True, text=True)
    print("  rc=%s  out=%s" % (v.returncode, (v.stdout + v.stderr).strip()[:200]))
    g = subprocess.run(["git", "status", "--short"], cwd=SANDBOX, capture_output=True, text=True)
    print("  git status:", repr(g.stdout))

    print("=== 密钥落盘检查（只报结论） ===")
    hit = []
    for root, _, files in os.walk(HOME):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if key.encode() in open(fp, "rb").read():
                    hit.append(fp)
            except Exception:
                pass
    print("  凭据出现在 CODEX_HOME 文件里：", hit or "无 ✅")


if __name__ == "__main__":
    main()
