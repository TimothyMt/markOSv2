"""
Lệnh Telegram điều khiển Web Dashboard (chiều Telegram → Web).

Các lệnh ghi/đọc vào CÙNG store với web (webapp.store). Hiệu quả nhất khi bot
và web cùng cấu hình Supabase (SUPABASE_URL + SUPABASE_SERVICE_KEY) để chia sẻ
dữ liệu; nếu mỗi bên dùng SQLite riêng (2 service tách biệt) thì dữ liệu không
nhìn thấy nhau. Sau khi thay đổi, tải lại web để thấy cập nhật.
"""
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from webapp import store

logger = logging.getLogger(__name__)


async def cmd_web_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕹️ <b>Điều khiển Web Dashboard từ Telegram</b>\n\n"
        "/web_status — Tổng quan hệ thống\n"
        "/web_campaign &lt;tên&gt; — Tạo chiến dịch mới\n"
        "/web_track &lt;tên&gt; — Thêm đối thủ theo dõi\n"
        "/web_optimize — Áp dụng đề xuất tối ưu đầu tiên\n"
        "/web_alerts — Xem cảnh báo hiện tại\n\n"
        "<i>Thay đổi sẽ hiện trên web sau khi tải lại trang.</i>",
        parse_mode="HTML",
    )


async def cmd_web_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = await store.get_state()
    await update.message.reply_text(
        "📊 <b>Web Dashboard — Tổng quan</b>\n\n"
        f"🚀 Chiến dịch: <b>{len(s['campaigns'])}</b>\n"
        f"🕵️ Đối thủ theo dõi: <b>{len(s['tracked'])}</b>\n"
        f"⚡ Đề xuất tối ưu: <b>{len(s['optimizations'])}</b>\n"
        f"🔔 Cảnh báo: <b>{len(s['alerts'])}</b>\n"
        f"🔗 Tài khoản QC: <b>{len(s['accounts'])}</b>\n"
        f"💾 Backend: <b>{store.backend_name()}</b>",
        parse_mode="HTML",
    )


async def cmd_web_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Cú pháp: <code>/web_campaign Tên chiến dịch</code>", parse_mode="HTML")
        return
    s = await store.add_campaign(name)
    await update.message.reply_text(
        f"✅ Đã tạo chiến dịch <b>{name}</b> (tổng {len(s['campaigns'])}).", parse_mode="HTML")


async def cmd_web_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Cú pháp: <code>/web_track Tên đối thủ</code>", parse_mode="HTML")
        return
    s = await store.add_tracked(name)
    await update.message.reply_text(
        f"✅ Đang theo dõi <b>{name}</b> (tổng {len(s['tracked'])}).", parse_mode="HTML")


async def cmd_web_optimize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = await store.get_state()
    if not s["optimizations"]:
        await update.message.reply_text("✅ Không còn đề xuất tối ưu nào.")
        return
    top = s["optimizations"][0]
    s = await store.remove_optimization(top["id"])
    await update.message.reply_text(
        f"⚡ Đã áp dụng: <b>{top['text']}</b>\nCòn lại {len(s['optimizations'])} đề xuất.", parse_mode="HTML")


async def cmd_web_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = await store.get_state()
    if not s["alerts"]:
        await update.message.reply_text("✅ Không có cảnh báo.")
        return
    lines = [f"{a['icon']} <b>{a['title']}</b> — {a['meta']}" for a in s["alerts"]]
    await update.message.reply_text("🔔 <b>Cảnh báo hiện tại</b>\n\n" + "\n".join(lines), parse_mode="HTML")


def register(app: Application) -> None:
    """Đăng ký các lệnh /web_* vào PTB application."""
    app.add_handler(CommandHandler("web_help", cmd_web_help))
    app.add_handler(CommandHandler("web_status", cmd_web_status))
    app.add_handler(CommandHandler("web_campaign", cmd_web_campaign))
    app.add_handler(CommandHandler("web_track", cmd_web_track))
    app.add_handler(CommandHandler("web_optimize", cmd_web_optimize))
    app.add_handler(CommandHandler("web_alerts", cmd_web_alerts))
