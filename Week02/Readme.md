# AI Document Intelligence & Workflow Platform — Week 3

**Zyroo AI/ML Internship — Task 02: Improve Document Understanding**

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

## Project structure

```
zyroo_week3/
├── app.py                     # Streamlit app (run this)
├── train_classifier.py        # Train + evaluate + compare models (run this first)
├── text_utils.py               # Text cleaning shared by training & app
├── ocr_preprocessing.py        # Image preprocessing for difficult OCR cases
├── extraction.py                # Regex-based field extraction (Invoice/Resume)
├── dataset/
│   ├── generate_dataset.py     # Builds dataset/documents.csv
│   └── documents.csv           # Generated training data (180 rows)
└── models/                      # Created by train_classifier.py
    ├── vectorizer.joblib
    ├── classifier.joblib
    ├── labels_order.joblib
    ├── best_model_name.joblib
    ├── model_comparison.txt     # Accuracy/precision/recall/F1 for all 3 models
    └── confusion_matrix.png
```

## How to run

```bash
pip install streamlit pymupdf easyocr pillow numpy scikit-learn matplotlib joblib

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

## Evaluation results (current run)

See `models/model_comparison.txt` for the full report. Summary: all three
models (Logistic Regression, Linear SVM, Naive Bayes) reached high
accuracy on the held-out test split, and **Logistic Regression** was
selected as it gave the best macro F1-score. The confusion matrix
(`models/confusion_matrix.png`) shows predictions vs. true labels for the
selected model. Because the three document classes are quite distinct in
vocabulary, scores are high on this synthetic set — testing on real,
messier documents (Step 11) is expected to reveal more mistakes, which
is exactly what that step is for.

## Manual testing notes (Step 11)

Record results here as you test with real documents, e.g.:

| Document | Expected Type | Predicted Type | Fields Missing | Notes |
|---|---|---|---|---|
| sample_invoice_1.pdf | Invoice | | | |
| scanned_resume.jpg | Resume | | | |
| random_letter.pdf | Other | | | |

## Known limitations / next steps

- Classifier trained on synthetic data — accuracy on real-world scans may
  be lower until real examples are added.
- OCR preprocessing is intentionally simple (Pillow-only); a production
  system might use OpenCV for more advanced denoising/deskewing.
- Confidence is only shown for models that support `predict_proba`.
