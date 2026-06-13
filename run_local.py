"""
Local development runner — polling mode.
Không cần webhook, không cần public URL.
Bot tự hỏi Telegram mỗi giây, log hiện trong terminal.

Chạy: python run_local.py
Dừng: Ctrl+C
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from storage import init_pool, init_db
from bot.handlers import (
    cmd_start,
    cmd_reset,
    cmd_help,
    cmd_dbg_funnel,
    cmd_settings,
    cmd_connect_ads,
    cmd_disconnect_ads,
    cmd_ads_settings,
    cmd_ads_analytics,
    cmd_ads_optimizer,
    handle_message,
    handle_callback,
    handle_photo,
    handle_document,
    cmd_admin_addquota,
    cmd_admin_setquota,
    cmd_admin_resetusage,
    cmd_admin_userinfo,
    cmd_history,
    cmd_post,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    await init_pool()
    await init_db()
    logger.info("✅ Supabase connected.")
    logger.info("✅ Bot running in POLLING mode — local dev.")
    logger.info("💬 Mở Telegram và chat với bot. Ctrl+C để dừng.\n")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN chưa được set trong .env")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("reset",        cmd_reset))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("dbgfunnel",    cmd_dbg_funnel))
    app.add_handler(CommandHandler("settings",     cmd_settings))
    app.add_handler(CommandHandler("setting",      cmd_settings))
    app.add_handler(CommandHandler("config",       cmd_settings))
    app.add_handler(CommandHandler("connect_ads",  cmd_connect_ads))
    app.add_handler(CommandHandler("disconnect_ads", cmd_disconnect_ads))
    app.add_handler(CommandHandler("ads_settings", cmd_ads_settings))
    app.add_handler(CommandHandler("ads_analytics", cmd_ads_analytics))
    app.add_handler(CommandHandler("ads_optimizer", cmd_ads_optimizer))

    app.add_handler(CommandHandler("addquota",     cmd_admin_addquota))
    app.add_handler(CommandHandler("setquota",     cmd_admin_setquota))
    app.add_handler(CommandHandler("resetusage",   cmd_admin_resetusage))
    app.add_handler(CommandHandler("userinfo",     cmd_admin_userinfo))

    app.add_handler(CommandHandler("history",      cmd_history))
    app.add_handler(CommandHandler("post",         cmd_post))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
