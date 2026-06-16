"""
Cầu nối thông báo Web → Telegram.

Gửi tin nhắn về Telegram khi có thao tác trên web. Best-effort: nếu chưa cấu
hình token/chat_id thì tự bỏ qua (không làm hỏng action). Dùng Bot API trực
tiếp qua httpx — không cần khởi tạo python-telegram-bot.

Cấu hình bằng biến môi trường:
  TELEGRAM_BOT_TOKEN  — token bot (cùng bot Telegram của dự án)
  TELEGRAM_CHAT_ID    — chat nhận thông báo (user id hoặc group id)
"""
import logging
import os

logger = logging.getLogger(__name__)


def _cfg():
    return os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")


def enabled() -> bool:
    token, chat = _cfg()
    return bool(token and chat)


async def notify(text: str) -> bool:
    """Gửi 1 thông báo. Trả True nếu gửi thành công."""
    token, chat = _cfg()
    if not (token and chat):
        logger.info("[notify bỏ qua — chưa cấu hình Telegram] %s", text)
        return False
    try:
        import httpx  # lazy — chỉ cần khi thực sự gửi
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": text, "parse_mode": "HTML"},
            )
            if r.status_code != 200:
                logger.warning("Telegram sendMessage %s: %s", r.status_code, r.text[:200])
            return r.status_code == 200
    except Exception as e:
        logger.warning("notify failed: %s", e)
        return False
