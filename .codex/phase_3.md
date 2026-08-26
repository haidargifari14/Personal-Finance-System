# Personal Finance System
## Phase 3 — UI/UX & Production Engineering Plan

**Status:** Planned  
**Phase Goal:** Mengubah Personal Finance Dashboard V1 yang sudah functional menjadi aplikasi yang polished, reliable, secure, performant, dan production-ready tanpa mengganti framework Streamlit.

---

# 1. Phase 3 Objectives

Phase 3 tidak berfokus pada penambahan fitur besar baru.

Core functionality dari Phase 2 dipertahankan:

- Overview
- Analytics
- Transactions
- Forecast
- Settings
- Financial Goals
- Telegram Bot
- Google Sheets Integration
- Analytics Service
- Forecast Service
- Settings Service
- Data Management Service
- Report Service

Fokus Phase 3:

1. UI/UX redesign.
2. Memaksimalkan kemampuan interface Streamlit.
3. Mengurangi Streamlit default look.
4. Membangun design system yang konsisten.
5. Meningkatkan usability dan interaction.
6. Memperkuat validation dan error handling.
7. Meningkatkan performance.
8. Menambahkan automated testing.
9. Meningkatkan security dan data reliability.
10. Deployment dashboard dan Telegram Bot.
11. Production release Personal Finance System V1.

---

# 2. Tool Strategy

Phase 3 menggunakan beberapa tools sesuai comparative advantage masing-masing.

## GPT

Digunakan untuk:

- Product thinking.
- Architecture decision.
- UI/UX reasoning.
- Design direction.
- Requirement definition.
- Trade-off analysis.
- Membuat implementation specification untuk Codex.

---

## GPT + Screenshot

Digunakan sebagai metode utama untuk:

- UI review.
- Visual hierarchy review.
- Layout analysis.
- Typography review.
- Spacing review.
- Information density review.
- Cross-page consistency review.
- Final visual QA.

GPT + Screenshot menjadi **visual reviewer utama**, bukan Work mode.

---

## Codex

Digunakan untuk:

- Coding.
- Refactoring.
- CSS implementation.
- Component implementation.
- Service improvement.
- Validation.
- Error handling.
- Logging.
- Caching.
- Testing.
- Security.
- Production configuration.
- Deployment preparation.

---

## Work Mode

Digunakan terutama sebagai:

**Functional QA / Computer Operator.**

Work mode digunakan untuk:

- Menjalankan aplikasi.
- Navigasi antarhalaman.
- Mencoba CRUD.
- Menguji filter.
- Menguji form.
- Menguji dialog.
- Menguji export.
- Menguji scenario simulator.
- Menguji settings.
- Menguji failure state.
- End-to-end testing.

Work mode tidak menjadi reviewer utama estetika UI.

---

# 3. Standard Phase 3 Workflow

## Design Workflow

```text
Screenshot
    ↓
GPT
    ↓
UI Analysis
    ↓
Design Decision
    ↓
Implementation Specification
    ↓
Codex
    ↓
Implementation
    ↓
Screenshot
    ↓
GPT Review
    ↓
Approved / Revision
```

---

## Engineering Workflow

```text
GPT Requirement
      ↓
Codex
      ↓
Implementation
      ↓
Automated Test
      ↓
Work Mode QA
      ↓
Bug Found?
   ↙       ↘
 Yes       No
  ↓         ↓
Codex      Done
 Fix
```

---

# 4. Sprint 8 — UI/UX Audit & Visual Direction

## Objective

Memahami kelemahan UI V1 sebelum melakukan perubahan code.

Sprint ini menentukan:

- Apa yang dipertahankan.
- Apa yang diperbaiki.
- Apa yang harus diredesign.
- Visual direction aplikasi.
- Information hierarchy.
- Design philosophy.

Tidak dilakukan redesign besar sebelum Sprint 8 selesai.

---

## Sprint 8.1 — Overview UI Audit

**Tool:** GPT + Screenshot

### Scope

Review:

- Page header.
- Global filters.
- KPI.
- Income vs Expense.
- Expense by Category.
- Cashflow Trend.
- Monthly Trend.
- Recent Transactions.
- Financial Insight.
- Whitespace.
- Border usage.
- Typography.
- Alignment.
- Visual hierarchy.

### Classification

Setiap bagian dikategorikan:

```text
KEEP
IMPROVE
REDESIGN
REMOVE VISUALLY
```

### Output

Overview UI Audit.

---

## Sprint 8.2 — Analytics UI Audit

