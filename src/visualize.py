import argparse
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


SEG = "segment_summary.csv"
COH = "cohort_retention.csv"
CHURN = "churn_risk.csv"
OUT = "./reports"

BACKGROUND = "#050A14"
PANEL = "#0B1220"
GRID = "#233044"
TEXT = "#E5E7EB"
MUTED = "#9CA3AF"
ORANGE = "#F59E0B"
AMBER = "#FBBF24"
TEAL = "#14B8A6"
GREEN = "#10B981"
RED = "#F43F5E"
BLUE = "#3B82F6"
INDIGO = "#6366F1"
GRAY = "#6B7280"

SEGMENT_COLORS = {
    "Champions": BLUE,
    "Loyal Customers": INDIGO,
    "Potential Loyalists": TEAL,
    "New Customers": GREEN,
    "At Risk": ORANGE,
    "Cannot Lose Them": RED,
    "Hibernating": GRAY,
    "Lost": "#4B5563",
}


def ensure_output_dir():
    os.makedirs(OUT, exist_ok=True)


def configure_browser_export():
    brave_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    if os.path.exists(brave_path):
        os.environ.setdefault("BROWSER_PATH", brave_path)


def dark_layout(title, subtitle=None, margin=None):
    text = f"<b>{title}</b>"
    if subtitle:
        text += f"<br><span style='font-size:12px;color:{MUTED}'>{subtitle}</span>"

    return dict(
        title=dict(
            text=text,
            font=dict(size=19, color=TEXT, family="Inter, Arial"),
            x=0.04,
            y=0.965,
            xanchor="left",
        ),
        plot_bgcolor=PANEL,
        paper_bgcolor=BACKGROUND,
        font=dict(family="Inter, Arial", color=TEXT),
        margin=margin or dict(l=70, r=42, t=86, b=64),
    )


def dark_axis(title=None, ticksuffix=None, range=None):
    return dict(
        title=dict(text=title, font=dict(color=MUTED, size=12)) if title else None,
        gridcolor=GRID,
        griddash="dot",
        zeroline=False,
        linecolor=GRID,
        tickfont=dict(color=MUTED, size=11),
        ticksuffix=ticksuffix,
        range=range,
    )


def create_revenue_concentration_v2():
    seg = pd.read_csv(SEG).sort_values("total_revenue", ascending=True)
    colors = [SEGMENT_COLORS.get(s, BLUE) for s in seg["segment"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=seg["segment"],
            x=seg["customer_pct"],
            name="% of Customers",
            orientation="h",
            marker=dict(
                color="rgba(156, 163, 175, 0.28)",
                line=dict(color="rgba(229, 231, 235, 0.34)", width=1),
            ),
            text=[f"{v:.1f}%" for v in seg["customer_pct"]],
            textposition="outside",
            textfont=dict(size=11, color=MUTED),
            cliponaxis=False,
        )
    )
    fig.add_trace(
        go.Bar(
            y=seg["segment"],
            x=seg["revenue_pct"],
            name="% of Revenue",
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="rgba(255, 255, 255, 0.32)", width=1),
            ),
            text=[f"{v:.1f}%" for v in seg["revenue_pct"]],
            textposition="outside",
            textfont=dict(size=12, color=TEXT),
            cliponaxis=False,
        )
    )

    fig.update_layout(
        **dark_layout(
            "Revenue Concentration by Customer Segment",
            "Champions represent 6.6% of customers but generate 33.4% of total revenue",
        ),
        barmode="group",
        bargap=0.26,
        bargroupgap=0.08,
        xaxis=dark_axis("Percentage", "%", [0, 42]),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(size=12, color=TEXT),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11),
        ),
        height=460,
        width=900,
    )
    fig.write_image(f"{OUT}/01_revenue_concentration.png", scale=2)


