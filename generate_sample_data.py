import pandas as pd
import numpy as np

np.random.seed(42)

# RFM segments sample
segments = ['Champions','Loyal Customers','Potential Loyalists',
            'New Customers','At Risk','Cannot Lose Them','Hibernating','Lost']
seg_data = {
    'segment': segments,
    'customer_count': [312, 687, 534, 423, 398, 187, 892, 1441],
    'total_revenue':  [487231, 398443, 187234, 43211, 89432, 134221, 67234, 23443],
    'avg_ltv':        [1562, 580, 350, 102, 225, 718, 75, 16],
    'avg_recency':    [12, 28, 45, 8, 98, 145, 210, 312],
    'avg_frequency':  [18, 9, 5, 2, 7, 11, 3, 1],
    'customer_pct':   [6.6, 14.5, 11.3, 8.9, 8.4, 3.9, 18.8, 30.4],
    'revenue_pct':    [33.4, 27.3, 12.8, 3.0, 6.1, 9.2, 4.6, 1.6],
}
pd.DataFrame(seg_data).to_csv('segment_summary.csv', index=False)

# Cohort retention sample
rows = []
cohorts = pd.date_range('2009-12-01', periods=13, freq='MS')
sizes = [854,372,318,441,380,295,412,387,356,402,478,521,312]
for i, (cohort, size) in enumerate(zip(cohorts, sizes)):
    for month in range(min(13, 13-i)):
        base = 100 if month == 0 else max(5, 65 - month*5 + np.random.randint(-3,4))
        rows.append({
            'cohort_month': cohort,
            'cohort_size': size,
            'month_number': month,
            'retained': int(size * base / 100),
            'retention_rate': base
        })
pd.DataFrame(rows).to_csv('cohort_retention.csv', index=False)

# Churn risk sample
n = 4970
churn_data = pd.DataFrame({
    'customer_id': range(10000, 10000+n),
    'lifetime_value': np.random.exponential(800, n),
    'days_since_purchase': np.random.randint(1, 500, n),
    'total_orders': np.random.randint(1, 50, n),
})
churn_data['churn_risk_flag'] = 'Active'
churn_data.loc[(churn_data['lifetime_value']>5000)&(churn_data['days_since_purchase']>90),'churn_risk_flag'] = 'High Value At Risk'
churn_data.loc[(churn_data['lifetime_value'].between(1000,5000))&(churn_data['days_since_purchase']>120),'churn_risk_flag'] = 'Mid Value At Risk'
churn_data.to_csv('churn_risk.csv', index=False)

print("🎉 Data successfully generated inside your project root folder!")
