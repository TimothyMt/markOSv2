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


def test_intake_suggest_route_present():
    """D-032 step 2: endpoint sinh chip gợi ý câu chiến lược."""
    assert "/api/biz/intake/suggest" in _paths(), "Thiếu route /api/biz/intake/suggest"


def test_intake_suggest_degrades_without_llm():
    """D-032: thiếu context → {} ; không raise."""
    assert asyncio.run(biz.intake_suggestions({})) == {}


def test_context_string_labels_inferred_fields():
    """D-032 step 3: to_context_string render câu chiến lược + nhãn (giả định) cho inferred."""
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "_models_isolated", os.path.join(_ROOT, "storage", "models.py"))
    _m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    BusinessProfile = _m.BusinessProfile
    p = BusinessProfile(
        industry="thời trang", product_service="đồ nhà plus-size", target_customer="nữ 25-45",
        intake_extra={"answers": {"jtbd": "mặc thoải mái ở nhà"},
                      "provenance": {"jtbd": "typed", "objection": "inferred",
                                     "competitive_alternative": "inferred"}},
    )
    out = p.to_context_string()
    assert "Job-to-be-done" in out and "mặc thoải mái" in out, "Câu chiến lược chưa vào context"
    assert "GIẢ ĐỊNH" in out and "Rào cản" in out, "Field inferred chưa được gắn nhãn giả định"
    assert "Job-to-be-done của khách" not in out.split("GIẢ ĐỊNH")[1], "typed bị gắn nhãn nhầm"


def test_editor_routes_present():
    # T2-T4: save (sửa tay), skillruns (lịch sử), patch (nhờ Max chỉnh)
    p = _paths()
    need = ["/api/biz/skillrun/save", "/api/biz/skillruns", "/api/biz/skillrun/{id:str}/patch"]
    missing = [x for x in need if x not in p]
    assert not missing, f"Thiếu route editor: {missing}"


def test_business_degrades_without_supabase():
    # Mọi hàm business → {}/{"error"}/[] ; KHÔNG raise khi không có Supabase
    assert asyncio.run(biz.skill_run_content("nope")) == {}
    r = asyncio.run(biz.rate_skill_run("nope", 5))
    assert isinstance(r, dict) and ("error" in r or r.get("ok") is False)
    s = asyncio.run(biz.save_skill_edit(1, "competitor", "noi dung"))
    assert isinstance(s, dict) and "error" in s
    assert asyncio.run(biz.list_skill_versions(1, "competitor")) == []
    pt = asyncio.run(biz.patch_skill_run("nope", "viết ngắn hơn"))
    assert isinstance(pt, dict) and ("error" in pt or pt.get("status"))


def test_standalone_build_has_doc_reader():
    from webapp.build_standalone import build
    html = build()
    assert "P.doc" in html, "Trang đọc riêng #doc chưa có trong bundle"
    assert "data-act=\"open-doc\"" in html or "#doc/" in html, "Chưa có lối vào trang đọc"


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
        return f.read()


def test_static_wizard_covers_discovery_fields():
    """A1: static wizard phải hỏi đủ các trường discovery.REQUIRED_FIELDS."""
    import re
    disc = _read("agents/discovery.py")
    m = re.search(r"REQUIRED_FIELDS\s*=\s*\[(.*?)\]", disc, re.S)
    assert m, "Không tìm thấy REQUIRED_FIELDS trong discovery.py"
    required = set(re.findall(r"[\"']([a-z_]+)[\"']", m.group(1)))
    app = _read("web/app.js")
    blk = re.search(r"const INTAKE_STEPS\s*=\s*\[(.*?)\n\s*\];", app, re.S)
    assert blk, "Không tìm thấy INTAKE_STEPS trong app.js"
    wizard_keys = set(re.findall(r"key:\s*'([a-z_]+)'", blk.group(1)))
    missing = required - wizard_keys
    assert not missing, f"Static wizard thiếu trường discovery: {missing}"


def test_strategy_no_dead_maxchat_and_has_occasion_bridge():
    """C2 + B3: gỡ nút chết Max-chat; có cầu nối occasion."""
    from webapp.build_standalone import build
    html = build()
    assert "Trò chuyện với Max" not in html, "Còn nút Max-chat (đã bỏ theo D-026/C2)"
    assert 'href="#home"' not in html, "Còn link chết #home"
    assert "P.occasion" in html and "#occasion" in html, "Thiếu cầu nối Lập chiến dịch theo dịp (B3)"


def test_synthesis_prompt_is_directional():
    """B0/D-030: prompt synthesis nêu định hướng, KHÔNG ép SMART số cứng ở M0."""
    p = _read("agents/prompts.py")
    assert "Mục Tiêu Định Hướng Theo Giai Đoạn" in p, "Section 4 chưa đổi sang định hướng"
    assert "Chỉ Số Cần Theo Dõi" in p, "Section 7 KPI chưa đổi sang 'cần theo dõi'"
    assert "## 4. SMART Goals (2-3 goals" not in p, "Section 4 vẫn còn SMART số cứng cũ"


