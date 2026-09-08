# 📄 AI Document Intelligence & Workflow Platform

**Zyroo AI/ML Internship Program • Week 2 • Task 01**

An intelligent Streamlit application that processes documents (PDFs and images) to automatically identify document types, extract key information, and present results in an intuitive interface. Built with cutting-edge Python libraries for document processing and OCR.

---

## 🎯 Project Overview

This application streamlines document processing workflows by leveraging computer vision and natural language processing techniques. Users can upload invoices or resumes in various formats, and the system automatically:

1. **Reads & Extracts** text using PyMuPDF or OCR
2. **Classifies** document type using keyword-based intelligence
3. **Extracts** structured data from identified documents
4. **Presents** results in an interactive web interface

### Supported Document Types

- **Invoices** → Invoice Number, Date, Company Name, Total Amount
- **Resumes** → Name, Email, Phone, Skills
- **Other Documents** → General text extraction

---

## ✨ Key Features

✅ **Multi-format Support** — Accepts PDF, JPG/JPEG, PNG files  
✅ **Intelligent Text Extraction** — PyMuPDF for digital PDFs, OCR fallback for scanned documents  
✅ **Smart Classification** — Keyword-based document type detection  
✅ **Structured Field Extraction** — Regex patterns for targeted information retrieval  
✅ **User-Friendly Interface** — Clean Streamlit UI with real-time processing  
✅ **Robust Error Handling** — Graceful fallbacks and informative error messages  

---

## 🚀 Live Demo

