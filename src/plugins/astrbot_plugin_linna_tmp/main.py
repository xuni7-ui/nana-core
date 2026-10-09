# -*- coding: utf-8 -*-
import asyncio
from astrbot.api.star import Context, Star, register

GROUP_ID = 1108356142
TARGET_ID = 3635517561
DURATION = 60
OUT = "/AstrBot/data/tmp/linna_ban_result.txt"


@register("astrbot_plugin_linna_tmp", "Linna", "临时禁言执行器", "1.0.0")
class LinnaTmp(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context, config)
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._run())
        except Exception as e:
            self._write("SCHEDULE_ERR " + repr(e))

    def _write(self, text):
        try:
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass

    async def _run(self):
        self._write("START")
        try:
            for inst in self.context.platform_manager.platform_insts:
                bot = getattr(inst, "bot", None)
                self._write("INST %r bot=%r" % (inst, type(bot)))
                if bot is None:
                    continue
                try:
                    r = await bot.call_action(
                        "set_group_ban",
                        group_id=GROUP_ID,
                        user_id=TARGET_ID,
                        duration=DURATION,
                    )
                    self._write("BAN_OK %r" % (r,))
                except Exception as e:
                    self._write("BAN_ERR %r" % (e,))
        except Exception as e:
            self._write("ERR " + repr(e))
        self._write("DONE")
