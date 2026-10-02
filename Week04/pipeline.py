"""
pipeline.py
Document processing pipeline (no Streamlit code).

The read / clean / classify / extract / store functions are the SAME ones that
were in Week 4's app.py - moved here so the UI file only contains UI code and
so the pipeline can be tested without Streamlit.

New in Week 5: process_upload(), run_workflow(), evaluate_document(), run_batch()
which connect the pipeline to workflow.py, validator.py and audit.py.
"""

import os
import re
import io
import uuid
import hashlib
import functools
import json
from datetime import datetime
from time import perf_counter

import numpy as np
import pymupdf as fitz  # PyMuPDF
from PIL import Image

import audit
import database as db
import validator
import workflow

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE_MB = 10
STORAGE_ROOT = "storage"
FOLDERS = {
    "Invoice": os.path.join(STORAGE_ROOT, "invoices"),
    "Resume": os.path.join(STORAGE_ROOT, "resumes"),
    "Other": os.path.join(STORAGE_ROOT, "others"),
}


def ensure_folders():
    for folder in FOLDERS.values():
        os.makedirs(folder, exist_ok=True)


@functools.lru_cache(maxsize=1)
def get_ocr_reader():
    import easyocr  # imported lazily so tests / non-OCR paths don't need it
    return easyocr.Reader(["en"], gpu=False)


# ----------------------------------------------------------------------
# VALIDATE FILE + HASH
# ----------------------------------------------------------------------

def validate_file(uploaded_file) -> str:
    """Returns an error message string, or '' if the file is valid."""
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type: .{ext}. Allowed: PDF, JPG, JPEG, PNG."

    size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return f"File is too large ({size_mb:.1f} MB). Max allowed is {MAX_FILE_SIZE_MB} MB."

    return ""


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ----------------------------------------------------------------------
# READ TEXT (PDF / OCR)
# ----------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()


def extract_text_with_ocr_from_pdf(file_bytes: bytes) -> str:
    reader = get_ocr_reader()
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            result = reader.readtext(np.array(img), detail=0)
            text += " ".join(result) + "\n"
    return text.strip()


def extract_text_from_image(file_bytes: bytes) -> str:
    reader = get_ocr_reader()
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    result = reader.readtext(np.array(img), detail=0)
    return " ".join(result).strip()


def read_document_text(file_bytes: bytes, ext: str) -> tuple[str, str]:
    """Returns (text, method_used). Never raises - returns ('', 'Failed: ...') on error."""
    try:
        if ext == "pdf":
            text = extract_text_from_pdf(file_bytes)
            if len(text) > 20:
                return text, "PyMuPDF (text layer)"
            text = extract_text_with_ocr_from_pdf(file_bytes)
            return text, "OCR (scanned PDF)"
        else:
            text = extract_text_from_image(file_bytes)
            return text, "OCR (image)"
    except Exception as e:
        return "", f"Failed: {e}"


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = raw_text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()


# ----------------------------------------------------------------------
# CLASSIFY (rule-based - returns NO confidence score)
# ----------------------------------------------------------------------

def detect_document_type(text: str) -> str:
    lower_text = text.lower()
    invoice_keywords = ["invoice", "total", "invoice number", "bill to", "amount due"]
    resume_keywords = ["resume", "skills", "education", "experience", "curriculum vitae"]

    invoice_score = sum(1 for kw in invoice_keywords if kw in lower_text)
    resume_score = sum(1 for kw in resume_keywords if kw in lower_text)

    if invoice_score == 0 and resume_score == 0:
        return "Other"
    return "Invoice" if invoice_score >= resume_score else "Resume"


# ----------------------------------------------------------------------
# EXTRACT FIELDS (regex-based)
# ----------------------------------------------------------------------

