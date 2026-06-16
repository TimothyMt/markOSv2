"""
JSON API cho web dashboard. Mount vào Starlette (run_web.py hoặc bot/main.py).

Hợp đồng: GET /api/bootstrap trả về phần dữ liệu "động" mà frontend dùng để
override lên dữ liệu mock tĩnh. Các endpoint còn lại thực hiện thao tác ghi và
trả về toàn bộ state mới để frontend render lại.
"""
from starlette.responses import JSONResponse
from starlette.routing import Route

from webapp import store


async def bootstrap(request):
    return JSONResponse(store.get_state())


async def add_tracked(request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    return JSONResponse(store.add_tracked(name))


async def del_tracked(request):
    return JSONResponse(store.del_tracked(int(request.path_params["id"])))


async def toggle_job(request):
    return JSONResponse(store.toggle_job(request.path_params["name"]))


async def apply_optimization(request):
    return JSONResponse(store.remove_optimization(int(request.path_params["id"])))


async def dismiss_alert(request):
    return JSONResponse(store.dismiss_alert(int(request.path_params["id"])))


async def set_setting(request):
    data = await request.json()
    key = data.get("key")
    value = int(data.get("value", 0))
    if not key:
        return JSONResponse({"error": "key required"}, status_code=400)
    return JSONResponse(store.set_setting(key, value))


def api_routes() -> list:
    return [
        Route("/api/bootstrap",                    bootstrap,           methods=["GET"]),
        Route("/api/tracked",                      add_tracked,         methods=["POST"]),
        Route("/api/tracked/{id:int}",             del_tracked,         methods=["DELETE"]),
        Route("/api/jobs/{name:str}/toggle",       toggle_job,          methods=["POST"]),
        Route("/api/optimizations/{id:int}/apply", apply_optimization,  methods=["POST"]),
        Route("/api/alerts/{id:int}/dismiss",      dismiss_alert,       methods=["POST"]),
        Route("/api/settings",                     set_setting,         methods=["POST"]),
    ]
