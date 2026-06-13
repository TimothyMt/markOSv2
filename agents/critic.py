"""
Critic Review Layer — Sonnet reviews agent output before sending to user.
Catches hallucinations: fabricated stats, internal contradictions, fake citations.
Post-processes to add hyperlinks for known VN data sources.
"""
import re
import logging
import anthropic

from config import CLAUDE_HAIKU_MODEL, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


CRITIC_SYSTEM = """Bạn là silent editor — fix các lỗi factual trong output của AI advisor cho founder VN.

**⚠️ CRITICAL — ĐỌC KỸ:**
- Bạn KHÔNG phải là reviewer viết report.
- Bạn KHÔNG được output các header kiểu "REVIEW HOÀN THÀNH", "Kết quả kiểm tra", "✅ OK", "❌ Issue".
- Bạn KHÔNG được tóm tắt những gì đã check.
- Bạn KHÔNG được nói "Output này không có vấn đề" hay tương tự.

**NHIỆM VỤ DUY NHẤT:**
Trả về NGUYÊN VĂN output user gửi, CHỈ sửa các lỗi sau (in-place edit):

**1. Số liệu bịa / không hợp lý**
- Số quá tròn (50000, 1 triệu) → đổi thành range hợp lý (~45-55K, 0.8-1.2M)
- Số không hợp lý cho VN (TAM F&B "100 tỷ USD") → đổi sang số đúng
- Thêm "(ước tính)" sau số nếu không có nguồn
- MỌI con số định lượng (market size, CAGR, growth rate, số liệu ngành...) phải có
  NGAY SAU NÓ trong cùng câu: hyperlink tới nguồn cụ thể, HOẶC nhãn "(ước tính)".
  Một danh sách "Nguồn tham khảo" ở cuối bài KHÔNG đủ — nếu con số nào "trần"
  (không hyperlink, không "(ước tính)") thì thêm "(ước tính)" ngay sau nó.

**2. Mâu thuẫn nội bộ**
- 2 số khác nhau cho cùng 1 thứ → giữ 1 version hợp lý, sửa version còn lại

**3. Cite nguồn không tồn tại**
- "Báo cáo XYZ Vietnam 2025" mà tổ chức không có report đó → xóa cite, đổi "industry estimate"
- Nguồn thật (Statista, GSO, Nielsen) → giữ nguyên

**4. Brand claim cụ thể nghi bịa**
- "Cocoon có 50,000 customers" → "các brand local lớn" hoặc xóa con số

**5. Over-claim không có evidence**
- Câu absolute không có hậu thuẫn: "Chắc chắn tăng 300% doanh thu" / "100% khách hài lòng" / "Tốt nhất Việt Nam"
- → Soften: "có khả năng tăng doanh thu" / "đa số khách phản hồi tích cực" / "trong nhóm chất lượng cao"
- Câu absolute về tương lai: "Sẽ trở thành unicorn" → "Có tiềm năng tăng trưởng mạnh"
- Câu "luôn", "không bao giờ", "tất cả mọi người" → soften thành "thường", "ít khi", "phần lớn"

**6. Câu cần evidence nhưng chưa cite**
- Số liệu thị trường không có nguồn → thêm "(ước tính ngành)"
- Claim về behavior người dùng → thêm "theo benchmark" hoặc xóa

**OUTPUT FORMAT:**
- Trả về CHÍNH XÁC output gốc, chỉ thay text ở những chỗ cần sửa.
- Nếu KHÔNG có lỗi gì → trả về NGUYÊN VĂN output gốc, KHÔNG thay đổi 1 chữ nào.
- KHÔNG thêm preamble ("Đây là output sau review:", "Tôi đã sửa các lỗi sau:")
- KHÔNG thêm postamble ("Output trên đã được review", "Kết luận:")
- KHÔNG thay đổi cấu trúc, headings, bullets, tables.

Output bắt đầu trực tiếp bằng ký tự đầu tiên của output gốc."""


# Patterns chỉ ra Critic đã write meta-review thay vì sửa output
META_REVIEW_PATTERNS = [
    r"REVIEW HOÀN THÀNH",
    r"Kết quả kiểm tra",
    r"không chứa các vấn đề chính",
    r"Output này\s+\*?\*?(không|đã)",
    r"^[✅❌]\s*(OK|Issue|Phát hiện)",
    r"đã được review",
    r"theo \d tiêu chí",
]
_META_REVIEW_RE = re.compile("|".join(META_REVIEW_PATTERNS), re.IGNORECASE | re.MULTILINE)