**Tool:** GPT + Screenshot

### Scope

Review:

- Top Spending Categories.
- Category Drilldown.
- Period Comparison.
- Financial Statistics.
- Chart hierarchy.
- Information flow.
- Card usage.
- Analytical experience.

### Goal

Analytics harus terasa sebagai analytical workspace, bukan sekadar kumpulan chart.

### Output

Analytics UI Audit.

---

## Sprint 8.3 — Transactions UI Audit

**Tool:** GPT + Screenshot

### Scope

Review:

- Toolbar.
- Search.
- Filters.
- Sort.
- Table.
- Pagination.
- CRUD actions.
- Export.
- Transaction summary.
- Information density.

### Goal

Transactions harus terasa seperti proper data-management workspace.

### Output

Transactions UI Audit.

---

## Sprint 8.4 — Forecast UI Audit

**Tool:** GPT + Screenshot

### Scope

Review:

- Financial Projection.
- Cashflow Forecast.
- Scenario Simulator.
- Goal Forecast.
- Risk Detection.
- AI Recommendation.
- Information hierarchy.
- Page length.
- Narrative flow.

### Goal

Forecast harus terasa sebagai financial planning journey.

Target flow:

```text
Current Position
      ↓
Projection
      ↓
Cashflow Forecast
      ↓
Scenario
      ↓
Goals
      ↓
Risks
      ↓
Recommendation
```

### Output

Forecast UI Audit.

---

## Sprint 8.5 — Settings UI Audit

**Tool:** GPT + Screenshot

### Scope

Review:

- Profile.
- Application Settings.
- Financial Profile.
- Financial Goals.
- Integrations.
- Data Management.
- Navigation.
- Form density.
- Grouping.
- Long-scroll problem.

### Output

Settings UI Audit.

---

## Sprint 8.6 — Visual Direction & Redesign Specification

**Tool:** GPT

### Define

- Visual personality.
- Typography hierarchy.
- Color philosophy.
- Background.
- Surface hierarchy.
- Spacing philosophy.
- Card philosophy.
- Navigation style.
- Chart philosophy.
- Table philosophy.
- Form philosophy.
- Information hierarchy.

### Output

`UI_REDESIGN_PLAN.md`

Dokumen ini menjadi acuan Sprint 9–11.

---

# 5. Sprint 9 — Design System & UI Foundation

## Objective

Membangun satu bahasa visual yang digunakan seluruh aplikasi.

Redesign page tidak dilakukan secara independen.

---

## Sprint 9.1 — Design Tokens

**Tool:** GPT → Codex

### Define

Colors:

- Background.
- Surface.
- Text.
- Muted Text.
- Accent.
- Positive.
- Negative.
- Warning.

Layout:

- Spacing scale.
- Container width.
- Section gap.

UI:

- Border radius.
- Shadow.
- Border.
- Typography scale.

### Output

Centralized Design Tokens.

---

## Sprint 9.2 — Global Streamlit Styling

**Tool:** GPT → Codex

### Scope

Global styling untuk:

- Application shell.
- Main content.
- Sidebar.
- Buttons.
- Inputs.
- Selectbox.
- Tabs.
- Expanders.
- Dialogs.
- Popovers.
- Dataframe.
- Scrollbar.
- Tooltip.

### Goal

Mengurangi Streamlit default look tanpa membuat CSS terlalu fragile.

### Output

Global Streamlit UI Foundation.

---

## Sprint 9.3 — Core Reusable Components

**Tool:** GPT → Codex

### Components

- PageHeader.
- SectionHeader.
- MetricCard.
- StatItem.
- StatusBadge.
- InsightPanel.
- InfoBanner.
- ActionToolbar.
- EmptyState.
- ErrorState.

### Principle

Reusable component tidak berarti semua informasi harus berada di dalam card.

### Output

Reusable UI Component Library.

---

## Sprint 9.4 — Chart Design System

**Tool:** GPT → Codex

### Standardize

- Font.
- Axis.
- Grid.
- Legend.
- Tooltip.
- Margin.
- Chart height.
- Bar spacing.
- Line width.
- Background.
- Number formatting.

### Output

Consistent Plotly Design System.

---

## Sprint 9.5 — Foundation Visual QA

**Tool:** GPT + Screenshot

### Process

1. Jalankan aplikasi.
2. Ambil screenshot hasil design foundation.
3. Review dengan GPT.
4. Perbaiki visual direction jika diperlukan.
5. Lock design foundation.

### Output

Approved UI Foundation.

---

