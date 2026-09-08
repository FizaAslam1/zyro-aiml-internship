"""
AI Document Intelligence & Workflow Platform
Zyroo Internship - Week 1 - Task 01

Flow: Upload -> Read Text (PDF/OCR) -> Identify Type -> Extract Fields -> Show Result
"""

import re
import io

import numpy as np
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import easyocr


@st.cache_resource
def get_ocr_reader():
    """Load the EasyOCR reader once and cache it (first run downloads model files)."""
    return easyocr.Reader(["en"], gpu=False)


# ----------------------------------------------------------------------
# STEP 2: READ TEXT
# ----------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract selectable text from a normal PDF using PyMuPDF."""
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()


def extract_text_with_ocr_from_pdf(file_bytes: bytes) -> str:
    """If PDF has no selectable text (scanned), render pages as images and OCR them."""
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
    """OCR a plain image file (JPG/PNG) using EasyOCR."""
    reader = get_ocr_reader()
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    result = reader.readtext(np.array(img), detail=0)
    return " ".join(result).strip()


def read_document_text(file_bytes: bytes, file_type: str) -> tuple[str, str]:
    """
    Returns (extracted_text, method_used)
    method_used tells us whether normal text extraction or OCR was needed.
    """
    if file_type == "pdf":
        text = extract_text_from_pdf(file_bytes)
        if len(text) > 20:  # enough real text found -> normal PDF
            return text, "PyMuPDF (text layer)"
        else:  # probably scanned PDF -> fallback to OCR
            text = extract_text_with_ocr_from_pdf(file_bytes)
            return text, "OCR (scanned PDF)"
    else:  # jpg / jpeg / png
        text = extract_text_from_image(file_bytes)
        return text, "OCR (image)"


# ----------------------------------------------------------------------
# STEP 3: SIMPLE DOCUMENT TYPE (rule/keyword based)
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
# STEP 4: EXTRACT SIMPLE INFORMATION (regex based)
# ----------------------------------------------------------------------

def extract_invoice_fields(text: str) -> dict:
    fields = {}

    invoice_no = re.search(r"(invoice\s*(no|number|#)?\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
                            text, re.IGNORECASE)
    fields["Invoice Number"] = invoice_no.group(3) if invoice_no else "Not found"

    date = re.search(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b", text)
    fields["Date"] = date.group(1) if date else "Not found"

    total = re.search(
        r"(total|amount due|grand total)\s*[:\-]?\s*"
        r"([A-Za-z]{0,4}\s?[\$\€\£]?\s?[\d,]+\.?\d{0,2})",
        text, re.IGNORECASE
    )
    fields["Total Amount"] = total.group(2).strip() if total else "Not found"

    company = re.search(r"(company|from|billed by)\s*[:\-]?\s*([A-Za-z0-9 &.,\-]+)",
                         text, re.IGNORECASE)
    fields["Company Name"] = company.group(2).strip() if company else "Not found"

    return fields


def extract_resume_fields(text: str) -> dict:
    fields = {}

    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    fields["Email"] = email.group(0) if email else "Not found"

    phone = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text)
    fields["Phone"] = phone.group(0) if phone else "Not found"

    # Name = first non-empty line (very simple heuristic for beginners)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    fields["Name"] = lines[0] if lines else "Not found"

    skills_match = re.search(r"skills\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
    fields["Skills"] = skills_match.group(1).strip()[:200] if skills_match else "Not found"

    return fields


def extract_fields(text: str, doc_type: str) -> dict:
    if doc_type == "Invoice":
        return extract_invoice_fields(text)
    elif doc_type == "Resume":
        return extract_resume_fields(text)
    return {}


# ----------------------------------------------------------------------
# STEP 1 & 5: STREAMLIT UI
# ----------------------------------------------------------------------

st.set_page_config(page_title="AI Document Intelligence", page_icon="📄", layout="centered")

st.title("📄 AI Document Intelligence & Workflow Platform")
st.caption("Zyroo Internship Program • Week 2 • Task 01")

st.write("Upload a PDF or image (Invoice / Resume) and the app will read it, "
         "identify its type, and extract a few key fields.")

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["pdf", "jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name
    file_ext = file_name.split(".")[-1].lower()
    file_type = "pdf" if file_ext == "pdf" else "image"

    st.success(f"Uploaded: **{file_name}**  |  Type: **{file_ext.upper()}**")

    with st.spinner("Reading document..."):
        extracted_text, method = read_document_text(file_bytes, file_type)

    if not extracted_text:
        st.error("Could not extract any text from this document.")
    else:
        st.info(f"Text extracted using: **{method}**")

        doc_type = detect_document_type(extracted_text)
        st.subheader(f"📌 Document Type: {doc_type}")

        fields = extract_fields(extracted_text, doc_type)

        if fields:
            st.subheader("🔎 Extracted Fields")
            for key, value in fields.items():
                st.write(f"**{key}:** {value}")
        else:
            st.warning("No specific fields defined for this document type ('Other').")

        with st.expander("📃 View Full Extracted Text"):
            st.text(extracted_text)
else:
    st.info("👆 Please upload a PDF, JPG, or PNG file to get started.")
