"""
JSON API cho web dashboard. Mount vào Starlette (run_web.py hoặc bot/main.py).

GET /api/bootstrap trả về state động; các endpoint còn lại ghi và trả state mới.
"""
import asyncio
import json

from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from webapp import store
from webapp import notify as tg
from webapp import business as biz
from webapp.events import hub


def _ok(state):
    return JSONResponse(state)


async def full_state() -> dict:
    """State đầy đủ dùng cho bootstrap, SSE snapshot và watcher.

    Chỉ chứa phần NHẸ (web_* + cờ + danh sách job in-memory). Dữ liệu nghiệp vụ
    THẬT (nhiều query Supabase) lấy on-demand qua /api/biz để watcher 4s không
    nện DB liên tục — nhưng tiến độ AI agent (in-memory) vẫn đẩy live qua SSE.
    """
    state = await store.get_state()
    state["telegramEnabled"] = tg.enabled()
    state["bizEnabled"] = biz.available()
    state["agentJobs"] = biz.jobs_public()
    return state


async def bootstrap(request):
    return JSONResponse(await full_state())


async def stream(request):
    """SSE: gửi snapshot ngay, sau đó đẩy state mới khi có thay đổi."""
    async def gen():
        q = hub.subscribe()
        try:
            yield f"data: {json.dumps(await full_state(), ensure_ascii=False)}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"  # giữ kết nối qua proxy Railway
                if await request.is_disconnected():
                    break
        finally:
            hub.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


async def notify_test(request):
    ok = await tg.notify("✅ <b>Marketing OS</b> — kết nối thông báo Telegram thành công!")
    return JSONResponse({"ok": ok, "enabled": tg.enabled()})


# ── Dữ liệu nghiệp vụ thật + AI agent ───────────────────────────────
async def biz_data(request):
    """Dữ liệu thật của 1 user (profile, campaigns, đối thủ, skill runs, brand voice)."""
    return JSONResponse(await biz.biz_data(request.query_params.get("user_id")))


async def biz_skillrun(request):
    """Full content 1 skill_run (để xem chi tiết output AI đã tạo)."""
    return JSONResponse(await biz.skill_run_content(request.path_params["id"]))


async def biz_save_profile(request):
    """Lưu hồ sơ doanh nghiệp (điểm khởi đầu form-first)."""
    data = await request.json()
    res = await biz.save_profile(data.get("user_id"), data.get("fields") or {})
    return JSONResponse(res, status_code=400 if "error" in res else 200)


async def biz_intake(request):
    """Một lượt phỏng vấn AI-adaptive của Max (onboarding)."""
    data = await request.json()
    res = await biz.intake_turn(data.get("user_id"), data.get("message", ""))
    return JSONResponse(res, status_code=400 if "error" in res else 200)


async def biz_skillrun_rate(request):
    """Chấm điểm 1 output research (👍/👎 → 5/1)."""
    data = await request.json()
    res = await biz.rate_skill_run(request.path_params["id"], data.get("rating", 0), data.get("feedback"))
    return JSONResponse(res, status_code=400 if "error" in res else 200)


async def biz_skillrun_save(request):
    """Lưu chỉnh sửa output thành version mới (sửa tay / đặt làm hiện hành)."""
    data = await request.json()
    res = await biz.save_skill_edit(data.get("user_id"), data.get("skill_name", ""), data.get("content", ""))
    return JSONResponse(res, status_code=400 if "error" in res else 200)


async def biz_skill_versions(request):
    """Danh sách version của 1 skill cho user."""
    return JSONResponse({"versions": await biz.list_skill_versions(
        request.query_params.get("user_id"), request.query_params.get("skill", ""))})


async def biz_skillrun_patch(request):
    """Nhờ Max chỉnh 1 đoạn → version mới (surgical_edit)."""
    data = await request.json()
    res = await biz.patch_skill_run(request.path_params["id"], data.get("comment", ""))
    return JSONResponse(res, status_code=400 if "error" in res else 200)


