# UAT Test Plan, Test Cases & Defect Log — Healthcare Revenue Cycle Intelligence

*(Machine-readable Excel workbook generated at [`uat_test_log.xlsx`](./uat_test_log.xlsx))*

## 1. UAT Scope & Strategy
User Acceptance Testing validates star schema reconciliation, interactive filter behavior, HTTP error handling, forecast boundary invariants, and CSV export accuracy via automated `pytest` verification and live browser rendering checks.

## 2. Test Case Summary
| Test ID | Req ID | Description | Expected Outcome | Status |
| :--- | :--- | :--- | :--- | :--- |
| `TC-001` | `BR-001` | Star schema ETL load & FK integrity | All 7 tables populated; zero orphan records | Pass |
| `TC-002` | `BR-002` | Oncology KPI accuracy check | 6,000 visits, ~50K claims, ~13% denial, ~85.7% acceptance | Pass |
| `TC-003` | `BR-003` | Claims status partition reconciliation | `Accepted + Denied + Pending == Total Claims` | Pass |
| `TC-004` | `BR-004` | Payer denial ranking | UnitedHealthcare exhibits highest denial rate (~17%) | Pass |
| `TC-005` | `BR-005` | Monthly billing gap reconciliation | `Billed - Paid == Billing Gap` for all months | Pass |
| `TC-006` | `BR-006` | Top 6 denial reasons ordering | Sorted descending; non-zero counts | Pass |
| `TC-007` | `BR-007` | Appeals subset invariant | `Overturned <= Appealed <= Denied` | Pass |
| `TC-008` | `BR-008` | API filter input validation | Valid returns 200; unknown payer/dept returns 400 | Pass |
| `TC-009` | `BR-009` | Q1 2026 forecast generation | 3 forecast months with `lower_95 <= pred <= upper_95` | Pass |
| `TC-010` | `BR-010` | Filtered CSV export | Returns HTTP 200 `text/csv` attachment | Pass |

## 3. Defect Log
| Defect ID | Severity | Issue Identified | Resolution | Status |
| :--- | :--- | :--- | :--- | :--- |
| `DEF-001` | Minor | Reference dashboard mockup spelled "Surplus" as "SUPLUS" | Corrected label in web UI and documentation | Closed |
| `DEF-002` | Medium | Oncology-filtered numbers risked misinterpretation as whole-hospital totals | Added explicit Scope pill banner and "All Depts" reset toggle | Closed |
