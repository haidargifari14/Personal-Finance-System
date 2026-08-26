# Personal Finance Dashboard
## Phase 2 Summary

Last Updated: August 2026

---

# Project Overview

Personal Finance Dashboard adalah sistem manajemen keuangan pribadi yang dibangun menggunakan:

- Streamlit Dashboard
- Telegram Bot
- Google Sheets
- Python

Project berfokus pada Financial Decision Support System, bukan sekadar aplikasi pencatat transaksi.

Workflow utama:

Telegram Bot
↓

Google Sheets

↓

Analytics Service

↓

Dashboard

↓

Forecast & Decision Support

---

# Architecture

Telegram Bot

↓

Google Sheets

↓

SheetService

↓

AnalyticsService

↓

ForecastService

↓

Dashboard Pages

Settings menggunakan:

SettingsService

↓

Financial Profile

↓

Financial Goals

↓

ForecastService

---

# Dashboard Structure

## Overview

Purpose

Memberikan gambaran kondisi keuangan saat ini.

Features

- Global Filter
- KPI Cards
- Income vs Expense
- Expense by Category
- Cashflow Trend
- Monthly Trend
- Recent Transactions
- Financial Insight

---

## Analytics

Purpose

Menjelaskan penyebab perubahan kondisi keuangan.

Features

- Top Spending Categories
- Category Drilldown
- Period Comparison
- Financial Statistics

---

## Transactions

Purpose

Mengelola seluruh transaksi.

Features

- Search
- Filter
- Sort
- CRUD
- CSV Export
- Excel Export
- Transaction Summary
- Refresh
- Validation

---

## Forecast

Purpose

Membantu user mengambil keputusan finansial.

Features

- Financial Projection
- Cashflow Forecast
- Scenario Simulator
- Goal Forecast
- Risk Detection
- AI Recommendation

Forecast menggunakan:

ForecastService

sebagai pusat seluruh business logic.

---

## Settings

Purpose

Mengelola konfigurasi user.

Sections

- Profile
- Application Settings
- Financial Profile
- Financial Goals
- Integrations
- Data Management

Settings menggunakan:

SettingsService

sebagai single source of truth.

---

# Services

Current Services

- SheetService
- AnalyticsService
- ForecastService
- SettingsService
- IntegrationService
- DataManagementService
- ReportService

---

# Current Architecture Principles

- UI tidak boleh melakukan business logic.
- Business logic berada pada Service Layer.
- Dashboard Page hanya melakukan rendering.
- Reusable Components digunakan sebanyak mungkin.
- Formatter digunakan secara konsisten.
- CRUD dilakukan melalui Service.
- Forecast menggunakan ForecastService.
- Financial Goals dibaca melalui SettingsService.

---

# Design Principles

Dashboard bukan sekadar visualisasi data.

Setiap halaman memiliki tujuan berbeda.

Overview

↓

Apa yang terjadi?

Analytics

↓

Mengapa terjadi?

Transactions

↓

Data apa yang menyebabkan?

Forecast

↓

Apa yang kemungkinan akan terjadi?

Settings

↓

Konfigurasi user.

---

# Phase 2 Result

Phase 2 berhasil menyelesaikan Dashboard V1.

Seluruh halaman utama telah selesai dibangun beserta fitur inti masing-masing.

Project siap memasuki Phase 3:
Production Engineering.