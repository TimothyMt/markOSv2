"""
Surgical edit — sửa CHÍNH XÁC 1 section / sub-point trong output chiến lược
(StrategySynthesis 10 sections, hoặc Campaign Brief) mà KHÔNG làm lại cả file.

Cơ chế hybrid:
  - (b) Comment đủ rõ "đổi gì → thành gì" → patch luôn.
  - (a) Comment mơ hồ ("phần này chưa ổn") → trả về câu hỏi để Max hỏi lại.

Granularity: section + sub-point. Detector chỉ ra section nào (theo số ## N.)
và sub-point bên trong; rewriter chỉ viết lại đúng đoạn đó rồi ghép lại,
giữ nguyên các section khác.
"""
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Kết quả patch
PATCH_OK = "patched"      # đã sửa, kèm full text mới
PATCH_ASK = "ask"         # comment mơ hồ — cần hỏi lại user
PATCH_NOOP = "noop"       # không tìm thấy section khớp / lỗi → giữ nguyên

_SECTION_RE = re.compile(r'^(#{1,3})\s+(\d+)\.\s+(.+)$', re.MULTILINE)


def split_sections(text: str) -> list[dict]:
    """Tách output thành list section theo heading '## N. Title'.

    Returns: [{num: int, title: str, heading: str, body: str, start: int, end: int}]
    Phần text trước section đầu tiên (preamble) bỏ qua khi ghép — giữ riêng.
    """
    matches = list(_SECTION_RE.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append({
            "num": int(m.group(2)),
            "title": m.group(3).strip(),
            "heading": m.group(0).strip(),
            "body": text[start:end].rstrip(),
            "start": start,
            "end": end,
        })
    return sections


def _sections_outline(sections: list[dict]) -> str:
    """Bản tóm tắt section list để feed cho detector."""
    return "\n".join(f"{s['num']}. {s['title']}" for s in sections)


_DETECT_SYSTEM = """Bạn là bộ định tuyến chỉnh sửa tài liệu. Người dùng vừa đọc 1 tài liệu chiến lược marketing (có các section đánh số) và đưa ra nhận xét/yêu cầu sửa.

Nhiệm vụ: Phân tích nhận xét → xác định CHÍNH XÁC cần sửa section nào, và yêu cầu sửa là gì.

QUY TẮC:
- Nếu nhận xét nêu RÕ "đổi gì → thành gì" (đủ thông tin để sửa) → trả targets, clear=true.
- Nếu nhận xét MƠ HỒ (chỉ nói "phần này chưa ổn", "section X chưa đúng" mà KHÔNG nói sửa thế nào) → clear=false và đặt 1 câu hỏi ngắn để làm rõ.
- 1 nhận xét có thể chạm NHIỀU section. Liệt kê hết.
- sub_point: mô tả ngắn đoạn con bên trong section cần sửa (vd "USP chính", "Variant B", "budget %"). Nếu sửa cả section thì để "toàn section".

Chỉ trả JSON, không giải thích:
{
  "clear": true/false,
  "clarify_question": "câu hỏi nếu clear=false, còn lại để rỗng",
  "targets": [
    {"section_num": <int>, "sub_point": "<mô tả>", "instruction": "<yêu cầu sửa cụ thể>"}
  ]
}"""


async def detect_edit_target(comment: str, sections: list[dict]) -> dict:
    """Dùng router (Haiku-class) phân tích comment → target sections.

    Returns dict: {clear, clarify_question, targets:[{section_num, sub_point, instruction}]}
    """
    from tools.llm_router import call, TaskType

    outline = _sections_outline(sections)
    user = (
        f"DANH SÁCH SECTION:\n{outline}\n\n"
        f"NHẬN XÉT CỦA NGƯỜI DÙNG:\n{comment.strip()}\n\n"
        f"Trả JSON theo schema."
    )
    try:
        res = await call(
            task_type=TaskType.CLASSIFICATION,
            system=_DETECT_SYSTEM,
            user=user,
            max_tokens=1024,
        )
        raw = (res.get("output") or "").strip()
        # Bóc JSON khỏi code fence nếu có
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            raw = m.group(0)
        data = json.loads(raw)
    except Exception as e:
        logger.warning("detect_edit_target: parse failed (%s) — fallback ask", e)
        return {
            "clear": False,
            "clarify_question": "Sếp muốn em chỉnh phần nào, và đổi thành hướng nào ạ? Cho em cụ thể chút.",
            "targets": [],
        }

    data.setdefault("clear", False)
    data.setdefault("clarify_question", "")
    data.setdefault("targets", [])
    return data


_REWRITE_SYSTEM = """Bạn là biên tập viên chiến lược marketing. Nhiệm vụ: viết lại MỘT section theo yêu cầu chỉnh sửa của sếp.

QUY TẮC CỨNG:
- CHỈ viết lại đúng section được đưa. GIỮ NGUYÊN dòng heading (## N. Title).
- Giữ nguyên cấu trúc/format (bullet, bold, sub-heading) — chỉ đổi nội dung theo yêu cầu.
- Áp dụng đúng yêu cầu sửa, KHÔNG tự ý đổi phần không liên quan trong section.
- KHÔNG thêm lời dẫn ("Đây là section đã sửa..."). Trả thẳng nội dung section đã sửa.
- Viết tiếng Việt, giọng tư vấn chuyên nghiệp."""


async def _rewrite_section(section: dict, instructions: list[str]) -> Optional[str]:
    """Viết lại 1 section theo các instruction. Returns body mới hoặc None nếu lỗi."""
    from tools.llm_router import call, TaskType

    instr_block = "\n".join(f"- {x}" for x in instructions if x)
    user = (
        f"SECTION HIỆN TẠI:\n{section['body']}\n\n"
        f"YÊU CẦU SỬA:\n{instr_block}\n\n"
        f"Viết lại section (giữ nguyên dòng heading '{section['heading']}')."
    )
    try:
        res = await call(
            task_type=TaskType.GENERIC_CREATIVE,
            system=_REWRITE_SYSTEM,
            user=user,
            max_tokens=4000,
        )
        out = (res.get("output") or "").strip()
        out = re.sub(r'^```\w*\s*|\s*```$', '', out, flags=re.MULTILINE).strip()
        return out or None
    except Exception as e:
        logger.warning("_rewrite_section #%s failed: %s", section.get("num"), e)
        return None


async def patch_document(text: str, comment: str) -> tuple[str, str, dict]:
    """Orchestrate: detect → (ask | patch).

    Returns (status, payload, meta):
      - (PATCH_ASK, clarify_question, detect_data)  — comment mơ hồ
      - (PATCH_OK, new_full_text, detect_data)      — đã patch
      - (PATCH_NOOP, original_text, detect_data)    — không khớp section nào
    """
    sections = split_sections(text)
    if not sections:
        return PATCH_NOOP, text, {"reason": "no_sections"}

    detect = await detect_edit_target(comment, sections)

    if not detect.get("clear", False):
        q = detect.get("clarify_question") or "Sếp muốn em chỉnh phần nào, đổi thành hướng nào ạ?"
        return PATCH_ASK, q, detect

    # Gom instruction theo section_num
    by_num: dict[int, list[str]] = {}
    for t in detect.get("targets", []):
        try:
            num = int(t.get("section_num"))
        except (TypeError, ValueError):
            continue
        instr = t.get("instruction") or ""
        sub = t.get("sub_point") or ""
        full_instr = f"[{sub}] {instr}" if sub and sub != "toàn section" else instr
        by_num.setdefault(num, []).append(full_instr)

    if not by_num:
        return PATCH_NOOP, text, detect

    sec_by_num = {s["num"]: s for s in sections}
    patched_bodies: dict[int, str] = {}
    for num, instrs in by_num.items():
        sec = sec_by_num.get(num)
        if not sec:
            logger.info("patch_document: section #%s không tồn tại — skip", num)
            continue
        new_body = await _rewrite_section(sec, instrs)
        if new_body:
            patched_bodies[num] = new_body

    if not patched_bodies:
        return PATCH_NOOP, text, detect

    # Ghép lại: thay body của các section đã patch, giữ nguyên phần còn lại
    out_parts = []
    preamble = text[:sections[0]["start"]].rstrip()
    if preamble:
        out_parts.append(preamble)
    for s in sections:
        out_parts.append(patched_bodies.get(s["num"], s["body"]))

    new_text = "\n\n".join(out_parts)
    return PATCH_OK, new_text, detect


def summarize_changes(detect: dict) -> str:
    """Tạo dòng tóm tắt 'đã sửa gì' để báo user."""
    targets = detect.get("targets", [])
    if not targets:
        return "Đã cập nhật."
    lines = []
    for t in targets:
        num = t.get("section_num", "?")
        sub = t.get("sub_point") or "toàn section"
        lines.append(f"  • Section {num} ({sub})")
    return "Đã sửa:\n" + "\n".join(lines)
