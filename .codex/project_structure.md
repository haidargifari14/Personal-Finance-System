# Project Structure

```text
PERSONAL-FINANCE-BOT/
├── app.py                    # Telegram Bot entry point
├── dashboard.py              # Streamlit entry point
├── config.py                 # Environment-backed configuration
├── handlers/                 # Telegram event handlers
├── keyboards/                # Reusable Telegram inline keyboards
├── states/                   # Telegram FSM states
├── services/                 # Business and integration services
│   ├── finance_service.py
│   ├── transaction_schema.py # Central Transaction headers and normalization
│   ├── analytics_service.py
│   ├── report_service.py
│   └── sheet_service.py
├── database/                 # Future database abstraction and migrations
├── models/                   # Domain models
├── dashboard/                # Streamlit pages, components, utilities, assets
│   ├── pages/
│   ├── components/
│   ├── utils/
│   └── assets/
├── utils/                    # Shared cross-interface utilities
├── docs/                     # Product and engineering documentation
└── .codex/                   # AI development context and project conventions
```

## Boundary rules

- `handlers/` depends on `services/`, never the reverse.
- `dashboard/pages/` depends on `dashboard/components/` and `services/` only.
- `services/` may depend on models, utilities, and persistence gateways.
- `SheetService` is the only direct integration point for Google Sheets.