# 6. Sprint 10 — Full Page Redesign

## Objective

Menerapkan design system ke seluruh halaman.

Setiap page menggunakan workflow:

```text
GPT Specification
      ↓
Codex Implementation
      ↓
Screenshot
      ↓
GPT Visual Review
      ↓
Revision
      ↓
Design Lock
```

---

## Sprint 10.1 — Overview Redesign

**Tool:** GPT → Codex → GPT + Screenshot

### Goal

Overview menjadi Financial Command Center.

Target hierarchy:

```text
Financial Overview

Financial Position
────────────────────────

Income    Expense    Cashflow    Savings Rate


Cashflow Trend
────────────────────────────────────
           Main Visualization


Spending Breakdown     Financial Insight


Recent Activity
```

### Output

Redesigned Overview.

Overview menjadi reference implementation untuk halaman berikutnya.

---

## Sprint 10.2 — Analytics Redesign

**Tool:** GPT → Codex → GPT + Screenshot

### Target Flow

```text
Spending Overview
       ↓
Category Ranking
       ↓
Drilldown
       ↓
Period Comparison
       ↓
Financial Statistics
```

### Goal

Analytics menjadi analytical workspace.

### Output

Redesigned Analytics.

---

## Sprint 10.3 — Transactions Redesign

**Tool:** GPT → Codex → GPT + Screenshot

### Target

```text
Transactions                         + Add

Search | Filter | Sort | Export

──────────────────────────────────────────

Transaction Table

──────────────────────────────────────────

Pagination / Record Information
```

### Existing Functionality

Tetap mempertahankan:

- Search.
- Filter.
- Sort.
- CRUD.
- Export.
- Pagination.
- Summary.

### Output

Redesigned Transactions Workspace.

---

## Sprint 10.4 — Forecast Redesign

**Tool:** GPT → Codex → GPT + Screenshot

### Target Flow

```text
Current Financial Position
          ↓
Financial Projection
          ↓
Cashflow Forecast
          ↓
Scenario Simulator
          ↓
Goal Outlook
          ↓
Risk Detection
          ↓
Recommendation
```

### Goal

Forecast menjadi satu financial planning journey, bukan kumpulan fitur terpisah.

### Output

Redesigned Forecast.

---

## Sprint 10.5 — Settings Redesign

**Tool:** GPT → Codex → GPT + Screenshot

### Scope

- Profile.
- Application Settings.
- Financial Profile.
- Financial Goals.
- Integrations.
- Data Management.

### Goal

Meningkatkan:

- Navigation.
- Grouping.
- Form hierarchy.
- Readability.
- Configuration experience.

### Output

Redesigned Settings.

---

## Sprint 10.6 — Cross-Page Consistency Audit

**Tool:** GPT + Screenshot

### Review

Bandingkan:

- Overview.
- Analytics.
- Transactions.
- Forecast.
- Settings.

Check:

- Spacing.
- Heading.
- Typography.
- Container.
- Chart.
- Button.
- Icon.
- Form.
- Table.
- Color.
- Navigation.

### Output

Cross-Page UI Consistency Approval.

---

# 7. Sprint 11 — Interaction & UX Polish

## Objective

Membuat aplikasi tidak hanya bagus dilihat tetapi juga nyaman digunakan.

---

## Sprint 11.1 — Navigation & Interaction States

**Tool:** GPT → Codex

### Scope

- Sidebar.
- Active navigation.
- Selected states.
- Tabs.
- Hover.
- Button states.
- Dialogs.
- Expanders.

### Output

Polished Navigation & Interaction.

---

## Sprint 11.2 — User Feedback System

**Tool:** GPT → Codex

### Implement

Consistent feedback:

```text
Saving...
Saved successfully

Deleting...
Deleted

Refreshing...
Updated

Exporting...
Ready
```

Gunakan:

- Toast.
- Status.
- Loading indicator.
- Success feedback.
- Warning feedback.

### Output

Consistent User Feedback System.

---

## Sprint 11.3 — Loading, Empty & Error States

**Tool:** GPT → Codex

### Cases

- No transactions.
- No financial goals.
- No forecast.
- Empty analytics.
- Loading data.
- Failed request.
- Missing configuration.

### Output

Complete Application States.

---

## Sprint 11.4 — Functional UX QA

**Tool:** Work Mode

### Test

- Navigation.
- Filters.
- CRUD.
- Dialogs.
- Financial Goals.
- Scenario Simulator.
- Settings.
- Export.
- Refresh.

### Work Mode Focus

