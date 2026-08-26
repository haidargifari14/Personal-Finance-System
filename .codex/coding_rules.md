# Coding Rules

## Python standards

- Use Python type hints for public functions, methods, and non-obvious variables.
- Write concise Google-style docstrings for modules, public classes, and public functions.
- Follow PEP 8 and use descriptive, consistent snake_case names.
- Keep functions small and focused on one responsibility.
- Prefer composition and reuse over copying code.

## Architecture standards

- Apply the Single Responsibility Principle.
- Put business logic in services, never in Telegram handlers or Streamlit pages.
- UI code must not calculate financial metrics or query Google Sheets directly.
- `SheetService` is the only layer that reads or writes Google Sheets.
- `FinanceService` owns transaction validation and transaction formatting.
- The centralized transaction schema owns physical header order and Expense
  metadata normalization; do not hard-code Transaction column positions.
- Expense classification is analytical metadata. Never use it to alter actual
  amount, Account balance, Current Balance, transaction count, or Goal progress.
- Use classified normalized spending only for Monthly Spending Limit, Spending
  Risk, and related comparable optimization analysis.
- Build behavioral category forecasts from Normal Expense records only. Periodic
  and One-off payments remain factual cash history and must not be converted
  into daily-spending observations.
- Financial Outlook is global: never use Forecast detail-inspection state as a
  financial input. Recommendation and Scenario must consume the same supplied
  global Outlook result.
- `AnalyticsService` owns dashboard aggregations and chart-ready data.
- Reuse dashboard components before creating page-specific UI.

## State ownership principle

Each UI state must have one clear owner. Shared global state belongs to the
sidebar; page-specific state belongs only to the page that uses it.

| State | Owner |
| --- | --- |
| Global Filter | Sidebar |
| Overview Filter | Overview Page |
| Analytics Filter | Analytics Page |
| Transaction Filter | Transactions Page |
| Forecast Filter | Forecast Page |
| Profile Personal, Financial Preferences, Account, Movement, and Goal UI state | Profile Page |
| Settings | Settings Page |

- Do not read or mutate another page's local filter state.
- Use distinct, consistently named session-state keys for each owner.
- Pass filter values explicitly to services; services must not read Streamlit
  session state.
- Overview owns `overview_categories` as a list. An empty list explicitly means
  **All Categories**; never combine an "All" option with a specific category.
- Analytics owns `analytics_category` as one selected category, because the
  Analytics page is a single-category drilldown.
- Category options depend on the local Transaction Type: Income and Expense
  use their respective centralized V1 vocabularies, while All uses the combined
  available category set. Remove only selections invalidated by that change.

## Google Sheets reliability and cache rules

- Read Transactions, Accounts, Account Movements, and Goals only through the
  centralized `SheetService` snapshot cache.
- Never add unrelated service-level caches for the same Google Sheets dataset.
- Invalidate only the dataset changed by a confirmed mutation; do not clear all
  cached data indiscriminately.
- Keep cache TTLs short and use explicit refresh for source-data freshness.
- Retry only bounded transient reads. Never automatically retry writes unless
  the persistence operation is explicitly idempotent and designed for it.
- If a stale snapshot is used, retain its true loaded timestamp and show a
  human-readable warning rather than a raw transport exception.

## Change standards

- Do not duplicate existing business logic.
- Avoid hardcoded values; use configuration, constants, or reusable mappings.
- Preserve backward compatibility unless a requirement explicitly changes behavior.
- Extend existing architecture instead of bypassing it for a short-term feature.
- Add or update tests for non-trivial business rules.
- Document architectural decisions and user-visible changes.
