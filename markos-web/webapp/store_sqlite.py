"""
SQLite backend cho web dashboard (mặc định, không cần credentials).

Interface async để đồng nhất với backend Supabase (REST). Mọi hàm trả về
toàn bộ state mới (dict) để frontend render lại.
"""
import os
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "markos_web.db"
_lock = threading.Lock()


def seed_demo_enabled() -> bool:
    """Chỉ seed dữ liệu demo khi WEB_SEED_DEMO bật. Mặc định TẮT → user mới thấy trạng thái sạch."""
    return os.getenv("WEB_SEED_DEMO", "").lower() in ("1", "true", "yes", "on")

# ── Seed (khớp web/data.js) ─────────────────────────────────────────
SEED_TRACKED = [
    ("Highlands Coffee", 24, "online", "12 phút trước"),
    ("Phúc Long", 17, "online", "1 giờ trước"),
    ("Katinat", 31, "warn", "3 giờ trước · 5 ad mới"),
]
SEED_JOBS = [
    ("Daily Digest", "08:00 hằng ngày", "on"),
    ("Weekly Report", "Thứ 2, 08:00", "on"),
    ("Alert Monitor", "Mỗi 4 giờ", "on"),
    ("Token Refresh", "02:00 hằng ngày", "on"),
    ("Snapshot Cleanup", "CN, 03:00", "on"),
    ("Competitor Monitor", "Mỗi 1 giờ", "on"),
]
SEED_OPT = [
    ("scale", "Tăng ngân sách 20% — “Re-targeting 7 ngày”", "ROAS 5,3x > mục tiêu"),
    ("pause", "Tạm dừng — “Carousel SP cũ”", "CPA 95.000₫ vượt ngưỡng"),
    ("dup", "Nhân bản — “Video 9:16” sang Lookalike 2%", "Mẫu thắng, mở rộng"),
    ("activate", "Bật lại — “CD Tết” (theo lịch)", "Đến khung giờ vàng"),
]
SEED_ALERTS = [
    ("danger", "⚠️", "CPA vượt ngưỡng", "CD “Khuyến mãi” · 95.000₫/đơn"),
    ("warn", "🔔", "Tần suất hiển thị cao", "Nhóm Re-targeting · 4,2"),
    ("ok", "✅", "ROAS đạt mục tiêu", "CD “Mùa hè” · 4,1x"),
]
SEED_SETTINGS = [("daily_digest", 1), ("alert_threshold", 1), ("weekly_report", 1), ("competitor_new", 0)]
SEED_CAMPAIGNS = [
    ("Mùa hè rực rỡ", "running", "6.5tr/ngày", "Chuyển đổi"),
    ("Re-targeting Q2", "running", "3tr/ngày", "Doanh số"),
]
SEED_CALENDAR = [
    (0, "Educate", "Mẹo pha cà phê"), (1, "Engage", "Mini-game"),
    (2, "Trust", "Review KH"), (2, "Convert", "Flash sale"),
    (3, "Educate", "Hậu trường"), (4, "Convert", "Combo cuối tuần"),
    (5, "Engage", "UGC repost"), (6, "Trust", "Câu chuyện thương hiệu"),
]
SEED_CONTENT = [
    (1, "“Buổi sáng cần một lý do…”", "FB Post", "ready"),
    (2, "“3 lý do khách quay lại”", "Carousel", "ready"),
    (3, "“Hậu trường pha chế”", "Reel 9:16", "generating"),
    (4, "“Mua 1 tặng 1 hôm nay”", "Ad BOFU", "ready"),
]
SEED_REPORTS = [
    ("Báo cáo tuần — CD Mùa hè", "Tuần", "14/06/2026"),
    ("Chiến lược 90 ngày — Quán cà phê", "Chiến lược", "10/06/2026"),
    ("Phân tích đối thủ — Q2", "Đối thủ", "02/06/2026"),
]
SEED_ACCOUNTS = [
    ("TK Quảng cáo 01", "act_8842", "online", "8.2M/ngày"),
    ("TK Quảng cáo 02", "act_5510", "off", "Tạm dừng"),
]
SEED_USERS = [
    ("527…412", "Pro", 200000, 142300),
    ("811…097", "Free", 50000, 49100),
    ("344…820", "Pro", 200000, 88600),
    ("905…173", "Team", 500000, 215400),
]


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _seed(c, table, cols, rows):
    if not c.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
        ph = ",".join("?" * len(cols))
        c.executemany(f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})", rows)


