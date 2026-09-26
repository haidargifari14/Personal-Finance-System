"""
dashboard/components/charts.py

Reusable chart components for
Personal Finance Dashboard.
"""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.formatter import format_currency
from dashboard.utils.theme import (
    CHART_HEIGHT,
    DANGER_COLOR,
    PIE_CHART_HEIGHT,
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
CATEGORY_COLORS = ("#75ADEF", "#F36B93", "#FDB549", "#E86A63", "#4BB980", "#A991E1")


# =====================================================
# Internal Helper
# =====================================================

def _apply_layout(fig):
    """Apply the shared visual style for dashboard charts."""

    fig.update_layout(
        template="plotly_white",
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
        hoverlabel=dict(
            bgcolor="#FFFDFB",
            bordercolor="#E8DBD1",
            font=dict(color="#332621", family="Inter, Arial, sans-serif"),
            namelength=-1,
        ),
        font=dict(color="#5F4D44", family="Inter, Arial, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
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
        gridcolor="#EFE6DE",
        tickfont=dict(color="#9A887E", size=10),
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
    """Render expense totals as a compact donut and readable category legend."""

    if data.empty:
        empty_chart("Belum ada data pengeluaran untuk filter yang dipilih.")
        return

    total_expense = int(data["amount"].sum())
    fig = px.pie(
        data_frame=data,
        names="category",
        values="amount",
        color_discrete_sequence=CATEGORY_COLORS,
        hole=0.66,
    )
    fig.update_traces(
        textinfo="none",
        hovertemplate="%{label}<br>Rp%{value:,.0f}<br>%{percent}<extra></extra>",
    )
    fig.add_annotation(
        text=(
            "<span style='font-size:11px;color:#806F66'>Total Expense</span><br>"
            f"<b>{format_currency(total_expense)}</b>"
        ),
        showarrow=False,
        font=dict(color="#332621", size=13),
    )
    fig.update_layout(
        template="plotly_white",
        height=PIE_CHART_HEIGHT,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#5F4D44", family="Inter, Arial, sans-serif"),
        hoverlabel=dict(
            bgcolor="#FFFDFB",
            bordercolor="#E8DBD1",
            font=dict(color="#332621", family="Inter, Arial, sans-serif"),
        ),
    )

    chart_column, legend_column = st.columns([0.82, 1.35], vertical_alignment="center")
    with chart_column:
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with legend_column:
        for index, row in enumerate(data.itertuples(index=False)):
            percentage = 0 if total_expense == 0 else int(row.amount) / total_expense * 100
            color = CATEGORY_COLORS[index % len(CATEGORY_COLORS)]
            st.markdown(
                "<div style='align-items:center;border-bottom:1px solid #F1E8E1;"
                "display:flex;gap:8px;justify-content:space-between;padding:7px 0;'>"
                "<span style='color:{color};font-size:16px;'>●</span>"
                "<span style='color:#4E3E36;flex:1;font-size:0.8rem;'>{category}</span>"
                "<span style='color:#4E3E36;font-size:0.78rem;font-weight:650;'>{amount}</span>"
                "<span style='color:#9B887D;font-size:0.72rem;min-width:38px;text-align:right;'>{percentage:.1f}%</span>"
                "</div>".format(
                    color=color,
                    category=escape(str(row.category)),
                    amount=format_currency(int(row.amount)),
                    percentage=percentage,
                ),
                unsafe_allow_html=True,
            )


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
        height=250,
        margin=dict(l=8, r=8, t=16, b=4),
    )
    _apply_layout(fig)
    fig.update_layout(height=250, margin=dict(l=8, r=8, t=16, b=4))
    _apply_currency_axis(fig)
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#9A887E", size=10))
    fig.update_traces(line=dict(width=2.2), marker=dict(size=4))

    st.plotly_chart(
        fig,
        width="stretch",
        config={"displayModeBar": False},
    )


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
        color_discrete_sequence=[PRIMARY_COLOR],
    )
    fig.update_traces(
        hovertemplate="%{x|%b %Y}<br>Rp%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        xaxis_title=None,
        showlegend=False,
        height=284,
        margin=dict(l=8, r=8, t=8, b=2),
    )
    _apply_currency_axis(fig)
    _apply_layout(fig)
    fig.update_layout(height=284, margin=dict(l=8, r=8, t=8, b=2))
    fig.update_xaxes(
        showgrid=False,
        tickformat="%b\n%Y",
        tickfont=dict(color="#9A887E", size=10),
        hoverformat="%b %Y",
    )

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


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
    fig.update_xaxes(
        tickformat="%d %b",
        hoverformat="%d %b %Y",
        showgrid=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


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
