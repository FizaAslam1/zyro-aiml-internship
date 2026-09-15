"""
Week 3 - Step 7 & 8: Improved information extraction + missing-field handling.

Improvements over Week 2:
- Invoice Number: also matches "Invoice No", "Bill No", handles OCR confusion
  of 'l' -> '1' -> 'I' in the word "Invoice".
- Date: matches DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, and "Month DD, YYYY".
- Total: matches "Total", "Amount Due", "Grand Total", "Total Amount",
  with optional currency symbol/word BEFORE or AFTER the number, and
  tolerates thousands separators.
- Company Name: matches "Billed By", "From", "Company", trims trailing
  punctuation and stray whitespace, and rejects obviously bad matches
  (too short / just numbers).
- Resume Name: no longer blindly grabs the first line (which could be a
  page header like "RESUME" or "CURRICULUM VITAE") - it skips such lines.
- Email/Phone: unchanged pattern (already solid) but phone is validated
  to have a plausible digit count.
- Skills: stops at the next ALL-CAPS section header instead of grabbing
  everything to the end of the text.
- ALL fields: every field always returns a value + a boolean "found" flag,
  so the app can show "Not Found" without crashing (Step 8).
"""

import re

NOT_FOUND = "Not Found"


def _field(value, found):
    return {"value": value if found else NOT_FOUND, "found": found}


# ----------------------------------------------------------------------
# INVOICE
# ----------------------------------------------------------------------

def extract_invoice_fields(text: str) -> dict:
    fields = {}

    # Invoice Number — tolerate "Invoice No", "Invoice #", "Bill No", OCR 'l'->'I'
    inv_no = re.search(
        r"(?:[il]nvoice|bill)\s*(?:no\.?|number|#)?\s*[:\-]?\s*"
        r"([A-Za-z]{0,4}-?\d{3,6}[A-Za-z0-9\-\/]*)",
        text, re.IGNORECASE
    )
    fields["Invoice Number"] = _field(inv_no.group(1).strip() if inv_no else None, bool(inv_no))

    # Date — numeric formats + "Month DD, YYYY"
    date = re.search(
        r"\b(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})\b"
        r"|\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
        text, re.IGNORECASE
    )
    if date:
        date_val = date.group(1) or date.group(2)
    else:
        date_val = None
    fields["Date"] = _field(date_val, bool(date))

    # Total — currency symbol/word can appear before OR after the number.
    # \b before "total"/"amount" avoids accidentally matching inside "Subtotal".
    total = re.search(
        r"\b(?:total\s*amount\s*due|grand\s*total|amount\s*due|total)\b\s*[:\-]?\s*"
        r"((?:USD|PKR|Rs\.?|\$|€|£)?\s?[\d,]+\.?\d{0,2}\s?(?:USD|PKR)?)",
        text, re.IGNORECASE
    )
    fields["Total Amount"] = _field(total.group(1).strip() if total else None, bool(total))

    # Company Name — "Billed By" / "From" / "Company", reject junk matches
    company = re.search(
        r"(?:billed\s*by|from|company)\s*[:\-]?\s*([A-Za-z][A-Za-z0-9 &.,\-]{2,60})",
        text, re.IGNORECASE
    )
    company_val = None
    if company:
        candidate = company.group(1).strip().splitlines()[0].strip(" .,-")
        # reject if it's mostly digits (likely matched an address/number by mistake)
        if candidate and sum(c.isdigit() for c in candidate) < len(candidate) / 2:
            company_val = candidate
    fields["Company Name"] = _field(company_val, bool(company_val))

    return fields


# ----------------------------------------------------------------------
# RESUME
# ----------------------------------------------------------------------

_SECTION_HEADERS = {
    "resume", "curriculum vitae", "cv", "profile", "summary",
    "education", "experience", "work history", "academic background",
    "skills", "projects", "certifications", "contact",
}


def extract_resume_fields(text: str) -> dict:
    fields = {}

    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    fields["Email"] = _field(email.group(0) if email else None, bool(email))

    phone = re.search(
        r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text
    )
    phone_val = None
    if phone:
        digit_count = sum(c.isdigit() for c in phone.group(0))
        if digit_count >= 7:  # avoid matching short unrelated numbers
            phone_val = phone.group(0).strip()
    fields["Phone"] = _field(phone_val, bool(phone_val))

    # Name — first non-empty line that ISN'T a section header / label
    name_val = None
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln.lower().strip(":") in _SECTION_HEADERS:
            continue
        if re.match(r"^(email|phone|tel)\b", ln, re.IGNORECASE):
            continue
        name_val = ln
        break
    fields["Name"] = _field(name_val, bool(name_val))

    # Skills — stop at the next ALL-CAPS section header (not just end of text)
    skills_match = re.search(
        r"skills\s*[:\-]?\s*(.+?)(?:\n[A-Z][A-Z \-]{2,}\n|\Z)",
        text, re.IGNORECASE | re.DOTALL
    )
    skills_val = None
    if skills_match:
        skills_val = re.sub(r"\s+", " ", skills_match.group(1)).strip()[:200]
        if not skills_val:
            skills_val = None
    fields["Skills"] = _field(skills_val, bool(skills_val))

    return fields


def extract_fields(text: str, doc_type: str) -> dict:
    if doc_type == "Invoice":
        return extract_invoice_fields(text)
    elif doc_type == "Resume":
        return extract_resume_fields(text)
    return {}
