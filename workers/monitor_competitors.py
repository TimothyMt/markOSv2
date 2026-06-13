"""
Cron worker — check tracked competitors mỗi giờ.
Khi phát hiện ads mới của 1 page đang track, notify user qua Telegram.

Deploy options:
- Railway cron service: chạy `python -m workers.monitor_competitors` mỗi giờ
- Local: schedule via APScheduler hoặc cron

Usage (one-shot):
    python -m workers.monitor_competitors
"""
import asyncio
import logging
from typing import Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN
from storage import init_pool
from storage.tracked_competitors import (
    get_due_tracked,
    update_after_check,
)
from tools.fb_ads_library import search_by_page_id, is_available

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _ad_ids_from_response(ads: list[dict]) -> list[str]:
    return [a.get("id") for a in ads if a.get("id")]


async def check_one(bot: Bot, tracked: dict) -> None:
    """Check 1 tracked entry → notify user nếu có ads mới."""
    user_id = tracked["user_id"]
    page_id = tracked["page_id"]
    page_name = tracked.get("page_name") or "đối thủ"
    interval = tracked.get("interval_hours", 24)
    previous_ids = set(tracked.get("last_ad_ids") or [])

    try:
        current_ads = await search_by_page_id(page_id, country="VN", limit=30)
    except Exception as e:
        logger.warning("Fetch ads failed for %s: %s", page_name, e)
        return

    current_ids = set(_ad_ids_from_response(current_ads))
    new_ids = list(current_ids - previous_ids)

    if new_ids:
        # Có ads mới — notify
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Phân tích ads mới",     callback_data=f"monitor_diff_{page_id}")],
            [InlineKeyboardButton("⏭️ Bỏ qua lần này",        callback_data="monitor_skip_diff")],
        ])
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🔔 *{page_name}* vừa tung *{len(new_ids)}* ads mới!\n\n"
                    f"_Em đã pull được data, sếp muốn em phân tích chi tiết không?_"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
            logger.info("Notified user %s about %d new ads from %s", user_id, len(new_ids), page_name)
        except Exception as e:
            logger.warning("Send notification failed for user %s: %s", user_id, e)
    else:
        # Không có ads mới — chỉ báo nếu interval >= 1 ngày (tránh spam)
        if interval >= 24:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ *{page_name}* không có ads mới ({interval}h qua).\n"
                        f"_Em vẫn theo dõi tiếp ạ._"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.warning("Send no-new-ads notify failed for user %s: %s", user_id, e)

    # Update last_check_at + ad_ids regardless
    await update_after_check(tracked["id"], list(current_ids))


async def run_once_with_bot(bot: Bot) -> None:
    """Run 1 pass với một Bot instance đã có sẵn (dùng cho in-process scheduler)."""
    if not is_available():
        logger.debug("FB Access token chưa setup — monitor skipped")
        return
    due = await get_due_tracked()
    if not due:
        return
    logger.info("Monitor: %d tracked entries due", len(due))
    for tracked in due:
        try:
            await check_one(bot, tracked)
            await asyncio.sleep(2)
        except Exception as e:
            logger.exception("check_one failed for tracked %s: %s", tracked.get("id"), e)


async def start_background_monitor(bot: Bot, interval_seconds: int = 3600) -> None:
    """Chạy monitor loop liên tục trong background (asyncio task).

    Gọi trong Application.post_init — không block main loop.
    Check mỗi interval_seconds (default 1h), tự skip nếu không có gì due.
    """
    logger.info("Background monitor started (interval=%ds)", interval_seconds)
    while True:
        try:
            await run_once_with_bot(bot)
        except Exception as e:
            logger.exception("Background monitor error: %s", e)
        await asyncio.sleep(interval_seconds)


async def run_once():
    """Run 1 pass — check tất cả tracked entries due."""
    if not is_available():
        logger.error("FB Access token chưa setup, không check được")
        return

    await init_pool()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    due = await get_due_tracked()
    logger.info("Found %d due tracked entries", len(due))

    for tracked in due:
        try:
            await check_one(bot, tracked)
            await asyncio.sleep(2)  # rate limit safety
        except Exception as e:
            logger.exception("check_one failed for tracked %s: %s", tracked.get("id"), e)


if __name__ == "__main__":
    asyncio.run(run_once())
