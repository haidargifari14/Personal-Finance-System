# UI Guidelines

## Principles

- Present financial information clearly before adding decoration.
- Use consistent currency, date, and percentage formatting.
- Prefer reusable components for metrics, filters, charts, and tables.
- Design meaningful empty, loading, and error states.
- Keep visual hierarchy consistent across dashboard pages.

## Dashboard conventions

| Element | Guideline |
| --- | --- |
| Pages | Orchestrate UI only; request prepared data from services. |
| Metric cards | Use consistent labels, time scope, and currency format. |
| Charts | Build reusable chart functions in `dashboard/components/charts.py`. |
| Tables | Provide readable columns, sensible ordering, and clear empty states. |
| Filters | Make filters reusable and apply them through the service layer. |
| Colors | Use a consistent semantic palette: income positive, expense cautionary, balance contextual. |

## Telegram conventions

- Use concise Indonesian messages.
- Keep keyboard labels action-oriented and consistent.
- Confirm irreversible or persistent actions.
- Return users to a clear next action after success, cancellation, or error.
