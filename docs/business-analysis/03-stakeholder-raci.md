# Stakeholder Analysis & RACI Matrix — Healthcare Revenue Cycle Intelligence

**Document ID:** HRCI-STAKE-001

## 1. Stakeholder Register
| Stakeholder Role | Key Business Interest | Engagement Strategy |
| :--- | :--- | :--- |
| **CFO / Finance Leadership** | Financial sustainability, collection rate, operating surplus, Q1 2026 forecast | Executive summary reviews & KPI validation |
| **Revenue Cycle Manager** | End-to-end claims velocity, denial exposure, payer SLA adherence | Weekly operational KPI governance |
| **Billing & Claims Team** | Clean claim submission, billing-to-collection lag reduction | Training on denial category insights |
| **Denial Management Team** | Appeal volume, overturn conversion rates, root-cause remediation | Targeted payer & reason drilldowns |
| **Department Managers (e.g., Oncology)** | Service-line revenue performance and operational margin | Department-filtered dashboard views |
| **Business Analyst (Abraham Adetola)** | Requirements elicitation, BRD/RTM, AS-IS/TO-BE design, UAT governance | End-to-end BA lifecycle ownership |
| **BI / Data Engineering Team** | ETL integrity, star schema modeling, DAX/SQL parity, performance | Technical implementation & QA |

## 2. RACI Matrix
*(R = Responsible, A = Accountable, C = Consulted, I = Informed)*

| Activity | CFO | RCM Mgr | Billing/Denials | Dept Mgr | Business Analyst | BI Engineer |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Define KPI Dictionary & Scope | A | C | C | I | **R** | C |
| Requirements Elicitation & BRD | I | C | C | C | **R/A** | C |
| Data Modeling & ETL Pipeline | I | C | I | I | C | **R/A** |
| Dashboard Build & DAX Alignment | I | C | C | I | C | **R/A** |
| UAT Planning & Execution | I | **A** | C | C | **R** | C |
| Executive Insight Sign-off | **A** | **R** | I | I | **R** | I |
