#!/usr/bin/env python3
"""R4b · Codex CLI 真实执行验证（降权外部沙箱 · 单次 · 有预算上限）

框架：Codex CLI 0.162.0（真 CLI，非模型 HTTP 包装）
模型：DeepSeek deepseek-flash（自定义 model_provider，wire_api=responses）
隔离：OS 级 —— 进程以 nobody(65534) 运行；生产文件 root-owned，0600 读不到 / 644 写不进
凭据：运行时从生产配置读入内存，仅注入子进程环境变量；不落盘、不打印、不回执
预算：1 次会话 · 墙钟 ≤300s · 沙箱内仅种子 README
"""
import json, os, shutil, subprocess, sys, time

HOME = "/opt/nana_codex/home"
SANDBOX = "/opt/nana_codex/sandbox/run01"
CODEX_JS = "/opt/nana_codex/node_modules/@openai/codex/bin/codex.js"

TASK = (
    "在当前目录完成一个最小可验证任务，不要联网、不要安装依赖、不要访问本目录以外的任何文件：\n"
    "1) 创建 calc.py，实现 add(a, b) 返回两数之和；\n"
    "2) 创建 test_calc.py，用 assert 覆盖 正数/负数/零 三种情况，带 __main__ 可直接运行；\n"
    "3) 执行 python3 test_calc.py，确认全部通过；\n"
    "4) 用一句话汇报。"
)


def load_key():
    cfg = json.load(open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig"))
    for s in cfg["provider_sources"]:
        if s.get("id") == "deepseek":
            k = s.get("key")
            if isinstance(k, list) and k:
                return k[0] if isinstance(k[0], str) else (k[0].get("value") or k[0].get("key"))
    raise SystemExit("no key")


def main():
    env_git = dict(os.environ, GIT_AUTHOR_NAME="nana", GIT_AUTHOR_EMAIL="n@n",
                   GIT_COMMITTER_NAME="nana", GIT_COMMITTER_EMAIL="n@n")
    shutil.rmtree(SANDBOX, ignore_errors=True)
    os.makedirs(SANDBOX)
    subprocess.run(["git", "init", "-q", "."], cwd=SANDBOX, env=env_git, check=True)
    open(SANDBOX + "/README.md", "w").write("sandbox seed, no sensitive content\n")
    subprocess.run(["git", "add", "-A"], cwd=SANDBOX, env=env_git, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=SANDBOX, env=env_git, check=True)
    subprocess.run(["chown", "-R", "nobody:nogroup", SANDBOX], check=True)

    key = load_key()
    inner = ["/usr/bin/env", "HOME=" + HOME, "CODEX_HOME=" + HOME,
             "TMPDIR=/opt/nana_codex/tmp", "NANA_BRIDGE_API_KEY=" + key,
             "/usr/bin/node", CODEX_JS, "exec", "--strict-config", "--json",
             "--dangerously-bypass-approvals-and-sandbox", "-C", SANDBOX, TASK]
    cmd = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups"] + inner

    t0 = time.time()
    p = subprocess.run(cmd, cwd=SANDBOX, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    dt = time.time() - t0
    out = (p.stdout or "") + "\n---STDERR---\n" + (p.stderr or "")
    if key and len(key) > 12 and key[:12] in out:
        out = out.replace(key, "<REDACTED-KEY>")
    print(out[-7000:])
    print("=== exit=%s  wall=%.1fs ===" % (p.returncode, dt))

    print("=== 沙箱产物 ===")
    for root, dirs, files in os.walk(SANDBOX):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            print("  ", os.path.join(root, f).replace(SANDBOX, "."))
    print("=== 奈奈独立验收（不采信模型自述） ===")
    v = subprocess.run(["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups",
                        "python3", "test_calc.py"], cwd=SANDBOX, capture_output=True, text=True)
    print("  rc=%s out=%s" % (v.returncode, (v.stdout + v.stderr).strip()[:200]))
    g = subprocess.run(["git", "status", "--short"], cwd=SANDBOX, capture_output=True, text=True)
    print("  git status:", repr(g.stdout))

    print("=== 凭据落盘检查（只报结论） ===")
    hit = []
    for root, _, files in os.walk(HOME):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if key.encode() in open(fp, "rb").read():
                    hit.append(fp)
            except Exception:
                pass
    print("  凭据出现在 CODEX_HOME：", hit or "无 ✅")


if __name__ == "__main__":
    main()
