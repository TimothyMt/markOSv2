"""
Supabase backend cho web dashboard (REST/HTTPS qua supabase-py AsyncClient).

Kích hoạt khi có SUPABASE_URL + SUPABASE_SERVICE_KEY. Bảng tiền tố `web_`
(chạy webapp/supabase_schema.sql trong Supabase trước). Cùng interface async
với store_sqlite — frontend không cần biết backend nào.
"""
import os
import random
from datetime import date

from supabase import acreate_client

from webapp import store_sqlite as seed  # tái dùng hằng số seed

_client = None


async def _c():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
        _client = await acreate_client(url, key)
    return _client


async def _empty(table):
    c = await _c()
    res = await c.table(table).select("id").limit(1).execute()
    return not res.data


async def init():
    c = await _c()
    # Seed các bảng còn rỗng (idempotent).
    async def seed_if_empty(table, rows):
        if await _empty(table):
            await c.table(table).insert(rows).execute()

    await seed_if_empty("web_tracked", [
        {"name": n, "ads": a, "status": s, "last": l} for (n, a, s, l) in seed.SEED_TRACKED])
    # jobs dùng name làm khóa → kiểm tra theo name
    jres = await c.table("web_jobs").select("name").limit(1).execute()
    if not jres.data:
        await c.table("web_jobs").insert(
            [{"name": n, "when_text": w, "status": s} for (n, w, s) in seed.SEED_JOBS]).execute()
    await seed_if_empty("web_optimizations", [
        {"action": a, "text": t, "why": w} for (a, t, w) in seed.SEED_OPT])
    await seed_if_empty("web_alerts", [
        {"sev": s, "icon": i, "title": t, "meta": m} for (s, i, t, m) in seed.SEED_ALERTS])
    sres = await c.table("web_settings").select("key").limit(1).execute()
    if not sres.data:
        await c.table("web_settings").insert(
            [{"key": k, "value": v} for (k, v) in seed.SEED_SETTINGS]).execute()
    await seed_if_empty("web_campaigns", [
        {"name": n, "status": s, "budget": b, "objective": o} for (n, s, b, o) in seed.SEED_CAMPAIGNS])
    await seed_if_empty("web_calendar_posts", [
        {"day": d, "pillar": p, "title": t} for (d, p, t) in seed.SEED_CALENDAR])
    await seed_if_empty("web_content_items", [
        {"idx": i, "hook": h, "format": f, "status": s} for (i, h, f, s) in seed.SEED_CONTENT])
    await seed_if_empty("web_reports", [
        {"name": n, "type": t, "date": d} for (n, t, d) in seed.SEED_REPORTS])
    await seed_if_empty("web_accounts", [
        {"name": n, "acc_id": a, "status": s, "spend": sp} for (n, a, s, sp) in seed.SEED_ACCOUNTS])
    await seed_if_empty("web_users", [
        {"uid": u, "plan": p, "quota": q, "used": us} for (u, p, q, us) in seed.SEED_USERS])


async def get_state():
    c = await _c()
    async def all_(table, order="id", desc=False):
        return (await c.table(table).select("*").order(order, desc=desc).execute()).data

    jobs_raw = await all_("web_jobs", order="name")
    jobs = [{"name": r["name"], "when": r["when_text"], "status": r["status"]} for r in jobs_raw]
    settings = {r["key"]: r["value"] for r in (await c.table("web_settings").select("*").execute()).data}
    return {
        "tracked": await all_("web_tracked"),
        "jobs": jobs,
        "optimizations": await all_("web_optimizations"),
        "alerts": await all_("web_alerts"),
        "settings": settings,
        "campaigns": await all_("web_campaigns", desc=True),
        "calendarPosts": await all_("web_calendar_posts"),
        "contentItems": await all_("web_content_items", order="idx"),
        "reports": await all_("web_reports", desc=True),
        "accounts": await all_("web_accounts"),
        "users": await all_("web_users"),
    }


# ── Mutations ───────────────────────────────────────────────────────
async def _ins(table, row):
    c = await _c(); await c.table(table).insert(row).execute(); return await get_state()

async def _del(table, i):
    c = await _c(); await c.table(table).delete().eq("id", i).execute(); return await get_state()


async def add_tracked(name):
    return await _ins("web_tracked", {"name": name, "ads": 0, "status": "online", "last": "vừa thêm"})

async def del_tracked(i):
    return await _del("web_tracked", i)

async def toggle_job(name):
    c = await _c()
    row = (await c.table("web_jobs").select("status").eq("name", name).execute()).data
    if row:
        new = "off" if row[0]["status"] == "on" else "on"
        await c.table("web_jobs").update({"status": new}).eq("name", name).execute()
    return await get_state()

async def remove_optimization(i):
    return await _del("web_optimizations", i)

async def dismiss_alert(i):
    return await _del("web_alerts", i)

async def set_setting(key, value):
    c = await _c()
    await c.table("web_settings").upsert({"key": key, "value": value}).execute()
    return await get_state()

async def add_campaign(name):
    return await _ins("web_campaigns", {"name": name, "status": "draft", "budget": "—", "objective": "Chuyển đổi"})

async def del_campaign(i):
    return await _del("web_campaigns", i)

async def add_calendar_post(day, pillar, title):
    return await _ins("web_calendar_posts", {"day": day, "pillar": pillar, "title": title})

async def del_calendar_post(i):
    return await _del("web_calendar_posts", i)

async def generate_content(topic):
    c = await _c()
    await c.table("web_content_items").delete().neq("id", -1).execute()
    items = [
        {"idx": 1, "hook": f"“{topic} — buổi sáng cần một lý do…”", "format": "FB Post", "status": "ready"},
        {"idx": 2, "hook": f"“3 lý do chọn {topic}”", "format": "Carousel", "status": "ready"},
        {"idx": 3, "hook": f"“Hậu trường {topic}”", "format": "Reel 9:16", "status": "ready"},
        {"idx": 4, "hook": f"“{topic} — Mua 1 tặng 1 hôm nay”", "format": "Ad BOFU", "status": "ready"},
    ]
    await c.table("web_content_items").insert(items).execute()
    return await get_state()

async def add_report(name, type_):
    return await _ins("web_reports", {"name": name, "type": type_, "date": date.today().strftime("%d/%m/%Y")})

async def del_report(i):
    return await _del("web_reports", i)

async def connect_account(name):
    return await _ins("web_accounts", {"name": name, "acc_id": f"act_{random.randint(1000,9999)}",
                                       "status": "online", "spend": "0₫/ngày"})

async def toggle_account(i):
    c = await _c()
    row = (await c.table("web_accounts").select("status").eq("id", i).execute()).data
    if row:
        new = "off" if row[0]["status"] == "online" else "online"
        await c.table("web_accounts").update({"status": new}).eq("id", i).execute()
    return await get_state()

async def disconnect_account(i):
    return await _del("web_accounts", i)

async def set_quota(i, value):
    c = await _c(); await c.table("web_users").update({"quota": value}).eq("id", i).execute(); return await get_state()

async def add_quota(i, value):
    c = await _c()
    row = (await c.table("web_users").select("quota").eq("id", i).execute()).data
    if row:
        await c.table("web_users").update({"quota": row[0]["quota"] + value}).eq("id", i).execute()
    return await get_state()

async def reset_usage(i):
    c = await _c(); await c.table("web_users").update({"used": 0}).eq("id", i).execute(); return await get_state()