```text
Does it work?
```

Bukan:

```text
Does it look beautiful?
```

### Output

UX Functional QA Report + Bug List.

---

# 8. Sprint 12 — Validation, Error Handling & Logging

## Objective

Membuat aplikasi tahan terhadap input buruk, data bermasalah, dan integration failure.

---

## Sprint 12.1 — Input Validation

**Tool:** Codex

### Validate

- Nominal.
- Date.
- Transaction.
- Financial Goal.
- Financial Profile.
- Settings.
- Scenario.

### Output

Centralized Input Validation.

---

## Sprint 12.2 — Data & Schema Validation

**Tool:** Codex

### Validate

Google Sheets schema dan required fields.

Contoh transaction schema:

```text
Tanggal
Jenis
Kategori
Nominal
Catatan
```

### Output

Data Schema Validation Layer.

---

## Sprint 12.3 — Error Handling Architecture

**Tool:** GPT → Codex

### Error Taxonomy

Contoh:

```text
ValidationError
DataError
ConfigurationError
IntegrationError
ForecastError
```

### Goal

UI menampilkan human-readable error, bukan raw traceback.

### Output

Centralized Error Handling Architecture.

---

## Sprint 12.4 — Logging

**Tool:** Codex

### Logging Level

```text
INFO
WARNING
ERROR
CRITICAL
```

### Log

- Application startup.
- Data load.
- Transaction actions.
- Goal actions.
- Forecast generation.
- Settings update.
- Integration failure.
- Unexpected errors.

Credential dan data sensitif tidak boleh masuk log.

### Output

Application Logging System.

---

## Sprint 12.5 — Failure Testing

**Tool:** Codex + Work Mode

### Test

- Invalid amount.
- Missing field.
- Empty data.
- Invalid goal.
- Failed connection.
- Bad configuration.
- Invalid schema.

### Output

Failure Scenario QA Report.

---

# 9. Sprint 13 — Performance & Caching

## Objective

Mengurangi unnecessary rerun, repeated calculation, dan repeated Google Sheets request.

---

## Sprint 13.1 — Performance Audit

**Tool:** Codex

### Inspect

- Google Sheets calls.
- Repeated dataframe processing.
- Forecast calculations.
- Settings reads.
- Streamlit reruns.
- Expensive rendering.

### Output

Performance Bottleneck Report.

---

## Sprint 13.2 — Data Caching

**Tool:** Codex

### Implement

Appropriate use of:

```python
st.cache_data
```

Tambahkan TTL jika diperlukan.

### Output

Data Cache Layer.

---

## Sprint 13.3 — Resource Caching

**Tool:** Codex

### Implement

Appropriate use of:

```python
st.cache_resource
```

Untuk reusable connections, clients, atau resources.

### Output

Resource Cache Layer.

---

## Sprint 13.4 — Cache Invalidation

**Tool:** Codex

### Cache Must Update After

- Add Transaction.
- Edit Transaction.
- Delete Transaction.
- Goal changes.
- Settings changes.
- Relevant data updates.

### Output

Reliable Cache Invalidation Strategy.

---

## Sprint 13.5 — Performance QA

**Tool:** Work Mode + Codex

### Test

- Navigation speed.
- Rerender.
- CRUD refresh.
- Data freshness.
- Forecast loading.
- Settings update.

### Look For

- Slow rerender.
- Stale data.
- Cache bugs.
- Delayed updates.
- Unnecessary loading.

### Output

Performance QA Approval.

---

# 10. Sprint 14 — Testing & Code Quality

## Objective

Menjamin business logic tetap benar setelah redesign dan refactor.

---

## Sprint 14.1 — Test Infrastructure

**Tool:** Codex

### Implement

- Test directory.
- Test configuration.
- Fixtures.
- Mock data.
- Testing conventions.

### Output

Automated Test Infrastructure.

---

## Sprint 14.2 — Service Unit Tests

**Tool:** Codex

### Priority

- SheetService.
- AnalyticsService.
- ForecastService.
- SettingsService.
- DataManagementService.

### Output

Service Unit Test Suite.

---

## Sprint 14.3 — CRUD & Validation Tests

**Tool:** Codex

### Test

- Transaction CRUD.
- Financial Goal CRUD.
- Validation.
- Formatter.
- Edge cases.

### Output

CRUD & Validation Test Suite.

---

## Sprint 14.4 — Architecture Cleanup

**Tool:** Codex

### Audit

