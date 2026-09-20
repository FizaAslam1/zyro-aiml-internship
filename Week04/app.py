"""
AI Document Intelligence & Workflow Platform - Week 4
Zyroo Internship Program

New in Week 4: organized file storage, SQLite metadata repository,
duplicate detection via SHA-256 hash, multi-field search, filters/sorting,
a document detail view, processing status, and safer error handling.

Flow: Upload -> Validate -> Hash -> Read/OCR -> Clean -> Classify -> Extract
      -> Store File -> Store Metadata -> Search/Filter -> View
"""

import os
import re
import io
import uuid
import hashlib
from datetime import datetime

import numpy as np
import streamlit as st
import pymupdf as fitz  # PyMuPDF
from PIL import Image
import easyocr

import database as db

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

for folder in FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

db.init_db()


@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(["en"], gpu=False)


# ----------------------------------------------------------------------
# STEP: VALIDATE
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


# ----------------------------------------------------------------------
# STEP: HASH (duplicate detection)
# ----------------------------------------------------------------------

def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ----------------------------------------------------------------------
# STEP: READ TEXT (PDF / OCR)
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


# ----------------------------------------------------------------------
# STEP: CLEAN TEXT
# ----------------------------------------------------------------------

def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = raw_text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)          # collapse repeated spaces/tabs
    text = re.sub(r"\n\s*\n+", "\n", text)        # collapse repeated blank lines
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()


# ----------------------------------------------------------------------
# STEP: CLASSIFY (rule-based)
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
# STEP: EXTRACT FIELDS (regex-based)
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
# STEP: STORE FILE
# ----------------------------------------------------------------------

