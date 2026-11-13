"""ETL pipeline for Healthcare Revenue Cycle Intelligence.

Generates a calibrated, reproducible multi-department healthcare revenue cycle
benchmark dataset (2025 historical monthly operations), transforms it into a
validated star schema, exports processed CSVs, and loads the SQLite warehouse.
"""

from __future__ import annotations

import calendar
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    DB_PATH,
    DENIAL_REASONS,
    DEPARTMENTS,
    PAYERS,
    RANDOM_SEED,
    SQL_DIR,
)

# Calibrated Oncology profile aligned with portfolio reference specification
DEPARTMENT_PROFILES = {
    "Oncology": {
        "visits": 6000,
        "claims_per_visit_mean": 8.3333,  # ~50,000 line-item claims
        "avg_billed_per_claim": 3620.0,
        "base_collection_rate": 0.378,
        "op_cost_ratio": 0.0207,  # ~97.9% net operating margin against collections
        "payer_weights": [0.2491, 0.2300, 0.2296, 0.1795, 0.1118],
        "denial_rates": {
            "UnitedHealthcare": 0.172,
            "Medicare": 0.118,
            "Aetna": 0.114,
            "Blue Cross Blue Shield": 0.113,
            "Medicaid": 0.111,
        },
    },
    "Cardiology": {
        "visits": 5200,
        "claims_per_visit_mean": 2.5,
        "avg_billed_per_claim": 2850.0,
        "base_collection_rate": 0.465,
        "op_cost_ratio": 0.145,
        "payer_weights": [0.22, 0.21, 0.30, 0.16, 0.11],
        "denial_rates": {
            "UnitedHealthcare": 0.148,
            "Medicare": 0.098,
            "Aetna": 0.105,
            "Blue Cross Blue Shield": 0.094,
            "Medicaid": 0.119,
        },
    },
    "Orthopedics": {
        "visits": 4100,
        "claims_per_visit_mean": 2.4,
        "avg_billed_per_claim": 3100.0,
        "base_collection_rate": 0.490,
        "op_cost_ratio": 0.180,
        "payer_weights": [0.26, 0.24, 0.23, 0.18, 0.09],
        "denial_rates": {
            "UnitedHealthcare": 0.155,
            "Medicare": 0.092,
            "Aetna": 0.108,
            "Blue Cross Blue Shield": 0.102,
            "Medicaid": 0.125,
        },
    },
    "General Medicine": {
        "visits": 7400,
        "claims_per_visit_mean": 1.8,
        "avg_billed_per_claim": 950.0,
        "base_collection_rate": 0.540,
        "op_cost_ratio": 0.240,
        "payer_weights": [0.23, 0.20, 0.26, 0.17, 0.14],
        "denial_rates": {
            "UnitedHealthcare": 0.126,
            "Medicare": 0.084,
            "Aetna": 0.095,
            "Blue Cross Blue Shield": 0.088,
            "Medicaid": 0.114,
        },
    },
    "Emergency": {
        "visits": 6300,
        "claims_per_visit_mean": 2.0,
        "avg_billed_per_claim": 1450.0,
        "base_collection_rate": 0.365,
        "op_cost_ratio": 0.285,
        "payer_weights": [0.19, 0.18, 0.24, 0.14, 0.25],
        "denial_rates": {
            "UnitedHealthcare": 0.164,
            "Medicare": 0.109,
            "Aetna": 0.121,
            "Blue Cross Blue Shield": 0.115,
            "Medicaid": 0.149,
        },
    },
}

MONTH_VISIT_WEIGHTS = np.array(
    [0.068, 0.072, 0.083, 0.085, 0.086, 0.085, 0.086, 0.087, 0.085, 0.087, 0.088, 0.088]
)
MONTH_VISIT_WEIGHTS /= MONTH_VISIT_WEIGHTS.sum()

# Reflects initial Jan clearinghouse lag and steady-state adjudication Mar-Dec
MONTH_COLLECTION_FACTOR = np.array(
    [0.05, 0.42, 1.07, 1.09, 1.12, 1.05, 1.12, 1.10, 1.08, 1.06, 1.06, 1.07]
)