- Dead code.
- Duplicate code.
- Unused imports.
- Giant functions.
- Inconsistent naming.
- Circular dependencies.
- Business logic inside UI.
- Obsolete Streamlit hacks.

### Output

Cleaned Production Codebase.

---

## Sprint 14.5 — Regression QA

**Tool:** Work Mode

### Test

Core user journeys setelah refactoring.

### Goal

Memastikan code cleanup tidak merusak functionality.

### Output

Regression QA Approval.

---

# 11. Sprint 15 — Security & Data Reliability

## Objective

Melindungi application secrets dan financial data.

---

## Sprint 15.1 — Secrets Audit

**Tool:** Codex

### Audit

- Telegram Bot Token.
- Google credentials.
- Spreadsheet ID.
- API keys.
- `.env`.
- `secrets.toml`.
- `.gitignore`.

### Output

Secrets Security Audit.

---

## Sprint 15.2 — Configuration Hardening

**Tool:** Codex

### Implement

- Centralized configuration.
- Environment validation.
- Startup validation.
- Human-readable configuration errors.

### Output

Production Configuration Layer.

---

## Sprint 15.3 — Data Integrity

**Tool:** Codex

### Validate

- Transaction ID.
- Goal ID.
- Duplicate data.
- Required fields.
- Data types.
- Dates.
- Schema consistency.

### Output

Data Integrity Protection.

---

## Sprint 15.4 — Backup & Recovery

**Tool:** GPT → Codex

### Strategy

Gunakan strategi yang proporsional untuk personal finance system.

Potential approach:

```text
Google Sheets
      ↓
Periodic Backup
      ↓
CSV / Excel / Snapshot
      ↓
Recovery Procedure
```

### Output

Backup & Recovery System.

---

## Sprint 15.5 — Reliability QA

**Tool:** Codex + Work Mode

### Test

- Backup.
- Recovery.
- Corrupt input.
- Missing configuration.
- Data integrity protection.
- Failure scenarios.

### Output

Reliability QA Approval.

---

# 12. Sprint 16 — Deployment & Production Release

## Objective

Menjalankan Personal Finance System secara production tanpa bergantung pada laptop lokal.

---

## Sprint 16.1 — Deployment Architecture

**Tool:** GPT

### Decide

Deployment strategy untuk:

- Streamlit Dashboard.
- Telegram Bot.
- Secrets.
- Google credentials.
- Logs.

Pertimbangkan:

- Cost.
- Complexity.
- Reliability.
- Maintenance.

### Output

Production Deployment Architecture.

---

## Sprint 16.2 — Production Configuration

**Tool:** Codex

### Prepare

- Requirements.
- Environment.
- Startup commands.
- Secrets.
- Logging.
- Production configuration.

### Output

Production-Ready Repository.

---

## Sprint 16.3 — Dashboard Deployment

**Tool:** Codex + Work Mode

### Scope

Deploy Streamlit Dashboard.

### Test

- Production URL.
- Navigation.
- Data loading.
- Charts.
- CRUD.
- Forecast.
- Settings.

### Output

Live Production Dashboard.

---

## Sprint 16.4 — Telegram Bot Deployment

**Tool:** Codex + Work Mode

### Goal

Telegram Bot berjalan tanpa laptop lokal.

### Test

```text
Telegram
    ↓
Transaction Input
    ↓
Google Sheets
```

### Output

24/7 Telegram Bot.

---

## Sprint 16.5 — End-to-End Production Test

**Tool:** Work Mode + Manual User Test

### Test Flow

```text
Telegram
    ↓
Input Transaction
    ↓
Google Sheets
    ↓
Dashboard
    ↓
Analytics
    ↓
Forecast
    ↓
Goal Tracking
```

User juga melakukan minimal satu manual end-to-end test sebagai actual system user.

### Output

Production E2E Approval.

---

## Sprint 16.6 — Final UI Review

**Tool:** GPT + Screenshot

### Review

Production screenshot:

- Overview.
- Analytics.
- Transactions.
- Forecast.
- Settings.

### Rule

Hanya minor correction.

Tidak melakukan redesign besar pada tahap ini.

### Output

Final Visual Approval.

---

## Sprint 16.7 — Release

**Tool:** GPT + Codex

### Finalize

- README.
- Summary.
- Progress.
- Architecture documentation.
- Deployment notes.
- Known limitations.
- Cleanup.
- Versioning.

### Release

```text
Personal Finance System
v1.0.0
```

### Output

**Production Release — v1.0.0**

---

# 13. Phase 3 Summary Table

