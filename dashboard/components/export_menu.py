"""Reusable export controls for filtered dashboard transactions."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_transaction_export_menu(
    container: Any,
    *,
    csv_data: bytes | None,
    excel_data: bytes | None,
    file_stem: str,
) -> None:
    """Render CSV and Excel downloads within a supplied popover container."""

    with container:
        st.caption("Export filtered transactions")
        if csv_data is None or excel_data is None:
            st.info("No transactions are available to export.")
        st.download_button(
            "Download CSV",
            data=csv_data or b"",
            file_name=f"{file_stem}.csv",
            mime="text/csv",
            icon=":material/table_view:",
            on_click="ignore",
            width="stretch",
            disabled=csv_data is None,
        )
        st.download_button(
            "Download Excel",
            data=excel_data or b"",
            file_name=f"{file_stem}.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            icon=":material/grid_on:",
            on_click="ignore",
            width="stretch",
            disabled=excel_data is None,
        )
