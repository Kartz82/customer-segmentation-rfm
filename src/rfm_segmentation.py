from pathlib import Path

import numpy as np
import pandas as pd


RAW_DATA_PATH = Path("data/raw/online_retail_II.xlsx")
PROCESSED_DIR = Path("data/processed")

REQUIRED_COLUMNS = {
    "invoice",
    "stockcode",
    "description",
    "quantity",
    "invoicedate",
    "price",
    "customer_id",
    "country",
}


def load_raw_transactions(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {path}. "
            "Download the Online Retail II Excel file and place it there."
        )

    print("Loading raw Online Retail II workbook...")
    sheets = pd.read_excel(path, sheet_name=None)
    df = pd.concat(sheets.values(), ignore_index=True)

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required column(s): {missing}")

    print(f"Raw rows: {len(df):,}")
    return df


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned[cleaned["customer_id"].notna()]
    cleaned = cleaned[cleaned["quantity"] > 0]
    cleaned = cleaned[cleaned["price"] > 0]
    cleaned = cleaned[~cleaned["invoice"].astype(str).str.startswith("C")]

    cleaned["invoicedate"] = pd.to_datetime(cleaned["invoicedate"])
    cleaned["invoice_month"] = cleaned["invoicedate"].dt.to_period("M").dt.to_timestamp()
    cleaned["revenue"] = cleaned["quantity"] * cleaned["price"]

    print(f"Clean rows: {len(cleaned):,}")
    print(f"Unique customers: {cleaned['customer_id'].nunique():,}")
    return cleaned


def quintile_score(series: pd.Series, labels: list[int]) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, q=5, labels=labels).astype(int)


def assign_segment(row: pd.Series) -> str:
    r, f, m = row["r_score"], row["f_score"], row["m_score"]

    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 3 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 2:
        return "New Customers"
    if r >= 3 and f >= 2 and m >= 3:
        return "Potential Loyalists"

    # Check this before the broader At Risk rule so inactive, historically
    # valuable repeat customers are not swallowed by a generic risk bucket.
    if r <= 2 and f >= 3 and m >= 3:
        return "Cannot Lose Them"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Lost"


def build_rfm(transactions: pd.DataFrame) -> pd.DataFrame:
    snapshot_date = transactions["invoicedate"].max() + pd.Timedelta(days=1)

    rfm = (
        transactions.groupby("customer_id")
        .agg(
            recency=("invoicedate", lambda x: (snapshot_date - x.max()).days),
            frequency=("invoice", "nunique"),
            monetary=("revenue", "sum"),
        )
        .reset_index()
    )

    # Recency is inverse-scored: fewer days since purchase receives a higher score.
    rfm["r_score"] = quintile_score(rfm["recency"], [5, 4, 3, 2, 1])
    rfm["f_score"] = quintile_score(rfm["frequency"], [1, 2, 3, 4, 5])
    rfm["m_score"] = quintile_score(rfm["monetary"], [1, 2, 3, 4, 5])
    rfm["segment"] = rfm.apply(assign_segment, axis=1)

    rfm["churn_risk"] = "Active"
    rfm.loc[
        (rfm["monetary"] > 5000) & (rfm["recency"] > 90),
        "churn_risk",
    ] = "High Value At Risk"
    rfm.loc[
        (rfm["monetary"].between(1000, 5000)) & (rfm["recency"] > 120),
        "churn_risk",
    ] = "Mid Value At Risk"

    return rfm