| Sprint | Parts | Focus | Primary Tools | Main Output |
|---|---|---|---|---|
| Sprint 8 | 8.1–8.6 | UI/UX Audit & Visual Direction | GPT + Screenshot | `UI_REDESIGN_PLAN.md` |
| Sprint 9 | 9.1–9.5 | Design System & UI Foundation | GPT + Codex | Global UI Foundation |
| Sprint 10 | 10.1–10.6 | Full Page Redesign | GPT + Screenshot + Codex | Redesigned Dashboard |
| Sprint 11 | 11.1–11.4 | Interaction & UX Polish | GPT + Codex + Work Mode | Polished UX |
| Sprint 12 | 12.1–12.5 | Validation, Errors & Logging | Codex + Work Mode | Robust Application |
| Sprint 13 | 13.1–13.5 | Performance & Caching | Codex + Work Mode | Optimized Application |
| Sprint 14 | 14.1–14.5 | Testing & Code Quality | Codex + Work Mode | Tested & Clean Codebase |
| Sprint 15 | 15.1–15.5 | Security & Data Reliability | GPT + Codex + Work Mode | Secure & Reliable System |
| Sprint 16 | 16.1–16.7 | Deployment & Release | GPT + Codex + Work Mode | Production v1.0.0 |

---

# 14. Tool Responsibility Summary

| Tool | Primary Responsibility |
|---|---|
| GPT | Architecture, product thinking, design decisions, requirements, trade-offs |
| GPT + Screenshot | Primary visual/UI reviewer |
| Codex | Coding, refactoring, testing, optimization, security, production engineering |
| Work Mode | Functional QA, interaction testing, end-to-end testing |
| User | Product owner, design approval, final usability approval |

---

# 15. Phase 3 Execution Principle

## UI Work

```text
Screenshot
    ↓
GPT Review
    ↓
Design Decision
    ↓
Codex Implementation
    ↓
Screenshot
    ↓
GPT Review
    ↓
Approved
```

## Engineering Work

```text
GPT Requirement
      ↓
Codex
      ↓
Automated Tests
      ↓
Work Mode QA
      ↓
Codex Fix
      ↓
Approved
```

## Production Release

```text
Codex
   ↓
Deployment
   ↓
Work Mode QA
   ↓
Manual User Test
   ↓
GPT Visual Review
   ↓
Final Fix
   ↓
v1.0.0
```

---

# 16. Definition of Done — Phase 3

Phase 3 dianggap selesai ketika:

- [ ] Seluruh halaman menggunakan design system yang konsisten.
- [ ] Streamlit default look telah diminimalkan.
- [ ] Overview telah menjadi financial command center.
- [ ] Analytics memiliki analytical flow yang jelas.
- [ ] Transactions memiliki proper data-management UX.
- [ ] Forecast memiliki financial planning narrative.
- [ ] Settings memiliki configuration hierarchy yang jelas.
- [ ] Navigation dan interaction telah dipolish.
- [ ] Loading, empty, success, warning, dan error states tersedia.
- [ ] Input dan data memiliki validation.
- [ ] Error handling terpusat.
- [ ] Logging tersedia.
- [ ] Google Sheets request dan expensive computation telah dioptimalkan.
- [ ] Caching dan cache invalidation bekerja dengan benar.
- [ ] Critical business logic memiliki automated tests.
- [ ] Codebase telah melalui architecture cleanup.
- [ ] Secrets tidak tersimpan secara tidak aman.
- [ ] Data integrity protection tersedia.
- [ ] Backup dan recovery procedure tersedia.
- [ ] Streamlit Dashboard berjalan secara production.
- [ ] Telegram Bot berjalan tanpa bergantung pada laptop lokal.
- [ ] End-to-end production flow berhasil.
- [ ] Final UI review selesai.
- [ ] Dokumentasi production selesai.
- [ ] Personal Finance System `v1.0.0` dirilis.

---

# Phase 3 Final Target

```text
PHASE 2
Functional Dashboard V1
        │
        ▼
PHASE 3
┌─────────────────────────────────┐
│ Sprint 8–11                     │
│ UI / UX                         │
│                                 │
│ Functional → Polished           │
├─────────────────────────────────┤
│ Sprint 12–15                    │
│ Production Engineering          │
│                                 │
│ Polished → Reliable             │
├─────────────────────────────────┤
│ Sprint 16                       │
│ Deployment                      │
│                                 │
│ Reliable → Production           │
└─────────────────────────────────┘
        │
        ▼
Personal Finance System
v1.0.0