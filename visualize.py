import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

# Paths setup
SEG   = 'segment_summary.csv'
COH   = 'cohort_retention.csv'
CHURN = 'churn_risk.csv'
OUT   = './reports'
os.makedirs(OUT, exist_ok=True)

BLUE    = '#1155CC'
DARK    = '#1a1a1a'
MUTED   = '#6b7280'
LIGHT   = '#f8fafc'
GRID    = '#e5e7eb'

SEGMENT_COLORS = {
    'Champions':          '#1155CC',
    'Loyal Customers':    '#2563eb',
    'Potential Loyalists':'#3b82f6',
    'New Customers':      '#10b981',
    'At Risk':            '#f59e0b',
    'Cannot Lose Them':   '#ef4444',
    'Hibernating':        '#9ca3af',
    'Lost':               '#d1d5db',
}

def base_layout(title, subtitle=None):
    t = f"<b>{title}</b>"
    if subtitle:
        t += f"<br><span style='font-size:12px;color:{MUTED}'>{subtitle}</span>"
    return dict(
        title=dict(text=t, font=dict(size=18, color=DARK, family='Inter, Arial'),
                   x=0.04, y=0.97, xanchor='left'),
        plot_bgcolor=LIGHT, paper_bgcolor='white',
        font=dict(family='Inter, Arial', color=DARK),
        margin=dict(l=60, r=40, t=80, b=60)
    )

# 1. Revenue Concentration
seg = pd.read_csv(SEG).sort_values('total_revenue', ascending=True)
colors = [SEGMENT_COLORS.get(s, BLUE) for s in seg['segment']]
fig1 = go.Figure()
fig1.add_trace(go.Bar(
    y=seg['segment'], x=seg['customer_pct'],
    name='% of Customers', orientation='h',
    marker=dict(color='rgba(17,85,204,0.25)', line=dict(color=BLUE, width=1.5)),
    text=[f"{v:.1f}%" for v in seg['customer_pct']],
    textposition='outside', textfont=dict(size=11, color=MUTED),
))
fig1.add_trace(go.Bar(
    y=seg['segment'], x=seg['revenue_pct'],
    name='% of Revenue', orientation='h',
    marker=dict(color=colors, line=dict(color='rgba(0,0,0,0.1)', width=0.5)),
    text=[f"{v:.1f}%" for v in seg['revenue_pct']],
    textposition='outside', textfont=dict(size=11, color=DARK, family='Inter Bold'),
))
fig1.update_layout(
    **base_layout("Revenue Concentration by Customer Segment", "Champions represent 6.6% of customers but generate 33.4% of total revenue"),
    barmode='group', xaxis=dict(title='Percentage (%)', gridcolor=GRID, range=[0, 42], ticksuffix='%', zeroline=False),
    yaxis=dict(gridcolor='rgba(0,0,0,0)', tickfont=dict(size=12)),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)'),
    showlegend=True, height=460, width=900,
)
fig1.write_image(f"{OUT}/01_revenue_concentration.png", scale=2)
print("✅ Chart 1 saved")

# 2. Segment Bubble Map
seg2 = pd.read_csv(SEG)
fig2 = go.Figure()
for _, row in seg2.iterrows():
    fig2.add_trace(go.Scatter(
        x=[row['customer_pct']], y=[row['revenue_pct']], mode='markers+text',
        name=row['segment'], text=[row['segment']], textposition='top center',
        textfont=dict(size=10.5, color=DARK),
        marker=dict(size=max(row['avg_ltv'] / 30, 12), color=SEGMENT_COLORS.get(row['segment'], BLUE), opacity=0.85, line=dict(color='white', width=2)),
        hovertemplate=f"<b>{row['segment']}</b><br>Customers: {row['customer_pct']:.1f}%<br>Revenue: {row['revenue_pct']:.1f}%<br>Avg LTV: £{row['avg_ltv']:,.0f}<extra></extra>"
    ))
fig2.add_shape(type='line', x0=0, y0=0, x1=35, y1=35, line=dict(color=GRID, width=1.5, dash='dot'))
fig2.update_layout(
    **base_layout("Customer Segment Map: Revenue vs Customer Share", "Bubble size = Average Lifetime Value"),
    xaxis=dict(title='% of Total Customers', gridcolor=GRID, ticksuffix='%', zeroline=False, range=[0, 38]),
    yaxis=dict(title='% of Total Revenue', gridcolor=GRID, ticksuffix='%', zeroline=False, range=[0, 40]),
    showlegend=False, height=500, width=900,
)
fig2.write_image(f"{OUT}/02_segment_bubble.png", scale=2)
print("✅ Chart 2 saved")

# 3. Retention Heatmap
coh = pd.read_csv(COH)
coh['cohort_month'] = pd.to_datetime(coh['cohort_month'])
coh['cohort_label'] = coh['cohort_month'].dt.strftime('%b %Y')
pivot = coh.pivot_table(index='cohort_label', columns='month_number', values='retention_rate', aggfunc='first')
cohort_order = coh.drop_duplicates('cohort_label').sort_values('cohort_month')['cohort_label'].tolist()
pivot = pivot.reindex(cohort_order)
z = pivot.values.tolist()
text = [[f"{v:.0f}%" if not np.isnan(v) else "" for v in row] for row in z]
fig3 = go.Figure(go.Heatmap(
    z=z, x=[f"Month {i}" for i in pivot.columns], y=pivot.index.tolist(),
    text=text, texttemplate="%{text}", textfont=dict(size=10.5),
    colorscale=[[0.0, '#fef3c7'], [0.5, '#60a5fa'], [1.0, '#1e3a8a']], zmin=0, zmax=100,
    colorbar=dict(title=dict(text='Retention %'), ticksuffix='%', len=0.8),
))
fig3.update_layout(
    **base_layout("Monthly Cohort Retention Matrix", "Percentage of each signup cohort that returned in subsequent months"),
    xaxis=dict(side='top', tickfont=dict(size=11)), yaxis=dict(tickfont=dict(size=11), autorange='reversed'),
    showlegend=False, height=520, width=980,
)
fig3.write_image(f"{OUT}/03_cohort_retention_heatmap.png", scale=2)
print("✅ Chart 3 saved")