async def biz_agent_run(request):
    """Khởi chạy pipeline/skill THẬT cho user. Trả jobId; theo dõi qua SSE agentJobs."""
    data = await request.json()
    task = (data.get("task") or "full").strip()
    res = await biz.run_agent(data.get("user_id"), task)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    await tg.notify(
        f"🤖 <b>AI Agent</b> bắt đầu: {biz.TASK_LABELS.get(task, task)} "
        f"(user <code>{res['job']['userId']}</code>)."
    )
    return JSONResponse(res)


async def biz_ads(request):
    """Ads analytics thật: snapshots, KPI, winners/losers, biểu đồ theo ngày."""
    days = int(request.query_params.get("days", 7))
    user_id = request.query_params.get("user_id")
    return JSONResponse(await biz.ads_data(user_id=user_id, days=days))


async def biz_fb_connect_url(request):
    """Trả link FB OAuth để user kết nối tài khoản Ads từ web."""
    res = await biz.fb_connect_url(request.query_params.get("user_id"))
    return JSONResponse(res, status_code=400 if "error" in res else 200)


# ── Max (đối thoại cố vấn) ──────────────────────────────────────────
async def chat(request):
    """Một lượt hội thoại với Max. Body: {user_id, message}."""
    from webapp import chat as chat_mod
    data = await request.json()
    res = await chat_mod.chat_turn(data.get("user_id"), data.get("message", ""))
    return JSONResponse(res, status_code=400 if "error" in res else 200)


async def chat_history(request):
    """Lịch sử hội thoại web (đọc bền từ Supabase, fallback in-memory)."""
    from webapp import chat as chat_mod
    return JSONResponse({"history": await chat_mod.load_history(request.query_params.get("user_id"))})