def test_tows_only_in_swot_not_tactical():
    """D-031: TOWS (SO/WO/ST/WT) là cấu trúc CHỈ ở SWOT/T3, KHÔNG ở Tactical/T5."""
    swot = _read("agents/prompts.py")
    tac = _read("agents/strategy_prompts.py")
    # T3 SWOT vẫn có ma trận TOWS đủ 4 ô
    assert "MA TRẬN CHIẾN LƯỢC (TOWS)" in swot, "SWOT mất heading ma trận TOWS"
    for q in ("### SO —", "### WO —", "### ST —", "### WT —"):
        assert q in swot, f"SWOT thiếu ô TOWS: {q}"
    # T5 Tactical KHÔNG còn dùng SO/WO/WT làm heading cấu trúc
    for bad in ("## SO —", "## WO —", "## WT —", "## ST —"):
        assert bad not in tac, f"Tactical vẫn dùng TOWS làm cấu trúc: {bad}"


def test_tactical_uses_funnel_skeleton():
    """D-031 C1: Tactical đổi xương sống sang Segment → Phễu (TOFU/MOFU/BOFU)."""
    tac = _read("agents/strategy_prompts.py")
    for stage in ("TOFU", "MOFU", "BOFU"):
        assert stage in tac, f"Tactical thiếu tầng phễu: {stage}"
    assert "phục vụ SO" in tac, "Tactical thiếu cơ chế tag TOWS (phục vụ SOx)"


def test_tactical_no_absolute_money_in_template():
    """D-031 4a: T5 bỏ số tiền tuyệt đối trong khung test (chỉ còn rule cấm)."""
    tac = _read("agents/strategy_prompts.py")
    # Dòng duy nhất được phép chứa "triệu/tuần" là rule CẤM nó.
    offenders = [ln for ln in tac.splitlines()
                 if "triệu/tuần" in ln and "KHÔNG ghi số tiền" not in ln]
    assert not offenders, f"T5 còn số tiền tuyệt đối ngoài rule cấm: {offenders}"


def test_archetype_banner_has_antifabrication_guard():
    """D-031 D1: banner archetype không được bịa segment/đối thủ (vd Gen Z/Zara)."""
    h = _read("bot/html_report.py")
    assert "CHỐNG BỊA" in h, "Banner LLM thiếu guard chống bịa"
    assert "context_snippets:" in h and "data = None" in h, \
        "Không có guard bỏ LLM khi thiếu context (dễ bịa nhất)"


def test_ai_renderer_supports_tables():
    """D-034 #1: renderAIContent render bảng markdown (không còn pipe thô)."""
    app = _read("web/app.js")
    assert "tbl-wrap" in app and "isRow" in app and "isSep" in app, \
        "renderAIContent chưa có parser bảng"
    assert "blockquote" in app, "renderAIContent chưa hỗ trợ blockquote"


def test_strategy_single_output_card():
    """D-037a: trang strategy không còn agentBar trùng (gộp 1 card)."""
    import re
    app = _read("web/app.js")
    m = re.search(r"P\.strategy\s*=\s*\{.*?\n  \};", app, re.S)
    assert m, "Không tìm thấy P.strategy"
    assert "agentBar('strategy'" not in m.group(0), \
        "P.strategy còn agentBar (output hiện 2 chỗ)"


def test_intake_uses_textarea():
    """D-032 §11: ô gõ intake là textarea (tự giãn/wrap), không phải input 1 dòng."""
    app = _read("web/app.js")
    assert 'textarea id="intakeBox"' in app, "Ô intake chưa đổi sang textarea"


def test_synthesis_slot_filled_and_pagenav():
    """Fix: slot synthesis được nạp (fillSkillRunSlots); có nút chuyển tab trước/sau."""
    app = _read("web/app.js")
    assert "fillSkillRunSlots" in app and "data-skill-run" in app, "Thiếu filler synthesis slot"
    assert "injectPageNav" in app and "PAGE_SEQ" in app, "Thiếu nút chuyển tab trước/sau"


def test_tactical_page_and_mock_cleaned():
    """D-038A + D-034 #3: có trang Tactical Playbook; dọn mock F&B ở trang phân tích."""
    app = _read("web/app.js")
    data = _read("web/data.js")
    assert "P.tactical" in app and "tactical_playbook" in app, "Thiếu trang Tactical Playbook"
    assert "id: 'tactical'" in data, "Sidebar chưa có mục Tactical Playbook"
    # mock F&B ở trang phân tích đã gỡ
    assert "Benchmark ngành F&B" not in app, "Còn mock Benchmark F&B ở trang market"
    assert "Tactical plays (SO/WO/ST/WT)" not in app, "Còn mock Tactical plays ở SWOT"
    assert "miniStat('TAM','2.400 tỷ'" not in app, "Còn mock TAM/SAM/SOM cứng"


def test_posmap_converter_and_rail_removed():
    """D-034 #4 + rail: ASCII map → visual; bỏ rail phải (main rộng hơn)."""
    app = _read("web/app.js")
    css = _read("web/styles.css")
    assert "enhancePosMaps" in app and "mq-plot" in app and "mq-dot" in app, "Thiếu converter Positioning Map (Magic Quadrant)"
    assert "248px 1fr;" in css, "Layout chưa bỏ cột rail (vẫn 3 cột)"
    assert ".rail { display: none; }" in css, "Rail phải chưa ẩn"


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
