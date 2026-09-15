# AI Document Intelligence & Workflow Platform — Week 3

**Zyroo AI/ML Internship — Task 02: Improve Document Understanding**

Live app: https://zyro-aiml-internship-6evjxpnz2rtel6t5cn753h.streamlit.app

This builds on the Week 2 MVP (upload → read text/OCR → identify type →
extract fields → show result) by making every stage more robust and adding
a trained ML classifier with an evaluated comparison.

## What changed from Week 2

| Area | Week 2 | Week 3 |
|---|---|---|
| Dataset | None (no training data) | `dataset/generate_dataset.py` builds a labeled, balanced dataset (60 Invoice / 60 Resume / 60 Other) — see note below |
| Text cleaning | None — raw extracted text used directly | `text_utils.py`: strips control chars, collapses repeated whitespace/blank lines, trims lines, checks for empty/too-short text |
| OCR | Single OCR pass, no preprocessing | `ocr_preprocessing.py`: if the first OCR pass returns too little text, the page/image is resized, grayscaled, auto-contrasted, denoised (median filter) and re-thresholded, then OCR'd again; the better result is kept |
| Classification | Keyword counting only | `train_classifier.py`: TF‑IDF features + 3 models trained and compared (Logistic Regression, Linear SVM, Naive Bayes); best one picked **by F1‑score**, not by "which is fancier". Rule-based Week 2 logic kept as a baseline and as a **fallback** if no trained model is found |
| Evaluation | None | Accuracy, macro precision/recall/F1, per-class report, and a confusion matrix image — see `models/model_comparison.txt` and `models/confusion_matrix.png` |
| Field extraction | Basic regex, some false matches (e.g. "Total" matched inside "Subtotal") | `extraction.py`: fixed the Subtotal/Total bug, added more date/number formats, resume "Name" no longer grabs a section header by mistake, "Skills" stops at the next section instead of eating the whole document |
| Missing fields | Returned the string `"Not found"` as a plain value | Every field now returns `{value, found}`; the UI clearly highlights missing fields and never crashes when a field is absent |
| Confidence | Not shown | Shown next to the document type (e.g. `Invoice \| Confidence: 91%`) **only** when the model genuinely supports it (Logistic Regression / Naive Bayes via `predict_proba`); no number is invented for Linear SVM |
| UI/UX | Plain top-to-bottom text list | Sidebar with pipeline explanation + evaluation results, progress bar during processing, card-style field display, type badge, confidence metric, JSON download button, image preview |

## Project structure

```
zyroo_week3/
├── app.py                     # Streamlit app (run this)
├── train_classifier.py        # Train + evaluate + compare models (run this first)
├── text_utils.py               # Text cleaning shared by training & app
├── ocr_preprocessing.py        # Image preprocessing for difficult OCR cases
├── extraction.py                # Regex-based field extraction (Invoice/Resume)
├── requirements.txt             # Python dependencies for deployment
├── dataset/
│   ├── generate_dataset.py     # Builds dataset/documents.csv
│   └── documents.csv           # Generated training data (180 rows)
├── samples/                     # Sample documents used for manual testing
└── models/                      # Created by train_classifier.py
    ├── vectorizer.joblib
    ├── classifier.joblib
    ├── labels_order.joblib
    ├── best_model_name.joblib
    ├── model_comparison.txt     # Accuracy/precision/recall/F1 for all 3 models
    └── confusion_matrix.png
```

## How to run locally

```bash
pip install -r requirements.txt

# 1. (Re)generate the dataset (optional — one is already included)
python dataset/generate_dataset.py

# 2. Train and evaluate the classifier (required before first run of the app)
python train_classifier.py

# 3. Launch the app
streamlit run app.py
```

## About the dataset

Real scanned invoices/resumes weren't available to collect during this
task, so `dataset/generate_dataset.py` **synthesizes** realistic text
samples (varied field labels/order, light OCR-style noise, and a few
deliberately tricky "Other" documents like purchase orders and quotations
that share vocabulary with invoices, so the classifier is actually
tested). **This is a starting point** — for a stronger real-world model,
replace/extend `dataset/documents.csv` with real collected examples per
the task's Step 1.

## Evaluation results

See `models/model_comparison.txt` for the full report. Summary: all three
models (Logistic Regression, Linear SVM, Naive Bayes) reached high
accuracy on the held-out test split, and **Logistic Regression** was
selected as it gave the best macro F1-score. The confusion matrix
(`models/confusion_matrix.png`) shows predictions vs. true labels for the
selected model.

## Manual testing (Step 11)

Tested on the deployed app with real personal documents (PDF resume and
a screenshot/image resume):

| # | Document | Type | Expected | Predicted | Fields Found | Fields Missing | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Fiza_CV.pdf | PDF (text layer) | Resume | Resume | Email, Phone, Name, Skills | None | Extraction: PyMuPDF (text layer). All fields extracted correctly from the clean text-based PDF. |
| 2 | Resume screenshot (PNG) | Image (OCR) | Resume | Resume | — | Email, Phone | Extraction: OCR (image). Email/Phone were not detected — likely because the header/contact line wasn't OCR'd cleanly or the layout put them far from the usual position. **Name** and **Skills** fields also grabbed the wrong text (a portfolio URL and page description instead of the actual name/skills line) — the OCR text order for this image didn't match the simple line-based extraction rules. |

**Observations / mistakes recorded:**
- Text-layer PDFs give clean, reliable extraction — no issues.
- OCR'd images are noticeably weaker: contact info can be missed entirely,
  and the "first non-header line = Name" / "text after 'Skills:' " heuristics
  break when OCR reorders or merges lines differently than a normal PDF
  text layer would.
- **Next improvement (not yet done):** make Name/Skills extraction more
  robust to OCR line reordering — e.g. searching the whole text for an
  email/phone-adjacent line for the name, and bounding the skills capture
  more tightly.

## Known issue on the deployed app

On the current Streamlit Cloud deployment, the app reports:
`Classifier: Rule-based (fallback - no trained model found)`

This means the trained ML model files in `models/` are **not being loaded**
on the deployed app (even though rule-based classification still worked
correctly in the tests above). Likely causes to check:
- The `models/*.joblib` files may not have actually been committed to
  GitHub (empty folder, or a `.gitignore` rule excluding them).
- The working directory on Streamlit Cloud may not match the `models/`
  relative path used in `app.py`.

**To fix:** confirm the `.joblib` files show a real file size on GitHub
(not 0 KB), and that they sit in a `models/` folder in the same directory
as `app.py`, then reboot the app.

## Known limitations / next steps

- Classifier trained on synthetic data — accuracy on real-world scans may
  be lower until real examples are added.
- OCR preprocessing is intentionally simple (Pillow-only); a production
  system might use OpenCV for more advanced denoising/deskewing.
- Confidence is only shown for models that support `predict_proba`.
- Name/Skills extraction from OCR'd images needs to be made more robust
  (see Manual Testing notes above).
