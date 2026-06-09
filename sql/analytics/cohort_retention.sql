WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', MIN(invoice_date)) AS cohort_month
    FROM fact_sales
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
activity AS (
    SELECT
        s.customer_id,
        c.cohort_month,
        (EXTRACT(YEAR FROM AGE(
            DATE_TRUNC('month', s.invoice_date),
            c.cohort_month
        )) * 12 +
        EXTRACT(MONTH FROM AGE(
            DATE_TRUNC('month', s.invoice_date),
            c.cohort_month
        )))::int AS month_number
    FROM fact_sales s
    JOIN cohorts c USING (customer_id)
),
cohort_sizes AS (
    SELECT cohort_month,
           COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    a.cohort_month,
    cs.cohort_size,
    a.month_number,
    COUNT(DISTINCT a.customer_id) AS retained,
    ROUND(
        COUNT(DISTINCT a.customer_id) * 100.0 / cs.cohort_size, 1
    ) AS retention_rate
FROM activity a
JOIN cohort_sizes cs USING (cohort_month)
GROUP BY a.cohort_month, cs.cohort_size, a.month_number
ORDER BY a.cohort_month, a.month_number;
