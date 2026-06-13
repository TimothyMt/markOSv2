# Marketing OS — Telegram Bot

AI-powered marketing strategy platform for Vietnamese founders & business owners.

## Tính năng

- **Intake tự nhiên**: Nhập mô tả business bằng tiếng Việt
- **6 bước phân tích**: Market Research → Competitor → Customer Insight → Psychology/Pricing → Social Listening → Strategy
- **8 ngành được calibrate**: FnB, Tech SaaS, E-commerce, Education, Health/Beauty, Retail, B2B Services, Real Estate
- **SAVE + SMART Framework**: Strategy output có cấu trúc, actionable
- **90-day Roadmap**: Execution plan cụ thể

## Cài đặt

```bash
cd marketing-os-bot
pip install -r requirements.txt
cp .env.example .env
# Điền TELEGRAM_BOT_TOKEN và ANTHROPIC_API_KEY vào .env
python bot/main.py
```

## Cấu trúc

```
marketing-os-bot/
├── agents/
│   ├── prompts.py       # 8 system prompts cho từng agent
│   └── pipeline.py      # Pipeline orchestration
├── frameworks/
│   ├── kpi_library.py   # KPI frameworks cho 8 ngành
│   ├── save_framework.py
│   └── smart_framework.py
├── storage/
│   ├── models.py        # Session data models
│   └── session.py       # SQLite persistence
├── bot/
│   ├── handlers.py      # Telegram handlers
│   ├── keyboards.py     # Inline keyboards
│   └── main.py          # Entry point
├── config.py
└── requirements.txt
```

## Commands

- `/start` — Bắt đầu phân tích mới
- `/reset` — Xóa phiên, bắt đầu lại
- `/help` — Hướng dẫn sử dụng
