"""Strategic Tasks Registry — Market research, USP, pricing, synthesis."""
from dataclasses import dataclass, field
from typing import List

from agents.logger import create_logger, error as log_error

logger = create_logger(__name__)


@dataclass
class TaskConfig:
    """Config for one user-facing task."""
    name: str
    label: str
    button_emoji: str
    category: str
    description: str = ""
    opening_question: str = ""
    skill_class_name: str = ""
    pipeline_stages: List[str] = field(default_factory=list)
    intake_fields: List[dict] = field(default_factory=list)
    intake_required_fields: List[str] = field(default_factory=list)


STRATEGIC_TASKS: dict[str, TaskConfig] = {
    "full": TaskConfig(
        name="full",
        label="Nghiên Cứu & Phân Tích Thị Trường",
        button_emoji="🔬",
        category="full",
        description="Phân tích thị trường toàn diện — Market + Đối thủ + Customer + Pricing + USP → Sếp chọn hướng → Kế hoạch chiến lược",
        skill_class_name="",
        pipeline_stages=[
            "market_research",
            "competitor",
            "customer_insight",
            "psychology_pricing",
            "usp_definition",
        ],
        intake_required_fields=[
            "industry", "product_service", "target_customer",
            "monthly_revenue", "primary_goal", "main_challenge",
        ],
        intake_fields=[
            {"key": "product_service",  "label": "Sản phẩm/dịch vụ chính", "example": "Spa laser trị mụn, combo 3 buổi 1.2M", "required": True},
            {"key": "target_customer",  "label": "Khách hàng mục tiêu",     "example": "Phụ nữ 25-35 đi làm văn phòng HCM", "required": True},
            {"key": "monthly_revenue",  "label": "Doanh thu tháng hiện tại","example": "80-120 triệu/tháng (hoặc 'mới mở chưa có')", "required": True},
            {"key": "primary_goal",     "label": "Mục tiêu 90 ngày tới",   "example": "Tăng doanh thu 30%, mở thêm kênh TikTok", "required": True},
            {"key": "main_challenge",   "label": "Khó khăn lớn nhất hiện tại", "example": "Chi phí ads cao, khách không quay lại", "required": True},
            {"key": "industry",         "label": "Ngành (tự map nếu không nhập)", "example": "health_beauty", "required": False},
        ],
    ),
    "market": TaskConfig(
        name="market",
        label="Tìm Hiểu Thị Trường",
        button_emoji="📊",
        category="strategic",
        description="TAM/SAM/SOM + Market Dynamics",
        skill_class_name="MarketResearchSkill",
        pipeline_stages=["market_research"],
        intake_required_fields=["industry", "product_service", "target_customer", "location"],
        intake_fields=[
            {"key": "product_service", "label": "Sản phẩm/dịch vụ", "example": "Spa làm đẹp · combo facial 680K", "required": True},
            {"key": "target_customer", "label": "Khách hàng mục tiêu", "example": "Nữ 25-40, thu nhập khá, quan tâm skincare", "required": True},
            {"key": "industry", "label": "Ngành", "example": "health_beauty", "required": True},
            {"key": "location", "label": "Địa điểm kinh doanh", "example": "Quận 1, TP.HCM", "required": True},
        ],
    ),
}


def get_strategic_task(name: str):
    """Lookup strategic task by name with error handling."""
    try:
        task = STRATEGIC_TASKS.get(name)
        if task is None:
            log_error(logger, f"Strategic task not found: {name}", task_name=name)
        return task
    except Exception as e:
        log_error(logger, f"Error looking up strategic task: {name}", exc_info=True, error=str(e))
        return None


def list_strategic_tasks():
    """List all strategic tasks."""
    return list(STRATEGIC_TASKS.values())
