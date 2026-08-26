# Business Requirements

## Product vision

Personal Finance System enables everyday financial tracking without requiring users to open Google Sheets. Users record transactions in Telegram and review their financial position in a dashboard.

## Business objectives

1. Make daily income and expense recording fast and reliable.
2. Make financial information easy to understand through useful summaries and visualizations.
3. Preserve Google Sheets as the initial source of truth while keeping the application ready for future storage evolution.
4. Provide a foundation for forecasting, budgeting, notifications, OCR, and AI financial advice.

## Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| BR-01 | Users can record income and expense transactions through Telegram. | Must |
| BR-02 | Transactions include date, type, category, amount, and optional note. | Must |
| BR-03 | Confirmed transactions are persisted to Google Sheets. | Must |
| BR-04 | Users can view daily and monthly financial summaries. | Must |
| BR-05 | The dashboard reads live transaction data through services. | Must |
| BR-06 | The dashboard presents metrics, tables, filters, and visualizations. | Must |
| BR-07 | Expense-by-category visualization is available. | In progress |
| BR-08 | The product supports future cashflow, budget, forecast, and AI features. | Should |

## Non-functional requirements

- Financial calculations must be consistent between bot reports and dashboard views.
- Google Sheets credentials must not be committed to source control.
- User-facing errors must be understandable and should preserve recoverable state where possible.
- Business rules must be reusable across Telegram and Streamlit interfaces.
- The project must remain maintainable as additional dashboard pages are added.
