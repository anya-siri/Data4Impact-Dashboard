"""
data_cleaning.py

Cleans the raw synthetic nonprofit dataset and produces an analysis-ready
CSV file. This script demonstrates standard Data Analyst cleaning tasks:
duplicate removal, missing-value handling, text/category standardization,
date parsing, numeric validation, and derived-metric creation.

Run:
    python src/data_cleaning.py
Input:
    data/raw/nonprofit_impact_raw.csv
Output:
    data/processed/nonprofit_impact_clean.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "nonprofit_impact_raw.csv"
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "nonprofit_impact_clean.csv"

# Canonical values used to standardize inconsistent text entries. Mapping
# keys are lowercased/stripped versions of possible raw values.
PROGRAM_NAME_MAP = {
    "education support": "Education Support",
    "food assistance": "Food Assistance",
    "healthcare access": "Healthcare Access",
    "health care access": "Healthcare Access",
    "housing support": "Housing Support",
    "youth development": "Youth Development",
    "job training": "Job Training",
    "community outreach": "Community Outreach",
}

REGION_MAP = {
    "northeast": "Northeast",
    "north east": "Northeast",
    "midwest": "Midwest",
    "mid west": "Midwest",
    "south": "South",
    "west": "West",
}


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load the raw CSV file into a DataFrame."""
    df = pd.read_csv(path)
    print(f"Loaded raw data: {df.shape[0]:,} rows, {df.shape[1]} columns")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows.

    Duplicate rows can occur when the same monthly report is accidentally
    logged twice (e.g. re-submitted by a program coordinator). Since every
    column -- including record_id -- matches in a true duplicate, a simple
    full-row duplicate check is sufficient and safe here.
    """
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    print(f"Removed {removed} exact duplicate rows")
    return df


def standardize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize inconsistent capitalization/spacing in categorical text
    columns using canonical lookup maps.

    Raw data often has inconsistent manual entry (e.g. 'food assistance' vs
    'FOOD ASSISTANCE' vs 'Food  Assistance' with a double space). We
    normalize by lowercasing, collapsing whitespace, and stripping, then map
    to a single canonical display value so downstream grouping/filtering is
    accurate.
    """
    df = df.copy()

    def normalize_key(value):
        if pd.isna(value):
            return value
        return " ".join(str(value).strip().lower().split())

    df["program_name"] = df["program_name"].apply(normalize_key).map(PROGRAM_NAME_MAP).fillna(df["program_name"])
    df["region"] = df["region"].apply(normalize_key).map(REGION_MAP)

    # program_category and state are generated consistently upstream, but we
    # still strip whitespace defensively since real-world data often needs
    # this even for "clean" columns.
    df["program_category"] = df["program_category"].astype(str).str.strip()
    df["state"] = df["state"].astype(str).str.strip().str.upper()
    df["program_status"] = df["program_status"].astype(str).str.strip()

    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values with column-appropriate strategies.

    - region: a categorical field with no reliable numeric substitute, so
      rows missing region are dropped since region is required for the
      geographic-analysis portion of this project.
    - funding_received: imputed with the median funding for that program,
      since funding amounts vary meaningfully by program and a simple
      overall median would distort smaller/larger programs.
    - volunteer_hours: imputed with the overall median, since volunteer
      hours are a supplementary (not core financial) metric.
    - satisfaction_score: imputed with the overall median, since a missing
      survey score is best approximated by the typical score rather than
      dropped, to preserve sample size for KPI calculations.
    """
    df = df.copy()

    before = len(df)
    df = df.dropna(subset=["region"])
    print(f"Dropped {before - len(df)} rows missing 'region' (required for geographic analysis)")

    df["funding_received"] = df.groupby("program_name")["funding_received"].transform(
        lambda s: s.fillna(s.median())
    )

    df["volunteer_hours"] = df["volunteer_hours"].fillna(df["volunteer_hours"].median())
    df["satisfaction_score"] = df["satisfaction_score"].fillna(df["satisfaction_score"].median())

    remaining_na = df.isna().sum().sum()
    print(f"Remaining missing values after imputation: {remaining_na}")
    return df


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert columns to correct, analysis-ready data types."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    df["record_id"] = df["record_id"].astype(int)
    df["number_of_volunteers"] = df["number_of_volunteers"].astype(int)
    return df


def validate_numeric_values(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and correct implausible numeric values.

    Some fields have a known valid range (e.g. satisfaction_score is on a
    1-5 scale, outcome_success_rate is a percentage from 0-100). Negative
    counts/dollar amounts are also physically impossible. Rather than
    silently dropping these rows (which would lose otherwise-good data in
    other columns), we correct out-of-range values using sensible rules:
    negative values are converted to their absolute value (a common
    data-entry sign error), and out-of-scale values are clipped to the
    valid range.
    """
    df = df.copy()

    # Negative counts/dollar amounts are impossible; treat as sign-entry
    # errors and take the absolute value.
    for col in ["beneficiaries_served", "target_beneficiaries", "funding_received", "program_expenses"]:
        negative_count = (df[col] < 0).sum()
        if negative_count:
            print(f"Corrected {negative_count} negative value(s) in '{col}' (converted to absolute value)")
        df[col] = df[col].abs()

    # satisfaction_score must be on a 1-5 scale.
    out_of_range = (~df["satisfaction_score"].between(1, 5)).sum()
    if out_of_range:
        print(f"Clipped {out_of_range} out-of-range value(s) in 'satisfaction_score' to the 1-5 scale")
    df["satisfaction_score"] = df["satisfaction_score"].clip(lower=1, upper=5)

    # outcome_success_rate must be a percentage between 0 and 100.
    out_of_range = (~df["outcome_success_rate"].between(0, 100)).sum()
    if out_of_range:
        print(f"Clipped {out_of_range} out-of-range value(s) in 'outcome_success_rate' to 0-100%")
    df["outcome_success_rate"] = df["outcome_success_rate"].clip(lower=0, upper=100)

    return df


