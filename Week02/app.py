"""
AI Document Intelligence & Workflow Platform
Zyroo Internship - Week 3 - Task 02: Improve Document Understanding

Flow: Upload -> Read Text/OCR -> Clean Text -> Identify Type ->
      Extract Fields -> Check Missing Fields -> Show Result -> Test

Changes from Week 2 are summarized in README.md.
"""

import io
import os

import numpy as np
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import easyocr
import joblib

from text_utils import clean_text, is_text_too_short
from ocr_preprocessing import preprocess_for_ocr, needs_preprocessing
from extraction import extract_fields, NOT_FOUND

MODEL_DIR = "models"


@st.cache_resource
def get_ocr_reader():
    """Load the EasyOCR reader once and cache it (first run downloads model files)."""
    return easyocr.Reader(["en"], gpu=False)


@st.cache_resource
def get_classifier():
    """
    Load the trained TF-IDF + ML classifier (Step 4/5/6).
    Returns None for any piece that isn't available yet, so the app can
    fall back to the Week 2 rule-based classifier without crashing
    (e.g. before train_classifier.py has been run).
    """
    try:
        vectorizer = joblib.load(os.path.join(MODEL_DIR, "vectorizer.joblib"))
        clf = joblib.load(os.path.join(MODEL_DIR, "classifier.joblib"))
        labels_order = joblib.load(os.path.join(MODEL_DIR, "labels_order.joblib"))
        model_name = joblib.load(os.path.join(MODEL_DIR, "best_model_name.joblib"))
        return vectorizer, clf, labels_order, model_name
    except FileNotFoundError:
        return None


# ----------------------------------------------------------------------
# STEP 2 & 3: READ TEXT + IMPROVED OCR HANDLING
# ----------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract selectable text from a normal PDF using PyMuPDF."""
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()


def _ocr_image(img: Image.Image, reader) -> str:
    result = reader.readtext(np.array(img), detail=0)
    return " ".join(result).strip()


def extract_text_with_ocr_from_pdf(file_bytes: bytes) -> tuple[str, bool]:
    """
    Render scanned PDF pages as images and OCR them.
    Returns (text, preprocessing_was_used).
    If the first OCR pass on a page returns very little text, the page is
    re-processed with preprocess_for_ocr() (resize/grayscale/contrast/
    threshold/denoise) and OCR'd again - this is Step 3's "try simple
    image preprocessing when OCR struggles".
    """
    reader = get_ocr_reader()
    text_parts = []
    preprocessing_used = False
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

            page_text = _ocr_image(img, reader)
            if needs_preprocessing(page_text):
                img2 = preprocess_for_ocr(img)
                retry_text = _ocr_image(img2, reader)
                if len(retry_text) > len(page_text):
                    page_text = retry_text
                    preprocessing_used = True

            text_parts.append(page_text)
    return "\n".join(text_parts).strip(), preprocessing_used


def extract_text_from_image(file_bytes: bytes) -> tuple[str, bool]:
    """OCR a plain image file (JPG/PNG), retrying with preprocessing if needed."""
    reader = get_ocr_reader()
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    text = _ocr_image(img, reader)
    preprocessing_used = False
    if needs_preprocessing(text):
        img2 = preprocess_for_ocr(img)
        retry_text = _ocr_image(img2, reader)
        if len(retry_text) > len(text):
            text = retry_text
            preprocessing_used = True

    return text.strip(), preprocessing_used


def read_document_text(file_bytes: bytes, file_type: str) -> tuple[str, str]:
    """
    Returns (extracted_text, method_used).
    method_used tells us whether normal text extraction or OCR (with or
    without preprocessing) was needed.
    """
    if file_type == "pdf":
        text = extract_text_from_pdf(file_bytes)
        if not is_text_too_short(text):
            return text, "PyMuPDF (text layer)"
        text, preprocessed = extract_text_with_ocr_from_pdf(file_bytes)
        method = "OCR (scanned PDF, preprocessed)" if preprocessed else "OCR (scanned PDF)"
        return text, method
    else:  # jpg / jpeg / png
        text, preprocessed = extract_text_from_image(file_bytes)
        method = "OCR (image, preprocessed)" if preprocessed else "OCR (image)"
        return text, method


