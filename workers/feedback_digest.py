"""
Cron worker — Build feedback digest mỗi 2 ngày, gửi cho admin qua Telegram.

Deploy:
- Railway cron: schedule "0 9 */2 * *" → python -m workers.feedback_digest
- Local: manual run cho test

Requires env var:
- ADMIN_CHAT_ID: Telegram chat ID của admin (sếp) — để bot send digest tới
"""
import asyncio
import logging
import os

from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN
from storage import init_pool
from storage.feedback_log import get_digest_summary

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")


def format_digest(summary: dict) -> str:
    """Build readable digest text từ summary dict."""
    if summary["total_count"] == 0:
        return f"📊 *Feedback Digest ({summary.get('period_days', 2)} ngày)*\n\n" + summary.get("summary", "Không có data")

    period = summary.get("period_days", 2)
    lines = [
        f"📊 *Feedback Digest — {period} ngày qua*",
        "",
        "📈 *Tổng quan:*",
        f"  - Total feedback: {summary['total_count']}",
        f"  - Avg rating: {summary['avg_rating']}/5",
        "",
        "🎯 *Breakdown theo skill:*",
    ]

    for skill, s in list(summary["by_skill"].items())[:10]:
        flag = "🔴" if s["avg_rating"] < 3.5 else ("🟡" if s["avg_rating"] < 4.2 else "🟢")
        lines.append(f"  {flag} {skill}: {s['count']} ratings, avg {s['avg_rating']}/5, low {s['low_count']}")

    lines.extend(["", "🏭 *Breakdown theo industry:*"])
    for ind, i in list(summary["by_industry"].items())[:8]:
        lines.append(f"  - {ind}: {i['count']} ratings, avg {i['avg_rating']}/5")

    if summary["top_complaints"]:
        lines.extend(["", "⚠️ *Top complaints (rating ≤ 3):*"])
        for c in summary["top_complaints"][:5]:
            lines.append(f"  • [{c['skill']}/{c['industry']}] {c['rating']}⭐ — _{c['feedback'][:150]}_")

    lines.append("")
    lines.append("_Admin review để cập nhật prompts cho các skill rating thấp._")
    return "\n".join(lines)


async def run_once():
    if not ADMIN_CHAT_ID:
        logger.error("ADMIN_CHAT_ID env var chưa setup — không gửi digest được")
        return
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN missing")
        return

    await init_pool()
    summary = await get_digest_summary(since_days=2)
    text = format_digest(summary)

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        # Split if too long
        if len(text) > 4000:
            chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
            for c in chunks:
                await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=c, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.3)
        else:
            await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=text, parse_mode=ParseMode.MARKDOWN)
        logger.info("Digest sent to admin (%d total feedback)", summary["total_count"])
    except Exception as e:
        logger.exception("Send digest failed: %s", e)


if __name__ == "__main__":
    asyncio.run(run_once())
