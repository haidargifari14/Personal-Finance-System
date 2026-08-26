# Sprint History

## Sprint 0 — Dashboard Setup

Established the Phase 2 project foundation: dashboard entry point, dashboard-oriented package structure, service boundaries, and database abstraction placeholders.

## Sprint 1 — Reusable UI Components

Delivered reusable dashboard building blocks, including navigation, sidebar, theme, metric cards, filters, and transaction table patterns.

## Sprint 2 — Analytics Service and Live Dashboard

Connected dashboard data to live Google Sheets and introduced shared analytics-oriented service boundaries.

## Sprint 3 — Visualization (Current)

Focus: complete the Expense by Category chart while preserving reusable chart and analytics architecture.

### Sprint 3 acceptance criteria

- Expense-by-category data is produced by `AnalyticsService`.
- Chart rendering is reusable through dashboard components.
- Dashboard pages do not access Google Sheets directly.
- Empty and error states are handled clearly.

## Sprint 8.7L — Settings Cleanup and Functional Finalization

Finalized product ownership after the V2 Account, Goal, Forecast,
Recommendation, and Scenario work.

- Profile owns Personal, Accounts, and Goals.
- Settings owns safe Integration status and Transaction Data Management only.
- Retired Settings-owned V1 financial profile and local Goal CRUD APIs while
  retaining legacy JSON keys as inert compatibility data.
- Transaction backup, restore, and reset are explicitly scoped to Transactions;
  Accounts, Account Movements, and Goals are preserved and never represented as
  part of this partial backup.
- Added regression coverage for legacy settings isolation, Saving Candidate
  persistence, V2 identity-preserving snapshots, and restore validation.

## Sprint 8.7M — Full Functional Regression and Bug Fix

Completed a V2 functional regression pass across Transactions, Accounts,
Account Movements, Goals, Forecast, Recommendation, Scenario, Analytics, and
data-management boundaries.

- Confirmed the service-layer source of truth: UI pages do not access Google
  Sheets directly, stable transaction identity uses `transaction_id`, and
  Account balances remain derived in `AccountService`.
- Added a regression test proving transaction metadata edits preserve the
  immutable Transaction ID and do not create a duplicate Account balance
  effect.
- Retired unreferenced V1 allocation-based Goal artifacts so Goal V2 remains
  the only active Goal path.
- Verified 98 automated tests and project compilation successfully. Streamlit
  startup remains covered by a non-mutating health smoke test.

## Sprint 8.7N — Performance, State, and Google Sheets Optimization

Reduced Google Sheets quota pressure without changing financial rules or
redesigning the dashboard.

- Added a centralized 45-second `SheetService` snapshot cache for Transactions,
  Accounts, Account Movements, and Goals, plus shared workbook initialization.
- Added targeted invalidation after confirmed Transaction, Account, Movement,
  and Goal mutations. Explicit page refreshes now force relevant source reads.
- Added three-attempt bounded retry for transient read failures and a clearly
  labelled last-known-data fallback when a prior snapshot exists.
- Verified a controlled Forecast cycle reduced remote reads from Transactions
  4, Accounts 3, Account Movements 3, Goals 1 to one read per dataset while
  preserving identical Forecast output.
- Added cache, invalidation, retry, stale-fallback, failed-write, and
  complex-Forecast reuse regression coverage.

## Sprint 8.7I Final Patch — Recommendation / Financial Outlook Alignment

Aligned Recommendation with the balance-based Financial Outlook without
changing Forecast, Goal, Scenario, Account, or cache formulas.

- Retired the Recommendation-only monthly income-minus-expense deficit model.
- Balance Risk initially meant the selected-category estimated balance was negative;
  its shortfall is reduced only by real, history-backed Saving Candidate
  opportunities.
- Preserved Saving Candidate independence from Forecast selection and limited
  optimization baselines.
- Kept Recommendation calculation in memory from loaded Outlook, Expense
  Forecast, and Goal Forecast results. This detail-selection baseline was
  superseded by the later global Financial Outlook finalization.

## Sprint 8.7I Final Risk Model Patch — Monthly Spending Limit

Added a Profile-owned Monthly Spending Limit as an early planning warning,
without turning it into an Income estimate, budget transaction, or Google
Sheets record.

- Projected tracked spending initially used actual Expense in the current
  calendar month plus selected Forecast categories; the later finalization
  supersedes this with classified normalized spending plus global projections.
- A configured limit creates Spending Risk only when that tracked amount is
  exceeded; Balance Risk remains the higher-severity liquidity fallback.
- Recommendation keeps Saving Candidate independence, bounds reductions by
  real capacity, and reuses existing cached Forecast results without new reads.

## Sprint 8.7I Final Risk Model Patch C — Expense Classification

Added analytical per-transaction Expense classification without changing cash
reality or daily-entry flows.

- Transactions append `Expense Type` and `Coverage Months` through the single
  centralized schema contract; the migration is idempotent and historical blank
  Expense metadata reads as Normal.
- Dashboard Edit supports Normal, Periodic, and One-off. Periodic requires a
  positive whole number of coverage months; Income always clears both fields.
- Monthly Spending Limit and Spending Risk now use normalized current-month
  contributions plus global usable future Forecast projections. Actual Expense,
  Account/Current Balance, Goals, and Financial Outlook continue using full
  actual cash amounts.
- Import/export and transaction-only backup/restore preserve classification;
  normalized analysis reuses the existing cached Transactions snapshot without
  another worksheet or per-record read.

## Sprint 8.7 Forecast Finalization — Global Financial Outlook

Finalized one shared Forecast condition for Financial Outlook, Recommendation,
and Scenario without changing source data or cache ownership.

- Financial Outlook aggregates sufficient categories and usable limited-data
  categories; insufficient categories remain audit-visible but excluded.
- Expense Forecast Detail now owns a presentation-only `Categories to inspect`
  selector. It cannot affect global projection, risks, trajectory,
  Recommendation, or Scenario.
- Normal Expense supplies behavioral training. Periodic cash payments retain a
  normalized monthly burden but do not become daily observations; One-off
  payments are excluded from both normalized burden and behavioral training.
- Calculation Details renders classification, category inclusion, and global
  reconciliation from the existing in-memory Forecast result.
- Scenario now starts from Global Financial Outlook and compares normalized
  spending-limit and balance results before and after non-persistent changes.