def store_file(file_bytes: bytes, original_filename: str, doc_type: str) -> tuple[str, str]:
    """Saves the file into the right folder with a safe generated name.
    Returns (stored_filename, file_path)."""
    ext = original_filename.split(".")[-1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    folder = FOLDERS.get(doc_type, FOLDERS["Other"])
    file_path = os.path.join(folder, stored_filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return stored_filename, file_path


# ----------------------------------------------------------------------
# PIPELINE: process one uploaded file end-to-end
# ----------------------------------------------------------------------

def process_and_store(uploaded_file):
    """Runs the full pipeline for one file. Returns a dict result for display."""
    file_bytes = uploaded_file.getvalue()
    original_filename = uploaded_file.name
    ext = original_filename.split(".")[-1].lower()

    # 1. Validate
    error = validate_file(uploaded_file)
    if error:
        return {"ok": False, "message": error}

    # 2. Hash + duplicate check
    file_hash = compute_file_hash(file_bytes)
    existing = db.get_document_by_hash(file_hash)
    if existing:
        return {"ok": True, "duplicate": True, "record": existing}

    # 3. Read text (PDF / OCR) - never crashes, returns Failed status instead
    raw_text, method = read_document_text(file_bytes, ext)
    if raw_text == "":
        status = "Failed"
        cleaned_text = ""
        doc_type = "Other"
        fields = {}
    else:
        # 4. Clean text
        cleaned_text = clean_text(raw_text)

        # 5. Classify
        doc_type = detect_document_type(cleaned_text)

        # 6. Extract fields
        fields = extract_fields(cleaned_text, doc_type)

        # 7. Decide status
        important_missing = any(v == "Not Found" for v in fields.values()) if fields else False
        status = "Needs Review" if important_missing else "Processed"

    # 8. Store file
    try:
        stored_filename, file_path = store_file(file_bytes, original_filename, doc_type)
    except Exception as e:
        return {"ok": False, "message": f"Could not save file: {e}"}

    # 9. Store metadata in the database
    record = {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "document_type": doc_type,
        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company": fields.get("Company Name", ""),
        "invoice_number": fields.get("Invoice Number", ""),
        "total_amount": fields.get("Total Amount", ""),
        "file_path": file_path,
        "text_preview": cleaned_text[:300],
        "file_hash": file_hash,
        "status": status,
    }

    try:
        new_id = db.insert_document(record)
    except Exception as e:
        return {"ok": False, "message": f"Database error: could not save record ({e})"}

    record["id"] = new_id
    return {
        "ok": True,
        "duplicate": False,
        "record": record,
        "fields": fields,
        "extraction_method": method,
        "full_text": cleaned_text,
    }


# ----------------------------------------------------------------------
# UI HELPERS
# ----------------------------------------------------------------------

def status_badge(status: str) -> str:
    colors = {"Processed": "🟢", "Needs Review": "🟡", "Failed": "🔴"}
    return f"{colors.get(status, '⚪')} {status}"


def show_document_detail(doc: dict, key_prefix: str = "detail"):
    """key_prefix must be unique per call site so widget keys never clash
    (e.g. the same document can appear in both the Upload tab and the
    Search & Browse tab within the same run)."""
    st.subheader(f"📄 {doc['original_filename']}")
    st.write(status_badge(doc["status"]))

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Document Type:** {doc['document_type']}")
        st.write(f"**Upload Date:** {doc['upload_date']}")
        st.write(f"**Company:** {doc['company'] or 'Not Found'}")
    with col2:
        st.write(f"**Invoice Number:** {doc['invoice_number'] or 'Not Found'}")
        st.write(f"**Total Amount:** {doc['total_amount'] or 'Not Found'}")
        st.write(f"**File Path:** `{doc['file_path']}`")

    st.write("**Text Preview:**")
    st.text(doc["text_preview"] or "(no preview available)")

    if doc["file_path"] and os.path.exists(doc["file_path"]):
        with open(doc["file_path"], "rb") as f:
            st.download_button(
                "⬇️ Download Original File",
                data=f.read(),
                file_name=doc["original_filename"],
                key=f"{key_prefix}_download_{doc['id']}",
            )
    else:
        st.warning("Stored file not found on disk.")


# ----------------------------------------------------------------------
# STREAMLIT APP
# ----------------------------------------------------------------------

st.set_page_config(page_title="AI Document Intelligence - Week 4", page_icon="📁", layout="wide")

st.title(" AI Document Intelligence & Workflow Platform")
st.caption("Zyroo Internship Program • Week 4 • Document Management Layer")

tab_upload, tab_browse = st.tabs(["📤 Upload", "🔎 Search & Browse"])

# ------------------------- UPLOAD TAB ----------------------------------
with tab_upload:
    st.write("Upload a PDF or image. It will be processed, classified, "
             "and saved to the document repository.")

    uploaded_files = st.file_uploader(
        "Upload document(s)",
        type=list(ALLOWED_EXTENSIONS),
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.divider()
            with st.spinner(f"Processing {uploaded_file.name}..."):
                result = process_and_store(uploaded_file)

            if not result["ok"]:
                st.error(f"❌ {uploaded_file.name}: {result['message']}")
                continue

            if result.get("duplicate"):
                st.warning(f"⚠️ Duplicate detected for **{uploaded_file.name}** — "
                           f"this file was already uploaded as "
                           f"**{result['record']['original_filename']}**.")
                show_document_detail(result["record"], key_prefix="upload_dup")
                continue

            record = result["record"]
            st.success(f"✅ {uploaded_file.name} processed and saved.")
            st.write(f"**Document Type:** {record['document_type']}  |  "
                     f"**Status:** {status_badge(record['status'])}")
            st.write(f"*Extraction method: {result['extraction_method']}*")

            if result["fields"]:
                st.write("**Extracted Fields:**")
                for k, v in result["fields"].items():
                    st.write(f"- **{k}:** {v}")

            with st.expander("View extracted text"):
                st.text(result["full_text"])

# ------------------------- BROWSE / SEARCH TAB --------------------------
with tab_browse:
    st.write("Search, filter, and browse all saved documents.")

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        keyword = st.text_input("Search (filename, company, invoice #, text...)")
    with col2:
        doc_type_filter = st.selectbox("Document Type", ["All", "Invoice", "Resume", "Other"])
    with col3:
        status_filter = st.selectbox("Status", ["All", "Processed", "Needs Review", "Failed"])
    with col4:
        sort_order = st.selectbox("Sort", ["Newest", "Oldest"])

    if st.button("🧹 Clear Filters"):
        st.rerun()

    results = db.search_documents(
        keyword=keyword,
        doc_type=doc_type_filter,
        status=status_filter,
        sort_order=sort_order,
    )

    st.write(f"**{len(results)} document(s) found**")

    if not results:
        st.info("No documents match your search/filters yet. Upload some documents first.")
    else:
        for i, doc in enumerate(results):
            with st.expander(
                f"{status_badge(doc['status']).split()[0]} {doc['original_filename']} "
                f"— {doc['document_type']} — {doc['upload_date']}"
            ):
                show_document_detail(doc, key_prefix=f"browse_{i}")