# ----------------------------------------------------------------------
# STEP 4/5/6: ML DOCUMENT TYPE CLASSIFICATION (with rule-based fallback)
# ----------------------------------------------------------------------

def detect_document_type_rules(text: str) -> str:
    """Week 2 baseline: keyword/rule based classifier, kept for comparison."""
    lower_text = text.lower()
    invoice_keywords = ["invoice", "total", "invoice number", "bill to", "amount due"]
    resume_keywords = ["resume", "skills", "education", "experience", "curriculum vitae"]
    invoice_score = sum(1 for kw in invoice_keywords if kw in lower_text)
    resume_score = sum(1 for kw in resume_keywords if kw in lower_text)
    if invoice_score == 0 and resume_score == 0:
        return "Other"
    return "Invoice" if invoice_score >= resume_score else "Resume"


def detect_document_type(text: str) -> dict:
    """
    Uses the trained ML classifier (TF-IDF + best model chosen in
    train_classifier.py) when available, with the confidence score
    where the model supports predict_proba (Step 9). Falls back to the
    Week 2 rule-based approach if no trained model is found, so the app
    never breaks.
    """
    bundle = get_classifier()
    if bundle is not None:
        vectorizer, clf, labels_order, model_name = bundle
        X = vectorizer.transform([text])
        pred = clf.predict(X)[0]

        confidence = None
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X)[0]
            confidence = float(np.max(proba))
        # LinearSVC has no predict_proba - decision_function can't be
        # cleanly turned into a probability, so we deliberately do NOT
        # invent a confidence number for it (per Step 9 instructions).

        return {
            "type": pred,
            "confidence": confidence,
            "method": f"ML model ({model_name})",
        }

    # Fallback: rule-based
    return {
        "type": detect_document_type_rules(text),
        "confidence": None,
        "method": "Rule-based (fallback - no trained model found)",
    }


# ----------------------------------------------------------------------
# STEP 1 & 10: STREAMLIT UI  (Week 3: redesigned for clarity + polish)
# ----------------------------------------------------------------------

import json
import time

