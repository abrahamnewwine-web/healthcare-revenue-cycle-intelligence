"""Generate genuine Excel RTM/UAT workbooks and ReportLab Executive PDF."""

from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.analytics import FilterParams, get_dashboard_data
from src.config import DOCS_BA_DIR

NAVY_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)


def _write_styled_sheet(
    wb: openpyxl.Workbook,
    title: str,
    headers: list[str],
    rows: list[list[object]],
    first_sheet: bool = False,
) -> None:
    ws = wb.active if first_sheet else wb.create_sheet(title=title)
    ws.title = title
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = NAVY_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=12)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 4, 14), 48)


def generate_rtm_workbook(out_path: Path) -> None:
    """Create Requirements Traceability Matrix (RTM) Excel workbook."""
    wb = openpyxl.Workbook()
    headers = [
        "Req ID",
        "Business Objective",
        "Requirement Description",
        "Priority",
        "Design Component",
        "Test Case ID",
        "Status",
    ]
    rows = [
        ["BR-001", "BO-01", "Consolidate patient visits, claims, payments, and costs into star schema", "High", "sql/schema.sql & src/pipeline.py", "TC-001", "Verified"],
        ["BR-002", "BO-01", "Display executive KPI summary cards with MoM deltas and sparklines", "High", "app/templates/index.html & src/analytics.py", "TC-002", "Verified"],
        ["BR-003", "BO-02", "Calculate Claims Acceptance Rate %, Denial Rate %, and Collection Rate %", "High", "src/analytics.py & powerbi/measures.dax", "TC-003", "Verified"],
        ["BR-004", "BO-02", "Compare claims denials and denial rates across 5 insurance payers", "High", "app/static/js/dashboard.js (Payer Charts)", "TC-004", "Verified"],
        ["BR-005", "BO-03", "Track monthly billed amounts, total payments, and billing gaps (Jan-Dec)", "High", "src/analytics.py (monthly_trends)", "TC-005", "Verified"],
        ["BR-006", "BO-04", "Classify and rank top claims denial reasons by volume and denied value", "Medium", "dim_denial_reason & fact_denials_appeals", "TC-006", "Verified"],
        ["BR-007", "BO-05", "Monitor monthly denial appeals vs. overturned claims and recovery", "Medium", "fact_denials_appeals & chartAppeals", "TC-007", "Verified"],
        ["BR-008", "BO-06", "Provide interactive Year, Month, Insurance Payer, and Department filters", "High", "app/main.py (/api/dashboard)", "TC-008", "Verified"],
        ["BR-009", "BO-07", "Produce Q1 2026 monthly revenue collection forecast with 95% CI", "Medium", "src/analytics.py (compute_q1_2026_forecast)", "TC-009", "Verified"],
        ["BR-010", "BO-06", "Export filtered monthly performance summary as CSV", "Low", "app/main.py (/api/export/monthly-csv)", "TC-010", "Verified"],
    ]
    _write_styled_sheet(wb, "RTM", headers, rows, first_sheet=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def generate_uat_workbook(out_path: Path) -> None:
    """Create UAT Test Cases & Defect Log Excel workbook."""
    wb = openpyxl.Workbook()
    tc_headers = [
        "Test ID",
        "Req ID",
        "Scenario",
        "Test Steps",
        "Expected Result",
        "Execution Result",
        "Automated Test",
    ]
    tc_rows = [
        ["TC-001", "BR-001", "ETL Warehouse Integrity", "Run pipeline.py and verify row counts and foreign keys", "All 7 tables populated with zero orphan keys", "Pass", "test_etl_pipeline_integrity"],
        ["TC-002", "BR-002", "KPI Card Accuracy (Oncology)", "Filter department=Oncology and inspect KPI cards", "6,000 visits, ~50K claims, ~13% denial rate, ~85.7% acceptance", "Pass", "test_oncology_kpis_reconcile"],
        ["TC-003", "BR-003", "KPI Formula Reconciliation", "Compare Acceptance + Denial + Pending shares", "Status proportions sum to exactly 100.0%", "Pass", "test_status_reconciliation"],
        ["TC-004", "BR-004", "Payer Comparison Validation", "Inspect payer denial rate ranking", "UnitedHealthcare exhibits highest denial rate (~17%)", "Pass", "test_payer_denial_ranking"],
        ["TC-005", "BR-005", "Monthly Billing Gap Math", "Check billed - payments == billing_gap across all months", "Exact equality across all 12 months", "Pass", "test_monthly_billing_gap_math"],
        ["TC-006", "BR-006", "Denial Reason Breakdown", "Verify top 6 denial reasons ordered descending", "Prior authorization & Coding lead denial counts", "Pass", "test_denial_reasons_populated"],
        ["TC-007", "BR-007", "Appeals & Overturns", "Verify overturned <= appealed <= denied_claims", "Logical subset invariant holds across filters", "Pass", "test_appeals_invariant"],
        ["TC-008", "BR-008", "Filter Validation & Error Handling", "Request valid and invalid payer/department query params", "HTTP 200 on valid filters; HTTP 400 on unknown values", "Pass", "test_api_filter_validation"],
        ["TC-009", "BR-009", "Q1 2026 Forecast Output", "Inspect forecast periods 2026-01 to 2026-03", "3 forecast periods returned with lower_95 <= pred <= upper_95", "Pass", "test_forecast_bounds"],
        ["TC-010", "BR-010", "CSV Export Endpoint", "GET /api/export/monthly-csv?department=Oncology", "HTTP 200 with valid CSV header and 12 monthly rows", "Pass", "test_csv_export"],
    ]
    _write_styled_sheet(wb, "UAT_Test_Cases", tc_headers, tc_rows, first_sheet=True)

    defect_headers = ["Defect ID", "Test ID", "Severity", "Description", "Resolution", "Status"]
    defect_rows = [
        ["DEF-001", "TC-002", "Minor", "Original reference layout spelled 'Surplus' as 'SUPLUS'", "Corrected label in app/templates/index.html", "Closed"],
        ["DEF-002", "TC-003", "Medium", "Ambiguity between Oncology slice and all-department totals", "Added explicit scope banner and quick All Depts reset", "Closed"],
    ]
    _write_styled_sheet(wb, "Defect_Log", defect_headers, defect_rows, first_sheet=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def generate_executive_pdf(out_path: Path) -> None:
    """Create a polished ReportLab Executive Insights PDF from reconciled SQLite metrics."""
    onc = get_dashboard_data(FilterParams(department="Oncology"))
    org = get_dashboard_data(FilterParams())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, title="Healthcare Revenue Cycle Executive Insights")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Healthcare Revenue Cycle Intelligence — Executive Insights & Recommendations", styles["Title"]),
        Paragraph("Prepared by Abraham Adetola, PMP®, PMI-PBA®, CSM®, CSPO® | Simulated Benchmark Analytical Report", styles["Italic"]),
        Spacer(1, 12),
        Paragraph("1. Reconciled Executive Summary", styles["Heading2"]),
        Paragraph(
            f"Across all five clinical departments in FY 2025, the analytical warehouse captures "
            f"{org['kpis']['total_patient_visits']:,} patient visits and {org['kpis']['total_claims']:,} claims, "
            f"generating ${org['kpis']['total_payments']:,.0f} in collections on ${org['kpis']['total_billed']:,.0f} billed "
            f"({org['kpis']['collection_rate_pct']:.1f}% collection rate; {org['kpis']['denial_rate_pct']:.1f}% denial rate). "
            f"Within the Oncology reference slice, {onc['kpis']['total_patient_visits']:,} visits generated "
            f"{onc['kpis']['total_claims']:,} claims with a {onc['kpis']['denial_rate_pct']:.1f}% denial rate and "
            f"{onc['kpis']['acceptance_rate_pct']:.1f}% acceptance rate.",
            styles["BodyText"],
        ),
        Spacer(1, 10),
        Paragraph("2. Key Findings & Payer Exposure (Oncology Reference View)", styles["Heading2"]),
    ]

    table_data = [["Insurance Payer", "Total Claims", "Claims Share %", "Denial Rate %"]]
    for row in onc["payer_denial_rates"]:
        table_data.append(
            [
                row["payer_name"],
                f"{int(row['total_claims']):,}",
                f"{row['claims_share_pct']:.2f}%",
                f"{row['denial_rate_pct']:.2f}%",
            ]
        )

    tbl = Table(table_data, colWidths=[180, 95, 105, 105])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.extend(
        [
            tbl,
            Spacer(1, 12),
            Paragraph("3. Strategic Recommendations", styles["Heading2"]),
            Paragraph(
                "• Prioritize pre-service prior authorization automation for commercial payers with elevated denial rates (notably UnitedHealthcare).<br/>"
                "• Implement mid-cycle coding/documentation audits targeting top denial categories.<br/>"
                "• Standardize appeal escalation workflows and track Q1 2026 forecast variance monthly.",
                styles["BodyText"],
            ),
        ]
    )
    doc.build(story)


def generate_all_ba_artifacts() -> None:
    """Generate Excel RTM, UAT workbook, and Executive Insights PDF."""
    generate_rtm_workbook(DOCS_BA_DIR / "rtm_workbook.xlsx")
    generate_uat_workbook(DOCS_BA_DIR / "uat_test_log.xlsx")
    generate_executive_pdf(DOCS_BA_DIR / "executive_insights_report.pdf")
