# AI Document Intelligence & Workflow Platform — Week 4

Zyroo Internship Program • AI/ML Internship • Week 4
**Document Management Layer**

This week upgrades the Week 3 document processor into a small document
**management system**: uploaded files are validated, processed, saved to
disk in an organized structure, and tracked in a SQLite database so they
can be searched, filtered, and viewed later.

## What's New Since Week 3

- Organized file storage: separate folders for Invoices, Resumes, and Other
- Safe, unique filenames on disk (original filename kept in the database)
- SQLite database (`documents.db`) storing metadata for every processed file
- **Duplicate detection** using a SHA-256 hash — the same file is never
  saved twice
- **Multi-field search** (filename, company, invoice number, type, text
  preview) powered by SQL queries
- **Filters and sorting**: by document type, status, and upload date
  (newest/oldest)
- **Document detail view**: metadata, extracted fields, status, and a
  download button
- **Processing status** per document: `Processed`, `Needs Review`, or
  `Failed`
- Safer error handling: unsupported file types, oversized files, unreadable
  documents, OCR failures, and database errors are all handled without
  crashing the app or exposing raw error details

## Target Flow

```
Upload -> Validate -> Hash -> Read/OCR -> Clean -> Classify -> Extract
       -> Store File -> Store Metadata -> Search/Filter -> View
```

## Project Structure

```
Week04/
├── app.py              # Streamlit UI + processing pipeline
├── database.py          # SQLite database layer (CRUD operations)
├── requirements.txt
├── README.md
├── documents.db          # created automatically on first run
└── storage/               # created automatically on first run
    ├── invoices/
    ├── resumes/
    └── others/
```

## Setup Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

No separate OCR engine install is needed — this project uses **EasyOCR**,
which is a pure pip-installable package.

### 2. Database setup

**Nothing to install or download.** SQLite comes built into Python's
standard library (`sqlite3`). The first time you run the app,
`database.py` automatically creates `documents.db` and the `documents`
table if they don't already exist — this happens via `db.init_db()` in
`app.py`.

### 3. Run the app

```bash
streamlit run app.py
```

Open the local URL shown in the terminal (usually
`http://localhost:8501`).

## How It Works

### Upload tab
1. Upload one or more PDF/JPG/PNG files.
2. Each file is validated (type + size), hashed, checked for duplicates,
   read (PyMuPDF or OCR), cleaned, classified (Invoice/Resume/Other),
   and has fields extracted.
3. The file is saved into `storage/invoices/`, `storage/resumes/`, or
   `storage/others/` with a randomly generated safe filename.
4. A metadata record (including the original filename, extracted fields,
   file path, hash, and status) is saved to `documents.db`.

### Search & Browse tab
- Type a keyword to search across filename, company, invoice number,
  document type, and the stored text preview.
- Filter by document type and/or processing status.
- Sort by newest or oldest upload date.
- Click a result to expand its full detail view, including a download
  button for the original file.

## Duplicate Detection

Every uploaded file's raw bytes are hashed with **SHA-256**. Before saving
a new record, the app checks whether that exact hash already exists in the
database. If it does, the existing saved document is shown instead of
creating a duplicate entry — so re-uploading the same file is always safe.

## Processing Status

- **Processed** — text was extracted and all expected fields were found.
- **Needs Review** — the document was read and classified, but one or
  more expected fields could not be found (shown as "Not Found").
- **Failed** — the file could not be read at all (e.g. corrupted PDF or
  OCR failure). The app does not crash; it records the failure and moves
  on.

## Testing Checklist

- [ ] Upload at least 10 documents (mix of invoices, resumes, other files)
- [ ] Upload a duplicate file and confirm it's detected
- [ ] Upload a scanned document (image-based PDF or photo)
- [ ] Upload a document that's missing some fields (check "Needs Review")
- [ ] Search using different fields (filename, company, invoice number)
- [ ] Try each filter and sort option
- [ ] Restart the app and confirm previously saved documents are still
      listed in Search & Browse

## Tech Stack

- Python
- Streamlit (web interface)
- SQLite (`sqlite3`, built into Python — document metadata repository)
- PyMuPDF (PDF text extraction)
- EasyOCR (scanned document / image OCR)
- Regular Expressions (field extraction)
- `hashlib` (SHA-256 duplicate detection)
