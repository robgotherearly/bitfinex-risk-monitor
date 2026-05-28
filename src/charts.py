"""
charts.py

Plotly figure builders, shared by the live Streamlit app and the static HTML
preview so both render identical visuals. All colours are driven by a small
palette dict to keep the "risk terminal" look consistent.
"""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

PALETTE = {
    "bg": "#0d1117",
    "grid": "#1f2630",
    "text": "#c9d1d9",
    "muted": "#6e7681",
    "accent": "#39d0d8",
    "up": "#26a17b",
    "down": "#f6465d",
    "warning": "#e3b341",
    "critical": "#f6465d",
}


def _base_layout(fig: go.Figure, height: int = 260, title: str = "") -> go.Figure:
    fig.update_layout(
        height=height,
        title=dict(text=title, font=dict(size=13, color=PALETTE["muted"]), x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], family="ui-monospace, monospace", size=11),
        margin=dict(l=48, r=16, t=34, b=28),
        showlegend=False,
        xaxis=dict(gridcolor=PALETTE["grid"], zeroline=False),
        yaxis=dict(gridcolor=PALETTE["grid"], zeroline=False),
    )
    return fig


def price_drawdown_chart(df, thresholds) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38],
        vertical_spacing=0.06,
        subplot_titles=("PRICE (close)", "ROLLING DRAWDOWN %"),
    )
    fig.add_trace(go.Scatter(
        x=df.index, y=df["close"], mode="lines",
        line=dict(color=PALETTE["accent"], width=1.4)), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["drawdown"], mode="lines",
        line=dict(color=PALETTE["down"], width=1.2),
        fill="tozeroy", fillcolor="rgba(246,70,93,0.12)"), row=2, col=1)
    fig.add_hline(y=thresholds["drawdown_warning"], line=dict(
        color=PALETTE["warning"], width=1, dash="dot"), row=2, col=1)
    fig.add_hline(y=thresholds["drawdown_critical"], line=dict(
        color=PALETTE["critical"], width=1, dash="dash"), row=2, col=1)
    _base_layout(fig, height=360)
    for ann in fig.layout.annotations:
        ann.font.update(size=11, color=PALETTE["muted"])
    return fig


def volatility_chart(df, thresholds) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["volatility"], mode="lines",
        line=dict(color=PALETTE["accent"], width=1.4),
        fill="tozeroy", fillcolor="rgba(57,208,216,0.08)"))
    fig.add_hline(y=thresholds["volatility_warning"], line=dict(
        color=PALETTE["warning"], width=1, dash="dot"))
    fig.add_hline(y=thresholds["volatility_critical"], line=dict(
        color=PALETTE["critical"], width=1, dash="dash"))
    return _base_layout(fig, title="ANNUALISED VOLATILITY %")


def volume_zscore_chart(df, thresholds) -> go.Figure:
    colors = [
        PALETTE["critical"] if abs(z) >= thresholds["volume_zscore_critical"]
        else PALETTE["warning"] if abs(z) >= thresholds["volume_zscore_warning"]
        else PALETTE["muted"]
        for z in df["volume_zscore"].fillna(0)
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=df["volume_zscore"], marker_color=colors))
    fig.add_hline(y=thresholds["volume_zscore_warning"], line=dict(
        color=PALETTE["warning"], width=1, dash="dot"))
    return _base_layout(fig, title="VOLUME ANOMALY (z-score vs baseline)")