REASON_WEIGHTS = np.array([0.270, 0.258, 0.232, 0.091, 0.084, 0.065])
REASON_WEIGHTS /= REASON_WEIGHTS.sum()


def build_dim_date(year: int = 2025) -> pd.DataFrame:
    """Create a complete daily calendar dimension for the reporting year."""
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    return pd.DataFrame(
        {
            "date_key": dates.strftime("%Y%m%d").astype(int),
            "full_date": dates.strftime("%Y-%m-%d"),
            "year": dates.year,
            "quarter": dates.quarter,
            "month_num": dates.month,
            "month_name": dates.strftime("%B"),
            "year_month": dates.strftime("%Y-%m"),
        }
    )


def generate_synthetic_data(seed: int = RANDOM_SEED) -> dict[str, pd.DataFrame]:
    """Generate calibrated healthcare visits, claims, and denial/appeal tables."""
    rng = np.random.default_rng(seed)

    dim_date = build_dim_date(2025)
    dim_payer = pd.DataFrame(PAYERS, columns=["payer_id", "payer_name", "payer_type"])
    dim_department = pd.DataFrame(
        DEPARTMENTS, columns=["department_id", "department_name", "service_line"]
    )
    dim_denial_reason = pd.DataFrame(
        DENIAL_REASONS, columns=["reason_id", "reason_name", "reason_category"]
    )

    payer_name_by_id = dict(zip(dim_payer["payer_id"], dim_payer["payer_name"]))
    dept_id_by_name = dict(
        zip(dim_department["department_name"], dim_department["department_id"])
    )

    month_date_keys = {
        m: dim_date.loc[dim_date["month_num"] == m, "date_key"].to_numpy()
        for m in range(1, 13)
    }

    visit_rows = []
    claim_rows = []
    denial_rows = []

    visit_id_seq = 1
    claim_id_seq = 1
    denial_id_seq = 1

    for dept_name, profile in DEPARTMENT_PROFILES.items():
        dept_id = dept_id_by_name[dept_name]
        total_visits = profile["visits"]
        monthly_visits = rng.multinomial(total_visits, MONTH_VISIT_WEIGHTS)
        payer_ids = dim_payer["payer_id"].to_numpy()
        p_weights = np.array(profile["payer_weights"], dtype=float)
        p_weights /= p_weights.sum()

        for month_idx, n_visits in enumerate(monthly_visits, start=1):
            if n_visits == 0:
                continue
            d_keys = rng.choice(month_date_keys[month_idx], size=n_visits, replace=True)
            v_payers = rng.choice(payer_ids, size=n_visits, replace=True, p=p_weights)

            # Determine claims per visit cleanly so Oncology hits ~50,000 claims
            claims_per_visit = rng.poisson(
                lam=max(profile["claims_per_visit_mean"] - 1.0, 0.1), size=n_visits
            ) + 1

            # Base visit operating cost
            visit_billed_est = (
                claims_per_visit
                * profile["avg_billed_per_claim"]
                * profile["base_collection_rate"]
                * profile["op_cost_ratio"]
            )
            op_costs = np.round(
                visit_billed_est * rng.uniform(0.92, 1.08, size=n_visits), 2
            )

            for i in range(n_visits):
                vid = visit_id_seq
                visit_id_seq += 1
                dk = int(d_keys[i])
                pid = int(v_payers[i])
                visit_rows.append((vid, dk, dept_id, pid, 1, float(op_costs[i])))

                n_claims = int(claims_per_visit[i])
                pname = payer_name_by_id[pid]
                denial_prob = profile["denial_rates"][pname]
                pending_prob = 0.013
                accept_prob = max(0.0, 1.0 - denial_prob - pending_prob)

                statuses = rng.choice(
                    ["Accepted", "Denied", "Pending"],
                    size=n_claims,
                    p=[accept_prob, denial_prob, pending_prob],
                )
                billed_vals = np.round(
                    profile["avg_billed_per_claim"]
                    * rng.lognormal(mean=-0.03, sigma=0.24, size=n_claims),
                    2,
                )

                # Paid amount reflects collection rate & month lag; denied claims pay 0 upfront unless overturned
                m_factor = MONTH_COLLECTION_FACTOR[month_idx - 1]
                target_rate = np.clip(
                    profile["base_collection_rate"] * m_factor / 0.94, 0.01, 0.85
                )

                for j in range(n_claims):
                    cid = claim_id_seq
                    claim_id_seq += 1
                    st = str(statuses[j])
                    billed = float(billed_vals[j])

                    if st == "Accepted":
                        paid = round(
                            billed
                            * float(np.clip(rng.normal(target_rate * 1.15, 0.08), 0.02, 0.95)),
                            2,
                        )
                    elif st == "Pending":
                        paid = 0.0
                    else:
                        paid = 0.0

                    if st == "Denied":
                        rid = int(rng.choice(dim_denial_reason["reason_id"], p=REASON_WEIGHTS))
                        appealed = 1 if (month_idx >= 2 and rng.random() < 0.62) else (1 if rng.random() < 0.25 else 0)
                        overturned = 1 if (appealed == 1 and rng.random() < 0.44) else 0
                        recovered = (
                            round(billed * float(np.clip(rng.normal(target_rate * 0.92, 0.07), 0.05, 0.85)), 2)
                            if overturned == 1
                            else 0.0
                        )
                        paid = recovered
                        denial_rows.append(
                            (
                                denial_id_seq,
                                cid,
                                dk,
                                dept_id,
                                pid,
                                rid,
                                billed,
                                appealed,
                                overturned,
                                recovered,
                            )
                        )
                        denial_id_seq += 1

                    claim_rows.append((cid, vid, dk, dept_id, pid, st, billed, paid))

    fact_patient_visits = pd.DataFrame(
        visit_rows,
        columns=[
            "visit_id",
            "date_key",
            "department_id",
            "payer_id",
            "visit_count",
            "operating_cost",
        ],
    )
    fact_claims = pd.DataFrame(
        claim_rows,
        columns=[
            "claim_id",
            "visit_id",
            "date_key",
            "department_id",
            "payer_id",
            "claim_status",
            "billed_amount",
            "paid_amount",
        ],
    )
    fact_denials_appeals = pd.DataFrame(
        denial_rows,
        columns=[
            "denial_id",
            "claim_id",
            "date_key",
            "department_id",
            "payer_id",
            "reason_id",
            "denied_amount",
            "appealed_flag",
            "overturned_flag",
            "recovered_amount",
        ],
    )

    return {
        "dim_date": dim_date,
        "dim_payer": dim_payer,
        "dim_department": dim_department,
        "dim_denial_reason": dim_denial_reason,
        "fact_patient_visits": fact_patient_visits,
        "fact_claims": fact_claims,
        "fact_denials_appeals": fact_denials_appeals,
    }