def extract_invoice_fields(text: str) -> dict:
    fields = {}

    invoice_no = re.search(r"(invoice\s*(no|number|#)?\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
                            text, re.IGNORECASE)
    fields["Invoice Number"] = invoice_no.group(3) if invoice_no else "Not Found"

    date = re.search(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b", text)
    fields["Date"] = date.group(1) if date else "Not Found"

    total = re.search(
        r"(total|amount due|grand total)\s*[:\-]?\s*"
        r"([A-Za-z]{0,4}\s?[\$\€\£]?\s?[\d,]+\.?\d{0,2})",
        text, re.IGNORECASE
    )
    fields["Total Amount"] = total.group(2).strip() if total else "Not Found"

    company = re.search(r"(company|from|billed by)\s*[:\-]?\s*([A-Za-z0-9 &.,\-]+)",
                         text, re.IGNORECASE)
    fields["Company Name"] = company.group(2).strip() if company else "Not Found"

    return fields


def extract_resume_fields(text: str) -> dict:
    fields = {}

    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    fields["Email"] = email.group(0) if email else "Not Found"

    phone = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text)
    fields["Phone"] = phone.group(0) if phone else "Not Found"

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    fields["Name"] = lines[0] if lines else "Not Found"

    skills_match = re.search(r"skills\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
    fields["Skills"] = skills_match.group(1).strip()[:200] if skills_match else "Not Found"

    return fields


def extract_fields(text: str, doc_type: str) -> dict:
    if doc_type == "Invoice":
        return extract_invoice_fields(text)
    elif doc_type == "Resume":
        return extract_resume_fields(text)
    return {}


# ----------------------------------------------------------------------
# STORE FILE
# ----------------------------------------------------------------------

def store_file(file_bytes: bytes, original_filename: str, doc_type: str) -> tuple[str, str]:
    """Saves the file into the right folder with a safe generated name.
    Returns (stored_filename, file_path)."""
    ext = original_filename.split(".")[-1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    folder = FOLDERS.get(doc_type, FOLDERS["Other"])
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, stored_filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return stored_filename, file_path


# ----------------------------------------------------------------------
# WEEK 5: ANALYSE -> EVALUATE (validate + rules + state change)
# ----------------------------------------------------------------------

def _failed_analysis(method: str, seconds: float) -> dict:
    return {"failed": True, "method": method, "text": "", "doc_type": "Other",
            "fields": {}, "confidence": None, "seconds": seconds}


def analyse_document(file_bytes: bytes, ext: str) -> dict:
    """Read -> clean -> classify -> extract. Never raises."""
    t0 = perf_counter()
    raw_text, method = read_document_text(file_bytes, ext)
    if raw_text == "":
        if not method.startswith("Failed"):
            method = f"{method}: no readable text found"
        return _failed_analysis(method, perf_counter() - t0)

    cleaned = clean_text(raw_text)
    doc_type = detect_document_type(cleaned)
    fields = extract_fields(cleaned, doc_type)
    return {
        "failed": False, "method": method, "text": cleaned, "doc_type": doc_type,
        "fields": fields,
        "confidence": None,   # the rule-based classifier provides none - never invented
        "seconds": perf_counter() - t0,
    }


def evaluate_document(doc_id: int, analysis: dict) -> dict:
    """
    Run one document through: Processing -> Validate -> Apply Rules ->
    Needs Review / Completed (or Failed). Every state change is audited.
    Returns {"doc_id", "status", "reason"}.
    """
    workflow.transition(doc_id, workflow.PROCESSING, "Processing started")

    try:
        if analysis["failed"]:
            reason = analysis["method"]
            db.update_document(doc_id, {
                "extraction_method": analysis["method"],
                "review_reason": reason,
                "processing_seconds": analysis["seconds"],
            })
            workflow.transition(doc_id, workflow.FAILED, "Processing failed", reason)
            return {"doc_id": doc_id, "status": workflow.FAILED, "reason": reason}

        fields = analysis["fields"]
        validation = validator.validate_document(analysis["doc_type"], fields)
        decision = workflow.decide(analysis["doc_type"], validation, analysis["confidence"])

        db.update_document(doc_id, {
            "document_type": analysis["doc_type"],
            "predicted_type": analysis["doc_type"],
            "confidence": analysis["confidence"],
            "company": fields.get("Company Name", ""),
            "invoice_number": fields.get("Invoice Number", ""),
            "total_amount": fields.get("Total Amount", ""),
            "text_preview": analysis["text"][:300],
            "fields_json": json.dumps(fields),
            "validation_json": json.dumps(validation),
            "review_reason": decision.reason if decision.action == "needs_review" else None,
            "extraction_method": analysis["method"],
            "processing_seconds": analysis["seconds"],
        })

        if decision.action == "needs_review":
            workflow.transition(doc_id, workflow.NEEDS_REVIEW,
                                "Sent to human review", decision.reason)
            return {"doc_id": doc_id, "status": workflow.NEEDS_REVIEW, "reason": decision.reason}

        workflow.transition(doc_id, workflow.COMPLETED,
                            "Auto-completed by rules", decision.reason)
        return {"doc_id": doc_id, "status": workflow.COMPLETED, "reason": decision.reason}

    except Exception as e:
        # Something broke mid-workflow: don't leave the document stuck in "Processing"
        current = db.get_document_by_id(doc_id)
        if current and current["status"] == workflow.PROCESSING:
            reason = f"Unexpected error: {e}"
            workflow.transition(doc_id, workflow.FAILED, "Processing failed", reason)
            return {"doc_id": doc_id, "status": workflow.FAILED, "reason": reason}
        raise


def run_workflow(doc_id: int) -> dict:
    """Re-run the workflow for an already stored document (batch / retry)."""
    doc = db.get_document_by_id(doc_id)
    if doc is None:
        raise ValueError(f"Document {doc_id} not found")
    t0 = perf_counter()
    try:
        with open(doc["file_path"], "rb") as f:
            file_bytes = f.read()
        ext = doc["original_filename"].split(".")[-1].lower()
        analysis = analyse_document(file_bytes, ext)
    except Exception as e:
        analysis = _failed_analysis(f"Failed: could not read stored file ({e})",
                                    perf_counter() - t0)
    return evaluate_document(doc_id, analysis)


def process_upload(uploaded_file) -> dict:
    """Full upload flow for one file. Never raises."""
    file_bytes = uploaded_file.getvalue()
    original_filename = uploaded_file.name
    ext = original_filename.split(".")[-1].lower()

    error = validate_file(uploaded_file)
    if error:
        return {"ok": False, "message": error}

    file_hash = compute_file_hash(file_bytes)
    existing = db.get_document_by_hash(file_hash)
    if existing:
        audit.log_event(existing["id"], "Duplicate upload blocked",
                        existing["status"], existing["status"],
                        f"Same file uploaded again as '{original_filename}'")
        return {"ok": True, "duplicate": True, "record": existing}

    analysis = analyse_document(file_bytes, ext)

    try:
        stored_filename, file_path = store_file(file_bytes, original_filename,
                                                analysis["doc_type"])
    except Exception as e:
        return {"ok": False, "message": f"Could not save file: {e}"}

    try:
        doc_id = db.insert_document({
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "document_type": analysis["doc_type"],
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_path": file_path,
            "text_preview": analysis["text"][:300],
            "file_hash": file_hash,
            "status": workflow.NEW,
        })
        audit.log_event(doc_id, "Document uploaded", None, workflow.NEW,
                        f"Stored as {stored_filename}")
    except Exception as e:
        try:
            os.remove(file_path)   # don't leave an orphan file behind
        except OSError:
            pass
        return {"ok": False, "message": f"Database error: could not save record ({e})"}

    try:
        outcome = evaluate_document(doc_id, analysis)
    except Exception as e:
        return {"ok": False, "message": f"Workflow error for document #{doc_id}: {e}"}

    return {"ok": True, "duplicate": False, "doc_id": doc_id,
            "outcome": outcome, "extraction_method": analysis["method"],
            "full_text": analysis["text"]}


# ----------------------------------------------------------------------
# WEEK 5: BATCH PROCESSING
# ----------------------------------------------------------------------

def run_batch(doc_ids: list, progress=None) -> dict:
    """
    Run the same workflow for every selected document. One failure never stops
    the batch, and every document gets its own result row.
    """
    results = []
    for i, doc_id in enumerate(doc_ids, start=1):
        doc = db.get_document_by_id(doc_id)
        row = {"id": doc_id, "filename": doc["original_filename"] if doc else "?",
               "outcome": "", "reason": ""}
        try:
            if doc is None:
                raise ValueError("Document not found")
            if doc["status"] not in workflow.RUNNABLE_STATES:
                row.update(outcome="Skipped",
                           reason=f"Status '{doc['status']}' cannot be re-run")
            else:
                out = run_workflow(doc_id)
                row.update(outcome=out["status"], reason=out["reason"])
        except Exception as e:
            row.update(outcome=workflow.FAILED, reason=str(e))
        results.append(row)
        if progress:
            progress(i / len(doc_ids))

    def count(name):
        return sum(1 for r in results if r["outcome"] == name)

    return {
        "results": results,
        "processed": count(workflow.COMPLETED),
        "review": count(workflow.NEEDS_REVIEW),
        "failed": count(workflow.FAILED),
        "skipped": count("Skipped"),
    }
