# -*- coding: utf-8 -*-
"""奈奈 · 管理员名单守卫

作用：AstrBot 每次启动时检查 admins_id，若少了名单里的 ID 就补回去并落盘。
清单是硬编码的，只能“补”不能“删”，也不接受外部输入，避免被滥用。
"""
from astrbot.api import logger
from astrbot.api.star import Context, Star, register

KEEP_ADMINS = [
    "3974051585",
    "2CCF6F55B9601F03AD16B0B95212F3E6",
]


@register(
    "astrbot_plugin_nana_admin_guard",
    "Linna",
    "管理员名单守卫（启动时自动补回姐姐的 ID）",
    "1.0.0",
)
class NanaAdminGuard(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context, config)
        try:
            self._ensure_admins()
        except Exception as e:  # 守卫失败绝不能拖累启动
            logger.error(f"[nana-admin-guard] 守卫执行异常: {e!r}")

    def _ensure_admins(self):
        cfg = self.context.get_config()
        current = list(cfg.get("admins_id") or [])
        missing = [i for i in KEEP_ADMINS if i not in current]
        if not missing:
            logger.info("[nana-admin-guard] admins_id 完整，无需修复。")
            return
        cfg["admins_id"] = current + missing
        cfg.save_config()
        logger.info(f"[nana-admin-guard] 已补回缺失的管理员 ID: {missing}")
