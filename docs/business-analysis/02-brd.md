# Business Requirements Document (BRD) — Healthcare Revenue Cycle Intelligence

**Document ID:** HRCI-BRD-001 | **Version:** 1.0 | **Author:** Abraham Adetola

## 1. Functional Requirements
| Req ID | Requirement | Priority | Acceptance Standard |
| :--- | :--- | :--- | :--- |
| `BR-001` | Consolidate visit, claim, payment, cost, and denial/appeal records into a star schema warehouse (`SQLite` + CSV). | High | All dimension and fact tables load cleanly with zero orphan foreign keys. |
| `BR-002` | Provide executive KPI cards (Visits, Collection %, Denial %, Operating Margin %, Net Surplus, Acceptance Gauge) with MoM deltas. | High | Cards reconcile directly against SQL queries and DAX measures. |
| `BR-003` | Support interactive slicing by `Year`, `Month`, `Insurance Payer`, and `Department` (including Oncology preset & All-Department reset). | High | All 9 charts and 6 KPI cards update consistently on filter change. |
| `BR-004` | Display payer-level denial counts, denial rates, and total claims share distribution across 5 major payers. | High | Payer shares sum to 100%; denial rates match `Denied / Total`. |
| `BR-005` | Rank top 6 claims denial reasons (`Prior authorization`, `Coding / documentation`, `Eligibility / coverage`, `Duplicate claim`, `Timely filing`, `Other payer policy`). | Medium | Ordered descending by denial volume with dollar impact tracked. |
| `BR-006` | Track monthly billed vs. collected amounts, billing gaps, and appeals vs. overturned recoveries. | High | `Billing Gap = Billed - Paid` across every monthly interval. |
| `BR-007` | Generate Q1 2026 (Jan–Mar) monthly collection forecast with 95% prediction confidence intervals. | Medium | `lower_95 <= forecast <= upper_95` and assumptions documented. |
| `BR-008` | Support filtered CSV export and input validation with clear HTTP error handling on unknown filter values. | Medium | Invalid filter inputs return HTTP 400; CSV export downloads cleanly. |

## 2. Non-Functional Requirements
- **Data Integrity:** `Accepted + Denied + Pending = 100%` of claims in every filter slice.
- **Clarity of Scope:** Explicitly differentiate department-filtered reference views (e.g., Oncology) from organization-wide totals.
- **Reproducibility:** Deterministic ETL pipeline (`RANDOM_SEED = 20250101`) ensures repeatable verification across environments.
