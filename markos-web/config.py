import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")  # cho image gen (gpt-image-1)
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")  # multi-provider router fallback (from three-tier)

# Admin Telegram user IDs — phân cách bằng dấu phẩy: "123456789,987654321"
ADMIN_IDS: set[int] = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

# Facebook APIs
FB_ACCESS_TOKEN    = os.getenv("FB_ACCESS_TOKEN", "")   # User/System token (ads_read, read_insights)
FB_APP_ID          = os.getenv("FB_APP_ID", "")         # App ID
FB_APP_SECRET      = os.getenv("FB_APP_SECRET", "")     # App Secret
FB_AD_ACCOUNT_ID   = os.getenv("FB_AD_ACCOUNT_ID", "")  # act_XXXXXXXXXX (để pull data ads của sếp)
GRAPH_API_VERSION  = os.getenv("GRAPH_API_VERSION", "v19.0")  # FB Graph API version (from three-tier)

# Competitor monitoring (hybrid: nguồn fb_ads_library + interval user-set từ Spy Radar)
SPY_CHECK_INTERVAL_MINUTES = int(os.getenv("SPY_CHECK_INTERVAL_MINUTES", "15"))

# Supabase — dùng HTTPS (port 443), không bao giờ bị block
SUPABASE_URL       = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY       = os.getenv("SUPABASE_SERVICE_KEY", "")  # service_role key

# Webhook — Railway public domain (no trailing slash)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Railway sets PORT automatically; fallback 8000 for local testing
PORT = int(os.getenv("PORT", "8000"))

# 2-tier model: Haiku cho intake (classification + JSON extract, rẻ), Sonnet cho deep analysis + critic
CLAUDE_SONNET_MODEL = "claude-sonnet-4-6"
CLAUDE_HAIKU_MODEL  = "claude-haiku-4-5"
CLAUDE_MODEL        = CLAUDE_SONNET_MODEL  # backward-compat alias

# OpenAI models (S8.8 — Phase 1b multi-provider router)
GPT5_MODEL          = "gpt-5"           # Flagship — competitor + USP + psychology fallback
GPT5_MINI_MODEL     = "gpt-5-mini"      # Sweet spot — retention/winback/intake primary
GPT5_NANO_MODEL     = "gpt-5-nano"      # Cheap — bulk classify
GPT_4_1_MINI_MODEL  = "gpt-4.1-mini"    # Long context fallback (1M ctx)

# Pipeline timeouts (Sprint hotfix: synthesis với 8-stage pipeline cần buffer lớn hơn)
# Synthesis context ~70K input + 10K output có thể tốn 180-300s + retry → 540s+ wall time
AGENT_TIMEOUT  = 1800  # 30 phút — buffer cho content generator pipeline (4 sub-skills × batch lớn)
MAX_HISTORY_TURNS = 20

# Sprint 8 — Multi-Agent Orchestrator feature flag.
# True (default): task=full chạy qua Multi-Agent Orchestrator (parallel tier execution)
# False: fallback xuống run_targeted_pipeline cũ (sequential)
# Set qua env var để rollback nhanh: USE_MULTI_AGENT=false
USE_MULTI_AGENT_PIPELINE = os.getenv("USE_MULTI_AGENT", "true").lower() in ("true", "1", "yes")

# DB Refactor v2 — Dual-Write Migration (Migration 006).
#
# 2 flags độc lập để rollout từng giai đoạn an toàn:
#
#   DB_V2_WRITE  : True → ghi vào CẢ v1 + v2 (dual-write mode)
#                  False → chỉ ghi v1 (legacy)
#   DB_V2_READ   : True → đọc TỪ v2 (production hit v2)
#                  False → đọc từ v1 (tested)
#
# Workflow 4 giai đoạn:
#   Phase A: WRITE=F READ=F → v1 only (như hiện tại)
#   Phase B: WRITE=T READ=F → dual-write, đọc v1 (1-2 tuần test v2)
#   Phase C: WRITE=T READ=T → đọc v2, vẫn ghi cả 2 (1-2 tuần)
#   Phase D: WRITE=F READ=T → v2 only (sau khi confident)
#
# Rollback: set 2 vars về False bất cứ lúc nào → quay về v1 only
DB_V2_WRITE = os.getenv("DB_V2_WRITE", "false").lower() in ("true", "1", "yes")  # Phase D: default False (V2-only, no dual-write)
DB_V2_READ  = os.getenv("DB_V2_READ",  "true").lower()  in ("true", "1", "yes")  # Phase D: default True (read from V2)
# Legacy compat
USE_DB_V2 = DB_V2_READ  # backward-compat nếu code khác đang đọc

STAGES = ["idea", "mvp", "growth", "scale"]

# FB OAuth per-user — Ads Scheduler
# ENCRYPTION_KEY: Fernet 32-byte key base64. Gen: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY   = os.getenv("ENCRYPTION_KEY", "")
# Base URL của server (no trailing slash) — dùng cho OAuth redirect_uri
WEBHOOK_BASE_URL = WEBHOOK_URL  # dùng lại WEBHOOK_URL đã có
