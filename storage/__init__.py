from .session import get_session, save_session, reset_session, init_pool, init_db
from .models import Session, BusinessProfile, PipelineStage, BrandVoice
from .brand_voice import (
    get_brand_voice,
    save_brand_voice,
    has_brand_voice,
    deactivate_brand_voice,
)
from .campaign_history import (
    save_campaign_history,
    search_similar_campaigns,
    list_campaigns,
)
from .embeddings import embed_text

# Public API re-exported by this package (consumed via `from storage import ...`).
__all__ = [
    "get_session", "save_session", "reset_session", "init_pool", "init_db",
    "Session", "BusinessProfile", "PipelineStage", "BrandVoice",
    "get_brand_voice", "save_brand_voice", "has_brand_voice", "deactivate_brand_voice",
    "save_campaign_history", "search_similar_campaigns", "list_campaigns",
    "embed_text",
]
