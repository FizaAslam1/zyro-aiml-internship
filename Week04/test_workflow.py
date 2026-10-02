"""
Automated workflow tests (Week 5).  Run:   python -m unittest -v test_workflow
(or `pytest -v`).  Uses a temporary database/storage folder - your real
documents.db and storage/ are never touched.
"""

import os
import shutil
import sqlite3
import tempfile
import unittest

import pymupdf

# --- run everything inside a temp directory ---------------------------------
_TMP = tempfile.mkdtemp(prefix="week5_tests_")
os.chdir(_TMP)

import audit                      # noqa: E402
import database as db             # noqa: E402
import pipeline                   # noqa: E402
import validator                  # noqa: E402
import workflow                   # noqa: E402

db.DB_PATH = os.path.join(_TMP, "test.db")


class FakeUpload:
    """Minimal stand-in for Streamlit's UploadedFile."""
    def __init__(self, name, data):
        self.name, self._data = name, data

    def getvalue(self):
        return self._data


def make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_text((50, 72), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


GOOD_INVOICE = ("Invoice Number: INV-2041\nDate: 12/09/2026\n"
                "Billed By: Acme Traders Ltd\nTotal: $1,250.00")
GOOD_RESUME = ("Fiza Aslam\nEmail: fiza@example.com\nPhone: +92 316 7430130\n"
               "Skills: Python, SQL, Machine Learning\nEducation: BS IT\nExperience: ML Intern")


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists(db.DB_PATH):
            os.remove(db.DB_PATH)
        shutil.rmtree("storage", ignore_errors=True)
        db.init_db()
        pipeline.ensure_folders()

    def upload(self, name, text):
        return pipeline.process_upload(FakeUpload(name, make_pdf(text)))

    def status(self, doc_id):
        return db.get_document_by_id(doc_id)["status"]

    # ---- 1-2: normal invoice and resume complete automatically ------------
    def test_normal_invoice_completes(self):
        r = self.upload("invoice_ok.pdf", GOOD_INVOICE)
        self.assertEqual(r["outcome"]["status"], "Completed")
        self.assertIsNone(db.get_document_by_id(r["doc_id"])["confidence"])  # never invented

    def test_normal_resume_completes(self):
        r = self.upload("resume_ok.pdf", GOOD_RESUME)
        self.assertEqual(r["outcome"]["status"], "Completed")

    # ---- 3: missing required fields -> Needs Review -----------------------
    def test_missing_fields_need_review(self):
        r = self.upload("resume_no_email.pdf", GOOD_RESUME.replace("Email: fiza@example.com\n", ""))
        self.assertEqual(r["outcome"]["status"], "Needs Review")
        self.assertIn("Email", r["outcome"]["reason"])

    # ---- 4: invalid date / amount recorded exactly ------------------------
    def test_invalid_date_and_amount(self):
        r = self.upload("invoice_bad.pdf",
                        "Invoice Number: INV-2042\nDate: 45/13/2026\nBilled By: Acme Traders\nTotal: 0")
        self.assertEqual(r["outcome"]["status"], "Needs Review")
        v = validator.validate_document("Invoice", {
            "Invoice Number": "INV-2042", "Date": "45/13/2026",
            "Company Name": "Acme Traders", "Total Amount": "0"})
        self.assertEqual(set(v["failed_fields"]), {"Date", "Total Amount"})

    # ---- 5: Week 4 bug case: invoice number "DataFrame" -------------------
    def test_dataframe_invoice_number_is_rejected_by_validation(self):
        r = self.upload("sample_invoice_dataframe.pdf",
                        "Sample Invoice DataFrame\nInvoice_ID\nCustomer\nProduct\nQuantity")
        self.assertEqual(r["outcome"]["status"], "Needs Review")
        doc = db.get_document_by_id(r["doc_id"])
        self.assertIn("Invoice Number", doc["review_reason"])

    # ---- 6: unrecognised type -> Needs Review -----------------------------
    def test_other_type_needs_review(self):
        r = self.upload("note.pdf", "Hello, this is just a random note about lunch plans.")
        self.assertEqual(r["outcome"]["status"], "Needs Review")
        self.assertIn("Unrecognised", r["outcome"]["reason"])

    # ---- 7: unreadable document -> Failed (and can be retried) ------------
    def test_unreadable_document_fails(self):
        r = self.upload("blank.pdf", "")
        self.assertEqual(r["outcome"]["status"], "Failed")
        self.assertTrue(workflow.can_transition("Failed", "Processing"))

    # ---- 8: duplicate ------------------------------------------------------
    def test_duplicate_is_detected_and_logged(self):
        data = make_pdf(GOOD_INVOICE)      # same bytes -> same SHA-256 hash
        first = pipeline.process_upload(FakeUpload("a.pdf", data))
        again = pipeline.process_upload(FakeUpload("a_copy.pdf", data))
        self.assertTrue(again["duplicate"])
        actions = [h["action"] for h in audit.get_history(first["doc_id"])]
        self.assertIn("Duplicate upload blocked", actions)

    # ---- 9: optional phone problem is only a warning ----------------------
    def test_bad_phone_is_warning_only(self):
        v = validator.validate_document("Resume", {
            "Name": "Fiza Aslam", "Email": "fiza@example.com",
            "Skills": "Python, SQL", "Phone": "12"})
        self.assertTrue(v["valid"])
        self.assertIn("Phone", v["warnings"])

    # ---- 10: whole-line "name" (OCR style) is flagged ---------------------
    def test_long_name_line_is_invalid(self):
        v = validator.validate_document("Resume", {
            "Name": "FIZA ASLAM ML Engineer | Predictive Maintenance, NLP & Model Deployment",
            "Email": "fiza@example.com", "Skills": "Python"})
        self.assertIn("Name", v["invalid"])

    # ---- 11: confidence rule only when a confidence exists ----------------
    def test_confidence_rule(self):
        ok = validator.validate_document("Invoice", {
            "Invoice Number": "INV-1", "Date": "01/02/2026", "Company Name": "Acme", "Total Amount": "10"})
        # INV-1 is only 5 chars -> valid format (3-30 chars, has a digit)
        self.assertEqual(workflow.decide("Invoice", ok, confidence=None).action, "complete")
        low = workflow.decide("Invoice", ok, confidence=0.40)
        self.assertEqual(low.action, "needs_review")
        self.assertIn("Low classification confidence", low.reason)
        self.assertEqual(workflow.decide("Invoice", ok, confidence=0.95).action, "complete")

    # ---- 12: invalid transitions are blocked ------------------------------
    def test_invalid_transitions_blocked(self):
        r = self.upload("a.pdf", GOOD_INVOICE)           # now Completed
        with self.assertRaises(workflow.InvalidTransition):
            workflow.transition(r["doc_id"], "Approved", "x")
        with self.assertRaises(workflow.InvalidTransition):
            workflow.approve_document(r["doc_id"])        # not in review
        self.assertEqual(self.status(r["doc_id"]), "Completed")
        # nothing was written to the audit log for the blocked attempts
        self.assertEqual(audit.get_history(r["doc_id"])[-1]["new_status"], "Completed")

    # ---- 13: review actions update status + audit -------------------------
    def test_approve_and_reject_update_audit(self):
        a = self.upload("a.pdf", GOOD_RESUME.replace("Email: fiza@example.com\n", ""))
        b = self.upload("b.pdf", "Hello this is a random note")
        workflow.approve_document(a["doc_id"], "Email checked manually")
        self.assertEqual(self.status(a["doc_id"]), "Completed")
        actions = [h["action"] for h in audit.get_history(a["doc_id"])]
        self.assertEqual(actions, ["Document uploaded", "Processing started",
                                   "Sent to human review", "Approved by reviewer",
                                   "Workflow completed"])
        with self.assertRaises(ValueError):               # reason required
            workflow.reject_document(b["doc_id"], "   ")
        self.assertEqual(self.status(b["doc_id"]), "Needs Review")
        workflow.reject_document(b["doc_id"], "Not a business document")
        self.assertEqual(self.status(b["doc_id"]), "Rejected")
        self.assertEqual(audit.get_history(b["doc_id"])[-1]["reason"], "Not a business document")

    # ---- 14: storage / database failures ----------------------------------
    def test_storage_and_database_failure(self):
        real_store, real_insert = pipeline.store_file, db.insert_document
        try:
            pipeline.store_file = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
            r = self.upload("a.pdf", GOOD_INVOICE)
            self.assertFalse(r["ok"]); self.assertIn("Could not save file", r["message"])
            pipeline.store_file = real_store

            db.insert_document = lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("locked"))
            r = self.upload("b.pdf", GOOD_RESUME)
            self.assertFalse(r["ok"]); self.assertIn("Database error", r["message"])
            leftovers = [f for _, _, fs in os.walk("storage") for f in fs]
            self.assertEqual(leftovers, [])               # no orphan files
        finally:
            pipeline.store_file, db.insert_document = real_store, real_insert

    # ---- 15: mixed-success batch ------------------------------------------
    def test_mixed_batch_continues_after_failure(self):
        ok = self.upload("ok.pdf", GOOD_INVOICE)                       # Completed -> Skipped
        review = self.upload("r.pdf", GOOD_RESUME.replace("Email: fiza@example.com\n", ""))
        # A Needs Review doc whose stored file was deleted -> fails alone
        broken = self.upload("n.pdf", "Hello this is a random note")
        os.remove(db.get_document_by_id(broken["doc_id"])["file_path"])

        batch = pipeline.run_batch([ok["doc_id"], review["doc_id"], broken["doc_id"], 9999])
        outcomes = {r["id"]: r["outcome"] for r in batch["results"]}
        self.assertEqual(outcomes[ok["doc_id"]], "Skipped")
        self.assertEqual(outcomes[review["doc_id"]], "Needs Review")
        self.assertEqual(outcomes[broken["doc_id"]], "Failed")
        self.assertEqual(outcomes[9999], "Failed")
        self.assertEqual(len(batch["results"]), 4)                     # one result per document
        self.assertEqual((batch["review"], batch["failed"], batch["skipped"]), (1, 2, 1))

    # ---- 16: search / filters / metrics -----------------------------------
    def test_search_filters_and_metrics(self):
        self.upload("invoice_ok.pdf", GOOD_INVOICE)
        self.upload("resume_ok.pdf", GOOD_RESUME)
        self.upload("note.pdf", "Hello this is a random note")
        self.assertEqual(len(db.search_documents(status="Completed")), 2)
        self.assertEqual(len(db.search_documents(status="Needs Review")), 1)
        hit = db.search_documents(keyword="INV-2041")
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["last_action"], "Auto-completed by rules")
        self.assertTrue(hit[0]["last_action_time"])
        m = db.get_metrics()
        self.assertEqual(m["total"], 3)
        self.assertEqual(m["by_status"], {"Completed": 2, "Needs Review": 1})
        self.assertEqual(m["by_type"], {"Invoice": 1, "Resume": 1, "Other": 1})
        self.assertIsNotNone(m["avg_processing_seconds"])

    # ---- 17: Week 4 database is migrated, nothing lost ---------------------
    def test_week4_database_migration(self):
        old = os.path.join(_TMP, "week4.db")
        conn = sqlite3.connect(old)
        conn.execute("""CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL, stored_filename TEXT NOT NULL, document_type TEXT,
            upload_date TEXT, company TEXT, invoice_number TEXT, total_amount TEXT,
            file_path TEXT, text_preview TEXT, file_hash TEXT UNIQUE, status TEXT)""")
        conn.execute("INSERT INTO documents (original_filename, stored_filename, document_type, "
                     "file_hash, status) VALUES ('cv.pdf','x.pdf','Resume','h1','Processed')")
        conn.commit(); conn.close()

        db.DB_PATH = old
        try:
            db.init_db(); db.init_db()                    # running twice must be safe
            doc = db.get_document_by_id(1)
            self.assertEqual((doc["original_filename"], doc["status"]), ("cv.pdf", "New"))
            history = audit.get_history(1)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["previous_status"], "Processed")
        finally:
            db.DB_PATH = os.path.join(_TMP, "test.db")


if __name__ == "__main__":
    unittest.main(verbosity=2)
