"""
Entry point — Marketing OS Telegram Bot (Webhook mode).
Designed for Railway + Supabase deployment.

Dùng starlette + uvicorn trực tiếp (thay vì app.run_webhook) để có thể
gắn custom route /oauth/fb/callback vào cùng 1 server + 1 port.
"""
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL, PORT
from storage import init_pool, init_db
from bot.handlers import (
    cmd_start,
    cmd_reset,
    cmd_help,
    cmd_dbg_funnel,
    cmd_settings,
    cmd_connect_ads,
    cmd_disconnect_ads,
    cmd_switch_account,
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
    cmd_video_script_gen,
    cmd_content_generator,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Build PTB Application ────────────────────────────────────────

def _build_app() -> Application:
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("reset",        cmd_reset))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("dbgfunnel",    cmd_dbg_funnel))
    app.add_handler(CommandHandler("settings",     cmd_settings))
    app.add_handler(CommandHandler("setting",      cmd_settings))
    app.add_handler(CommandHandler("config",       cmd_settings))
    app.add_handler(CommandHandler("connect_ads",    cmd_connect_ads))
    app.add_handler(CommandHandler("disconnect_ads", cmd_disconnect_ads))
    app.add_handler(CommandHandler("switch_account", cmd_switch_account))
    app.add_handler(CommandHandler("ads_settings",   cmd_ads_settings))
    app.add_handler(CommandHandler("ads_analytics",  cmd_ads_analytics))
    app.add_handler(CommandHandler("ads_optimizer",  cmd_ads_optimizer))

    app.add_handler(CommandHandler("addquota",     cmd_admin_addquota))
    app.add_handler(CommandHandler("setquota",     cmd_admin_setquota))
    app.add_handler(CommandHandler("resetusage",   cmd_admin_resetusage))
    app.add_handler(CommandHandler("userinfo",     cmd_admin_userinfo))

    app.add_handler(CommandHandler("history",      cmd_history))
    app.add_handler(CommandHandler("post",         cmd_post))
    app.add_handler(CommandHandler("video_script_gen", cmd_video_script_gen))
    app.add_handler(CommandHandler("content_generator", cmd_content_generator))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


ptb_app = _build_app()


# ── Starlette route handlers ─────────────────────────────────────

async def telegram_webhook(request: Request) -> PlainTextResponse:
    """Nhận Telegram updates và đẩy vào PTB update queue."""
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.update_queue.put(update)
    return PlainTextResponse("OK")


async def oauth_fb_callback(request: Request):
    """FB OAuth 2.0 callback — exchange code → lưu token → notify user."""
    from services.fb_oauth import handle_callback
    return await handle_callback(request, ptb_app.bot)


# ── Web dashboard (Auto Ads Facebook) ────────────────────────────

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


async def dashboard(request: Request) -> RedirectResponse:
    """Chuyển hướng /dashboard → /web/ (StaticFiles phục vụ index + assets)."""
    return RedirectResponse(url="/web/")


# JSON API cho web dashboard (SQLite mock-first; tự dùng Supabase nếu có env).
from webapp.api import api_routes  # noqa: E402
from webapp import store as web_store  # noqa: E402


# ── Startup / shutdown lifecycle ─────────────────────────────────

@asynccontextmanager
async def lifespan(app: Starlette):
    # ── Startup ──────────────────────────────────────────────────
    await init_pool()
    await init_db()
    logger.info("DB pool ready.")

    web_store.configure()
    await web_store.init()
    logger.info("Web dashboard store ready (%s).", web_store.backend_name())

    await ptb_app.initialize()
    await ptb_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}",
        drop_pending_updates=True,
    )
    await ptb_app.start()
    logger.info("PTB webhook registered: %s", f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")

    from workers.monitor_competitors import start_background_monitor
    from services.ads_scheduler import start_ads_scheduler
    asyncio.create_task(start_background_monitor(ptb_app.bot, interval_seconds=3600))
    asyncio.create_task(start_ads_scheduler(ptb_app.bot))
    logger.info("Background tasks started (competitor monitor + ads scheduler).")

    yield  # app is running

    # ── Shutdown ─────────────────────────────────────────────────
    await ptb_app.stop()
    await ptb_app.shutdown()
    logger.info("PTB shutdown complete.")


# ── Starlette app ────────────────────────────────────────────────

starlette_app = Starlette(
    routes=[
        Route(f"/{TELEGRAM_BOT_TOKEN}", telegram_webhook, methods=["POST"]),
        Route("/oauth/fb/callback",     oauth_fb_callback, methods=["GET"]),
        Route("/dashboard",             dashboard,         methods=["GET"]),
        *api_routes(),
        Mount("/web", app=StaticFiles(directory=WEB_DIR, html=True), name="web"),
    ],
    lifespan=lifespan,
)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")
    if not WEBHOOK_URL:
        raise ValueError("WEBHOOK_URL is not set.")

    logger.info("Starting server on port %d", PORT)
    uvicorn.run(starlette_app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    main()
