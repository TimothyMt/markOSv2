"""
Store facade — chọn backend theo môi trường.

- Mặc định: SQLite (webapp/markos_web.db) — không cần credentials.
- Nếu có SUPABASE_URL + SUPABASE_SERVICE_KEY (và supabase-py cài được):
  chuyển sang Supabase (REST). Chạy webapp/supabase_schema.sql trước.

Toàn bộ interface là async; frontend không cần biết backend nào đang chạy.
"""
import logging
import os

from webapp import store_sqlite as _sqlite

logger = logging.getLogger(__name__)
_backend = _sqlite
_name = "sqlite"


def configure() -> str:
    """Chọn backend. Gọi 1 lần lúc khởi động (trước init())."""
    global _backend, _name
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
    if url and key:
        try:
            from webapp import store_supabase as _sb
            _backend, _name = _sb, "supabase"
            logger.info("Web dashboard store: Supabase (REST).")
        except Exception as e:  # supabase-py thiếu / lỗi import → fallback
            _backend, _name = _sqlite, "sqlite"
            logger.warning("Supabase backend unavailable (%s) → fallback SQLite.", e)
    else:
        _backend, _name = _sqlite, "sqlite"
        logger.info("Web dashboard store: SQLite (mock-first).")
    return _name


def backend_name() -> str:
    return _name


# ── Delegation (giữ nguyên chữ ký async) ────────────────────────────
async def init():                        return await _backend.init()
async def get_state():                   return await _backend.get_state()
async def add_tracked(name):             return await _backend.add_tracked(name)
async def del_tracked(i):                return await _backend.del_tracked(i)
async def toggle_job(name):              return await _backend.toggle_job(name)
async def remove_optimization(i):        return await _backend.remove_optimization(i)
async def dismiss_alert(i):              return await _backend.dismiss_alert(i)
async def set_setting(key, value):       return await _backend.set_setting(key, value)
async def add_campaign(name):            return await _backend.add_campaign(name)
async def del_campaign(i):               return await _backend.del_campaign(i)
async def add_calendar_post(d, p, t):    return await _backend.add_calendar_post(d, p, t)
async def del_calendar_post(i):          return await _backend.del_calendar_post(i)
async def generate_content(topic):       return await _backend.generate_content(topic)
async def add_report(name, type_):       return await _backend.add_report(name, type_)
async def del_report(i):                 return await _backend.del_report(i)
async def connect_account(name):         return await _backend.connect_account(name)
async def toggle_account(i):             return await _backend.toggle_account(i)
async def disconnect_account(i):         return await _backend.disconnect_account(i)
async def set_quota(i, value):           return await _backend.set_quota(i, value)
async def add_quota(i, value):           return await _backend.add_quota(i, value)
async def reset_usage(i):                return await _backend.reset_usage(i)