# ── Tracked competitors ─────────────────────────────────────────────
async def add_tracked(request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    return _ok(await store.add_tracked(name))

async def del_tracked(request):
    return _ok(await store.del_tracked(int(request.path_params["id"])))


# ── Jobs / optimizations / alerts / settings ────────────────────────
async def toggle_job(request):
    return _ok(await store.toggle_job(request.path_params["name"]))

async def apply_optimization(request):
    state = await store.remove_optimization(int(request.path_params["id"]))
    await tg.notify("⚡ Đã áp dụng một đề xuất tối ưu quảng cáo.")
    return _ok(state)

async def dismiss_alert(request):
    return _ok(await store.dismiss_alert(int(request.path_params["id"])))

async def set_setting(request):
    data = await request.json()
    key = data.get("key")
    if not key:
        return JSONResponse({"error": "key required"}, status_code=400)
    return _ok(await store.set_setting(key, int(data.get("value", 0))))


# ── Campaigns ───────────────────────────────────────────────────────
async def add_campaign(request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    state = await store.add_campaign(name)
    await tg.notify(f"🚀 Chiến dịch mới: <b>{name}</b>")
    return _ok(state)

async def del_campaign(request):
    return _ok(await store.del_campaign(int(request.path_params["id"])))


# ── Calendar posts ──────────────────────────────────────────────────
async def add_calendar_post(request):
    data = await request.json()
    title = (data.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    return _ok(await store.add_calendar_post(
        int(data.get("day", 0)), data.get("pillar", "Educate"), title))

async def del_calendar_post(request):
    return _ok(await store.del_calendar_post(int(request.path_params["id"])))


# ── Content generation ──────────────────────────────────────────────
async def generate_content(request):
    data = await request.json()
    topic = (data.get("topic") or "Khuyến mãi").strip()
    return _ok(await store.generate_content(topic))


# ── Reports ─────────────────────────────────────────────────────────
async def add_report(request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    return _ok(await store.add_report(name, data.get("type", "Tuần")))

async def del_report(request):
    return _ok(await store.del_report(int(request.path_params["id"])))


# ── Ad accounts ─────────────────────────────────────────────────────
async def connect_account(request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    state = await store.connect_account(name)
    await tg.notify(f"🔗 Đã kết nối tài khoản quảng cáo: <b>{name}</b>")
    return _ok(state)

async def toggle_account(request):
    return _ok(await store.toggle_account(int(request.path_params["id"])))

async def disconnect_account(request):
    return _ok(await store.disconnect_account(int(request.path_params["id"])))


# ── Admin: user quota ───────────────────────────────────────────────
async def set_quota(request):
    data = await request.json()
    return _ok(await store.set_quota(int(request.path_params["id"]), int(data.get("value", 0))))

async def add_quota(request):
    data = await request.json()
    return _ok(await store.add_quota(int(request.path_params["id"]), int(data.get("value", 0))))

async def reset_usage(request):
    return _ok(await store.reset_usage(int(request.path_params["id"])))


def api_routes() -> list:
    return [
        Route("/api/bootstrap",                    bootstrap,          methods=["GET"]),
        Route("/api/stream",                       stream,             methods=["GET"]),
        Route("/api/notify/test",                  notify_test,        methods=["POST"]),
        Route("/api/biz",                          biz_data,           methods=["GET"]),
        Route("/api/biz/skillrun/{id:str}",        biz_skillrun,       methods=["GET"]),
        Route("/api/biz/profile",                  biz_save_profile,   methods=["POST"]),
        Route("/api/biz/intake",                   biz_intake,         methods=["POST"]),
        Route("/api/biz/skillrun/{id:str}/rate",   biz_skillrun_rate,  methods=["POST"]),
        Route("/api/biz/skillrun/save",            biz_skillrun_save,  methods=["POST"]),
        Route("/api/biz/skillruns",                biz_skill_versions, methods=["GET"]),
        Route("/api/biz/skillrun/{id:str}/patch",  biz_skillrun_patch, methods=["POST"]),
        Route("/api/biz/agent",                    biz_agent_run,      methods=["POST"]),
        Route("/api/biz/ads",                      biz_ads,            methods=["GET"]),
        Route("/api/biz/fb/connect-url",           biz_fb_connect_url, methods=["GET"]),
        Route("/api/chat",                         chat,               methods=["POST"]),
        Route("/api/chat/history",                 chat_history,       methods=["GET"]),
        Route("/api/tracked",                      add_tracked,        methods=["POST"]),
        Route("/api/tracked/{id:int}",             del_tracked,        methods=["DELETE"]),
        Route("/api/jobs/{name:str}/toggle",       toggle_job,         methods=["POST"]),
        Route("/api/optimizations/{id:int}/apply", apply_optimization, methods=["POST"]),
        Route("/api/alerts/{id:int}/dismiss",      dismiss_alert,      methods=["POST"]),
        Route("/api/settings",                     set_setting,        methods=["POST"]),
        Route("/api/campaigns",                    add_campaign,       methods=["POST"]),
        Route("/api/campaigns/{id:int}",           del_campaign,       methods=["DELETE"]),
        Route("/api/calendar",                     add_calendar_post,  methods=["POST"]),
        Route("/api/calendar/{id:int}",            del_calendar_post,  methods=["DELETE"]),
        Route("/api/content/generate",             generate_content,   methods=["POST"]),
        Route("/api/reports",                      add_report,         methods=["POST"]),
        Route("/api/reports/{id:int}",             del_report,         methods=["DELETE"]),
        Route("/api/accounts",                     connect_account,    methods=["POST"]),
        Route("/api/accounts/{id:int}/toggle",     toggle_account,     methods=["POST"]),
        Route("/api/accounts/{id:int}",            disconnect_account, methods=["DELETE"]),
        Route("/api/users/{id:int}/quota",         set_quota,          methods=["POST"]),
        Route("/api/users/{id:int}/addquota",      add_quota,          methods=["POST"]),
        Route("/api/users/{id:int}/reset",         reset_usage,        methods=["POST"]),
    ]
