"""
Smoke tests cho web API + business layer.

Mục tiêu (đóng điểm yếu "không có test"): kiểm route được khai báo đủ và lớp
business degrade AN TOÀN khi không có Supabase (trả {}/{"error"}, không raise).

Chạy: `pytest tests/test_web_api.py`  HOẶC  `python tests/test_web_api.py`
(không cần pytest — có runner ở cuối).
"""
import asyncio
import os
import sys

# Đảm bảo không vô tình bật Supabase trong test
for _k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY"):
    os.environ.pop(_k, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.api import api_routes          # noqa: E402
from webapp import business as biz         # noqa: E402


def _paths() -> set:
    return {r.path for r in api_routes()}


def test_core_routes_present():
    need = ["/api/bootstrap", "/api/stream", "/api/chat", "/api/chat/history",
            "/api/biz", "/api/biz/ads", "/api/biz/skillrun/{id:str}", "/api/biz/agent"]
    missing = [p for p in need if p not in _paths()]
    assert not missing, f"Thiếu route: {missing}"


def test_business_degrades_without_supabase():
    # skill_run_content → {} ; rate_skill_run → {"error"} ; KHÔNG raise
    assert asyncio.run(biz.skill_run_content("nope")) == {}
    r = asyncio.run(biz.rate_skill_run("nope", 5))
    assert isinstance(r, dict) and ("error" in r or r.get("ok") is False)


def test_standalone_build_has_doc_reader():
    from webapp.build_standalone import build
    html = build()
    assert "P.doc" in html, "Trang đọc riêng #doc chưa có trong bundle"
    assert "data-act=\"open-doc\"" in html or "#doc/" in html, "Chưa có lối vào trang đọc"


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL  {name}: {e}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{'OK' if not failed else f'{failed} FAILED'}")
    sys.exit(1 if failed else 0)
