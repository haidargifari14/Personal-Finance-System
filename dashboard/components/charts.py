"""
dashboard/components/charts.py

Reusable chart components for
Personal Finance Dashboard.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.theme import (
    CHART_HEIGHT,
    DANGER_COLOR,
    PRIMARY_COLOR,
    SUCCESS_COLOR,
)


INCOME_COLOR = SUCCESS_COLOR
EXPENSE_COLOR = DANGER_COLOR
BALANCE_COLOR = PRIMARY_COLOR
TRANSACTION_COLORS = {
    "Income": INCOME_COLOR,
    "Expense": EXPENSE_COLOR,
    "income": INCOME_COLOR,
    "expense": EXPENSE_COLOR,
}


# =====================================================
# Internal Helper
# =====================================================

def _apply_layout(fig):
    """Apply the shared visual style for dashboard charts."""

    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(
            l=8,
            r=8,
            t=24,
            b=8,
        ),
        legend_title=None,
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=1.02,
            yanchor="bottom",
        ),
        hoverlabel=dict(namelength=-1),
        separators=",.",
    )

    return fig


def _apply_currency_axis(fig) -> None:
    """Format a chart's value axis with readable Rupiah values."""

    fig.update_yaxes(
        title=None,
        tickprefix="Rp ",
        tickformat=",.0f",
        showgrid=True,
        zeroline=False,
    )


# =====================================================
# Generic Charts
# =====================================================

def line_chart(
    data: pd.DataFrame,
    *,
    x: str,
    y,
    title: str,
):
    """
    Render reusable line chart.
    """

    fig = px.line(
        data_frame=data,
        x=x,
        y=y,
        title=title,
    )

    _apply_layout(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )


def bar_chart(
    data: pd.DataFrame,
    *,
    x: str,
    y: str,
    title: str,
):
    """
    Render reusable bar chart.
    """

    fig = px.bar(
        data_frame=data,
        x=x,
        y=y,
        title=title,
        text_auto=True,
    )

    _apply_layout(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )


def pie_chart(
    data: pd.DataFrame,
    *,
    names: str,
    values: str,
    title: str,
):
    """
    Render reusable pie chart.
    """

    fig = px.pie(
        data_frame=data,
        names=names,
        values=values,
        title=title,
    )

    _apply_layout(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )

# =====================================================
# Personal Finance Charts
# =====================================================

