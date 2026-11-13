# Power BI Star Schema Data Model — Healthcare Revenue Cycle Intelligence

## Architecture Overview

The analytical model uses a 4-dimension, 3-fact star/constellation schema built from `data/processed/*.csv` or `data/processed/healthcare_rcm.db` (`SQLite` ODBC/Python connector).

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_PATIENT_VISITS : "date_key"
    DIM_DATE ||--o{ FACT_CLAIMS : "date_key"
    DIM_DATE ||--o{ FACT_DENIALS_APPEALS : "date_key"
    DIM_DEPARTMENT ||--o{ FACT_PATIENT_VISITS : "department_id"
    DIM_DEPARTMENT ||--o{ FACT_CLAIMS : "department_id"
    DIM_DEPARTMENT ||--o{ FACT_DENIALS_APPEALS : "department_id"
    DIM_PAYER ||--o{ FACT_PATIENT_VISITS : "payer_id"
    DIM_PAYER ||--o{ FACT_CLAIMS : "payer_id"
    DIM_PAYER ||--o{ FACT_DENIALS_APPEALS : "payer_id"
    DIM_DENIAL_REASON ||--o{ FACT_DENIALS_APPEALS : "reason_id"
    FACT_PATIENT_VISITS ||--o{ FACT_CLAIMS : "visit_id"
    FACT_CLAIMS ||--o| FACT_DENIALS_APPEALS : "claim_id"

    DIM_DATE {
        int date_key PK
        date full_date
        int year
        int quarter
        int month_num
        string month_name
        string year_month
    }
    DIM_DEPARTMENT {
        int department_id PK
        string department_name
        string service_line
    }
    DIM_PAYER {
        int payer_id PK
        string payer_name
        string payer_type
    }
    DIM_DENIAL_REASON {
        int reason_id PK
        string reason_name
        string reason_category
    }
    FACT_PATIENT_VISITS {
        int visit_id PK
        int date_key FK
        int department_id FK
        int payer_id FK
        int visit_count
        float operating_cost
    }
    FACT_CLAIMS {
        int claim_id PK
        int visit_id FK
        int date_key FK
        int department_id FK
        int payer_id FK
        string claim_status
        float billed_amount
        float paid_amount
    }
    FACT_DENIALS_APPEALS {
        int denial_id PK
        int claim_id FK
        int date_key FK
        int department_id FK
        int payer_id FK
        int reason_id FK
        float denied_amount
        int appealed_flag
        int overturned_flag
        float recovered_amount
    }
```

## Relationships & Cardinality

| From Table (Many) | To Table (One) | Join Key | Cardinality | Cross-Filter Direction |
| :--- | :--- | :--- | :--- | :--- |
| `fact_patient_visits` | `dim_date` | `date_key` | Many-to-One (`*:1`) | Single |
| `fact_patient_visits` | `dim_department` | `department_id` | Many-to-One (`*:1`) | Single |
| `fact_patient_visits` | `dim_payer` | `payer_id` | Many-to-One (`*:1`) | Single |
| `fact_claims` | `dim_date` | `date_key` | Many-to-One (`*:1`) | Single |
| `fact_claims` | `dim_department` | `department_id` | Many-to-One (`*:1`) | Single |
| `fact_claims` | `dim_payer` | `payer_id` | Many-to-One (`*:1`) | Single |
| `fact_denials_appeals` | `dim_date` | `date_key` | Many-to-One (`*:1`) | Single |
| `fact_denials_appeals` | `dim_department` | `department_id` | Many-to-One (`*:1`) | Single |
| `fact_denials_appeals` | `dim_payer` | `payer_id` | Many-to-One (`*:1`) | Single |
| `fact_denials_appeals` | `dim_denial_reason` | `reason_id` | Many-to-One (`*:1`) | Single |
