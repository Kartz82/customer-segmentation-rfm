import pandas as pd
import numpy as np

# ── LOAD ─────────────────────────────────────────────────────
print("Loading data... (this takes ~30 seconds for 1M rows)")
sheets = pd.read_excel('data/raw/online_retail_II.xlsx', sheet_name=None)
df = pd.concat(sheets.values(), ignore_index=True)
print(f"Raw rows: {len(df):,}")

# ── NORMALIZE COLUMN NAMES FIRST ─────────────────────────────
df.columns = (df.columns
              .str.strip()
              .str.lower()
              .str.replace(' ', '_'))

# Columns are now: invoice, stockcode, description,
# quantity, invoicedate, price, customer_id, country

# ── CLEAN ────────────────────────────────────────────────────
df = df[df['customer_id'].notna()]
df = df[df['quantity'] > 0]
df = df[df['price'] > 0]
df['invoicedate'] = pd.to_datetime(df['invoicedate'])
df['revenue'] = df['quantity'] * df['price']

# Remove returns (invoices starting with C)
df = df[~df['invoice'].astype(str).str.startswith('C')]

print(f"Clean rows: {len(df):,}")
print(f"Unique customers: {df['customer_id'].nunique():,}")

# ── RFM CALCULATION ──────────────────────────────────────────
snapshot_date = df['invoicedate'].max() + pd.Timedelta(days=1)

rfm = df.groupby('customer_id').agg(
    recency   = ('invoicedate', lambda x: (snapshot_date - x.max()).days),
    frequency = ('invoice',     'nunique'),
    monetary  = ('revenue',     'sum')
).reset_index()

# ── SCORE 1-5 ────────────────────────────────────────────────
rfm['r_score'] = pd.qcut(rfm['recency'],
                          q=5, labels=[5,4,3,2,1])
rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'),
                          q=5, labels=[1,2,3,4,5])
rfm['m_score'] = pd.qcut(rfm['monetary'],
                          q=5, labels=[1,2,3,4,5])

rfm['r_score'] = rfm['r_score'].astype(int)
rfm['f_score'] = rfm['f_score'].astype(int)
rfm['m_score'] = rfm['m_score'].astype(int)

# ── ASSIGN SEGMENTS ──────────────────────────────────────────
def assign_segment(row):
    r, f, m = row['r_score'], row['f_score'], row['m_score']
    if r >= 4 and f >= 4 and m >= 4:
        return 'Champions'
    elif r >= 3 and f >= 3 and m >= 3:
        return 'Loyal Customers'
    elif r >= 4 and f <= 2:
        return 'New Customers'
    elif r >= 3 and f >= 2 and m >= 3:
        return 'Potential Loyalists'
    elif r == 2 and f >= 3:
        return 'At Risk'
    elif r <= 2 and f >= 3 and m >= 3:
        return 'Cannot Lose Them'
    elif r <= 2 and f <= 2:
        return 'Hibernating'
    else:
        return 'Lost'

rfm['segment'] = rfm.apply(assign_segment, axis=1)

# ── REVENUE CONCENTRATION ────────────────────────────────────
total_revenue = rfm['monetary'].sum()
segment_summary = rfm.groupby('segment').agg(
    customer_count = ('customer_id', 'count'),
    total_revenue  = ('monetary',    'sum'),
    avg_ltv        = ('monetary',    'mean'),
    avg_recency    = ('recency',     'mean'),
    avg_frequency  = ('frequency',   'mean')
).reset_index()

segment_summary['revenue_pct'] = (
    segment_summary['total_revenue'] / total_revenue * 100
).round(2)

segment_summary['customer_pct'] = (
    segment_summary['customer_count'] / len(rfm) * 100
).round(2)

segment_summary = segment_summary.sort_values(
    'total_revenue', ascending=False)

# ── CHURN RISK FLAG ──────────────────────────────────────────
rfm['churn_risk'] = 'Active'
rfm.loc[
    (rfm['monetary'] > 5000) & (rfm['recency'] > 90),
    'churn_risk'
] = 'High Value At Risk'
rfm.loc[
    (rfm['monetary'].between(1000, 5000)) & (rfm['recency'] > 120),
    'churn_risk'
] = 'Mid Value At Risk'

at_risk = rfm[rfm['churn_risk'] == 'High Value At Risk']

# ── SAVE OUTPUTS ─────────────────────────────────────────────
rfm.to_csv('data/processed/rfm_segments.csv', index=False)
segment_summary.to_csv('data/processed/segment_summary.csv', index=False)
at_risk.to_csv('data/processed/churn_risk_high_value.csv', index=False)

# ── PRINT RESULTS ────────────────────────────────────────────
print("\n── SEGMENT SUMMARY ─────────────────────────────────")
print(segment_summary[[
    'segment','customer_count','customer_pct',
    'total_revenue','revenue_pct','avg_ltv'
]].to_string(index=False))

print(f"\n── CHURN RISK ──────────────────────────────────────")
print(f"High-value customers at risk:  {len(at_risk):,}")
print(f"Revenue at risk:               £{at_risk['monetary'].sum():,.2f}")

print("\n✅ Saved to data/processed/")