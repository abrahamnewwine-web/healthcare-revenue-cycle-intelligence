"""Configuration and domain metadata for Healthcare Revenue Cycle Intelligence."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
SQL_DIR = BASE_DIR / "sql"
DOCS_BA_DIR = BASE_DIR / "docs" / "business-analysis"
SCREENSHOTS_DIR = BASE_DIR / "assets" / "screenshots"
DB_PATH = DATA_PROCESSED_DIR / "healthcare_rcm.db"

RANDOM_SEED = 20250101

PAYERS = [
    (1, "Blue Cross Blue Shield", "Commercial"),
    (2, "UnitedHealthcare", "Commercial"),
    (3, "Medicare", "Government"),
    (4, "Aetna", "Commercial"),
    (5, "Medicaid", "Government"),
]

DEPARTMENTS = [
    (1, "Oncology", "Specialty Care"),
    (2, "Cardiology", "Specialty Care"),
    (3, "Orthopedics", "Surgical"),
    (4, "General Medicine", "Primary & Inpatient"),
    (5, "Emergency", "Acute Care"),
]

DENIAL_REASONS = [
    (1, "Prior authorization", "Pre-Service"),
    (2, "Coding / documentation", "Mid-Cycle"),
    (3, "Eligibility / coverage", "Front-End"),
    (4, "Duplicate claim", "Billing Hygiene"),
    (5, "Timely filing", "Compliance"),
    (6, "Other payer policy", "Adjudication"),
]
