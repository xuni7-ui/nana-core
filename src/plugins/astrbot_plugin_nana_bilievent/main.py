# -*- coding: utf-8 -*-
"""奈奈 · B站事件轮询挂载点（C.4 第一阶段）

这个插件只做**一件事**：
    向 **已有的 AstrBot cron 调度器**（Context.cron_manager，APScheduler）
    注册一个每 60 秒的 basic 周期任务；
    任务处理器 = 用**独立子进程**跑 bili_event_pump.py。

它**不是**新 scheduler，也**不是**新发送系统：
  * 周期触发 → 复用 AstrBot 核心 cron（和 SelfEvolution 的 daily job 同一套）
  * B站网络 IO / LLM / 发送 → 全在子进程里（bili_event_pump.py → bili_agent.py → bili_send_core.py）
  * 本插件进程内**不读不写任何 memory**，因此不可能持有主聊天 Memory 写锁

安全：
  * 子进程默认 observe（只读空跑）；是否允许真实发送由 bili_event_state.json 的 mode 决定
  * 单飞锁 + 子进程超时；超时/异常只记日志，绝不重试、绝不影响主聊天
"""

import asyncio
import os
import time

from astrbot.api import logger
from astrbot.api.star import Context, Star, register

PUMP = "/root/.nana_secrets/bili_event_pump.py"
CRON_LOG = "/root/.nana_secrets/bili_event_pump_cron.log"
TICK_LOCK = "/tmp/nana_bili_event_tick.lock"
JOB_NAME = "NanaBiliEventPoll"
CRON = "* * * * *"          # 每 60 秒（现有 scheduler 能给的温和周期）
SUB_TIMEOUT = 110           # 子进程硬超时（秒）
LOG_MAX_BYTES = 1024 * 1024


@register("astrbot_plugin_nana_bilievent", "Nana",
          "奈奈B站事件轮询挂载点（C.4·复用 AstrBot cron）", "1.0.0")
class NanaBiliEvent(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context, config)
        try:
            asyncio.get_event_loop().create_task(self._setup())
        except Exception as e:                       # 绝不让插件加载失败
            self._log("SETUP_SCHEDULE_ERR %s: %s" % (type(e).__name__, e))

    # ---------------- 日志 ----------------
    def _log(self, text: str) -> None:
        try:
            if os.path.exists(CRON_LOG) and os.path.getsize(CRON_LOG) > LOG_MAX_BYTES:
                with open(CRON_LOG, encoding="utf-8", errors="replace") as f:
                    tail = f.read()[-200 * 1024:]
                with open(CRON_LOG, "w", encoding="utf-8") as f:
                    f.write("[rotated]\n" + tail)
            with open(CRON_LOG, "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
        except Exception:
            pass

    # ---------------- 注册周期任务（复用现有 cron） ----------------
    async def _setup(self) -> None:
        for attempt in range(1, 11):
            try:
                cm = getattr(self.context, "cron_manager", None)
                if cm is not None:
                    try:
                        for job in await cm.list_jobs():
                            if job.name == JOB_NAME:
                                await cm.delete_job(job.job_id)   # 去重：先删旧再登记
                    except Exception as e:
                        self._log("LIST_JOBS_WARN %s: %s" % (type(e).__name__, e))
                    await cm.add_basic_job(
                        name=JOB_NAME,
                        cron_expression=CRON,
                        handler=self._tick,
                        description="奈奈: B站回复/@ 事件轮询（60s·独立子进程·默认只读）",
                        persistent=True,
                    )
                    if os.path.exists(PUMP):
                        self._log("REGISTERED %s %s" % (JOB_NAME, CRON))
                    else:
                        self._log("REGISTERED 但找不到 %s" % PUMP)
                    return
            except Exception as e:
                self._log("REGISTER_ATTEMPT%d_ERR %s: %s"
                          % (attempt, type(e).__name__, e))
            await asyncio.sleep(3)
        self._log("REGISTER_FAILED 10 次尝试后仍未注册")

    # ---------------- 每 60 秒被 cron 拉起 ----------------
    async def _tick(self) -> None:
        now = time.time()
        try:
            if os.path.exists(TICK_LOCK) and now - os.path.getmtime(TICK_LOCK) < 300:
                return                       # 上一轮还没跑完 → 不叠加
            with open(TICK_LOCK, "w") as f:
                f.write(str(now))
        except Exception:
            pass
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", PUMP, "--timeout", "95",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            out = b""
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=SUB_TIMEOUT)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                out = b"[hard-timeout] pump killed, no retry"
            text = (out or b"").decode("utf-8", "replace").strip()
            self._log("TICK " + (text[-1500:] if text else "(no output)"))
        except Exception as e:
            self._log("TICK_ERR %s: %s" % (type(e).__name__, e))
        finally:
            try:
                os.remove(TICK_LOCK)
            except Exception:
                pass

    async def terminate(self) -> None:       # noqa: D401
        """插件卸载/重载时：把周期任务摘掉，避免留下没有 handler 的孤儿任务。"""
        try:
            cm = getattr(self.context, "cron_manager", None)
            if cm is not None:
                for job in await cm.list_jobs():
                    if job.name == JOB_NAME:
                        await cm.delete_job(job.job_id)
            self._log("TERMINATED job removed")
        except Exception as e:
            logger.warning("[NanaBiliEvent] terminate 清理失败: %s" % e)