async def init():
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS tracked(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ads INTEGER, status TEXT, last TEXT);
            CREATE TABLE IF NOT EXISTS jobs(name TEXT PRIMARY KEY, when_text TEXT, status TEXT);
            CREATE TABLE IF NOT EXISTS optimizations(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, text TEXT, why TEXT);
            CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, sev TEXT, icon TEXT, title TEXT, meta TEXT);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value INTEGER);
            CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT, budget TEXT, objective TEXT);
            CREATE TABLE IF NOT EXISTS calendar_posts(id INTEGER PRIMARY KEY AUTOINCREMENT, day INTEGER, pillar TEXT, title TEXT);
            CREATE TABLE IF NOT EXISTS content_items(id INTEGER PRIMARY KEY AUTOINCREMENT, idx INTEGER, hook TEXT, format TEXT, status TEXT);
            CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, date TEXT);
            CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, acc_id TEXT, status TEXT, spend TEXT);
            CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, plan TEXT, quota INTEGER, used INTEGER);
            """
        )
        if not seed_demo_enabled():
            return   # user mới: bảng trống, không bơm dữ liệu demo giả
        _seed(c, "tracked", ["name", "ads", "status", "last"], SEED_TRACKED)
        _seed(c, "jobs", ["name", "when_text", "status"], SEED_JOBS)
        _seed(c, "optimizations", ["action", "text", "why"], SEED_OPT)
        _seed(c, "alerts", ["sev", "icon", "title", "meta"], SEED_ALERTS)
        _seed(c, "settings", ["key", "value"], SEED_SETTINGS)
        _seed(c, "campaigns", ["name", "status", "budget", "objective"], SEED_CAMPAIGNS)
        _seed(c, "calendar_posts", ["day", "pillar", "title"], SEED_CALENDAR)
        _seed(c, "content_items", ["idx", "hook", "format", "status"], SEED_CONTENT)
        _seed(c, "reports", ["name", "type", "date"], SEED_REPORTS)
        _seed(c, "accounts", ["name", "acc_id", "status", "spend"], SEED_ACCOUNTS)
        _seed(c, "users", ["uid", "plan", "quota", "used"], SEED_USERS)


async def get_state():
    with _conn() as c:
        rows = lambda q: [dict(r) for r in c.execute(q)]
        jobs = [{"name": r["name"], "when": r["when_text"], "status": r["status"]}
                for r in c.execute("SELECT name,when_text,status FROM jobs")]
        settings = {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings")}
        users = [{"id": r["id"], "uid": r["uid"], "plan": r["plan"], "quota": r["quota"], "used": r["used"]}
                 for r in c.execute("SELECT * FROM users ORDER BY id")]
        return {
            "tracked": rows("SELECT id,name,ads,status,last FROM tracked ORDER BY id"),
            "jobs": jobs,
            "optimizations": rows("SELECT id,action,text,why FROM optimizations ORDER BY id"),
            "alerts": rows("SELECT id,sev,icon,title,meta FROM alerts ORDER BY id"),
            "settings": settings,
            "campaigns": rows("SELECT id,name,status,budget,objective FROM campaigns ORDER BY id DESC"),
            "calendarPosts": rows("SELECT id,day,pillar,title FROM calendar_posts ORDER BY id"),
            "contentItems": rows("SELECT id,idx,hook,format,status FROM content_items ORDER BY idx"),
            "reports": rows("SELECT id,name,type,date FROM reports ORDER BY id DESC"),
            "accounts": rows("SELECT id,name,acc_id,status,spend FROM accounts ORDER BY id"),
            "users": users,
        }


def _exec(sql, params=()):
    with _lock, _conn() as c:
        c.execute(sql, params)


# ── Mutations ───────────────────────────────────────────────────────
async def add_tracked(name):
    _exec("INSERT INTO tracked(name,ads,status,last) VALUES(?,?,?,?)", (name, 0, "online", "vừa thêm"))
    return await get_state()

async def del_tracked(i):
    _exec("DELETE FROM tracked WHERE id=?", (i,)); return await get_state()

async def toggle_job(name):
    with _lock, _conn() as c:
        row = c.execute("SELECT status FROM jobs WHERE name=?", (name,)).fetchone()
        if row:
            c.execute("UPDATE jobs SET status=? WHERE name=?",
                      ("off" if row["status"] == "on" else "on", name))
    return await get_state()

async def remove_optimization(i):
    _exec("DELETE FROM optimizations WHERE id=?", (i,)); return await get_state()

async def dismiss_alert(i):
    _exec("DELETE FROM alerts WHERE id=?", (i,)); return await get_state()

async def set_setting(key, value):
    _exec("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    return await get_state()

async def add_campaign(name):
    _exec("INSERT INTO campaigns(name,status,budget,objective) VALUES(?,?,?,?)", (name, "draft", "—", "Chuyển đổi"))
    return await get_state()

async def del_campaign(i):
    _exec("DELETE FROM campaigns WHERE id=?", (i,)); return await get_state()

async def add_calendar_post(day, pillar, title):
    _exec("INSERT INTO calendar_posts(day,pillar,title) VALUES(?,?,?)", (day, pillar, title))
    return await get_state()

async def del_calendar_post(i):
    _exec("DELETE FROM calendar_posts WHERE id=?", (i,)); return await get_state()

async def generate_content(topic):
    items = [
        (1, f"“{topic} — buổi sáng cần một lý do…”", "FB Post", "ready"),
        (2, f"“3 lý do chọn {topic}”", "Carousel", "ready"),
        (3, f"“Hậu trường {topic}”", "Reel 9:16", "ready"),
        (4, f"“{topic} — Mua 1 tặng 1 hôm nay”", "Ad BOFU", "ready"),
    ]
    with _lock, _conn() as c:
        c.execute("DELETE FROM content_items")
        c.executemany("INSERT INTO content_items(idx,hook,format,status) VALUES(?,?,?,?)", items)
    return await get_state()

async def add_report(name, type_):
    from datetime import date
    _exec("INSERT INTO reports(name,type,date) VALUES(?,?,?)", (name, type_, date.today().strftime("%d/%m/%Y")))
    return await get_state()

async def del_report(i):
    _exec("DELETE FROM reports WHERE id=?", (i,)); return await get_state()

async def connect_account(name):
    import random
    _exec("INSERT INTO accounts(name,acc_id,status,spend) VALUES(?,?,?,?)",
          (name, f"act_{random.randint(1000,9999)}", "online", "0₫/ngày"))
    return await get_state()

async def toggle_account(i):
    with _lock, _conn() as c:
        row = c.execute("SELECT status FROM accounts WHERE id=?", (i,)).fetchone()
        if row:
            c.execute("UPDATE accounts SET status=? WHERE id=?",
                      ("off" if row["status"] == "online" else "online", i))
    return await get_state()

async def disconnect_account(i):
    _exec("DELETE FROM accounts WHERE id=?", (i,)); return await get_state()

async def set_quota(i, value):
    _exec("UPDATE users SET quota=? WHERE id=?", (value, i)); return await get_state()

async def add_quota(i, value):
    _exec("UPDATE users SET quota=quota+? WHERE id=?", (value, i)); return await get_state()

async def reset_usage(i):
    _exec("UPDATE users SET used=0 WHERE id=?", (i,)); return await get_state()
