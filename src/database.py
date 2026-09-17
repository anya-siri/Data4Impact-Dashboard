"""
database.py

Creates the SQLite database for the Data4Impact Dashboard project and loads
the cleaned CSV dataset into the `impact_metrics` table, using the schema
defined in sql/create_tables.sql.

Run:
    python src/database.py
Input:
    data/processed/nonprofit_impact_clean.csv
    sql/create_tables.sql
Output:
    database/data4impact.db
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "nonprofit_impact_clean.csv"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "create_tables.sql"
DB_PATH = PROJECT_ROOT / "database" / "data4impact.db"

TABLE_NAME = "impact_metrics"


def create_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """Execute the create_tables.sql script to (re)create the database
    schema. This drops and recreates the table so the script is safely
    re-runnable.
    """
    schema_sql = schema_path.read_text()
    conn.executescript(schema_sql)
    print(f"Applied schema from {schema_path.name}")


def load_data_into_table(conn: sqlite3.Connection, csv_path: Path) -> int:
    """Load the cleaned CSV into the impact_metrics table."""
    df = pd.read_csv(csv_path)

    # Ensure the date column is stored as plain ISO text (YYYY-MM-DD),
    # matching the TEXT column type defined in the schema.
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    return len(df)


def verify_load(conn: sqlite3.Connection) -> None:
    """Run a quick sanity check query to confirm the data loaded correctly."""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    row_count = cursor.fetchone()[0]
    print(f"Verified: {row_count:,} rows present in '{TABLE_NAME}' table")

    cursor = conn.execute(f"SELECT DISTINCT program_name FROM {TABLE_NAME} ORDER BY program_name")
    programs = [row[0] for row in cursor.fetchall()]
    print(f"Programs in database: {', '.join(programs)}")


def main():
    if not CLEAN_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {CLEAN_DATA_PATH}. "
            "Run 'python src/data_cleaning.py' first."
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove any existing database file so this script is safely re-runnable
    # from a clean state.
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn, SCHEMA_PATH)
        rows_loaded = load_data_into_table(conn, CLEAN_DATA_PATH)
        conn.commit()
        print(f"Loaded {rows_loaded:,} rows into '{TABLE_NAME}'")
        verify_load(conn)
    finally:
        conn.close()

    print(f"Database ready at: {DB_PATH}")


if __name__ == "__main__":
    main()
