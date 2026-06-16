"""
Standalone web dashboard server — KHÔNG cần Telegram token.

Chạy:  python run_web.py
Mở:    http://localhost:8000

Mặc định lưu vào SQLite (webapp/markos_web.db). Nếu set SUPABASE_URL +
SUPABASE_SERVICE_KEY (chạy webapp/supabase_schema.sql trước) thì tự dùng Supabase.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from webapp.api import api_routes, full_state
from webapp import store, events

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app: Starlette):
    backend = store.configure()
    await store.init()
    logging.info("Web dashboard ready (store=%s).", backend)
    # SSE: watcher (luôn chạy) + Supabase Realtime (nếu có)
    asyncio.create_task(events.watcher(full_state))
    asyncio.create_task(events.realtime_listener(full_state))
    yield


app = Starlette(
    routes=api_routes() + [
        Mount("/", app=StaticFiles(directory=str(WEB_DIR), html=True), name="web"),
    ],
    lifespan=lifespan,
)


def main():
    port = int(os.environ.get("PORT", "8000"))
    print(f"\n  Marketing OS web dashboard → http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
