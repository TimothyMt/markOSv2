"""
Standalone web dashboard server — KHÔNG cần Telegram token / credentials.

Chạy:  python run_web.py
Mở:    http://localhost:8000

Phục vụ giao diện trong web/ + JSON API trong webapp/ (SQLite mock-first).
Dữ liệu lưu ở webapp/markos_web.db (tự tạo lần đầu).
"""
import os
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from webapp.api import api_routes
from webapp import store

WEB_DIR = Path(__file__).resolve().parent / "web"


def build_app() -> Starlette:
    store.init_db()
    routes = api_routes() + [
        Mount("/", app=StaticFiles(directory=str(WEB_DIR), html=True), name="web"),
    ]
    return Starlette(routes=routes)


app = build_app()


def main():
    port = int(os.environ.get("PORT", "8000"))
    print(f"\n  Marketing OS web dashboard → http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
