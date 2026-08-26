"""Global date controls shared by every dashboard page."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

QUICK_FILTER_OPTIONS = ("Today", "This Week", "This Month", "This Year")
GLOBAL_START_DATE_KEY = "global_start_date"
GLOBAL_END_DATE_KEY = "global_end_date"
GLOBAL_QUICK_FILTER_KEY = "global_quick_filter"


def render_global_filter() -> tuple[date, date]:
    """Render the global date filter in the dashboard sidebar."""

    _initialize_global_filter()

    with st.sidebar:
        st.divider()
        with st.expander("Global filter", expanded=True):
            st.selectbox(
                "Quick filter",
                QUICK_FILTER_OPTIONS,
                key=GLOBAL_QUICK_FILTER_KEY,
                on_change=_apply_quick_filter,
                index=None,
                placeholder="Custom date range",
                width="stretch",
            )
            st.date_input(
                "Start date",
                key=GLOBAL_START_DATE_KEY,
                on_change=_mark_custom_date_range,
            )
            st.date_input(
                "End date",
                key=GLOBAL_END_DATE_KEY,
                on_change=_mark_custom_date_range,
            )

    return get_global_filter_values()


def get_global_filter_values() -> tuple[date, date]:
    """Return the active global date range from Streamlit session state."""

    _initialize_global_filter()
    return (
        st.session_state[GLOBAL_START_DATE_KEY],
        st.session_state[GLOBAL_END_DATE_KEY],
    )


def _initialize_global_filter() -> None:
    """Initialize the global date range with the current month."""

    today = date.today()
    st.session_state.setdefault(GLOBAL_START_DATE_KEY, today.replace(day=1))
    st.session_state.setdefault(GLOBAL_END_DATE_KEY, today)
    st.session_state.setdefault(GLOBAL_QUICK_FILTER_KEY, "This Month")


def _apply_quick_filter() -> None:
    """Synchronize the global date range with the selected quick filter."""

    date_range = _get_quick_filter_dates(
        st.session_state.get(GLOBAL_QUICK_FILTER_KEY),
        date.today(),
    )
    if date_range is None:
        return

    st.session_state[GLOBAL_START_DATE_KEY] = date_range[0]
    st.session_state[GLOBAL_END_DATE_KEY] = date_range[1]


def _mark_custom_date_range() -> None:
    """Clear the quick-filter selection after a manual date change."""

    st.session_state[GLOBAL_QUICK_FILTER_KEY] = None


def _get_quick_filter_dates(
    quick_filter: str | None,
    reference_date: date,
) -> tuple[date, date] | None:
    """Return the range represented by a quick-filter selection."""

    if quick_filter == "Today":
        return reference_date, reference_date
    if quick_filter == "This Week":
        return (
            reference_date - timedelta(days=reference_date.weekday()),
            reference_date,
        )
    if quick_filter == "This Month":
        return reference_date.replace(day=1), reference_date
    if quick_filter == "This Year":
        return reference_date.replace(month=1, day=1), reference_date
    return None
