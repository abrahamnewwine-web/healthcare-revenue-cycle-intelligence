# Agile Epics, Features, User Stories & Acceptance Criteria

**Project:** Healthcare Revenue Cycle Intelligence | **Methodology:** Scrum / Iterative Delivery

## Epic 1: Governed Revenue Cycle Data Warehouse
- **Feature 1.1:** Star Schema ETL & Validation
  - **Story US-101:** *As a BI Engineer, I want patient visits, claims, payments, and denial appeals normalized into a SQLite star schema so all KPIs share one source of truth.*
  - **Acceptance Criteria:** Foreign key constraints pass with zero orphans; CSV and SQLite tables export cleanly.

## Epic 2: Executive Performance & Payer Risk Dashboard
- **Feature 2.1:** Executive KPI Strip & Acceptance Gauge
  - **Story US-201:** *As a CFO, I want to view Patient Visits, Collection Rate %, Denial Rate %, Operating Margin %, Net Surplus, and Acceptance Rate % in one view so I can assess financial health rapidly.*
  - **Acceptance Criteria:** All 6 KPIs update dynamically when Year, Month, Payer, or Department filters change; Oncology filter scope is clearly displayed.
- **Feature 2.2:** Payer & Denial Root-Cause Analytics
  - **Story US-202:** *As a Denial Management Lead, I want claims denials and denial rates ranked by insurance payer and denial category so I can target high-leakage payers like UnitedHealthcare.*
  - **Acceptance Criteria:** Payer denial rates reconcile to `Denied Claims / Total Claims` and denial reasons sort descending.

## Epic 3: Appeals Tracking & Q1 2026 Forecasting
- **Feature 3.1:** Appeals Recovery & Forecast Modeling
  - **Story US-301:** *As a Revenue Cycle Director, I want monthly appeals vs. overturned claims plus a Q1 2026 collection forecast with 95% confidence bounds so I can plan staffing and cash flow.*
  - **Acceptance Criteria:** Forecast spans Jan–Mar 2026 with `lower_95 <= forecast <= upper_95`.
