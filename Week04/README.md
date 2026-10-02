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
| `screenshots/` | Testing evidence (see "Testing evidence" below) |

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
All screenshots are in the [`screenshots/`](screenshots/) folder, taken on the live app
(https://zyro-aiml-internship-wrh2leervgnfzahfn4ybui.streamlit.app/).

```
screenshots/
  01_normal_invoice.png
  02_normal_resume.png
  03_missing_email.png
  04_invalid_date_amount.png
  05_scanned_document.png
  06_duplicate_upload.png
  07_unrecognised_document.png
  08_reject_without_reason.png
  09_approve_reject_audit.png
  10_mixed_batch.png
  11_search_filters.png
  12_metrics_dashboard.png
  13_audit_history.png
  14_unit_tests_passing.png
```

| # | Test case | Expected | Result | Screenshot |
|---|---|---|---|---|
| 1 | Normal invoice | Completed automatically | | [01](screenshots/01_normal_invoice.png) |
| 2 | Normal resume | Completed automatically | | [02](screenshots/02_normal_resume.png) |
| 3 | Resume without email | Needs Review, "Email" named | | [03](screenshots/03_missing_email.png) |
| 4 | Invoice with invalid date / amount | Needs Review, failed fields named | | [04](screenshots/04_invalid_date_amount.png) |
| 5 | Scanned / unreadable document | Failed or Needs Review | | [05](screenshots/05_scanned_document.png) |
| 6 | Duplicate upload | Blocked + audit event | | [06](screenshots/06_duplicate_upload.png) |
| 7 | Unrecognised document | Needs Review | | [07](screenshots/07_unrecognised_document.png) |
| 8 | Reject without a reason | Blocked, status unchanged | | [08](screenshots/08_reject_without_reason.png) |
| 9 | Approve / Reject in review queue | Status + audit history updated | | [09](screenshots/09_approve_reject_audit.png) |
| 10 | Mixed-success batch | One result per document, batch continues | | [10](screenshots/10_mixed_batch.png) |
| 11 | Workflow search & filters | Filters work, latest action + time shown | | [11](screenshots/11_search_filters.png) |
| 12 | Metrics dashboard | Counts match the documents | | [12](screenshots/12_metrics_dashboard.png) |
| 13 | Audit history of one document | Full trail visible | | [13](screenshots/13_audit_history.png) |
| 14 | Automated tests (`python -m unittest -v test_workflow`) | 17 tests OK (covers invalid transitions, DB/storage failure) | | [14](screenshots/14_unit_tests_passing.png) |

Fill the **Result** column with Pass / Fail after testing on the live app.
