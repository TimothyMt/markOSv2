"""
Storage v2 — Normalized schema (Migration 006).

Modules:
- users       : User identity + token quota + soft delete
- profiles    : Business profile (1:1 with users)
- sessions    : Slim session state (hot data only)
- skill_runs  : Immutable versioned skill outputs
- campaigns   : Campaign entity with embeddings
- posts       : POST-XXX with adapt/variant linkage
- engagements : Discovery→Strategy→Execution spine (Migration 007)
- briefs      : Diagnostic briefs — McKinsey Discovery output (Migration 007)
- strategies  : CMO marketing plans (Migration 007)

Coexists with v1 (storage/session.py) during Phase 1-2 migration.
"""
from .users import (
    get_user, upsert_user, soft_delete_user,
    add_token_usage, set_token_quota, reset_token_usage,
    clear_industry_cached,
)
from .profiles import (
    get_profile, upsert_profile, delete_profile,
)
from .sessions_slim import (
    get_session_slim, upsert_session_slim, touch_last_message,
    delete_session_slim,
)
from .skill_runs import (
    insert_skill_run, get_latest_skill_run, list_skill_runs,
    update_rating, delete_skill_runs,
)
from .campaigns_v2 import (
    create_campaign, get_campaign, list_campaigns_v2,
    update_campaign_embedding,
)
from .posts import (
    insert_post, get_post, update_post,
    list_posts_by_campaign, list_posts_by_user, soft_delete_post,
)
from .engagements import (
    create_engagement, get_engagement, get_active_engagement,
    get_latest_with_strategy, update_engagement, list_engagements,
)
from .briefs import (
    insert_brief, get_brief, get_latest_brief,
)
from .strategies import (
    insert_strategy, get_strategy, get_latest_strategy,
    update_rating as update_strategy_rating,
)

# Public API re-exported by this package (consumed via `from storage.v2 import ...`).
__all__ = [
    # users
    "get_user", "upsert_user", "soft_delete_user",
    "add_token_usage", "set_token_quota", "reset_token_usage",
    "clear_industry_cached",
    # profiles
    "get_profile", "upsert_profile", "delete_profile",
    # sessions_slim
    "get_session_slim", "upsert_session_slim", "touch_last_message",
    "delete_session_slim",
    # skill_runs
    "insert_skill_run", "get_latest_skill_run", "list_skill_runs",
    "update_rating", "delete_skill_runs",
    # campaigns_v2
    "create_campaign", "get_campaign", "list_campaigns_v2",
    "update_campaign_embedding",
    # posts
    "insert_post", "get_post", "update_post",
    "list_posts_by_campaign", "list_posts_by_user", "soft_delete_post",
    # engagements
    "create_engagement", "get_engagement", "get_active_engagement",
    "get_latest_with_strategy", "update_engagement", "list_engagements",
    # briefs
    "insert_brief", "get_brief", "get_latest_brief",
    # strategies
    "insert_strategy", "get_strategy", "get_latest_strategy",
    "update_strategy_rating",
]