**Try the application now:** [https://zyro-aiml-internship-6evjxpnz2rtel6t5cn753h.streamlit.app/](https://zyro-aiml-internship-6evjxpnz2rtel6t5cn753h.streamlit.app/)

No installation required — test with sample documents directly in your browser!

---

## 📦 Project Structure

```
Week02/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
└── Readme.md              # This file
```

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | Streamlit |
| **PDF Processing** | PyMuPDF (fitz) |
| **OCR Engine** | EasyOCR |
| **Image Processing** | Pillow, NumPy |
| **Pattern Matching** | Regular Expressions |
| **Language** | Python 3.8+ |

---

## 📋 Workflow Architecture

```
┌─────────────────┐
│  Upload Document │
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ Extract Text/OCR     │
│ (PyMuPDF / EasyOCR)  │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Detect Document Type │
│ (Keyword Analysis)   │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Extract Key Fields   │
│ (Regex Patterns)     │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Display Results      │
│ (Streamlit UI)       │
└──────────────────────┘
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Tesseract OCR (system dependency)

### Step 1: Clone the Repository

```bash
git clone https://github.com/FizaAslam1/zyro-aiml-internship.git
cd zyro-aiml-internship/Week02
```

### Step 2: Create Virtual Environment

```bash
# Create environment
python -m venv venv

# Activate environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Tesseract OCR

**Windows:**
- Download installer: [tesseract-ocr](https://github.com/UB-Mannheim/tesseract/wiki)
- Run installer and note installation path
- (Optional) Add to `app.py`: `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`

**macOS:**
```bash
brew install tesseract
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### Step 5: Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 🧪 Testing & Validation

### Test Cases

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| **Digital Invoice (PDF)** | Invoice PDF with text layer | Type: Invoice, Fields extracted correctly |
| **Scanned Invoice (PDF)** | Scanned invoice image as PDF | Type: Invoice, OCR fallback used, Fields extracted |
| **Resume (PDF)** | Resume PDF | Type: Resume, Name/Email/Phone/Skills extracted |
| **Resume Image (JPG/PNG)** | Resume image file | Type: Resume, OCR used, fields extracted |
| **Unknown Document** | Unclassified document | Type: Other, Full text displayed |

### How to Test

1. Prepare sample documents (invoices and resumes)
2. Upload one at a time using the web interface
3. Verify:
   - ✓ Text extracted correctly
   - ✓ Document type identified accurately
   - ✓ Key fields extracted properly
   - ✓ Missing fields show "Not found" (no crashes)
   - ✓ Full text viewable in expandable section

---

## 🌐 Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)

1. Push code to GitHub
2. Visit [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app" → Select repository
4. Add `packages.txt` with `tesseract-ocr` for server-side OCR:

```
tesseract-ocr
```

5. Deploy!

### Option 2: Hugging Face Spaces

1. Create Space on [Hugging Face](https://huggingface.co/spaces)
2. Select Streamlit as SDK
3. Upload files and `packages.txt`
4. Automatic deployment

### Option 3: Self-Hosted

```bash
# Install Nginx/Apache for reverse proxy
# Run: streamlit run app.py --server.port 8501
# Configure reverse proxy to forward traffic
```

---

## 📊 Performance Characteristics

| Operation | Avg Time | Notes |
|-----------|----------|-------|
| Text extraction (PDF) | 1-3s | Depends on page count |
| OCR (full page) | 10-30s | GPU acceleration recommended |
| Type detection | <100ms | Lightweight keyword analysis |
| Field extraction | <500ms | Regex-based processing |

---

## 🔍 Advanced Features & Extensibility

### Future Enhancements

- [ ] Machine Learning-based document classification (SVM/Neural Networks)
- [ ] Support for additional document types (Tax forms, Receipts, IDs)
- [ ] Advanced field extraction using Named Entity Recognition (NER)
- [ ] Batch processing for multiple documents
- [ ] Export results to CSV/JSON
- [ ] Integration with cloud storage (S3, Google Drive)

### Customization Guide

**Add New Document Type:**
```python
# In extract_fields() function:
elif doc_type == "CustomType":
    return extract_custom_fields(text)
```

**Improve Classification:**
Enhance `detect_document_type()` with ML models:
```python
from sklearn.naive_bayes import MultinomialNB
# Train and use classifier instead of keyword matching
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Tesseract not found" | Install Tesseract and set path in app.py |
| "No text extracted" | Ensure PDF isn't corrupted; check file format |
| "Slow OCR processing" | Enable GPU in EasyOCR or use smaller images |
| "Port 8501 already in use" | Run `streamlit run app.py --server.port 8502` |
| "Module not found errors" | Verify all requirements installed: `pip install -r requirements.txt` |

---

## 📚 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | Latest | Web framework |
| PyMuPDF (fitz) | Latest | PDF text extraction |
| easyocr | Latest | OCR engine |
| Pillow (PIL) | Latest | Image processing |
| numpy | Latest | Array operations |

---

## 📖 Code Structure

### Main Functions

1. **Text Extraction Module**
   - `extract_text_from_pdf()` — Digital PDF processing
   - `extract_text_with_ocr_from_pdf()` — Scanned PDF handling
   - `extract_text_from_image()` — Image OCR

2. **Classification Module**
   - `detect_document_type()` — Keyword-based classification

3. **Field Extraction Module**
   - `extract_invoice_fields()` — Invoice-specific patterns
   - `extract_resume_fields()` — Resume-specific patterns

4. **UI Module**
   - Streamlit page config
   - File uploader
   - Results display

---

## 📝 Sample Output

```
Uploaded: sample_invoice.pdf | Type: PDF

Text extracted using: PyMuPDF (text layer)

📌 Document Type: Invoice

🔎 Extracted Fields
Invoice Number: INV-2024-001
Date: 01/15/2024
Company Name: Acme Corporation
Total Amount: $5,299.99

📃 View Full Extracted Text
[Expandable section with complete extracted text]
```

---

## 📧 Contact & Links

- **GitHub Repository:** [zyro-aiml-internship](https://github.com/FizaAslam1/zyro-aiml-internship)
- **Live Demo:** [Streamlit App](https://zyro-aiml-internship-6evjxpnz2rtel6t5cn753h.streamlit.app/)
- **Developer:** [Fiza Aslam](https://github.com/FizaAslam1)

---

## 👩‍💻 Author

**Fiza Aslam**  
AI/ML Engineer | Data Scientist  
*Zyroo AI/ML Internship Program — Week 2*

---

## 📄 License

This project is part of the **Zyroo AI/ML Internship Program**.

---

## 🙏 Acknowledgments

- Zyroo Internship Program for the opportunity
- Open-source communities: Streamlit, PyMuPDF, EasyOCR
- Python ecosystem for excellent ML/AI libraries

---

**Last Updated:** 2024 | **Status:** ✅ Production Ready
