"""
Build bản 1-file (standalone) cho web dashboard.

Inline styles.css + data.js + app.js vào web/index.html → web/dashboard-standalone.html
và copy ra ./index.html (cho GitHub Pages tĩnh). Giữ nguyên Chart.js CDN.

Chạy lại mỗi khi sửa web/*.{css,js,html}:
    python webapp/build_standalone.py
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def build() -> str:
    shell = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    data_js = (WEB / "data.js").read_text(encoding="utf-8")
    app_js = (WEB / "app.js").read_text(encoding="utf-8")

    out = shell.replace(
        '<link rel="stylesheet" href="styles.css" />',
        f"<style>\n{css}\n</style>",
    ).replace(
        '<script src="data.js"></script>',
        f"<script>\n{data_js}\n</script>",
    ).replace(
        '<script src="app.js"></script>',
        f"<script>\n{app_js}\n</script>",
    )
    return out


def main():
    html = build()
    (WEB / "dashboard-standalone.html").write_text(html, encoding="utf-8")
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"Built standalone ({len(html):,} bytes) → web/dashboard-standalone.html + index.html")


if __name__ == "__main__":
    main()