def _looks_like_meta_review(text: str) -> bool:
    """Detect nếu Critic output là meta-review chứ không phải reviewed output."""
    if not text:
        return False
    head = text[:500]
    return bool(_META_REVIEW_RE.search(head))


# Mapping nguồn data VN phổ biến → URL chính thức
# Critic giữ tên nguồn, post-process inject hyperlink
KNOWN_SOURCES: dict[str, str] = {
    "Statista":              "https://www.statista.com/markets/vietnam/",
    "GSO":                   "https://www.gso.gov.vn/en/",
    "Tổng cục Thống kê":     "https://www.gso.gov.vn/",
    "WorldBank":             "https://www.worldbank.org/en/country/vietnam",
    "World Bank":            "https://www.worldbank.org/en/country/vietnam",
    "Nielsen":               "https://www.nielsen.com/vn/",
    "Q&Me":                  "https://qandme.net/en/",
    "Decision Lab":          "https://www.decisionlab.co/",
    "Vietcetera":            "https://vietcetera.com/",
    "CafeF":                 "https://cafef.vn/",
    "VnEconomy":             "https://vneconomy.vn/",
    "Brands Vietnam":        "https://www.brandsvietnam.com/",
    "Advertising Vietnam":   "https://advertisingvietnam.com/",
    "iPrice":                "https://iprice.vn/insights/",
    "Cốc Cốc":               "https://coccoc.com/",
    "Adsota":                "https://adsota.com/",
    "Kantar":                "https://www.kantar.com/vi/",
}


def _add_hyperlinks(text: str) -> str:
    """Pattern match known VN sources, add Markdown hyperlinks if not already linked."""
    for source, url in KNOWN_SOURCES.items():
        # Match source name not already inside a Markdown link [text](url)
        # Negative lookbehind: not preceded by '['
        # Negative lookahead: not immediately followed by ']('
        # Only replace first occurrence per source to avoid spamming
        pattern = rf'(?<!\[){re.escape(source)}(?!\])'
        if re.search(pattern, text):
            text = re.sub(pattern, f'[{source}]({url})', text, count=1)
    return text


async def run_critic(agent_output: str, agent_name: str = "agent", session=None) -> str:
    """Run critic review on agent output, return reviewed text with hyperlinks.

    session: nếu truyền vào → track token Haiku của critic dưới cùng job_seq
             (để footer hiện đúng "nhiều API cùng làm job").
    """
    if not agent_output or not agent_output.strip():
        return agent_output

    try:
        client = _get_client()
        response = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=5000,
            system=[
                {
                    "type": "text",
                    "text": CRITIC_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": agent_output}],
        )

        # Track critic token usage (Haiku) dưới cùng job hiện tại
        if session is not None:
            try:
                from tools.token_tracker import track_skill
                from tools.llm_router import Provider
                usage = response.usage
                track_skill(
                    session,
                    skill_name=f"{agent_name}_critic",
                    provider=Provider.ANTHROPIC_HAIKU.value,
                    input_tok=getattr(usage, "input_tokens", 0) or 0,
                    output_tok=getattr(usage, "output_tokens", 0) or 0,
                    cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
                    cache_create=getattr(usage, "cache_creation_input_tokens", 0) or 0,
                )
            except Exception as _e:
                logger.warning("Critic token track failed: %s", _e)

        reviewed = response.content[0].text
        if not reviewed or not reviewed.strip():
            logger.warning("Critic returned empty for %s, falling back to original", agent_name)
            return agent_output

        # Safety: nếu Haiku misbehave và viết meta review → dùng original
        if _looks_like_meta_review(reviewed):
            logger.warning("Critic [%s] returned meta-review, falling back to original output", agent_name)
            return _add_hyperlinks(agent_output)

        # Sanity check: reviewed output không nên ngắn hơn đáng kể so với original
        if len(reviewed) < len(agent_output) * 0.4:
            logger.warning(
                "Critic [%s] output too short (%d vs original %d), falling back",
                agent_name, len(reviewed), len(agent_output),
            )
            return _add_hyperlinks(agent_output)

        # Post-process: add hyperlinks for known sources
        reviewed = _add_hyperlinks(reviewed)
        return reviewed
    except Exception as e:
        logger.warning("Critic failed for %s: %s — using original output", agent_name, e)
        return agent_output
