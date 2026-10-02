# Week 5 - Advanced Document Workflow & Automation

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

## Run
```
pip install -r requirements.txt
streamlit run app.py
python -m unittest -v test_workflow
```

## Testing log (fill in with your own screenshots)
| # | Case | Expected | Result |
|---|---|---|---|
| 1 | Normal invoice | Completed | |
| 2 | Normal resume | Completed | |
| 3 | Resume without email | Needs Review | |
| 4 | Invoice with invalid date / amount | Needs Review (fields named) | |
| 5 | Scanned / unreadable document | Failed or Needs Review | |
| 6 | Duplicate upload | Blocked + audit event | |
| 7 | Unrecognised document | Needs Review | |
| 8 | Reject without reason | Blocked | |
| 9 | Approve / Reject | Status + audit updated | |
| 10 | Mixed batch | One result per doc, batch continues | |