def build_segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    total_revenue = rfm["monetary"].sum()

    segment_summary = (
        rfm.groupby("segment")
        .agg(
            customer_count=("customer_id", "count"),
            total_revenue=("monetary", "sum"),
            avg_ltv=("monetary", "mean"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
        )
        .reset_index()
    )

    segment_summary["revenue_pct"] = (
        segment_summary["total_revenue"] / total_revenue * 100
    ).round(2)
    segment_summary["customer_pct"] = (
        segment_summary["customer_count"] / len(rfm) * 100
    ).round(2)

    return segment_summary.sort_values("total_revenue", ascending=False)


def build_churn_risk(transactions: pd.DataFrame, rfm: pd.DataFrame) -> pd.DataFrame:
    last_orders = (
        transactions.groupby("customer_id")
        .agg(last_order_date=("invoicedate", "max"))
        .reset_index()
    )

    churn = rfm.merge(last_orders, on="customer_id", how="left")
    churn = churn.rename(
        columns={
            "recency": "days_since_purchase",
            "monetary": "lifetime_value",
            "frequency": "total_orders",
            "churn_risk": "churn_risk_flag",
        }
    )

    columns = [
        "customer_id",
        "last_order_date",
        "days_since_purchase",
        "lifetime_value",
        "total_orders",
        "churn_risk_flag",
    ]
    return churn[columns].sort_values("lifetime_value", ascending=False)


def build_cohort_retention(transactions: pd.DataFrame) -> pd.DataFrame:
    customer_cohorts = (
        transactions.groupby("customer_id")["invoice_month"]
        .min()
        .reset_index()
        .rename(columns={"invoice_month": "cohort_month"})
    )

    activity = transactions[["customer_id", "invoice_month"]].drop_duplicates()
    activity = activity.merge(customer_cohorts, on="customer_id", how="left")

    activity["month_number"] = (
        (activity["invoice_month"].dt.year - activity["cohort_month"].dt.year) * 12
        + (activity["invoice_month"].dt.month - activity["cohort_month"].dt.month)
    ).astype(int)

    cohort_sizes = (
        customer_cohorts.groupby("cohort_month")["customer_id"]
        .nunique()
        .reset_index(name="cohort_size")
    )

    retention = (
        activity.groupby(["cohort_month", "month_number"])["customer_id"]
        .nunique()
        .reset_index(name="retained")
        .merge(cohort_sizes, on="cohort_month", how="left")
    )
    retention["retention_rate"] = (
        retention["retained"] * 100.0 / retention["cohort_size"]
    ).round(1)

    return retention[
        ["cohort_month", "cohort_size", "month_number", "retained", "retention_rate"]
    ].sort_values(["cohort_month", "month_number"])


def validate_outputs(
    rfm: pd.DataFrame,
    segment_summary: pd.DataFrame,
    churn_risk: pd.DataFrame,
    cohort_retention: pd.DataFrame,
) -> None:
    outputs = {
        "rfm_segments": rfm,
        "segment_summary": segment_summary,
        "churn_risk": churn_risk,
        "cohort_retention": cohort_retention,
    }

    for name, df in outputs.items():
        if df.empty:
            raise ValueError(f"{name} output is empty")

    if not np.isclose(segment_summary["customer_pct"].sum(), 100, atol=0.1):
        raise ValueError("Segment customer percentages do not sum to approximately 100")
    if not np.isclose(segment_summary["revenue_pct"].sum(), 100, atol=0.1):
        raise ValueError("Segment revenue percentages do not sum to approximately 100")


def save_outputs(
    rfm: pd.DataFrame,
    segment_summary: pd.DataFrame,
    churn_risk: pd.DataFrame,
    cohort_retention: pd.DataFrame,
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    rfm.to_csv(PROCESSED_DIR / "rfm_segments.csv", index=False)
    segment_summary.to_csv(PROCESSED_DIR / "segment_summary.csv", index=False)
    churn_risk.to_csv(PROCESSED_DIR / "churn_risk.csv", index=False)
    cohort_retention.to_csv(PROCESSED_DIR / "cohort_retention.csv", index=False)

    high_value_at_risk = rfm[rfm["churn_risk"] == "High Value At Risk"]
    high_value_at_risk.to_csv(
        PROCESSED_DIR / "churn_risk_high_value.csv",
        index=False,
    )


def print_summary(segment_summary: pd.DataFrame, churn_risk: pd.DataFrame) -> None:
    print("\nSegment summary")
    print(
        segment_summary[
            [
                "segment",
                "customer_count",
                "customer_pct",
                "total_revenue",
                "revenue_pct",
                "avg_ltv",
            ]
        ].to_string(index=False)
    )

    high_value = churn_risk[churn_risk["churn_risk_flag"] == "High Value At Risk"]
    print("\nChurn risk")
    print(f"High-value customers at risk: {len(high_value):,}")
    print(f"Revenue at risk: GBP {high_value['lifetime_value'].sum():,.2f}")
    print(f"\nSaved processed outputs to {PROCESSED_DIR}/")


def main() -> None:
    raw = load_raw_transactions()
    transactions = clean_transactions(raw)
    rfm = build_rfm(transactions)
    segment_summary = build_segment_summary(rfm)
    churn_risk = build_churn_risk(transactions, rfm)
    cohort_retention = build_cohort_retention(transactions)

    validate_outputs(rfm, segment_summary, churn_risk, cohort_retention)
    save_outputs(rfm, segment_summary, churn_risk, cohort_retention)
    print_summary(segment_summary, churn_risk)


if __name__ == "__main__":
    main()
