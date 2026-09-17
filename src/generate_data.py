"""
generate_data.py

Generates a synthetic nonprofit impact dataset for the Data4Impact Dashboard
portfolio project.

IMPORTANT: This dataset is entirely SYNTHETIC. It was generated programmatically
for portfolio/demo purposes and does not represent any real organization,
program, or individual.

The script builds realistic relationships between variables (e.g. programs with
more funding tend to serve more beneficiaries) and intentionally injects a
handful of data-quality issues (missing values, duplicates, inconsistent
capitalization, inconsistent category naming, and a few invalid values) so
that the downstream data_cleaning.py script has real problems to solve.

Run:
    python src/generate_data.py
Output:
    data/raw/nonprofit_impact_raw.csv
"""

import random
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Resolve paths relative to the project root, regardless of where the script
# is executed from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "nonprofit_impact_raw.csv"

YEARS = [2022, 2023, 2024, 2025]
MONTHS = list(range(1, 13))

# Each program has a baseline "scale" and "quality" that drives realistic
# relationships between funding, beneficiaries, expenses, and outcomes.
PROGRAMS = {
    "Education Support": {"category": "Education", "scale": 1.15, "quality": 0.80},
    "Food Assistance": {"category": "Basic Needs", "scale": 1.40, "quality": 0.78},
    "Healthcare Access": {"category": "Health", "scale": 1.00, "quality": 0.75},
    "Housing Support": {"category": "Basic Needs", "scale": 0.75, "quality": 0.68},
    "Youth Development": {"category": "Education", "scale": 0.90, "quality": 0.82},
    "Job Training": {"category": "Economic Empowerment", "scale": 0.70, "quality": 0.72},
    "Community Outreach": {"category": "Community", "scale": 0.60, "quality": 0.70},
}

REGIONS = {
    "Northeast": ["NY", "MA", "PA"],
    "Midwest": ["IL", "OH", "MI"],
    "South": ["TX", "GA", "FL"],
    "West": ["CA", "WA", "AZ"],
}

PROGRAM_STATUSES = ["Active", "Active", "Active", "Active", "Paused", "Completed"]

# Variants used to intentionally create inconsistent text formatting, which
# data_cleaning.py will later standardize.
PROGRAM_NAME_VARIANTS = {
    "Education Support": ["Education Support", "education support", "EDUCATION SUPPORT ", "Education  Support"],
    "Food Assistance": ["Food Assistance", "food assistance", "Food assistance", "FOOD ASSISTANCE"],
    "Healthcare Access": ["Healthcare Access", "healthcare access", "Health Care Access", "HEALTHCARE ACCESS"],
    "Housing Support": ["Housing Support", "housing support", "Housing  Support", "HOUSING SUPPORT"],
    "Youth Development": ["Youth Development", "youth development", "Youth development", "YOUTH DEVELOPMENT"],
    "Job Training": ["Job Training", "job training", "Job  Training", "JOB TRAINING"],
    "Community Outreach": ["Community Outreach", "community outreach", "Community outreach", "COMMUNITY OUTREACH"],
}

REGION_VARIANTS = {
    "Northeast": ["Northeast", "northeast", "NORTHEAST", "North East"],
    "Midwest": ["Midwest", "midwest", "MIDWEST", "Mid West"],
    "South": ["South", "south", "SOUTH"],
    "West": ["West", "west", "WEST"],
}


def random_program_name_variant(program_name: str) -> str:
    """Return a randomly (mostly-clean) formatted variant of a program name.

    ~80% of the time returns the clean canonical name, ~20% of the time
    returns a "dirty" variant, simulating inconsistent manual data entry.
    """
    if random.random() < 0.80:
        return program_name
    return random.choice(PROGRAM_NAME_VARIANTS[program_name])


def random_region_variant(region_name: str) -> str:
    """Return a randomly (mostly-clean) formatted variant of a region name."""
    if random.random() < 0.85:
        return region_name
    return random.choice(REGION_VARIANTS[region_name])