st.set_page_config(
    page_title="AI Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- light custom styling (kept minimal & framework-native) ----
st.markdown(
    """
    <style>
    .field-card {
        background: rgba(120,120,120,0.06);
        border: 1px solid rgba(120,120,120,0.18);
        border-radius: 10px;
        padding: 0.6rem 0.9rem;
        margin-bottom: 0.5rem;
    }
    .field-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.65;
        margin-bottom: 0.1rem;
    }
    .field-value-found { font-size: 1.02rem; font-weight: 600; }
    .field-value-missing { font-size: 1.02rem; font-weight: 600; color: #d68a00; }
    .type-badge {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.95rem;
        background: rgba(46,125,50,0.12);
        color: #2e7d32;
        border: 1px solid rgba(46,125,50,0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- sidebar: about / pipeline / model info ----
with st.sidebar:
    st.header("📄 About this app")
    st.write(
        "Reads an Invoice or Resume (PDF/JPG/PNG), classifies it with a "
        "trained ML model, and extracts key fields."
    )
    st.markdown("**Pipeline**")
    st.markdown(
        "1. Upload\n"
        "2. Read text (PyMuPDF / OCR)\n"
        "3. Clean & normalize text\n"
        "4. Classify document type\n"
        "5. Extract fields\n"
        "6. Handle missing fields\n"
        "7. Show results"
    )
    st.divider()
    bundle = get_classifier()
    if bundle is not None:
        _, _, _, model_name = bundle
        st.success(f"Model loaded: **{model_name}**")
        if os.path.exists(os.path.join(MODEL_DIR, "confusion_matrix.png")):
            with st.expander("📊 Evaluation results"):
                st.image(os.path.join(MODEL_DIR, "confusion_matrix.png"),
                          caption="Confusion matrix (held-out test set)")
                if os.path.exists(os.path.join(MODEL_DIR, "model_comparison.txt")):
                    with open(os.path.join(MODEL_DIR, "model_comparison.txt")) as f:
                        st.text(f.read())
    else:
        st.warning(
            "No trained classifier found.\nRun `python train_classifier.py` "
            "for ML-based classification with confidence scores."
        )
    st.divider()
    st.caption("Zyroo Internship Program • ")

# ---- header ----
st.title("📄 AI Document Intelligence & Workflow Platform")
st.caption("Upload a PDF or image (Invoice / Resume) — the app reads it, cleans the text, "
           "classifies it, and extracts key fields, handling missing data gracefully.")

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["pdf", "jpg", "jpeg", "png"],
    help="Supported: PDF, JPG, JPEG, PNG",
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name
    file_ext = file_name.split(".")[-1].lower()
    file_type = "pdf" if file_ext == "pdf" else "image"

    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.success(f"📎 **{file_name}**  ·  {file_ext.upper()}  ·  {len(file_bytes)/1024:.0f} KB")
    with top_col2:
        if file_type == "image":
            st.image(file_bytes, width=90)

    # ---- visible progress through the pipeline (Step 10: same flow, clearer UX) ----
    progress = st.progress(0, text="Reading document...")
    raw_text, method = read_document_text(file_bytes, file_type)
    progress.progress(45, text="Cleaning text...")

    if is_text_too_short(raw_text, min_chars=5):
        progress.empty()
        st.error(
            "❌ Could not extract meaningful text from this document. "
            "Try a clearer scan/photo, or a document with a text layer."
        )
    else:
        cleaned_text = clean_text(raw_text)
        progress.progress(70, text="Classifying document...")
        result = detect_document_type(cleaned_text)
        doc_type = result["type"]
        progress.progress(90, text="Extracting fields...")
        fields = extract_fields(cleaned_text, doc_type)
        progress.progress(100, text="Done!")
        time.sleep(0.15)
        progress.empty()

        # ---- results header row: type badge + confidence metric + method ----
        r1, r2, r3 = st.columns([2, 1, 2])
        with r1:
            st.markdown(f'<span class="type-badge">📌 {doc_type}</span>', unsafe_allow_html=True)
        with r2:
            if result["confidence"] is not None:
                st.metric("Confidence", f"{result['confidence']*100:.0f}%")
        with r3:
            st.caption(f"Extraction: **{method}**  \nClassifier: **{result['method']}**")

        st.divider()

        # ---- extracted fields as a clean card grid ----
        if fields:
            st.subheader("🔎 Extracted Fields")
            missing_any = False
            field_items = list(fields.items())
            cols = st.columns(2)
            for i, (key, info) in enumerate(field_items):
                with cols[i % 2]:
                    if info["found"]:
                        st.markdown(
                            f'<div class="field-card"><div class="field-label">{key}</div>'
                            f'<div class="field-value-found">{info["value"]}</div></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        missing_any = True
                        st.markdown(
                            f'<div class="field-card"><div class="field-label">{key}</div>'
                            f'<div class="field-value-missing">⚠️ {NOT_FOUND}</div></div>',
                            unsafe_allow_html=True,
                        )
            if missing_any:
                st.caption(
                    "ℹ️ Some fields could not be found — recorded so extraction "
                    "rules can be improved. The app continues working normally."
                )

            # ---- download results ----
            export = {
                "file_name": file_name,
                "document_type": doc_type,
                "confidence": result["confidence"],
                "extraction_method": method,
                "classification_method": result["method"],
                "fields": {k: v["value"] for k, v in fields.items()},
            }
            st.download_button(
                "⬇️ Download results as JSON",
                data=json.dumps(export, indent=2),
                file_name=f"{os.path.splitext(file_name)[0]}_result.json",
                mime="application/json",
            )
        else:
            st.warning("No specific fields defined for this document type ('Other').")

        with st.expander("📃 View cleaned extracted text"):
            st.text(cleaned_text)
        with st.expander("🧾 View raw extracted text (before cleaning)"):
            st.text(raw_text)
else:
    st.info("👆 Upload a PDF, JPG, or PNG file to get started.")
    with st.expander("ℹ️ How this works"):
        st.write(
            "1. **Read** — text-layer PDFs use PyMuPDF; scanned PDFs/images use OCR "
            "(with automatic image preprocessing if the first OCR pass struggles).\n"
            "2. **Clean** — whitespace and noise are normalized.\n"
            "3. **Classify** — a trained TF-IDF + ML model predicts Invoice / Resume / Other.\n"
            "4. **Extract** — regex rules pull out key fields per document type.\n"
            "5. **Handle gaps** — missing fields are shown clearly, never crash the app."
        )