def create_segment_bubble_v2():
    seg = pd.read_csv(SEG)
    max_x = max(36, float(seg["customer_pct"].max()) + 4)
    max_y = max(40, float(seg["revenue_pct"].max()) + 8)

    fig = go.Figure()
    for _, row in seg.iterrows():
        segment = row["segment"]
        fig.add_trace(
            go.Scatter(
                x=[row["customer_pct"]],
                y=[row["revenue_pct"]],
                mode="markers+text",
                name=segment,
                text=[segment],
                textposition="top center",
                textfont=dict(size=11, color=TEXT),
                marker=dict(
                    size=max(row["avg_ltv"] / 30, 14),
                    color=SEGMENT_COLORS.get(segment, BLUE),
                    opacity=0.9,
                    line=dict(color="rgba(255,255,255,0.62)", width=1.6),
                ),
                hovertemplate=(
                    f"<b>{segment}</b><br>"
                    f"Customers: {row['customer_pct']:.1f}%<br>"
                    f"Revenue: {row['revenue_pct']:.1f}%<br>"
                    f"Avg LTV: £{row['avg_ltv']:,.0f}<extra></extra>"
                ),
            )
        )

    diagonal_end = min(max_x, max_y)
    fig.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=diagonal_end,
        y1=diagonal_end,
        line=dict(color="rgba(156, 163, 175, 0.45)", width=1.4, dash="dot"),
    )
    fig.update_layout(
        **dark_layout(
            "Customer Segment Map: Revenue vs Customer Share",
            "Bubble size = Average Lifetime Value",
        ),
        xaxis=dark_axis("% of Total Customers", "%", [0, max_x]),
        yaxis=dark_axis("% of Total Revenue", "%", [0, max_y]),
        showlegend=False,
        height=500,
        width=900,
    )
    fig.write_image(f"{OUT}/02_segment_bubble.png", scale=2)


def create_cohort_retention_heatmap_v2():
    coh = pd.read_csv(COH)
    coh["cohort_month"] = pd.to_datetime(coh["cohort_month"])
    coh["cohort_label"] = coh["cohort_month"].dt.strftime("%b %Y")
    pivot = coh.pivot_table(
        index="cohort_label",
        columns="month_number",
        values="retention_rate",
        aggfunc="first",
    )
    cohort_order = (
        coh.drop_duplicates("cohort_label")
        .sort_values("cohort_month")["cohort_label"]
        .tolist()
    )
    pivot = pivot.reindex(cohort_order)
    z = pivot.values.tolist()
    text = [[f"{v:.0f}%" if not np.isnan(v) else "" for v in row] for row in z]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[f"Month {i}" for i in pivot.columns],
            y=pivot.index.tolist(),
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=10.5, color=TEXT),
            colorscale=[
                [0.0, "#172033"],
                [0.18, "#1E3A5F"],
                [0.42, "#0F766E"],
                [0.68, TEAL],
                [1.0, AMBER],
            ],
            zmin=0,
            zmax=100,
            xgap=2,
            ygap=2,
            hovertemplate="Cohort: %{y}<br>%{x}: %{z:.0f}%<extra></extra>",
            colorbar=dict(
                title=dict(text="Retention %", font=dict(color=MUTED)),
                ticksuffix="%",
                len=0.78,
                tickfont=dict(color=MUTED),
                bgcolor=BACKGROUND,
                outlinecolor=GRID,
            ),
        )
    )
    fig.update_layout(
        **dark_layout(
            "Monthly Cohort Retention Matrix",
            "Percentage of each signup cohort that returned in subsequent months",
            margin=dict(l=86, r=76, t=92, b=42),
        ),
        xaxis=dict(
            side="top",
            tickfont=dict(size=11, color=MUTED),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=11, color=MUTED),
            autorange="reversed",
            showgrid=False,
            zeroline=False,
        ),
        showlegend=False,
        height=520,
        width=980,
    )
    fig.write_image(f"{OUT}/03_cohort_retention_heatmap.png", scale=2)


