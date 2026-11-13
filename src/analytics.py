"""Analytical query, KPI reconciliation, and Q1 2026 forecast engine."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from src.config import DB_PATH


@dataclass(frozen=True)
class FilterParams:
    """Supported interactive dashboard slicer filters."""

    year: int | None = None
    month: int | None = None
    payer: str | None = None
    department: str | None = None


def _build_where(filters: FilterParams, alias: str = "c") -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if filters.year is not None:
        clauses.append("d.year = ?")
        params.append(filters.year)
    if filters.month is not None:
        clauses.append("d.month_num = ?")
        params.append(filters.month)
    if filters.payer and filters.payer != "All":
        clauses.append("p.payer_name = ?")
        params.append(filters.payer)
    if filters.department and filters.department != "All":
        clauses.append("dep.department_name = ?")
        params.append(filters.department)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        from src.pipeline import run_pipeline

        run_pipeline()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_filter_options() -> dict[str, list[Any]]:
    """Return distinct slicer values from dimension tables."""
    with _connect() as conn:
        years = [r[0] for r in conn.execute("SELECT DISTINCT year FROM dim_date ORDER BY year")]
        months = [
            {"month_num": r[0], "month_name": r[1]}
            for r in conn.execute(
                "SELECT DISTINCT month_num, month_name FROM dim_date ORDER BY month_num"
            )
        ]
        payers = [
            r[0] for r in conn.execute("SELECT payer_name FROM dim_payer ORDER BY payer_name")
        ]
        departments = [
            r[0]
            for r in conn.execute(
                "SELECT department_name FROM dim_department ORDER BY department_name"
            )
        ]
    return {
        "years": years,
        "months": months,
        "payers": payers,
        "departments": departments,
    }


def compute_q1_2026_forecast(monthly_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Produce a Q1 2026 (Jan-Mar) monthly revenue collection forecast with 95% CI.

    Uses steady-state operational months (from month 3 onward where clearinghouse
    lag has stabilized) for trend regression, while returning all 2025 actuals
    plus 3 projected months with upper/lower 95% prediction intervals.
    """
    if monthly_df.empty:
        return []

    df = monthly_df.sort_values("year_month").reset_index(drop=True)
    steady = df.iloc[2:] if len(df) >= 6 else df

    x = np.arange(len(steady), dtype=float)
    y = steady["total_payments"].to_numpy(dtype=float)

    if len(x) >= 2 and np.std(x) > 0:
        slope, intercept, _, _, _ = stats.linregress(x, y)
        y_hat = intercept + slope * x
        residuals = y - y_hat
        dof = max(len(x) - 2, 1)
        s_err = float(np.sqrt(np.sum(residuals**2) / dof))
        t_crit = float(stats.t.ppf(0.975, dof))
        x_mean = float(np.mean(x))
        s_xx = float(np.sum((x - x_mean) ** 2)) or 1.0
    else:
        slope, intercept, s_err, t_crit, x_mean, s_xx = (
            0.0,
            float(np.mean(y)),
            float(np.std(y)),
            1.96,
            0.0,
            1.0,
        )

    results: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        results.append(
            {
                "period": row["year_month"],
                "actual_payments": round(float(row["total_payments"]), 2),
                "forecast_payments": None,
                "lower_95": None,
                "upper_95": None,
            }
        )

    # Anchor bridge at last actual point for continuous chart display
    last_actual = round(float(df.iloc[-1]["total_payments"]), 2)
    results[-1]["forecast_payments"] = last_actual
    results[-1]["lower_95"] = last_actual
    results[-1]["upper_95"] = last_actual

    base_idx = len(steady) - 1
    for step, ym in enumerate(["2026-01", "2026-02", "2026-03"], start=1):
        xf = base_idx + step
        pred = max(0.0, float(intercept + slope * xf))
        margin = t_crit * s_err * float(
            np.sqrt(1.0 + 1.0 / len(x) + ((xf - x_mean) ** 2) / s_xx)
        )
        results.append(
            {
                "period": ym,
                "actual_payments": None,
                "forecast_payments": round(pred, 2),
                "lower_95": round(max(0.0, pred - margin), 2),
                "upper_95": round(pred + margin, 2),
            }
        )
    return results


