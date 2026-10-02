# Week 5 - Advanced Document Workflow & Automation

**Project:** AI Document Intelligence & Workflow Platform - Zyroo AI/ML Internship

**Live app:** https://zyro-aiml-internship-wrh2leervgnfzahfn4ybui.streamlit.app/

Upgrade of the Week 4 app: documents now move through a controlled, auditable workflow.

```
Upload -> Process -> Classify -> Extract -> Validate -> Apply Rules
       -> Review / Approve / Reject -> Complete -> Audit History
```

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI only (Upload, Search & Workflow, Review Queue, Batch, Metrics) |
| `pipeline.py` | Read/OCR, classify, extract, store (moved from Week 4 `app.py`) + upload, workflow run, batch |
| `workflow.py` | States, valid transitions, rule-based decision engine, approve/reject |
| `validator.py` | Field validation (invoice / resume, email, phone, date, amount) |
| `audit.py` | Audit log: document ID, action, previous/new status, timestamp, reason |
| `database.py` | SQLite layer (+ workflow columns, `audit_log` table, metrics) |
| `test_workflow.py` | Automated tests (17) |
| `Week04/Screenshots/` | Testing evidence screenshots (see "Testing evidence" below) |

## Workflow states
`New -> Processing -> Needs Review | Completed | Failed`,
`Needs Review -> Approved -> Completed | Rejected | Processing (re-run)`, `Failed -> Processing (retry)`.
`Completed` and `Rejected` are final. Any other change raises `InvalidTransition` and is not written.

## Rules (edit `workflow.py`, no UI change needed)
A document goes to **Needs Review** if: type is not Invoice/Resume, a required field is missing,
a required field is invalid, or classifier confidence < `CONFIDENCE_THRESHOLD` (0.70).
The current rule-based classifier returns **no confidence**, so that rule is skipped and no value is ever invented.
Otherwise the document is **auto-completed**.

## Upgrading an existing Week 4 database
Just run the app. `init_db()` adds the new columns/table and resets old Week 4 statuses to `New`
(logged in the audit log as "Migrated from Week 4"). Then use **Batch Processing** to run them through the workflow.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
python -m unittest -v test_workflow
```

## Testing evidence
Screenshots are in the [`Week04/Screenshots/`](/Week04/Screenshots/) folder, taken on the live app
(https://zyro-aiml-internship-wrh2leervgnfzahfn4ybui.streamlit.app/).

| # | Test case | Expected | Result | Screenshot |
|---|---|---|---|---|
| 1 | Normal invoice processed through the workflow | Rules applied, status + audit history shown | | [invoice processing](/Week04/Screenshots/invoice%20processing.png), [invoice workflow](/Week04/Screenshots/invoice%20workflow.png) |
| 2 | Normal resume analysed | Fields extracted and validated | | [resume analyze](/Week04/Screenshots/resume%20analyze.png) |
| 3 | Human review queue (Approve / Reject) | Status + audit history updated | | [invoice review](/Week04/Screenshots/invoice%20review.png) |
| 4 | Batch processing - invoices | One result per document, batch continues | | [invoice batch](/Week04/Screenshots/invoice%20batch%20normalization.png) |
| 5 | Batch processing - resumes | One result per document, batch continues | | [resume batch](/Week04/Screenshots/resume%20batch%20processing.png) |
| 6 | Workflow search & filters | Filters work, latest action + time shown | | [search for resume](/Week04/Screenshots/search%20for%20resume.png) |
| 7 | Metrics dashboard - invoices | Counts match the documents | | [invoice metrics](/Week04/Screenshots/invoice%20metrices.png) |
| 8 | Metrics dashboard - resumes | Counts match the documents | | [resume metrics](/Week04/Screenshots/resume%20metrices.png) |
| 9 | App overview / UI | All Week 5 tabs available | | [UI](/Week04/Screenshots/Ai%20doc%20analyzer%20UI.png) |
| 10 | Missing required field (e.g. resume without email) | Needs Review, field named | | not added yet |
| 11 | Invalid date / amount | Needs Review, failed fields named | | not added yet |
| 12 | Scanned / unreadable document | Failed or Needs Review | | not added yet |
| 13 | Duplicate upload | Blocked + audit event | | not added yet |
| 14 | Reject without a reason | Blocked, status unchanged | | not added yet |
| 15 | Automated tests (`python -m unittest -v test_workflow`) | 17 tests OK (incl. invalid transitions, DB/storage failure) | | not added yet |

Fill the **Result** column with Pass / Fail after checking each case on the live app.

### Screenshots
![App UI](/Week04/Screenshots/Ai%20doc%20analyzer%20UI.png)
![Invoice processing](/Week04/Screenshots/invoice%20processing.png)
![Invoice workflow](/Week04/Screenshots/invoice%20workflow.png)
![Invoice review queue](/Week04/Screenshots/invoice%20review.png)
![Invoice batch processing](/Week04/Screenshots/invoice%20batch%20normalization.png)
![Invoice metrics](/Week04/Screenshots/invoice%20metrices.png)
![Resume analysis](/Week04/Screenshots/resume%20analyze.png)
![Resume batch processing](/Week04/Screenshots/resume%20batch%20processing.png)
![Resume metrics](/Week04/Screenshots/resume%20metrices.png)
![Search for resume](/Week04/Screenshots/search%20for%20resume.png)
