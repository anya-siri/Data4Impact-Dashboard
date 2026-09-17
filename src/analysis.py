"""
analysis.py

Reusable analysis and KPI-calculation helper functions shared by the
exploratory notebook and the Streamlit dashboard (app.py). Centralizing
these calculations here keeps the KPI logic consistent and avoids
duplicating formulas across the project.

These functions operate on the CLEANED dataframe (or a filtered subset of
it) and are safe to call on any subset produced by dashboard filters.
"""

from pathlib import Path
import sqlite3

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "nonprofit_impact_clean.csv"
DB_PATH = PROJECT_ROOT / "database" / "data4impact.db"


def load_clean_data() -> pd.DataFrame:
    """Load the cleaned dataset from CSV with correct dtypes."""
    df = pd.read_csv(CLEAN_DATA_PATH, parse_dates=["date"])
    return df


def load_data_from_db() -> pd.DataFrame:
    """Load the impact_metrics table directly from the SQLite database.
    Useful for demonstrating SQL-backed reads instead of CSV reads.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM impact_metrics", conn, parse_dates=["date"])
    finally:
        conn.close()
    return df


def calculate_kpis(df: pd.DataFrame) -> dict:
    """Calculate top-line KPI values for the given (possibly filtered)
    dataframe. All divisions guard against division-by-zero.
    """
    total_beneficiaries = int(df["beneficiaries_served"].sum())
    total_funding = float(df["funding_received"].sum())
    total_expenses = float(df["program_expenses"].sum())
    total_target = df["target_beneficiaries"].sum()

    avg_cost_per_beneficiary = (
        total_expenses / total_beneficiaries if total_beneficiaries else 0.0
    )
    overall_target_achievement = (
        (total_beneficiaries / total_target) * 100 if total_target else 0.0
    )
    avg_outcome_success_rate = (
        float(df["outcome_success_rate"].mean()) if len(df) else 0.0
    )

    return {
        "total_beneficiaries": total_beneficiaries,
        "total_funding": total_funding,
        "total_expenses": total_expenses,
        "avg_cost_per_beneficiary": avg_cost_per_beneficiary,
        "overall_target_achievement": overall_target_achievement,
        "avg_outcome_success_rate": avg_outcome_success_rate,
    }


def beneficiaries_by_program(df: pd.DataFrame) -> pd.DataFrame:
    """Total beneficiaries served, grouped by program, sorted descending."""
    return (
        df.groupby("program_name", as_index=False)["beneficiaries_served"]
        .sum()
        .sort_values("beneficiaries_served", ascending=False)
    )


def funding_vs_expenses_by_program(df: pd.DataFrame) -> pd.DataFrame:
    """Total funding received vs. program expenses, grouped by program."""
    return (
        df.groupby("program_name", as_index=False)
        .agg(funding_received=("funding_received", "sum"), program_expenses=("program_expenses", "sum"))
        .sort_values("funding_received", ascending=False)
    )


def impact_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly beneficiaries-served trend across the filtered date range."""
    trend = (
        df.groupby(["year", "month"], as_index=False)["beneficiaries_served"]
        .sum()
        .sort_values(["year", "month"])
    )
    trend["period"] = pd.to_datetime(trend["year"].astype(str) + "-" + trend["month"].astype(str) + "-01")
    return trend


def success_rate_by_program(df: pd.DataFrame) -> pd.DataFrame:
    """Average outcome success rate by program."""
    return (
        df.groupby("program_name", as_index=False)["outcome_success_rate"]
        .mean()
        .round(2)
        .sort_values("outcome_success_rate", ascending=False)
    )


def geographic_impact(df: pd.DataFrame, level: str = "region") -> pd.DataFrame:
    """Beneficiaries served and funding received by region or state."""
    return (
        df.groupby(level, as_index=False)
        .agg(beneficiaries_served=("beneficiaries_served", "sum"), funding_received=("funding_received", "sum"))
        .sort_values("beneficiaries_served", ascending=False)
    )


