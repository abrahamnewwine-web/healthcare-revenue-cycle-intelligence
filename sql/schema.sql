-- Healthcare Revenue Cycle Intelligence - Star Schema DDL (SQLite)

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_denials_appeals;
DROP TABLE IF EXISTS fact_claims;
DROP TABLE IF EXISTS fact_patient_visits;
DROP TABLE IF EXISTS dim_denial_reason;
DROP TABLE IF EXISTS dim_department;
DROP TABLE IF EXISTS dim_payer;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,  -- YYYYMMDD
    full_date       TEXT NOT NULL,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,
    month_num       INTEGER NOT NULL,
    month_name      TEXT NOT NULL,
    year_month      TEXT NOT NULL
);

CREATE TABLE dim_payer (
    payer_id        INTEGER PRIMARY KEY,
    payer_name      TEXT NOT NULL UNIQUE,
    payer_type      TEXT NOT NULL
);

CREATE TABLE dim_department (
    department_id   INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE,
    service_line    TEXT NOT NULL
);

CREATE TABLE dim_denial_reason (
    reason_id       INTEGER PRIMARY KEY,
    reason_name     TEXT NOT NULL UNIQUE,
    reason_category TEXT NOT NULL
);

CREATE TABLE fact_patient_visits (
    visit_id        INTEGER PRIMARY KEY,
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    department_id   INTEGER NOT NULL REFERENCES dim_department(department_id),
    payer_id        INTEGER NOT NULL REFERENCES dim_payer(payer_id),
    visit_count     INTEGER NOT NULL CHECK (visit_count >= 0),
    operating_cost  REAL NOT NULL CHECK (operating_cost >= 0)
);

CREATE TABLE fact_claims (
    claim_id        INTEGER PRIMARY KEY,
    visit_id        INTEGER NOT NULL REFERENCES fact_patient_visits(visit_id),
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    department_id   INTEGER NOT NULL REFERENCES dim_department(department_id),
    payer_id        INTEGER NOT NULL REFERENCES dim_payer(payer_id),
    claim_status    TEXT NOT NULL CHECK (claim_status IN ('Accepted', 'Denied', 'Pending')),
    billed_amount   REAL NOT NULL CHECK (billed_amount >= 0),
    paid_amount     REAL NOT NULL CHECK (paid_amount >= 0)
);

CREATE TABLE fact_denials_appeals (
    denial_id       INTEGER PRIMARY KEY,
    claim_id        INTEGER NOT NULL REFERENCES fact_claims(claim_id),
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    department_id   INTEGER NOT NULL REFERENCES dim_department(department_id),
    payer_id        INTEGER NOT NULL REFERENCES dim_payer(payer_id),
    reason_id       INTEGER NOT NULL REFERENCES dim_denial_reason(reason_id),
    denied_amount   REAL NOT NULL CHECK (denied_amount >= 0),
    appealed_flag   INTEGER NOT NULL CHECK (appealed_flag IN (0, 1)),
    overturned_flag INTEGER NOT NULL CHECK (overturned_flag IN (0, 1)),
    recovered_amount REAL NOT NULL CHECK (recovered_amount >= 0)
);

CREATE INDEX idx_visits_date_dept ON fact_patient_visits(date_key, department_id, payer_id);
CREATE INDEX idx_claims_date_dept_payer ON fact_claims(date_key, department_id, payer_id, claim_status);
CREATE INDEX idx_denials_reason_payer ON fact_denials_appeals(date_key, department_id, payer_id, reason_id);
