"""
Embedding utility — Sprint 8 Semantic Search.

Dùng OpenAI text-embedding-3-small (1536 dims, cheap ~$0.02/1M tokens).
Graceful degradation: returns None on any error — không block bot flow.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_openai_client = None


def _get_client():
    """Lazy-init OpenAI async client."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    try:
        from config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            logger.warning("embeddings: OPENAI_API_KEY not set — semantic search disabled")
            return None
        import openai
        _openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        return _openai_client
    except Exception as e:
        logger.warning("embeddings: failed to init OpenAI client: %s", e)
        return None


async def embed_text(text: str) -> Optional[list[float]]:
    """
    Generate embedding vector for a single text string.
    Returns list[float] (1536 dims) or None on any error.
    """
    client = _get_client()
    if client is None:
        return None

    text = text.replace("\n", " ").strip()
    if not text:
        return None

    # Truncate nếu quá dài (embedding model limit ~8191 tokens ≈ 32K chars)
    if len(text) > 30_000:
        text = text[:30_000]

    try:
        resp = await client.embeddings.create(
            input=text,
            model="text-embedding-3-small",
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.warning("embed_text failed: %s", e)
        return None