def income_vs_expense_chart(
    data: pd.DataFrame,
):
    """
    Render Income vs Expense bar chart.
    """

    if data.empty or data["amount"].sum() <= 0:
        empty_chart("Belum ada data Income atau Expense untuk filter yang dipilih.")
        return

    fig = px.bar(
        data_frame=data,
        x="type",
        y="amount",
        color="type",
        color_discrete_map=TRANSACTION_COLORS,
    )

    fig.update_traces(
        hovertemplate="%{x}<br>Rp%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(xaxis_title=None, showlegend=False)
    _apply_currency_axis(fig)

    _apply_layout(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )


def expense_by_category_chart(data: pd.DataFrame) -> None:
    """Render expense totals grouped by category as a pie chart."""

    if data.empty:
        empty_chart("Belum ada data pengeluaran untuk filter yang dipilih.")
        return

    fig = px.pie(
        data_frame=data,
        names="category",
        values="amount",
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>Rp%{value:,.0f}<br>%{percent}<extra></extra>",
    )
    _apply_layout(fig)

    st.plotly_chart(fig, width="stretch")


def cashflow_trend_chart(data: pd.DataFrame) -> None:
    """Render daily income and expense totals as a line chart."""

    if data.empty or data[["income", "expense"]].to_numpy().sum() <= 0:
        empty_chart("Belum ada data cashflow untuk filter yang dipilih.")
        return

    fig = px.line(
        data_frame=data,
        x="date",
        y=["income", "expense"],
        markers=True,
        labels={
            "date": "Tanggal",
            "value": "Nominal (Rp)",
            "variable": "Jenis",
            "income": "Income",
            "expense": "Expense",
        },
        color_discrete_map=TRANSACTION_COLORS,
    )
    fig.update_traces(
        hovertemplate="%{fullData.name}<br>%{x|%d %b %Y}<br>Rp%{y:,.0f}<extra></extra>"
    )
    fig.update_layout(
        xaxis_title=None,
        hovermode="x unified",
    )
    _apply_currency_axis(fig)
    _apply_layout(fig)

    st.plotly_chart(fig, width="stretch")


def monthly_trend_chart(data: pd.DataFrame) -> None:
    """Render monthly income and expense totals as grouped bars."""

    if data.empty or data[["income", "expense"]].to_numpy().sum() <= 0:
        empty_chart("Belum ada data bulanan untuk filter yang dipilih.")
        return

    fig = px.bar(
        data_frame=data,
        x="month",
        y=["income", "expense"],
        barmode="group",
        labels={
            "month": "Bulan",
            "value": "Nominal (Rp)",
            "variable": "Jenis",
            "income": "Income",
            "expense": "Expense",
        },
        color_discrete_map=TRANSACTION_COLORS,
    )
    fig.update_traces(
        hovertemplate="%{fullData.name}<br>%{x|%b %Y}<br>Rp%{y:,.0f}<extra></extra>"
    )
    fig.update_layout(
        xaxis_title=None,
        hovermode="x unified",
    )
    _apply_currency_axis(fig)
    _apply_layout(fig)

    st.plotly_chart(fig, width="stretch")


def category_monthly_trend_chart(data: pd.DataFrame) -> None:
    """Render the monthly expense trend for one selected category."""

    if data.empty or data["amount"].sum() <= 0:
        empty_chart("Belum ada tren bulanan untuk kategori yang dipilih.")
        return

    fig = px.bar(
        data_frame=data,
        x="month",
        y="amount",
        color_discrete_sequence=[EXPENSE_COLOR],
    )
    fig.update_traces(
        hovertemplate="%{x|%b %Y}<br>Rp%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(xaxis_title=None, showlegend=False)
    _apply_currency_axis(fig)
    _apply_layout(fig)

    st.plotly_chart(fig, width="stretch")


def cashflow_forecast_chart(data: pd.DataFrame, today: pd.Timestamp) -> None:
    """Render historical and forecast cashflow with a Today reference line."""

    if data.empty:
        empty_chart("Belum ada data yang cukup untuk membuat cashflow forecast.")
        return

    fig = go.Figure()
    series = (
        ("balance", "Balance", BALANCE_COLOR),
        ("income", "Income", INCOME_COLOR),
        ("expense", "Expense", EXPENSE_COLOR),
    )
    for period, dash in (("Historical", "solid"), ("Forecast", "dash")):
        period_data = data[data["period"] == period]
        for column, label, color in series:
            fig.add_trace(
                go.Scatter(
                    x=period_data["date"],
                    y=period_data[column],
                    mode="lines+markers",
                    name=f"{label} ({period})",
                    line=dict(color=color, dash=dash),
                    marker=dict(size=5),
                    hovertemplate=(
                        f"{label} ({period})<br>"
                        "%{x|%d %b %Y}<br>Rp%{y:,.0f}<extra></extra>"
                    ),
                )
            )

    fig.add_vline(
        x=today,
        line_dash="dot",
        line_color="gray",
        annotation_text="Today",
        annotation_position="top",
    )
    fig.update_layout(xaxis_title=None, hovermode="x unified")
    _apply_currency_axis(fig)
    _apply_layout(fig)

    st.plotly_chart(fig, width="stretch")


def estimated_balance_trajectory_chart(data: pd.DataFrame) -> None:
    """Render one forward-looking balance line from Forecast V2 trajectory data."""

    if data.empty:
        empty_chart("Pilih kategori Forecast untuk melihat trajectory saldo.")
        return

    fig = go.Figure(
        go.Scatter(
            x=data["date"],
            y=data["estimated_balance"],
            mode="lines+markers",
            name="Estimated Balance",
            line=dict(color=BALANCE_COLOR),
            marker=dict(size=5),
            customdata=data[
                ["projected_spending_today", "cumulative_selected_spending"]
            ].to_numpy(),
            hovertemplate=(
                "%{x|%d %b %Y}<br>"
                "Estimated Balance: Rp%{y:,.0f}<br>"
                "Projected Spending Today: Rp%{customdata[0]:,.0f}<br>"
                "Cumulative Selected Spending: Rp%{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(xaxis_title=None, showlegend=False)
    _apply_currency_axis(fig)
    _apply_layout(fig)
    st.plotly_chart(fig, width="stretch")


def scenario_balance_trajectory_chart(
    baseline_data: pd.DataFrame,
    scenario_data: pd.DataFrame,
) -> None:
    """Render aligned baseline and hypothetical Scenario balance trajectories."""

    if baseline_data.empty or scenario_data.empty:
        empty_chart("Pilih kategori Forecast untuk melihat Scenario trajectory.")
        return

    fig = go.Figure()
    for data, name, color, dash in (
        (baseline_data, "Baseline Estimated Balance", BALANCE_COLOR, "solid"),
        (scenario_data, "Scenario Estimated Balance", SUCCESS_COLOR, "dash"),
    ):
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["estimated_balance"],
                mode="lines+markers",
                name=name,
                line=dict(color=color, dash=dash),
                marker=dict(size=5),
                hovertemplate=(
                    f"{name}<br>%{{x|%d %b %Y}}<br>"
                    "Rp%{y:,.0f}<extra></extra>"
                ),
            )
        )
    fig.update_layout(xaxis_title=None, hovermode="x unified")
    _apply_currency_axis(fig)
    _apply_layout(fig)
    st.plotly_chart(fig, width="stretch")


# =====================================================
# Placeholder
# =====================================================

def empty_chart(
    message: str = "Belum ada data untuk ditampilkan.",
):
    """
    Display a consistent empty chart state.
    """

    st.info(message)


# =====================================================
# Error
# =====================================================

def show_chart_error(
    message: str,
):
    """
    Display chart error.
    """

    st.error(message)
