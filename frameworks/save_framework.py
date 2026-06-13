"""
SAVE Framework generator — thay thế 4P truyền thống (Product/Price/Place/Promotion)
bằng góc nhìn từ phía khách hàng: Solution / Access / Value / Education
"""


SAVE_DEFINITIONS = {
    "S": {
        "name": "Solution (Giải pháp)",
        "old": "Product",
        "principle": "Frame sản phẩm theo vấn đề nó giải quyết, không phải tính năng của nó.",
        "questions": [
            "Vấn đề cụ thể nào của khách hàng sản phẩm/dịch vụ này giải quyết?",
            "Khách hàng đang dùng gì thay thế trước khi có sản phẩm của bạn?",
            "Kết quả cụ thể nào khách hàng đạt được sau khi dùng?",
            "Pain point nào khiến họ sẵn sàng trả tiền ngay hôm nay?",
        ],
        "messaging_template": "Giúp [ICP] [đạt được kết quả X] mà không cần [nỗi đau/rào cản Y]",
    },
    "A": {
        "name": "Access (Tiếp cận)",
        "old": "Place",
        "principle": "Tối ưu cách khách hàng tiếp cận và mua, không phải kênh phân phối của bạn.",
        "questions": [
            "Khách hàng muốn mua theo cách nào tiện nhất cho họ?",
            "Kênh nào họ đang có mặt nhiều nhất?",
            "Rào cản nào trong quá trình mua cần được loại bỏ?",
            "Họ cần hỗ trợ gì trong quá trình ra quyết định?",
        ],
        "messaging_template": "Có thể [mua/dùng/trải nghiệm] ngay tại [nơi họ đang ở] — không cần [rào cản]",
    },
    "V": {
        "name": "Value (Giá trị)",
        "old": "Price",
        "principle": "Communicate total value nhận được, không phải số tiền phải trả.",
        "questions": [
            "ROI hoặc kết quả đo được là gì khi dùng sản phẩm?",
            "So sánh với alternative (làm tay, thuê người, không làm), cost bao nhiêu?",
            "Có thể anchor với một cái gì đó đắt hơn để làm giá trông reasonable hơn không?",
            "Perceived value tăng nếu đóng gói thêm gì?",
        ],
        "messaging_template": "Chỉ [giá] để [đạt kết quả X trị giá Y] — so với [alternative đắt hơn nhiều]",
    },
    "E": {
        "name": "Education (Giáo dục)",
        "old": "Promotion",
        "principle": "Thay vì quảng cáo, hãy dạy khách hàng tại sao họ cần giải pháp này TRƯỚC KHI pitch.",
        "questions": [
            "Khách hàng cần hiểu điều gì trước khi họ sẵn sàng mua?",
            "Misconception phổ biến nhất về sản phẩm/ngành là gì?",
            "Content nào sẽ khiến họ nhận ra vấn đề họ đang có?",
            "Cách nào để educate mà không bị coi là spam quảng cáo?",
        ],
        "messaging_template": "Bạn có biết [insight gây shock/tò mò]? Đó là lý do [giải pháp] tồn tại.",
    },
}


SAVE_INDUSTRY_EXAMPLES = {
    "fnb": {
        "S": "Không chỉ là quán cà phê — là nơi founder/remote worker làm việc hiệu quả với wifi tốt, ổ điện đầy đủ, và không bị rush.",
        "A": "Đặt bàn qua Zalo OA, order qua app không cần gọi nhân viên, nhận ưu đãi ngay khi check-in.",
        "V": "120k/người/buổi chiều, bao gồm 2 thức uống + không gian làm việc yên tĩnh = rẻ hơn thuê co-working 300k.",
        "E": "Bạn có biết 73% cuộc họp online thất bại vì môi trường xung quanh ồn ào? Đây là checklist chọn quán cà phê làm việc lý tưởng.",
    },
    "tech_saas": {
        "S": "Không phải phần mềm CRM — là công cụ giúp sales team không bao giờ bỏ sót follow-up, tự động nhắc đúng lúc.",
        "A": "Dùng ngay trên trình duyệt, không cần cài đặt. Onboard trong 15 phút. Import data từ Excel một click.",
        "V": "3 triệu/tháng. Sales team tăng close rate 25% = thêm 50 triệu/tháng doanh thu. ROI 16x trong tháng đầu.",
        "E": "80% deals bị thua vì follow-up quá muộn hoặc quên. Đây là data từ 1,200 sales team VN chúng tôi khảo sát.",
    },
    "ecommerce": {
        "S": "Không phải mua quần áo — là cảm giác tự tin mặc đẹp mà không tốn thời gian đến trung tâm thương mại.",
        "A": "Order trước 10pm, nhận ngay sáng hôm sau. Đổi trả miễn phí 30 ngày — mua xong rồi mới quyết.",
        "V": "Giá tương đương, chất lượng cao hơn hàng mall, cộng thêm free shipping và đổi trả dễ dàng.",
        "E": "Hướng dẫn chọn size chuẩn không cần thử — 89% khách hàng dùng guide này không cần đổi hàng.",
    },
    "education": {
        "S": "Không phải khóa học marketing — là lộ trình từ 0 đến job offer đầu tiên trong 90 ngày, có mentor 1-1.",
        "A": "Học live tối thứ 3, 5 + replay 24/7. Tham gia cộng đồng Slack hỏi đáp bất kỳ lúc nào.",
        "V": "12 triệu đầu tư. Alumni trung bình tăng lương 40% sau 6 tháng = hoàn vốn trong 3 tháng đầu đi làm.",
        "E": "90% người học marketing online tự học nhưng không có job sau 12 tháng. Đây là điểm khác biệt của có mentor.",
    },
}


def generate_save_analysis(
    industry: str,
    business_description: str,
    target_customer: str,
    product_service: str,
) -> str:
    """Generate a SAVE framework prompt for the AI to fill in."""
    examples = SAVE_INDUSTRY_EXAMPLES.get(industry, {})

    lines = [
        "## SAVE Framework Analysis",
        "",
        "Hãy phân tích theo SAVE Framework (thay thế 4P truyền thống):",
        "",
    ]

    for key, info in SAVE_DEFINITIONS.items():
        lines += [
            f"### {key} — {info['name']} (thay thế {info['old']})",
            f"**Nguyên tắc**: {info['principle']}",
            "",
            "**Câu hỏi cần trả lời**:",
        ]
        for q in info["questions"]:
            lines.append(f"- {q}")

        if key in examples:
            lines += [
                "",
                f"**Ví dụ trong ngành**: _{examples[key]}_",
            ]

        lines += [
            "",
            f"**Template**: {info['messaging_template']}",
            "",
            f"**Áp dụng cho {product_service}**: [AI điền vào dựa trên context]",
            "",
        ]

    return "\n".join(lines)
