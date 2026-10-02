"""
validator.py
Advanced document validation (Week 5).

Required fields
    Invoice: Invoice Number, Date, Company Name, Total Amount
    Resume : Name, Email, Skills            (Phone is optional -> warning only)

Every check returns None when OK, or a short human-readable reason.
`validate_document` records EXACTLY which fields failed and why.
"""

import re
from datetime import datetime

NOT_FOUND = "Not Found"

REQUIRED_FIELDS = {
    "Invoice": ["Invoice Number", "Date", "Company Name", "Total Amount"],
    "Resume": ["Name", "Email", "Skills"],
}
OPTIONAL_FIELDS = {
    "Invoice": [],
    "Resume": ["Phone"],
}


def is_missing(value) -> bool:
    return value is None or str(value).strip() in ("", NOT_FOUND)


# ----------------------------------------------------------------------
# Individual format checks
# ----------------------------------------------------------------------

def check_invoice_number(v: str):
    v = v.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-/#_]{2,29}", v):
        return "not a valid invoice number format"
    if not any(c.isdigit() for c in v):
        return "must contain at least one digit"
    return None


def check_date(v: str):
    parts = re.split(r"[/\-.]", v.strip())
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return "unrecognised date format"
    a, b, y = (int(p) for p in parts)
    if y < 100:
        y += 2000
    if not (1990 <= y <= datetime.now().year + 1):
        return "year is out of range"
    for day, month in ((a, b), (b, a)):  # accept DD/MM and MM/DD
        try:
            datetime(y, month, day)
            return None
        except ValueError:
            continue
    return "not a real calendar date"


def check_amount(v: str):
    cleaned = re.sub(r"(?i)usd|pkr|rs\.?|[$€£,\s]", "", v)
    try:
        amount = float(cleaned)
    except ValueError:
        return "not a valid number"
    if amount <= 0:
        return "must be greater than zero"
    return None


def check_company(v: str):
    v = v.strip()
    letters = sum(c.isalpha() for c in v)
    digits = sum(c.isdigit() for c in v)
    if len(v) < 2 or len(v) > 80 or letters < 2 or digits > len(v) / 2:
        return "does not look like a company name"
    return None


def check_email(v: str):
    if not re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", v.strip()):
        return "not a valid email address"
    return None


def check_phone(v: str):
    digits = re.sub(r"\D", "", v)
    if not re.fullmatch(r"\+?[\d\s\-().]+", v.strip()) or not 7 <= len(digits) <= 15:
        return "not a valid phone number (7-15 digits expected)"
    return None


def check_name(v: str):
    v = v.strip()
    if len(v) > 50 or len(v.split()) > 5:
        return "too long to be a name (extraction probably captured a whole line)"
    if re.search(r"[\d@|]", v):
        return "contains digits or symbols"
    return None


def check_skills(v: str):
    return None if len(v.strip()) >= 3 else "too short to be a skills list"


CHECKS = {
    "Invoice Number": check_invoice_number,
    "Date": check_date,
    "Total Amount": check_amount,
    "Company Name": check_company,
    "Email": check_email,
    "Phone": check_phone,
    "Name": check_name,
    "Skills": check_skills,
}


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def validate_document(doc_type: str, fields: dict) -> dict:
    """
    Returns:
        valid          - True if no required field is missing/invalid
        missing        - required fields that were not found
        invalid        - {field: reason} required fields with a bad format
        warnings       - {field: reason} optional fields with a bad format
        failed_fields  - missing + invalid field names
        results        - {field: "OK" | "Missing" | "Invalid: ..." | "Warning: ..." | ...}
    """
    missing, invalid, warnings, results = [], {}, {}, {}

    for name in REQUIRED_FIELDS.get(doc_type, []):
        value = fields.get(name)
        if is_missing(value):
            missing.append(name)
            results[name] = "Missing"
            continue
        error = CHECKS[name](str(value))
        if error:
            invalid[name] = error
            results[name] = f"Invalid: {error}"
        else:
            results[name] = "OK"

    for name in OPTIONAL_FIELDS.get(doc_type, []):
        value = fields.get(name)
        if is_missing(value):
            results[name] = "Not provided (optional)"
            continue
        error = CHECKS[name](str(value))
        if error:
            warnings[name] = error
            results[name] = f"Warning: {error}"
        else:
            results[name] = "OK"

    return {
        "valid": not missing and not invalid,
        "missing": missing,
        "invalid": invalid,
        "warnings": warnings,
        "failed_fields": missing + list(invalid),
        "results": results,
    }
