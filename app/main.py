"""FastAPI application for Healthcare Revenue Cycle Intelligence dashboard."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.analytics import FilterParams, get_dashboard_data, get_filter_options

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Healthcare Revenue Cycle Intelligence",
    description="Interactive executive BI dashboard and API for healthcare revenue cycle analytics.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    """Render the interactive executive BI dashboard."""
    options = get_filter_options()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"options": options},
    )


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "healthcare-revenue-cycle-intelligence"}


@app.get("/api/filters")
def api_filters() -> dict[str, object]:
    """Return available dashboard filter options."""
    return get_filter_options()


@app.get("/api/dashboard")
def api_dashboard(
    year: int | None = Query(default=None, ge=2020, le=2030),
    month: int | None = Query(default=None, ge=1, le=12),
    payer: str | None = Query(default=None),
    department: str | None = Query(default=None),
) -> dict[str, object]:
    """Return reconciled KPIs, trends, payer analytics, and Q1 2026 forecast."""
    options = get_filter_options()
    if payer and payer != "All" and payer not in options["payers"]:
        raise HTTPException(status_code=400, detail=f"Unknown insurance payer: {payer}")
    if department and department != "All" and department not in options["departments"]:
        raise HTTPException(status_code=400, detail=f"Unknown department: {department}")

    params = FilterParams(year=year, month=month, payer=payer, department=department)
    return get_dashboard_data(params)


@app.get("/api/export/monthly-csv")
def export_monthly_csv(
    year: int | None = Query(default=None, ge=2020, le=2030),
    month: int | None = Query(default=None, ge=1, le=12),
    payer: str | None = Query(default=None),
    department: str | None = Query(default=None),
) -> StreamingResponse:
    """Export filtered monthly KPI summary as CSV."""
    data = api_dashboard(year=year, month=month, payer=payer, department=department)
    rows = data["monthly_trends"]

    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buf.write("year_month,total_claims,denied_claims,billed_amount,total_payments\n")

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=healthcare_rcm_monthly_summary.csv"},
    )