def funding_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Share of total funding received, by program."""
    return (
        df.groupby("program_name", as_index=False)["funding_received"]
        .sum()
        .sort_values("funding_received", ascending=False)
    )


def target_vs_actual(df: pd.DataFrame) -> pd.DataFrame:
    """Target beneficiaries vs. actual beneficiaries served, by program."""
    return (
        df.groupby("program_name", as_index=False)
        .agg(
            target_beneficiaries=("target_beneficiaries", "sum"),
            beneficiaries_served=("beneficiaries_served", "sum"),
        )
        .sort_values("beneficiaries_served", ascending=False)
    )


def cost_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """Program-level view of spending vs. beneficiaries served, for a cost
    efficiency scatter plot.
    """
    return df.groupby("program_name", as_index=False).agg(
        program_expenses=("program_expenses", "sum"),
        beneficiaries_served=("beneficiaries_served", "sum"),
        avg_cost_per_beneficiary=("cost_per_beneficiary", "mean"),
    )


def generate_key_insights(df: pd.DataFrame) -> list:
    """Dynamically calculate a list of key business insights from the
    given (possibly filtered) dataframe. Returns an empty list if there is
    not enough data to generate meaningful insights.
    """
    insights = []
    if df.empty:
        return insights

    # Insight 1: program with the most beneficiaries served.
    by_program = beneficiaries_by_program(df)
    if not by_program.empty:
        top = by_program.iloc[0]
        insights.append(
            f"**{top['program_name']}** serves the most beneficiaries overall, "
            f"with {int(top['beneficiaries_served']):,} people served in the selected period."
        )

    # Insight 2: program with high funding but comparatively low target
    # achievement (funding in top half, achievement below 90%).
    program_summary = df.groupby("program_name", as_index=False).agg(
        funding_received=("funding_received", "sum"),
        beneficiaries_served=("beneficiaries_served", "sum"),
        target_beneficiaries=("target_beneficiaries", "sum"),
    )
    program_summary["achievement_rate"] = (
        program_summary["beneficiaries_served"] / program_summary["target_beneficiaries"].replace(0, pd.NA) * 100
    )
    if not program_summary.empty:
        funding_median = program_summary["funding_received"].median()
        underperformers = program_summary[
            (program_summary["funding_received"] >= funding_median)
            & (program_summary["achievement_rate"] < 90)
        ].sort_values("achievement_rate")
        if not underperformers.empty:
            row = underperformers.iloc[0]
            insights.append(
                f"**{row['program_name']}** receives above-median funding but has only reached "
                f"{row['achievement_rate']:.1f}% of its beneficiary target, suggesting a review of "
                f"program delivery or targets may be warranted."
            )

    # Insight 3: region with the strongest year-over-year growth in
    # beneficiaries served (only computed if multiple years are present).
    if df["year"].nunique() > 1:
        region_year = df.groupby(["region", "year"], as_index=False)["beneficiaries_served"].sum()
        pivot = region_year.pivot(index="region", columns="year", values="beneficiaries_served").fillna(0)
        first_year, last_year = pivot.columns.min(), pivot.columns.max()
        if first_year != last_year and (pivot[first_year] > 0).any():
            growth = ((pivot[last_year] - pivot[first_year]) / pivot[first_year].replace(0, pd.NA)) * 100
            growth = growth.dropna().sort_values(ascending=False)
            if not growth.empty and growth.iloc[0] > 0:
                insights.append(
                    f"The **{growth.index[0]}** region saw the strongest growth in beneficiaries served, "
                    f"up {growth.iloc[0]:.1f}% from {int(first_year)} to {int(last_year)}."
                )

    # Insight 4: program with the highest cost per beneficiary.
    cost_summary = df.groupby("program_name", as_index=False)["cost_per_beneficiary"].mean()
    if not cost_summary.empty:
        highest_cost = cost_summary.sort_values("cost_per_beneficiary", ascending=False).iloc[0]
        insights.append(
            f"**{highest_cost['program_name']}** has the highest average cost per beneficiary, "
            f"at ${highest_cost['cost_per_beneficiary']:,.2f} per person served."
        )

    # Insight 5: program that most consistently exceeds its beneficiary
    # targets (highest average target achievement rate).
    achievement_summary = df.groupby("program_name", as_index=False)["target_achievement_rate"].mean()
    if not achievement_summary.empty:
        best_achiever = achievement_summary.sort_values("target_achievement_rate", ascending=False).iloc[0]
        if best_achiever["target_achievement_rate"] > 100:
            insights.append(
                f"**{best_achiever['program_name']}** consistently exceeds its beneficiary targets, "
                f"averaging {best_achiever['target_achievement_rate']:.1f}% of target achieved."
            )

    # Insight 6: overall organization-wide year-over-year growth in
    # beneficiaries served (only computed if multiple years are present).
    if df["year"].nunique() > 1:
        yearly_totals = df.groupby("year")["beneficiaries_served"].sum().sort_index()
        first_year, last_year = yearly_totals.index.min(), yearly_totals.index.max()
        if yearly_totals.loc[first_year] > 0:
            overall_growth = (
                (yearly_totals.loc[last_year] - yearly_totals.loc[first_year])
                / yearly_totals.loc[first_year]
            ) * 100
            direction = "grew" if overall_growth >= 0 else "declined"
            insights.append(
                f"Organization-wide, total beneficiaries served {direction} by {abs(overall_growth):.1f}% "
                f"from {int(first_year)} ({int(yearly_totals.loc[first_year]):,}) to "
                f"{int(last_year)} ({int(yearly_totals.loc[last_year]):,})."
            )

    # Insight 7: program with the most efficient use of volunteer hours
    # (highest beneficiaries served per volunteer hour).
    volunteer_summary = df.groupby("program_name", as_index=False)["beneficiaries_per_volunteer_hour"].mean()
    if not volunteer_summary.empty:
        most_efficient = volunteer_summary.sort_values(
            "beneficiaries_per_volunteer_hour", ascending=False
        ).iloc[0]
        insights.append(
            f"**{most_efficient['program_name']}** makes the most efficient use of volunteer time, "
            f"serving {most_efficient['beneficiaries_per_volunteer_hour']:.2f} beneficiaries per volunteer hour."
        )

    return insights


if __name__ == "__main__":
    # Simple smoke test when run directly.
    data = load_clean_data()
    print("KPIs:", calculate_kpis(data))
    print("\nKey Insights:")
    for insight in generate_key_insights(data):
        print("-", insight)
