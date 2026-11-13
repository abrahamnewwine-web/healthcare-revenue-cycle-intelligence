"""Automated functional, reconciliation, and API tests for Healthcare RCM."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.analytics import FilterParams, get_dashboard_data, get_filter_options
from src.ba_artifacts import generate_all_ba_artifacts
from src.config import DB_PATH, DOCS_BA_DIR
from src.pipeline import run_pipeline

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_warehouse() -> None:
    run_pipeline()
    if not (DOCS_BA_DIR / "rtm_workbook.xlsx").exists():
        generate_all_ba_artifacts()


def test_etl_pipeline_integrity() -> None:
    assert DB_PATH.exists()
    with sqlite3.connect(DB_PATH) as conn:
        orphans = conn.execute(
            """
            SELECT COUNT(*) FROM fact_claims c
            LEFT JOIN fact_patient_visits v ON c.visit_id = v.visit_id
            WHERE v.visit_id IS NULL
            """
        ).fetchone()[0]
        assert orphans == 0

        bad_denials = conn.execute(
            """
            SELECT COUNT(*) FROM fact_denials_appeals da
            LEFT JOIN fact_claims c ON da.claim_id = c.claim_id
            WHERE c.claim_id IS NULL OR c.claim_status != 'Denied'
            """
        ).fetchone()[0]
        assert bad_denials == 0


def test_oncology_kpis_reconcile() -> None:
    data = get_dashboard_data(FilterParams(department="Oncology"))
    k = data["kpis"]
    assert k["total_patient_visits"] == 6000
    assert 49000 <= k["total_claims"] <= 51000
    assert 37.0 <= k["collection_rate_pct"] <= 43.0
    assert 12.0 <= k["denial_rate_pct"] <= 14.0
    assert 84.0 <= k["acceptance_rate_pct"] <= 87.5
    assert k["operating_margin_pct"] >= 95.0


def test_status_reconciliation() -> None:
    for dept in ["All", "Oncology", "Cardiology", "Emergency"]:
        k = get_dashboard_data(FilterParams(department=dept))["kpis"]
        assert (
            k["accepted_claims"] + k["denied_claims"] + k["pending_claims"]
            == k["total_claims"]
        )


def test_payer_denial_ranking_and_share() -> None:
    data = get_dashboard_data(FilterParams(department="Oncology"))
    rates = data["payer_denial_rates"]
    assert rates[0]["payer_name"] == "UnitedHealthcare"
    assert rates[0]["denial_rate_pct"] >= 16.0
    total_share = sum(r["claims_share_pct"] for r in rates)
    assert pytest.approx(total_share, abs=0.2) == 100.0


def test_monthly_billing_gap_math() -> None:
    data = get_dashboard_data(FilterParams())
    assert len(data["monthly_trends"]) == 12
    for row in data["monthly_trends"]:
        assert pytest.approx(row["billed_amount"] - row["total_payments"], abs=0.05) == row["billing_gap"]


def test_denial_reasons_and_appeals_invariant() -> None:
    data = get_dashboard_data(FilterParams())
    reasons = data["denial_reasons"]
    assert len(reasons) == 6
    assert reasons[0]["denial_count"] >= reasons[-1]["denial_count"]
    k = data["kpis"]
    assert 0 <= k["total_overturned"] <= k["total_appealed"] <= k["denied_claims"]


def test_forecast_bounds() -> None:
    fc = get_dashboard_data(FilterParams(department="Oncology"))["forecast_q1_2026"]
    q1_2026 = [r for r in fc if r["period"].startswith("2026-")]
    assert [r["period"] for r in q1_2026] == ["2026-01", "2026-02", "2026-03"]
    for r in q1_2026:
        assert r["lower_95"] <= r["forecast_payments"] <= r["upper_95"]


def test_api_endpoints_and_validation() -> None:
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 200

    opts = get_filter_options()
    assert "Oncology" in opts["departments"]

    res_ok = client.get("/api/dashboard?year=2025&department=Oncology")
    assert res_ok.status_code == 200
    assert res_ok.json()["kpis"]["total_patient_visits"] == 6000

    res_bad_payer = client.get("/api/dashboard?payer=UnknownCorp")
    assert res_bad_payer.status_code == 400

    res_bad_dept = client.get("/api/dashboard?department=NonExistent")
    assert res_bad_dept.status_code == 400

    res_csv = client.get("/api/export/monthly-csv?department=Oncology")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    lines = res_csv.text.strip().splitlines()
    assert len(lines) == 13  # header + 12 months


def test_ba_deliverables_generated() -> None:
    assert (DOCS_BA_DIR / "rtm_workbook.xlsx").exists()
    assert (DOCS_BA_DIR / "uat_test_log.xlsx").exists()
    assert (DOCS_BA_DIR / "executive_insights_report.pdf").exists()
