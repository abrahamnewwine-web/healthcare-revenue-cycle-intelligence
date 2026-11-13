-- Healthcare Revenue Cycle Intelligence - Core Production SQL Queries

-- 1. Executive KPI Summary by Department and Year
SELECT
    dep.department_name,
    d.year,
    SUM(v.visit_count) AS total_patient_visits,
    COUNT(c.claim_id) AS total_claims,
    ROUND(SUM(c.billed_amount), 2) AS total_billed,
    ROUND(SUM(c.paid_amount), 2) AS total_payments,
    ROUND(100.0 * SUM(c.paid_amount) / NULLIF(SUM(c.billed_amount), 0), 2) AS collection_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / NULLIF(COUNT(c.claim_id), 0), 2) AS denial_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Accepted' THEN 1 ELSE 0 END) / NULLIF(COUNT(c.claim_id), 0), 2) AS acceptance_rate_pct
FROM fact_claims c
JOIN dim_date d ON c.date_key = d.date_key
JOIN dim_department dep ON c.department_id = dep.department_id
JOIN (
    SELECT date_key, department_id, payer_id, SUM(visit_count) AS visit_count
    FROM fact_patient_visits
    GROUP BY date_key, department_id, payer_id
) v ON c.date_key = v.date_key AND c.department_id = v.department_id AND c.payer_id = v.payer_id
GROUP BY dep.department_name, d.year
ORDER BY total_billed DESC;

-- 2. Monthly Billed, Payments, Billing Gap & Collection Rate (2025)
SELECT
    d.year_month,
    ROUND(SUM(c.billed_amount), 2) AS billed_amount,
    ROUND(SUM(c.paid_amount), 2) AS total_payments,
    ROUND(SUM(c.billed_amount) - SUM(c.paid_amount), 2) AS billing_gap,
    ROUND(100.0 * SUM(c.paid_amount) / NULLIF(SUM(c.billed_amount), 0), 2) AS collection_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS denial_rate_pct
FROM fact_claims c
JOIN dim_date d ON c.date_key = d.date_key
GROUP BY d.year_month
ORDER BY d.year_month;

-- 3. Payer Performance, Denial Rates & Claims Share
SELECT
    p.payer_name,
    COUNT(*) AS total_claims,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS claims_share_pct,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS denial_rate_pct,
    ROUND(SUM(c.billed_amount), 2) AS billed_amount,
    ROUND(SUM(c.paid_amount), 2) AS paid_amount
FROM fact_claims c
JOIN dim_payer p ON c.payer_id = p.payer_id
GROUP BY p.payer_name
ORDER BY denial_rate_pct DESC;

-- 4. Top Denial Reasons & Appeals Overturn Performance
SELECT
    r.reason_name,
    r.reason_category,
    COUNT(*) AS denied_claim_count,
    ROUND(SUM(da.denied_amount), 2) AS total_denied_amount,
    SUM(da.appealed_flag) AS appealed_count,
    SUM(da.overturned_flag) AS overturned_count,
    ROUND(100.0 * SUM(da.overturned_flag) / NULLIF(SUM(da.appealed_flag), 0), 2) AS overturn_rate_pct
FROM fact_denials_appeals da
JOIN dim_denial_reason r ON da.reason_id = r.reason_id
GROUP BY r.reason_name, r.reason_category
ORDER BY denied_claim_count DESC;
