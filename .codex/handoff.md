# Project Handoff

Last Updated: August 2026

---

# Project

Personal Finance Dashboard

Status:

🟢 Dashboard V1 Complete

Current Phase:

Phase 3 — Production Engineering

---

# Project Goal

Build a Financial Decision Support System (FDSS), not just a personal finance tracker.

The application should help users:

- Record transactions
- Understand financial behavior
- Forecast future cashflow
- Detect financial risks
- Support financial decision making

---

# Technology Stack

Frontend

- Streamlit

Backend

- Python

Data Storage

- Google Sheets

Input

- Telegram Bot

Visualization

- Plotly

Architecture

- Service Layer

---

# Current Architecture

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

Settings

↓

SettingsService

↓

Financial Profile

↓

Financial Goals

↓

ForecastService

Dashboard pages should only orchestrate UI.

Business logic belongs inside Services.

---

# Pages

## Overview

Completed

Purpose

Current financial condition.

---

## Analytics

Completed

Purpose

Explain why financial changes happen.

---

## Transactions

Completed

Purpose

Manage transaction records.

---

## Forecast

Completed

Purpose

Predict future financial condition.

Uses:

ForecastService

---

## Settings

Completed

Purpose

Manage user configuration.

Uses:

SettingsService

---

# Service Layer

Current services

- SheetService
- AnalyticsService
- ForecastService
- SettingsService
- IntegrationService
- DataManagementService
- ReportService

New business logic should always be added to an appropriate Service.

Never place business logic inside Streamlit pages.

---

# Architectural Rules

Always:

- Keep Pages responsible only for rendering.
- Keep business logic inside Services.
- Reuse existing Services.
- Reuse existing Components.
- Reuse existing Formatter utilities.
- Prefer incremental changes.
- Keep architecture modular.
- Maintain separation between UI and business logic.

Never:

- Duplicate business logic.
- Read Google Sheets directly from Pages.
- Store business logic inside Components.
- Bypass Service Layer.
- Rewrite large existing files without necessity.
- Refactor unrelated modules during feature development.

---

# Single Source of Truth

Transactions

↓

SheetService

Analytics

↓

AnalyticsService

Forecast

↓

ForecastService

Settings

↓

SettingsService

Do not create parallel implementations.

---

# Coding Principles

- Keep components reusable.
- Prefer composition over duplication.
- Keep naming consistent.
- Maintain backward compatibility whenever possible.
- Avoid unnecessary abstraction.
- Avoid overengineering.
- Make incremental improvements.

---

# UI Principles

Dashboard should answer different business questions.

Overview

↓

"What is happening?"

Analytics

↓

"Why is it happening?"

Transactions

↓

"What data caused it?"

Forecast

↓

"What will likely happen?"

Settings

↓

"How should the system behave?"

---

# Scope Management

Each sprint should:

- Solve one problem.
- Have clear boundaries.
- Avoid unrelated refactoring.
- Reuse existing architecture.

If a feature requires major architectural changes:

Pause implementation.

Review architecture first.

---

# Testing Philosophy

After each completed sprint:

1. Manual testing
2. Computer Use testing
3. Bug fixing
4. Polish

Do not continue adding features while critical bugs remain.

---

# Current Project State

Phase 1

✅ Completed

Phase 2

✅ Completed

Dashboard V1 is feature complete.

Current focus:

Phase 3

Production Engineering

---

# Phase 3 Roadmap

Sprint 8

QA & Regression Testing

Sprint 9

UI / UX Polish

Sprint 10

Performance Optimization

Sprint 11

Architecture Refactor

Sprint 12

Documentation

Goal:

Transform Dashboard V1 into production-quality software.

---

# Future Roadmap

Phase 4

AI Intelligence

Potential features:

- OCR Receipt
- Voice Transaction
- Smart Categorization
- AI Advisor
- Conversational Financial Assistant

---

Phase 5

Production

Potential features:

- Authentication
- Cloud Database
- Deployment
- Notification System
- Recurring Transactions
- Shared Budget

---

# Development Workflow

Preferred workflow:

GPT

↓

Architecture

↓

Sprint Planning

↓

Codex

↓

Implementation

↓

Computer Use

↓

QA Testing

↓

GPT

↓

Bug Review

↓

Codex

↓

Bug Fix

Repeat for each sprint.

---

# Before Starting Any New Sprint

Review:

- summary.md
- progress.md
- .codex/context.md
- .codex/architecture.md
- .codex/coding_rules.md
- .codex/decision_log.md

Then:

- Define sprint objective.
- Limit implementation scope.
- Reuse existing architecture.
- Avoid unnecessary rewrites.

---

# Final Reminder

The priority is not to build more features.

The priority is to build maintainable, modular, production-ready software.

Every implementation should improve the system without increasing unnecessary complexity.