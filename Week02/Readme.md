# AI Document Intelligence & Workflow Platform

Zyroo Internship Program • AI/ML Internship • Week 1 • Task 01

A simple Streamlit app that lets a user upload a PDF or image, reads the
text (using PyMuPDF or OCR), identifies whether it's an **Invoice** or
**Resume**, extracts a few key fields, and displays the result.

## Flow

```
Upload -> Read Text/OCR -> Check Type -> Extract Fields -> Show Result
```

## Features

- Accepts PDF, JPG/JPEG, PNG files
- Extracts text from normal PDFs using PyMuPDF
- Falls back to OCR (Tesseract) for scanned PDFs / images
- Simple keyword-based classification: Invoice / Resume / Other
- Regex-based field extraction:
  - **Invoice:** Invoice Number, Date, Company Name, Total Amount
  - **Resume:** Name, Email, Phone, Skills
- Simple Streamlit UI to display results

## Project Structure

```
ai-document-intelligence/
├── app.py
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Clone / download the project

```bash
git clone <your-repo-url>
cd ai-document-intelligence
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR (system-level, required for OCR)

- **Windows:** Download and install from
  https://github.com/UB-Mannheim/tesseract/wiki
  (make sure to add it to your PATH, or set
  `pytesseract.pytesseract.tesseract_cmd` in `app.py` to the install path)
- **macOS:**
  ```bash
  brew install tesseract
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt-get install tesseract-ocr
  ```

### 5. Run the app locally

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal (usually
`http://localhost:8501`).

## Testing

Test with at least 3 sample documents:
- 2 sample invoices (PDF)
- 1 sample resume (PDF or image)

Check that:
- Text is extracted correctly
- Document type is identified correctly
- Fields not found are shown as "Not found" (instead of crashing)

## Deployment

You can deploy this app for free using:
- [Streamlit Community Cloud](https://streamlit.io/cloud)
- [Hugging Face Spaces](https://huggingface.co/spaces)

Note: On Streamlit Community Cloud you also need a `packages.txt` file
containing `tesseract-ocr` so the OCR engine is installed on the server:

```
tesseract-ocr
```

## Tech Stack

- Python
- Streamlit (web interface)
- PyMuPDF (PDF text extraction)
- Tesseract OCR / pytesseract (OCR)
- Regular Expressions (field extraction)
