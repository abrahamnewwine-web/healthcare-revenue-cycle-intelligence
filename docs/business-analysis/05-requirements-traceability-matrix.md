# Requirements Traceability Matrix (RTM) — Healthcare Revenue Cycle Intelligence

*(Machine-readable spreadsheet also generated at [`rtm_workbook.xlsx`](./rtm_workbook.xlsx))*

| Req ID | Objective | Requirement Summary | Design / Code Artifact | Test Case ID | Verification Method |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BR-001` | `BO-01` | Star schema warehouse (`SQLite` + CSV) | `sql/schema.sql`, `src/pipeline.py` | `TC-001` | Automated ETL integrity test |
| `BR-002` | `BO-01` | Executive KPI cards with MoM deltas & sparklines | `app/templates/index.html`, `src/analytics.py` | `TC-002` | Oncology & All-Dept reconciliation |
| `BR-003` | `BO-02` | Acceptance, Denial, Collection, Operating Margin KPIs | `src/analytics.py`, `powerbi/measures.dax` | `TC-003` | Claim status partition invariant |
| `BR-004` | `BO-02` | Payer denial counts, rates, and claims share | `src/analytics.py`, `app/static/js/dashboard.js` | `TC-004` | Payer ranking & 100% share check |
| `BR-005` | `BO-03` | Monthly billed, collected, and billing gap | `sql/analytics_queries.sql`, `src/analytics.py` | `TC-005` | `Billed - Paid == Gap` assertion |
| `BR-006` | `BO-04` | Denial reason classification (top 6 categories) | `dim_denial_reason`, `fact_denials_appeals` | `TC-006` | Reason ordering & sum validation |
| `BR-007` | `BO-05` | Monthly appeals vs. overturned recoveries | `fact_denials_appeals`, `chartAppeals` | `TC-007` | Subset invariant test |
| `BR-008` | `BO-06` | Interactive Year, Month, Payer, Department slicers | `app/main.py` (`/api/dashboard`) | `TC-008` | API valid/invalid filter tests |
| `BR-009` | `BO-07` | Q1 2026 collection forecast with 95% CI | `compute_q1_2026_forecast` | `TC-009` | Confidence bound monotonicity test |
| `BR-010` | `BO-06` | Filtered monthly CSV export | `app/main.py` (`/api/export/monthly-csv`) | `TC-010` | HTTP CSV header & row validation |
