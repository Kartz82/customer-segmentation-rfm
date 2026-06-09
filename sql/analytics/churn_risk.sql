cat > sql/analytics/churn_risk.sql << 'EOF'
SELECT
    customer_id,
    MAX(invoice_date)                          AS last_order_date,
    CURRENT_DATE - MAX(invoice_date)::date     AS days_since_purchase,
    SUM(quantity * unit_price)                 AS lifetime_value,
    COUNT(DISTINCT invoice_number)             AS total_orders,
    CASE
        WHEN SUM(quantity * unit_price) > 5000
         AND (CURRENT_DATE - MAX(invoice_date)::date) > 90
        THEN 'High Value At Risk'
        WHEN SUM(quantity * unit_price) BETWEEN 1000 AND 5000
         AND (CURRENT_DATE - MAX(invoice_date)::date) > 120
        THEN 'Mid Value At Risk'
        ELSE 'Active'
    END AS churn_risk_flag
FROM fact_sales
WHERE customer_id IS NOT NULL
  AND quantity > 0
GROUP BY customer_id
ORDER BY lifetime_value DESC;
EOF