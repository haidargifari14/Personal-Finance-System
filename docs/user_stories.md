# User Stories

## Telegram Bot

| ID | User story | Acceptance criteria |
| --- | --- | --- |
| US-01 | As a user, I want to record an expense so I can track money leaving my account. | I can select an expense category, enter a valid positive amount, add or skip a note, confirm, and save. |
| US-02 | As a user, I want to record income so I can track money coming in. | I can follow the same flow using income categories and the transaction is stored as income. |
| US-03 | As a user, I want to cancel an unconfirmed transaction so accidental input is not stored. | Cancelling clears the in-progress transaction and shows a clear next action. |
| US-04 | As a user, I want a daily report so I can understand today's income, expense, balance, and transaction count. | The report aggregates only transactions dated today. |
| US-05 | As a user, I want a monthly report so I can understand the current month's financial position. | The report includes income, expense, balance, and leading expense categories. |

## Dashboard

| ID | User story | Acceptance criteria |
| --- | --- | --- |
| US-06 | As a user, I want an overview dashboard so I can quickly see my financial position. | The page displays reusable metrics and live data sourced through `AnalyticsService`. |
| US-07 | As a user, I want to filter transactions so I can inspect a relevant period or category. | Filters are reusable and affect only the requested view. |
| US-08 | As a user, I want an expense-by-category chart so I can identify where I spend the most. | The chart uses prepared analytics data and handles empty data gracefully. |
| US-09 | As a user, I want to inspect transactions in a table so I can verify recorded entries. | The table has clear columns, readable formatting, and an empty state. |

## Future user stories

- As a user, I want a budget planner so I can set limits by category.
- As a user, I want a cashflow forecast so I can anticipate my financial position.
- As a user, I want notification reminders so I can keep my records current.
- As a user, I want receipt OCR so I can record purchases faster.
- As a user, I want an AI financial advisor so I can receive data-grounded suggestions.