def create_churn_risk_v2():
    churn = pd.read_csv(CHURN)
    risk_counts = churn["churn_risk_flag"].value_counts().reset_index()
    risk_counts.columns = ["risk", "count"]
    risk_revenue = churn.groupby("churn_risk_flag")["lifetime_value"].sum().reset_index()
    risk_revenue.columns = ["risk", "revenue"]

    risk_order = ["High Value At Risk", "Mid Value At Risk", "Active"]
    risk_colors = {
        "High Value At Risk": RED,
        "Mid Value At Risk": ORANGE,
        "Active": GREEN,
    }

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Customer Count by Risk Category", "Revenue at Risk"),
        horizontal_spacing=0.14,
    )
    for risk in risk_order:
        row_c = risk_counts[risk_counts["risk"] == risk]
        row_r = risk_revenue[risk_revenue["risk"] == risk]
        label = risk.replace(" At Risk", "<br>At Risk")
        color = risk_colors[risk]
        count = int(row_c["count"].iloc[0]) if len(row_c) else 0
        revenue = float(row_r["revenue"].iloc[0]) if len(row_r) else 0

        fig.add_trace(
            go.Bar(
                x=[label],
                y=[count],
                name=risk,
                marker=dict(color=color, line=dict(color="rgba(255,255,255,0.28)", width=1)),
                width=0.48,
                text=[f"{count:,}"],
                textposition="outside",
                textfont=dict(color=TEXT, size=11),
                cliponaxis=False,
                showlegend=True,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[revenue],
                name=risk,
                marker=dict(color=color, line=dict(color="rgba(255,255,255,0.28)", width=1)),
                width=0.48,
                text=[f"£{revenue:,.0f}"],
                textposition="outside",
                textfont=dict(color=TEXT, size=11),
                cliponaxis=False,
                showlegend=False,
            ),
            row=1,
            col=2,
        )

    fig.update_layout(
        **dark_layout(
            "Churn Risk Analysis",
            "Customer exposure by risk category",
            margin=dict(l=70, r=42, t=116, b=64),
        ),
        barmode="group",
        bargap=0.36,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11),
        ),
        height=440,
        width=900,
    )
    fig.update_annotations(font=dict(color=TEXT, size=13))
    fig.update_xaxes(tickfont=dict(color=MUTED, size=11), showgrid=False, linecolor=GRID)
    fig.update_yaxes(
        gridcolor=GRID,
        griddash="dot",
        zeroline=False,
        tickfont=dict(color=MUTED, size=11),
        title_font=dict(color=MUTED),
    )
    fig.update_yaxes(title_text="Customers", row=1, col=1)
    fig.update_yaxes(title_text="Lifetime Value", tickprefix="£", row=1, col=2)
    fig.write_image(f"{OUT}/04_churn_risk.png", scale=2)


def create_segment_scorecard_v2():
    seg = pd.read_csv(SEG).sort_values("total_revenue", ascending=False)
    header_vals = [
        "Segment",
        "Customers",
        "Cust %",
        "Revenue (£)",
        "Rev %",
        "Avg LTV (£)",
        "Avg Recency",
    ]
    cell_vals = [
        seg["segment"].tolist(),
        [f"{v:,}" for v in seg["customer_count"]],
        [f"{v:.1f}%" for v in seg["customer_pct"]],
        [f"£{v:,.0f}" for v in seg["total_revenue"]],
        [f"{v:.1f}%" for v in seg["revenue_pct"]],
        [f"£{v:,.0f}" for v in seg["avg_ltv"]],
        [f"{v:.0f} days" for v in seg["avg_recency"]],
    ]

    segment_fills = [SEGMENT_COLORS.get(s, BLUE) for s in seg["segment"]]
    numeric_fill = ["#111827" if i % 2 == 0 else PANEL for i in range(len(seg))]
    cell_fill = [segment_fills] + [numeric_fill] * 6
    cell_font = [["white"] * len(seg)] + [[TEXT] * len(seg)] * 6

    fig = go.Figure(
        go.Table(
            columnwidth=[2.35, 1.08, 0.9, 1.35, 0.82, 1.2, 1.24],
            header=dict(
                values=[f"<b>{h}</b>" for h in header_vals],
                fill_color="#111827",
                line_color=GRID,
                font=dict(color=TEXT, size=12),
                align=["left", "right", "right", "right", "right", "right", "right"],
                height=34,
            ),
            cells=dict(
                values=cell_vals,
                fill_color=cell_fill,
                line_color="#1F2937",
                font=dict(color=cell_font, size=11),
                align=["left", "right", "right", "right", "right", "right", "right"],
                height=33,
            ),
        )
    )
    fig.update_layout(
        **dark_layout(
            "Segment Performance Scorecard",
            "Revenue, customer mix, lifetime value, and recency by segment",
            margin=dict(l=34, r=34, t=86, b=28),
        ),
        showlegend=False,
        height=420,
        width=980,
    )
    fig.write_image(f"{OUT}/05_segment_scorecard.png", scale=2)


def create_all_reports():
    ensure_output_dir()
    configure_browser_export()
    create_revenue_concentration_v2()
    create_segment_bubble_v2()
    create_cohort_retention_heatmap_v2()
    create_churn_risk_v2()
    create_segment_scorecard_v2()


def main():
    parser = argparse.ArgumentParser(description="Generate customer segmentation report visuals.")
    parser.add_argument(
        "--dark",
        action="store_true",
        default=True,
        help="Generate dark-theme report PNGs. This is the default behavior.",
    )
    args = parser.parse_args()

    if args.dark:
        create_all_reports()
        print("Saved dark-theme report PNGs to ./reports")


if __name__ == "__main__":
    main()