def export_csvs(tables: dict[str, pd.DataFrame]) -> None:
    """Persist raw and processed star-schema CSV artifacts."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for name, df in tables.items():
        if name.startswith("fact_"):
            df.to_csv(DATA_RAW_DIR / f"{name}.csv", index=False)
        df.to_csv(DATA_PROCESSED_DIR / f"{name}.csv", index=False)


def load_sqlite(tables: dict[str, pd.DataFrame], db_path: Path = DB_PATH) -> None:
    """Create schema and bulk-load tables into SQLite warehouse."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    load_order = [
        "dim_date",
        "dim_payer",
        "dim_department",
        "dim_denial_reason",
        "fact_patient_visits",
        "fact_claims",
        "fact_denials_appeals",
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        for table_name in load_order:
            tables[table_name].to_sql(
                table_name, conn, if_exists="append", index=False, chunksize=5000
            )
        conn.commit()


def run_pipeline() -> dict[str, int]:
    """Execute full ETL pipeline and return row-count summary."""
    tables = generate_synthetic_data()
    export_csvs(tables)
    load_sqlite(tables)
    return {name: len(df) for name, df in tables.items()}


if __name__ == "__main__":
    counts = run_pipeline()
    for tbl, cnt in counts.items():
        print(f"Loaded {tbl}: {cnt:,} rows")