def get_dashboard_data(filters: FilterParams) -> dict[str, Any]:
    """Compute reconciled executive KPIs, trends, breakdowns, and forecast."""
    where_sql, params = _build_where(filters)

    with _connect() as conn:
        claims_sql = f"""
            SELECT
                COUNT(c.claim_id) AS total_claims,
                SUM(CASE WHEN c.claim_status = 'Accepted' THEN 1 ELSE 0 END) AS accepted_claims,
                SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
                SUM(CASE WHEN c.claim_status = 'Pending' THEN 1 ELSE 0 END) AS pending_claims,
                COALESCE(SUM(c.billed_amount), 0.0) AS total_billed,
                COALESCE(SUM(c.paid_amount), 0.0) AS total_payments
            FROM fact_claims c
            JOIN dim_date d ON c.date_key = d.date_key
            JOIN dim_payer p ON c.payer_id = p.payer_id
            JOIN dim_department dep ON c.department_id = dep.department_id
            {where_sql}
        """
        c_row = dict(conn.execute(claims_sql, params).fetchone())

        visits_sql = f"""
            SELECT
                COALESCE(SUM(v.visit_count), 0) AS total_visits,
                COALESCE(SUM(v.operating_cost), 0.0) AS operating_cost
            FROM fact_patient_visits v
            JOIN dim_date d ON v.date_key = d.date_key
            JOIN dim_payer p ON v.payer_id = p.payer_id
            JOIN dim_department dep ON v.department_id = dep.department_id
            {where_sql}
        """
        v_row = dict(conn.execute(visits_sql, params).fetchone())

        monthly_sql = f"""
            SELECT
                d.year_month,
                d.month_num,
                COUNT(c.claim_id) AS total_claims,
                SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
                COALESCE(SUM(c.billed_amount), 0.0) AS billed_amount,
                COALESCE(SUM(c.paid_amount), 0.0) AS total_payments
            FROM fact_claims c
            JOIN dim_date d ON c.date_key = d.date_key
            JOIN dim_payer p ON c.payer_id = p.payer_id
            JOIN dim_department dep ON c.department_id = dep.department_id
            {where_sql}
            GROUP BY d.year_month, d.month_num
            ORDER BY d.year_month
        """
        monthly_df = pd.read_sql_query(monthly_sql, conn, params=params)

        monthly_visits_sql = f"""
            SELECT
                d.year_month,
                COALESCE(SUM(v.visit_count), 0) AS visits,
                COALESCE(SUM(v.operating_cost), 0.0) AS operating_cost
            FROM fact_patient_visits v
            JOIN dim_date d ON v.date_key = d.date_key
            JOIN dim_payer p ON v.payer_id = p.payer_id
            JOIN dim_department dep ON v.department_id = dep.department_id
            {where_sql}
            GROUP BY d.year_month
            ORDER BY d.year_month
        """
        mv_df = pd.read_sql_query(monthly_visits_sql, conn, params=params)

        appeals_sql = f"""
            SELECT
                d.year_month,
                COUNT(da.denial_id) AS total_denials,
                COALESCE(SUM(da.appealed_flag), 0) AS appealed_denials,
                COALESCE(SUM(da.overturned_flag), 0) AS overturned_denials,
                COALESCE(SUM(da.recovered_amount), 0.0) AS recovered_amount
            FROM fact_denials_appeals da
            JOIN dim_date d ON da.date_key = d.date_key
            JOIN dim_payer p ON da.payer_id = p.payer_id
            JOIN dim_department dep ON da.department_id = dep.department_id
            {where_sql}
            GROUP BY d.year_month
            ORDER BY d.year_month
        """
        appeals_df = pd.read_sql_query(appeals_sql, conn, params=params)

        payer_sql = f"""
            SELECT
                p.payer_name,
                COUNT(c.claim_id) AS total_claims,
                SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
                COALESCE(SUM(c.billed_amount), 0.0) AS billed_amount,
                COALESCE(SUM(c.paid_amount), 0.0) AS total_payments
            FROM fact_claims c
            JOIN dim_date d ON c.date_key = d.date_key
            JOIN dim_payer p ON c.payer_id = p.payer_id
            JOIN dim_department dep ON c.department_id = dep.department_id
            {where_sql}
            GROUP BY p.payer_name
            ORDER BY denied_claims DESC
        """
        payer_df = pd.read_sql_query(payer_sql, conn, params=params)

        reasons_sql = f"""
            SELECT
                r.reason_name,
                r.reason_category,
                COUNT(da.denial_id) AS denial_count,
                COALESCE(SUM(da.denied_amount), 0.0) AS denied_amount,
                COALESCE(SUM(da.appealed_flag), 0) AS appealed_count,
                COALESCE(SUM(da.overturned_flag), 0) AS overturned_count
            FROM fact_denials_appeals da
            JOIN dim_date d ON da.date_key = d.date_key
            JOIN dim_payer p ON da.payer_id = p.payer_id
            JOIN dim_department dep ON da.department_id = dep.department_id
            JOIN dim_denial_reason r ON da.reason_id = r.reason_id
            {where_sql}
            GROUP BY r.reason_name, r.reason_category
            ORDER BY denial_count DESC
        """
        reasons_df = pd.read_sql_query(reasons_sql, conn, params=params)

    total_claims = int(c_row["total_claims"] or 0)
    accepted_claims = int(c_row["accepted_claims"] or 0)
    denied_claims = int(c_row["denied_claims"] or 0)
    pending_claims = int(c_row["pending_claims"] or 0)
    total_billed = float(c_row["total_billed"] or 0.0)
    total_payments = float(c_row["total_payments"] or 0.0)
    total_visits = int(v_row["total_visits"] or 0)
    operating_cost = float(v_row["operating_cost"] or 0.0)

    net_surplus = total_payments - operating_cost
    collection_rate = (100.0 * total_payments / total_billed) if total_billed > 0 else 0.0
    denial_rate = (100.0 * denied_claims / total_claims) if total_claims > 0 else 0.0
    acceptance_rate = (100.0 * accepted_claims / total_claims) if total_claims > 0 else 0.0
    operating_margin = (100.0 * net_surplus / total_payments) if total_payments > 0 else 0.0

    # Merge monthly tables for sparklines and MoM deltas
    if not monthly_df.empty:
        monthly_df = monthly_df.merge(mv_df, on="year_month", how="left").fillna(0.0)
        monthly_df["billing_gap"] = (
            monthly_df["billed_amount"] - monthly_df["total_payments"]
        )
        monthly_df["collection_rate_pct"] = np.where(
            monthly_df["billed_amount"] > 0,
            100.0 * monthly_df["total_payments"] / monthly_df["billed_amount"],
            0.0,
        )
        monthly_df["denial_rate_pct"] = np.where(
            monthly_df["total_claims"] > 0,
            100.0 * monthly_df["denied_claims"] / monthly_df["total_claims"],
            0.0,
        )
        monthly_df["net_surplus"] = (
            monthly_df["total_payments"] - monthly_df["operating_cost"]
        )
        monthly_df["operating_margin_pct"] = np.where(
            monthly_df["total_payments"] > 0,
            100.0 * monthly_df["net_surplus"] / monthly_df["total_payments"],
            0.0,
        )

    def _mom_delta(col: str, pct_change: bool = False) -> float:
        if len(monthly_df) < 2:
            return 0.0
        prev = float(monthly_df.iloc[-2][col])
        curr = float(monthly_df.iloc[-1][col])
        if pct_change:
            return round(((curr - prev) / prev * 100.0) if prev else 0.0, 2)
        return round(curr - prev, 2)

    if not payer_df.empty:
        payer_df["denial_rate_pct"] = np.where(
            payer_df["total_claims"] > 0,
            100.0 * payer_df["denied_claims"] / payer_df["total_claims"],
            0.0,
        )
        payer_df["claims_share_pct"] = (
            100.0 * payer_df["total_claims"] / total_claims if total_claims > 0 else 0.0
        )

    # Without-month context for Q1 2026 forecast if user picked a single month
    forecast_series = compute_q1_2026_forecast(monthly_df)

    return {
        "filters": {
            "year": filters.year,
            "month": filters.month,
            "payer": filters.payer or "All",
            "department": filters.department or "All",
        },
        "kpis": {
            "total_patient_visits": total_visits,
            "visits_mom_pct": _mom_delta("visits", pct_change=True),
            "total_claims": total_claims,
            "accepted_claims": accepted_claims,
            "denied_claims": denied_claims,
            "pending_claims": pending_claims,
            "total_billed": round(total_billed, 2),
            "total_payments": round(total_payments, 2),
            "billing_gap": round(total_billed - total_payments, 2),
            "collection_rate_pct": round(collection_rate, 2),
            "collection_mom_pp": _mom_delta("collection_rate_pct"),
            "denial_rate_pct": round(denial_rate, 2),
            "denial_mom_pp": _mom_delta("denial_rate_pct"),
            "acceptance_rate_pct": round(acceptance_rate, 2),
            "operating_margin_pct": round(operating_margin, 2),
            "margin_mom_pp": _mom_delta("operating_margin_pct"),
            "net_operating_surplus": round(net_surplus, 2),
            "surplus_mom_pct": _mom_delta("net_surplus", pct_change=True),
            "total_appealed": int(appeals_df["appealed_denials"].sum()) if not appeals_df.empty else 0,
            "total_overturned": int(appeals_df["overturned_denials"].sum()) if not appeals_df.empty else 0,
        },
        "monthly_trends": monthly_df.round(2).to_dict(orient="records"),
        "payer_denials": payer_df.sort_values("denied_claims", ascending=False).round(2).to_dict(orient="records"),
        "payer_denial_rates": payer_df.sort_values("denial_rate_pct", ascending=False).round(2).to_dict(orient="records"),
        "denial_reasons": reasons_df.round(2).to_dict(orient="records"),
        "appeals_monthly": appeals_df.round(2).to_dict(orient="records"),
        "forecast_q1_2026": forecast_series,
    }
