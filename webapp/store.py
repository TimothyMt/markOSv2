"""
SQLite-backed store cho web dashboard (mock-first).

Giữ các thực thể "động" mà người dùng có thể thay đổi từ giao diện:
tracked competitors, automation jobs, optimization suggestions, alerts, settings.
Dữ liệu tham chiếu tĩnh (frameworks, personas, pricing…) vẫn nằm ở frontend.

Khi nối dữ liệu thật sau này, chỉ cần thay phần đọc/ghi ở đây bằng nguồn thật
(Supabase, Facebook Marketing API…) — hợp đồng JSON với frontend giữ nguyên.
"""
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "markos_web.db"
_lock = threading.Lock()

# ── Seed data (khớp với web/data.js để demo nhất quán) ──────────────
SEED_TRACKED = [
    {"name": "Highlands Coffee", "ads": 24, "status": "online", "last": "12 phút trước"},
    {"name": "Phúc Long",        "ads": 17, "status": "online", "last": "1 giờ trước"},
    {"name": "Katinat",          "ads": 31, "status": "warn",   "last": "3 giờ trước · 5 ad mới"},
]
SEED_JOBS = [
    {"name": "Daily Digest",       "when": "08:00 hằng ngày", "status": "on"},
    {"name": "Weekly Report",      "when": "Thứ 2, 08:00",    "status": "on"},
    {"name": "Alert Monitor",      "when": "Mỗi 4 giờ",        "status": "on"},
    {"name": "Token Refresh",      "when": "02:00 hằng ngày", "status": "on"},
    {"name": "Snapshot Cleanup",   "when": "CN, 03:00",        "status": "on"},
    {"name": "Competitor Monitor", "when": "Mỗi 1 giờ",        "status": "on"},
]
SEED_OPT = [
    {"action": "scale",    "text": "Tăng ngân sách 20% — “Re-targeting 7 ngày”", "why": "ROAS 5,3x > mục tiêu"},
    {"action": "pause",    "text": "Tạm dừng — “Carousel SP cũ”",                "why": "CPA 95.000₫ vượt ngưỡng"},
    {"action": "dup",      "text": "Nhân bản — “Video 9:16” sang Lookalike 2%",  "why": "Mẫu thắng, mở rộng"},
    {"action": "activate", "text": "Bật lại — “CD Tết” (theo lịch)",             "why": "Đến khung giờ vàng"},
]
SEED_ALERTS = [
    {"sev": "danger", "icon": "⚠️", "title": "CPA vượt ngưỡng",       "meta": "CD “Khuyến mãi” · 95.000₫/đơn"},
    {"sev": "warn",   "icon": "🔔", "title": "Tần suất hiển thị cao",  "meta": "Nhóm Re-targeting · 4,2"},
    {"sev": "ok",     "icon": "✅", "title": "ROAS đạt mục tiêu",       "meta": "CD “Mùa hè” · 4,1x"},
]
SEED_SETTINGS = {
    "daily_digest": 1,
    "alert_threshold": 1,
    "weekly_report": 1,
    "competitor_new": 0,
}


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS tracked(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, ads INTEGER, status TEXT, last TEXT);
            CREATE TABLE IF NOT EXISTS jobs(
                name TEXT PRIMARY KEY, when_text TEXT, status TEXT);
            CREATE TABLE IF NOT EXISTS optimizations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT, text TEXT, why TEXT);
            CREATE TABLE IF NOT EXISTS alerts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sev TEXT, icon TEXT, title TEXT, meta TEXT);
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value INTEGER);
            """
        )
        if not c.execute("SELECT 1 FROM tracked LIMIT 1").fetchone():
            for t in SEED_TRACKED:
                c.execute("INSERT INTO tracked(name,ads,status,last) VALUES(?,?,?,?)",
                          (t["name"], t["ads"], t["status"], t["last"]))
        if not c.execute("SELECT 1 FROM jobs LIMIT 1").fetchone():
            for j in SEED_JOBS:
                c.execute("INSERT INTO jobs(name,when_text,status) VALUES(?,?,?)",
                          (j["name"], j["when"], j["status"]))
        if not c.execute("SELECT 1 FROM optimizations LIMIT 1").fetchone():
            for o in SEED_OPT:
                c.execute("INSERT INTO optimizations(action,text,why) VALUES(?,?,?)",
                          (o["action"], o["text"], o["why"]))
        if not c.execute("SELECT 1 FROM alerts LIMIT 1").fetchone():
            for a in SEED_ALERTS:
                c.execute("INSERT INTO alerts(sev,icon,title,meta) VALUES(?,?,?,?)",
                          (a["sev"], a["icon"], a["title"], a["meta"]))
        if not c.execute("SELECT 1 FROM settings LIMIT 1").fetchone():
            for k, v in SEED_SETTINGS.items():
                c.execute("INSERT INTO settings(key,value) VALUES(?,?)", (k, v))


def get_state() -> dict:
    with _conn() as c:
        tracked = [dict(r) for r in c.execute(
            "SELECT id,name,ads,status,last FROM tracked ORDER BY id")]
        jobs = [{"name": r["name"], "when": r["when_text"], "status": r["status"]}
                for r in c.execute("SELECT name,when_text,status FROM jobs")]
        optimizations = [dict(r) for r in c.execute(
            "SELECT id,action,text,why FROM optimizations ORDER BY id")]
        alerts = [dict(r) for r in c.execute(
            "SELECT id,sev,icon,title,meta FROM alerts ORDER BY id")]
        settings = {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings")}
    return {"tracked": tracked, "jobs": jobs, "optimizations": optimizations,
            "alerts": alerts, "settings": settings}


# ── Mutations ───────────────────────────────────────────────────────
def add_tracked(name: str) -> dict:
    with _lock, _conn() as c:
        c.execute("INSERT INTO tracked(name,ads,status,last) VALUES(?,?,?,?)",
                  (name, 0, "online", "vừa thêm"))
    return get_state()


def del_tracked(tid: int) -> dict:
    with _lock, _conn() as c:
        c.execute("DELETE FROM tracked WHERE id=?", (tid,))
    return get_state()


def toggle_job(name: str) -> dict:
    with _lock, _conn() as c:
        row = c.execute("SELECT status FROM jobs WHERE name=?", (name,)).fetchone()
        if row:
            new = "off" if row["status"] == "on" else "on"
            c.execute("UPDATE jobs SET status=? WHERE name=?", (new, name))
    return get_state()


def remove_optimization(oid: int) -> dict:
    with _lock, _conn() as c:
        c.execute("DELETE FROM optimizations WHERE id=?", (oid,))
    return get_state()


def dismiss_alert(aid: int) -> dict:
    with _lock, _conn() as c:
        c.execute("DELETE FROM alerts WHERE id=?", (aid,))
    return get_state()


def set_setting(key: str, value: int) -> dict:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value))
    return get_state()
