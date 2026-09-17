-- create_tables.sql
-- Schema definition for the Data4Impact SQLite database.
-- This table stores the cleaned, analysis-ready nonprofit impact dataset
-- produced by src/data_cleaning.py and loaded by src/database.py.

DROP TABLE IF EXISTS impact_metrics;

CREATE TABLE impact_metrics (
    record_id                      INTEGER PRIMARY KEY,
    date                           TEXT NOT NULL,          -- ISO format YYYY-MM-DD
    year                           INTEGER NOT NULL,
    month                          INTEGER NOT NULL,
    program_name                   TEXT NOT NULL,
    program_category               TEXT NOT NULL,
    program_status                 TEXT NOT NULL,
    region                         TEXT NOT NULL,
    state                          TEXT NOT NULL,
    beneficiaries_served           INTEGER NOT NULL,
    target_beneficiaries           INTEGER NOT NULL,
    target_achievement_rate        REAL NOT NULL,           -- percentage
    funding_received               REAL NOT NULL,           -- USD
    program_expenses               REAL NOT NULL,           -- USD
    funding_remaining              REAL NOT NULL,           -- USD
    funding_utilization_rate       REAL NOT NULL,           -- percentage
    cost_per_beneficiary           REAL NOT NULL,           -- USD
    volunteer_hours                REAL NOT NULL,
    number_of_volunteers           INTEGER NOT NULL,
    beneficiaries_per_volunteer_hour REAL NOT NULL,
    satisfaction_score             REAL NOT NULL,           -- 1-5 scale
    outcome_success_rate           REAL NOT NULL            -- percentage
);

-- Indexes to speed up the common filters used by the dashboard and
-- analysis queries.
CREATE INDEX idx_impact_program ON impact_metrics(program_name);
CREATE INDEX idx_impact_region ON impact_metrics(region);
CREATE INDEX idx_impact_year ON impact_metrics(year);
CREATE INDEX idx_impact_state ON impact_metrics(state);
