"""
Hub sự kiện + nguồn đổi dữ liệu cho SSE.

- hub: quản lý các client SSE đang kết nối; publish state mới cho tất cả.
- watcher: task nền đọc store mỗi `interval` giây, chỉ đẩy khi dữ liệu đổi
  (so hash). Hoạt động với MỌI backend (SQLite hoặc Supabase), kể cả khi thay
  đổi đến từ process khác (bot). Đây là "Bước 1" — luôn chạy, là lưới an toàn.
- realtime_listener: "Bước 2" — lắng nghe Supabase Realtime (postgres_changes)
  để đẩy gần như tức thì khi DB đổi. Best-effort: lỗi thì watcher vẫn lo.
"""
import asyncio
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class Hub:
    def __init__(self):
        self._subs: set[asyncio.Queue] = set()
        self._last_hash: str | None = None

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=8)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subs.discard(q)

    @property
    def count(self) -> int:
        return len(self._subs)

    async def publish(self, state: dict):
        data = json.dumps(state, ensure_ascii=False)
        for q in list(self._subs):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass  # client chậm → bỏ qua, lần sau sẽ có bản mới nhất

    @staticmethod
    def _hash(state: dict) -> str:
        return hashlib.md5(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    async def publish_if_changed(self, state: dict) -> bool:
        h = self._hash(state)
        if h != self._last_hash:
            self._last_hash = h
            await self.publish(state)
            return True
        return False


hub = Hub()


async def watcher(snapshot_fn, interval: float = 4.0):
    """Đọc store định kỳ, đẩy khi đổi. snapshot_fn: coroutine trả về state dict."""
    logger.info("SSE watcher started (interval=%ss).", interval)
    while True:
        try:
            state = await snapshot_fn()
            await hub.publish_if_changed(state)
        except Exception as e:  # không để watcher chết
            logger.warning("SSE watcher error: %s", e)
        await asyncio.sleep(interval)


# Bảng cần lắng nghe realtime
_TABLES = [
    "web_tracked", "web_jobs", "web_optimizations", "web_alerts", "web_settings",
    "web_campaigns", "web_calendar_posts", "web_content_items", "web_reports",
    "web_accounts", "web_users",
]


async def realtime_listener(snapshot_fn):
    """Lắng nghe Supabase Realtime → đẩy ngay khi DB đổi. Best-effort."""
    import os
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
    if not (url and key):
        return  # không có Supabase → bỏ qua, watcher lo
    try:
        from supabase import acreate_client
        loop = asyncio.get_running_loop()

        async def _push():
            try:
                await hub.publish_if_changed(await snapshot_fn())
            except Exception as e:
                logger.warning("realtime push error: %s", e)

        def _cb(_payload):
            loop.create_task(_push())

        client = await acreate_client(url, key)
        channel = client.channel("web-dashboard-changes")
        for t in _TABLES:
            channel = channel.on_postgres_changes(
                event="*", schema="public", table=t, callback=_cb)
        await channel.subscribe()
        logger.info("Supabase Realtime subscribed (%d tables).", len(_TABLES))
    except Exception as e:
        logger.warning("Supabase Realtime unavailable (%s) → dựa vào watcher.", e)