# 4. Churn Risk
churn = pd.read_csv(CHURN)
risk_counts = churn['churn_risk_flag'].value_counts().reset_index()
risk_counts.columns = ['risk', 'count']
risk_revenue = churn.groupby('churn_risk_flag')['lifetime_value'].sum().reset_index()
risk_revenue.columns = ['risk', 'revenue']
risk_order  = ['High Value At Risk', 'Mid Value At Risk', 'Active']
risk_colors = {'High Value At Risk': '#ef4444', 'Mid Value At Risk':  '#f59e0b', 'Active': '#10b981'}

fig4 = make_subplots(rows=1, cols=2, subplot_titles=('Customer Count by Risk Category', 'Revenue at Risk'), horizontal_spacing=0.12)
for risk in risk_order:
    row_c = risk_counts[risk_counts['risk'] == risk]
    row_r = risk_revenue[risk_revenue['risk'] == risk]
    c = risk_colors[risk]
    fig4.add_trace(go.Bar(x=[risk.replace(' At Risk','<br>At Risk')], y=row_c['count'].values if len(row_c) else [0], name=risk, marker_color=c, showlegend=True), row=1, col=1)
    fig4.add_trace(go.Bar(x=[risk.replace(' At Risk','<br>At Risk')], y=row_r['revenue'].values if len(row_r) else [0], name=risk, marker_color=c, showlegend=False), row=1, col=2)
fig4.update_layout(**base_layout("Churn Risk Analysis"), barmode='group', showlegend=True, height=440, width=900)
fig4.write_image(f"{OUT}/04_churn_risk.png", scale=2)
print("✅ Chart 4 saved")

# 5. Table Performance Scorecard
seg5 = pd.read_csv(SEG).sort_values('total_revenue', ascending=False)
header_vals = ['Segment', 'Customers', 'Cust %', 'Revenue (£)', 'Rev %', 'Avg LTV (£)', 'Avg Recency']
cell_vals = [seg5['segment'].tolist(), [f"{v:,}" for v in seg5['customer_count']], [f"{v:.1f}%" for v in seg5['customer_pct']], [f"£{v:,.0f}" for v in seg5['total_revenue']], [f"{v:.1f}%" for v in seg5['revenue_pct']], [f"£{v:,.0f}" for v in seg5['avg_ltv']], [f"{v:.0f} days" for v in seg5['avg_recency']]]
fig5 = go.Figure(go.Table(
    header=dict(values=[f"<b>{h}</b>" for h in header_vals], fill_color=DARK, font=dict(color='white', size=12)),
    cells=dict(values=cell_vals, fill_color=[[SEGMENT_COLORS.get(s, BLUE) for s in seg5['segment']]] + [['#f8fafc']]*6, font=dict(color=[['white']*len(seg5)] + [[DARK]*len(seg5)]*6))
))
fig5.update_layout(**base_layout("Segment Performance Scorecard"), showlegend=False, height=420, width=980)
fig5.write_image(f"{OUT}/05_segment_scorecard.png", scale=2)
print("✅ Chart 5 saved")

# 6. Combined Executive Dashboard
seg6 = pd.read_csv(SEG).sort_values('total_revenue', ascending=False)
fig6 = make_subplots(rows=2, cols=2, subplot_titles=('Revenue by Segment', 'Customer Count', 'Avg LTV vs Recency', 'Churn Risk Breakdown'), vertical_spacing=0.18, horizontal_spacing=0.12)
fig6.add_trace(go.Bar(x=seg6['segment'], y=seg6['total_revenue'], marker_color=[SEGMENT_COLORS.get(s, BLUE) for s in seg6['segment']], showlegend=False), row=1, col=1)
fig6.add_trace(go.Bar(x=seg6['segment'], y=seg6['customer_count'], marker_color=[SEGMENT_COLORS.get(s, BLUE) for s in seg6['segment']], showlegend=False), row=1, col=2)
fig6.add_trace(go.Scatter(x=seg6['avg_recency'], y=seg6['avg_ltv'], mode='markers+text', text=seg6['segment'], marker=dict(size=15, color=[SEGMENT_COLORS.get(s, BLUE) for s in seg6['segment']]), showlegend=False), row=2, col=1)
fig6.add_trace(go.Pie(labels=risk_revenue['risk'], values=risk_revenue['revenue'], hole=0.5, showlegend=False), row=2, col=2)
fig6.update_layout(**base_layout("Customer Intelligence Executive Dashboard"), showlegend=False, height=680, width=1100)
fig6.write_image(f"{OUT}/06_executive_dashboard.png", scale=2)
print("✅ Chart 6 saved")

print("\n🎉 Success! All 6 charts have compiled perfectly inside your local ./reports/ folder!")
