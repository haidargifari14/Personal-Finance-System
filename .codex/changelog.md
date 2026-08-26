# Changelog

## Unreleased

### Added

- Centralized V2 transaction schema contract with immutable Transaction IDs and nullable Account IDs.
- Safe, idempotent legacy worksheet migration with local pre-migration snapshots and post-migration financial validation.
- Account foundation: an idempotent `Accounts` worksheet contract, immutable UUID Account IDs, Account lifecycle rules, and a derived balance engine.
- Minimal Account Management in Settings/Profile for service-backed create, edit, delete, and archive actions.
- Account Management moved from Settings into the dedicated Profile workspace.
- Account selection for new Dashboard and Telegram transactions, using immutable Account IDs and active-Account validation.
- Account Movement foundation with immutable Movement IDs, Transfer, Adjustment, movement history, and service-backed deletion.
- Profile Account Management now separates Active and Archived Accounts and presents lifecycle guidance in its primary Account surface.
- Goal V2 with immutable Goal IDs, Account-linked persistence, derived progress, lifecycle actions, and calculated health under Profile.
- Forecast V2 with category eligibility, global remaining-month expense forecasts, active-Account Financial Outlook, and Account-linked Goal completion projections.
- Recommendation Engine V1 with explicit Saving Candidate preferences, deterministic excess-based reductions, Goal pace improvement allocation, and a temporary Scenario handoff contract.
- Decoupled Forecast confidence, Forecast display selection, and Saving Candidate optimization analysis; limited-data categories can now provide clearly labelled basic forecasts when safe.
- Saving Candidate configuration is now available for all standardized V1 Expense Categories, including categories without sufficient optimization history.
- Financial Outlook now includes an Account-derived global Estimated Balance Trajectory with day-level tooltip context.
- Scenario Simulator V1 with non-persistent category reductions, Potential Saving, Goal allocation, Goal impact projection, Recommendation prefill, reset, and baseline-versus-scenario balance trajectories.
- Settings Cleanup: Settings now contains only safe Integrations and Transaction Data Management; Personal, Accounts, and Goals remain in Profile.
- Full functional regression coverage for the V2 transaction, account, movement, goal, forecast, recommendation, and scenario boundaries.
- Centralized 45-second Google Sheets read snapshots with bounded retry, stale-data fallback, targeted mutation invalidation, and shared workbook initialization.
- Profile-owned Monthly Spending Limit preference with an early Spending Risk warning based on classified normalized current-month Expense and global usable Forecast projections.
- Per-transaction Expense Type and Coverage Months metadata with Normal,
  Periodic, and One-off handling. Dashboard Transaction Edit can classify an
  Expense without changing the normal Dashboard Add or Telegram flows.

### Changed

- Transaction CRUD, import/export, backup/restore, and reset paths now preserve V2 transaction identity fields.
- Dashboard transaction edit/delete now resolve the current Google Sheets row using Transaction ID.
- Telegram saves now default a missing transaction date to the current local date.
- V2 XLSX export now serializes the Amount column using the centralized export schema.
- Account balances now use only explicitly linked income and expense transactions; historical null Account IDs remain excluded.
- New transaction validation now requires an active Account while preserving null Account IDs on historical edits.
- Account current balance now derives Transfer and Adjustment effects without changing Income or Expense analytics.
- Legacy local Goals remain preserved without converting their allocated values into Account financial balances.
- Legacy income projections, arbitrary forecast horizons, scenario controls, and legacy Goal allocation forecasts are retired from the Forecast page.
- Recommendation baselines now compare current-month spending through the current day with prior historical spending normalized to the same number of days.
- Recommendation now consumes Financial Outlook’s global estimated balance rather than deriving a separate monthly income-versus-expense cashflow deficit.
- Recommendation primary KPIs now show Balance Risk, Balance Shortfall when applicable, Saving Candidate analysis, potential saving, and the expected balance impact; legacy cashflow-deficit fields were removed.
- Recommendation now distinguishes critical Balance Risk from Monthly Spending Limit warning risk, without restoring the retired monthly-income cashflow model.
- Scenario Simulator now presents its impact before Goal Allocation, with concise Balance Improvement, Scenario Estimated Balance, and Unallocated Saving metrics plus secondary calculation details.
- Overview now displays Account-derived Current Balance separately from date-filtered Income, Expense, and Net Cashflow; Analytics defensively excludes non-economic movement-like rows while retaining historical null-Account and legacy-category Transactions.
- Transaction backup, restore, and reset are explicitly labelled as Transaction-only operations. Validated V2 Transaction snapshots preserve Transaction ID and nullable Account ID without claiming to back up Accounts, Account Movements, or Goals.
- Retired Settings-owned V1 financial configuration and Goal CRUD APIs. Legacy local JSON fields remain compatible but inert for V2 financial logic.
- Retired unused V1 allocation-based Goal model and dashboard components. Goal V2 is now the sole active Goal implementation.
- Overview and Transactions refresh actions now invalidate their relevant source snapshots before fetching new data; Overview's timestamp now reflects the actual transaction-source load time.
- Monthly Spending Limit and Spending Risk now use normalized current-month
  Expense: Normal contributes its full amount, Periodic contributes its rounded
  monthly equivalent, and One-off contributes zero. Actual Expense, balances,
  Financial Outlook liquidity, Goals, and transaction count remain unchanged.
- Transaction export, legacy/V2 import, backup, restore, and reset preserve
  Expense Type and Coverage Months while legacy rows default missing metadata to
  Normal.
- Financial Outlook now aggregates every usable category forecast independently
  of detail inspection. Category detail selection controls cards only.
- Periodic and One-off transactions are excluded from daily behavioral forecast
  training; Calculation Details exposes classification and global-inclusion
  audit facts without an extra source read.

### Previous documentation update

- Project AI development context in `.codex/`.
- Product and engineering documentation in `docs/`.
- Architecture, coding, decision, sprint, roadmap, and UI guidance for Phase 2 development.