def generate_record(record_id: int, year: int, month: int) -> dict:
    """Generate one synthetic monthly program record with realistic
    relationships between funding, beneficiaries, expenses, and outcomes.
    """
    program_name = random.choice(list(PROGRAMS.keys()))
    program_info = PROGRAMS[program_name]
    category = program_info["category"]
    scale = program_info["scale"]
    quality = program_info["quality"]

    region_name = random.choice(list(REGIONS.keys()))
    state = random.choice(REGIONS[region_name])

    # Year-over-year growth: programs tend to grow modestly each year, with
    # some random monthly seasonality layered on top.
    year_growth_factor = 1 + (year - 2022) * 0.08
    seasonality = 1 + 0.10 * np.sin((month / 12) * 2 * np.pi)

    # Funding received: driven by program scale, growth over time, and noise.
    base_funding = 18000 * scale * year_growth_factor * seasonality
    funding_received = max(1000, np.random.normal(base_funding, base_funding * 0.18))

    # Beneficiaries served: correlated with funding (more funding -> more
    # people served), but with diminishing returns and program-quality noise.
    beneficiaries_base = (funding_received / 45) * quality * np.random.normal(1.0, 0.12)
    beneficiaries_served = max(5, int(round(beneficiaries_base)))

    # Target beneficiaries: set near, but not identical to, actual served,
    # so target-achievement analysis is meaningful (some programs over/under
    # perform).
    target_multiplier = np.random.normal(1.05, 0.15)
    target_beneficiaries = max(5, int(round(beneficiaries_served * target_multiplier)))

    # Program expenses: correlated with beneficiaries served (larger programs
    # cost more to run), plus overhead noise.
    expense_ratio = np.random.normal(0.78, 0.10)  # expenses as a share of funding
    program_expenses = max(500, funding_received * min(max(expense_ratio, 0.4), 1.15))

    # Volunteer hours & volunteer count: larger programs use more volunteers.
    number_of_volunteers = max(1, int(round((beneficiaries_served / 12) * np.random.normal(1.0, 0.25))))
    volunteer_hours = max(1, round(number_of_volunteers * np.random.normal(9.5, 2.5), 1))

    # Satisfaction score (1-5) and outcome success rate (%): both driven by
    # program quality, with realistic random variation.
    satisfaction_score = float(np.clip(np.random.normal(3.4 + quality * 1.4, 0.45), 1.0, 5.0))
    outcome_success_rate = float(np.clip(np.random.normal(quality * 100, 8), 20, 99))

    status = random.choice(PROGRAM_STATUSES)

    record = {
        "record_id": record_id,
        "date": f"{year}-{month:02d}-01",
        "year": year,
        "month": month,
        "program_name": random_program_name_variant(program_name),
        "program_category": category,
        "region": random_region_variant(region_name),
        "state": state,
        "beneficiaries_served": beneficiaries_served,
        "target_beneficiaries": target_beneficiaries,
        "funding_received": round(funding_received, 2),
        "program_expenses": round(program_expenses, 2),
        "volunteer_hours": volunteer_hours,
        "number_of_volunteers": number_of_volunteers,
        "satisfaction_score": round(satisfaction_score, 2),
        "outcome_success_rate": round(outcome_success_rate, 2),
        "program_status": status,
    }
    return record


def inject_data_quality_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Intentionally introduce realistic data-quality problems into an
    otherwise clean dataframe, so that data_cleaning.py has real issues to
    solve. This mimics common messy real-world nonprofit data entry.
    """
    df = df.copy()
    n = len(df)
    rng = np.random.default_rng(RANDOM_SEED)

    # 1) Missing values in a handful of columns.
    for col, frac in [
        ("satisfaction_score", 0.03),
        ("volunteer_hours", 0.02),
        ("funding_received", 0.01),
        ("region", 0.015),
    ]:
        missing_idx = rng.choice(n, size=int(n * frac), replace=False)
        df.loc[missing_idx, col] = np.nan

    # 2) Duplicate rows: append exact duplicates of a random sample of rows.
    dup_sample = df.sample(n=max(5, int(n * 0.01)), random_state=RANDOM_SEED)
    df = pd.concat([df, dup_sample], ignore_index=True)

    # 3) A few unrealistic / invalid numeric values requiring validation.
    invalid_idx = rng.choice(len(df), size=8, replace=False)
    for i, idx in enumerate(invalid_idx):
        if i % 4 == 0:
            df.loc[idx, "beneficiaries_served"] = -abs(df.loc[idx, "beneficiaries_served"])  # negative value
        elif i % 4 == 1:
            df.loc[idx, "program_expenses"] = -abs(df.loc[idx, "program_expenses"])  # negative expense
        elif i % 4 == 2:
            df.loc[idx, "satisfaction_score"] = 9.9  # impossible score (>5 scale)
        else:
            df.loc[idx, "outcome_success_rate"] = 150.0  # impossible percentage

    # Shuffle rows so duplicates/issues aren't neatly clustered at the end.
    df = df.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)

    # Reassign record_id AFTER shuffling so ids stay unique/sequential except
    # for the intentional duplicate rows, which should share the same
    # record_id + data as their original (a realistic duplicate-entry issue).
    return df


ROWS_PER_YEAR_MONTH = 34  # 4 years * 12 months * 34 ~= 1,632 base rows


def main():
    records = []
    record_id = 1
    for year in YEARS:
        for month in MONTHS:
            # Generate several records per program area per month (one row
            # roughly represents one program's monthly activity report,
            # with some months/programs having multiple regional entries).
            for _ in range(ROWS_PER_YEAR_MONTH):
                records.append(generate_record(record_id, year, month))
                record_id += 1

    df = pd.DataFrame(records)
    df = inject_data_quality_issues(df)

    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DATA_PATH, index=False)

    print(f"Generated {len(df):,} rows (synthetic, seed={RANDOM_SEED}).")
    print(f"Saved raw dataset to: {RAW_DATA_PATH}")


if __name__ == "__main__":
    main()