def create_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived KPI-ready metrics used throughout the SQL analysis
    and dashboard.

    All divisions guard against division-by-zero by replacing a zero
    denominator with NaN before dividing, then filling the resulting NaN
    with 0 -- this avoids inf/-inf values while keeping the column numeric.
    """
    df = df.copy()

    safe_beneficiaries = df["beneficiaries_served"].replace(0, np.nan)
    safe_target = df["target_beneficiaries"].replace(0, np.nan)
    safe_funding = df["funding_received"].replace(0, np.nan)
    safe_volunteer_hours = df["volunteer_hours"].replace(0, np.nan)

    # Cost per beneficiary: how much it costs, on average, to serve one
    # beneficiary under this program in this period.
    df["cost_per_beneficiary"] = (df["program_expenses"] / safe_beneficiaries).fillna(0).round(2)

    # Funding utilization rate: share of funding actually spent on the
    # program (values > 100% indicate overspending relative to funding).
    df["funding_utilization_rate"] = ((df["program_expenses"] / safe_funding) * 100).fillna(0).round(2)

    # Target achievement rate: how close actual beneficiaries served came to
    # the target (100% = met target exactly, >100% = exceeded target).
    df["target_achievement_rate"] = ((df["beneficiaries_served"] / safe_target) * 100).fillna(0).round(2)

    # Funding remaining: unspent funding after program expenses (can be
    # negative if a program overspent its received funding).
    df["funding_remaining"] = (df["funding_received"] - df["program_expenses"]).round(2)

    # Beneficiaries served per volunteer hour: a proxy for volunteer
    # productivity/efficiency.
    df["beneficiaries_per_volunteer_hour"] = (
        (df["beneficiaries_served"] / safe_volunteer_hours).fillna(0).round(3)
    )

    return df


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Place columns in a clean, logical order for downstream use."""
    column_order = [
        "record_id", "date", "year", "month",
        "program_name", "program_category", "program_status",
        "region", "state",
        "beneficiaries_served", "target_beneficiaries", "target_achievement_rate",
        "funding_received", "program_expenses", "funding_remaining", "funding_utilization_rate",
        "cost_per_beneficiary",
        "volunteer_hours", "number_of_volunteers", "beneficiaries_per_volunteer_hour",
        "satisfaction_score", "outcome_success_rate",
    ]
    return df[column_order]


def main():
    df = load_raw_data(RAW_DATA_PATH)
    df = remove_duplicates(df)
    df = standardize_text_columns(df)
    df = handle_missing_values(df)
    df = convert_types(df)
    df = validate_numeric_values(df)
    df = create_derived_columns(df)
    df = reorder_columns(df)

    CLEAN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_DATA_PATH, index=False)

    print(f"\nFinal cleaned dataset: {df.shape[0]:,} rows, {df.shape[1]} columns")
    print(f"Saved cleaned dataset to: {CLEAN_DATA_PATH}")


if __name__ == "__main__":
    main()
