"""
database.py
SQLite database layer for the AI Document Intelligence & Workflow Platform.
Keeps all database logic separate from the Streamlit interface (app.py).

Week 5 changes (all ADDITIVE - existing data is kept):
  * new workflow columns on `documents`
  * new `audit_log` table
  * one-time migration of Week 4 statuses -> workflow state "New"
  * search_documents() also returns the latest workflow action + timestamp
  * get_metrics() for the dashboard
"""

import sqlite3
from datetime import datetime

DB_PATH = "documents.db"

# Columns added in Week 5 (added with ALTER TABLE if missing)
WORKFLOW_COLUMNS = {
    "predicted_type": "TEXT",       # classifier output
    "confidence": "REAL",           # NULL unless the classifier really provides one
    "fields_json": "TEXT",          # all extracted fields (JSON)
    "validation_json": "TEXT",      # validation result (JSON)
    "review_reason": "TEXT",        # why the document needs review / failed
    "extraction_method": "TEXT",
    "processing_seconds": "REAL",   # measured around the real processing step
}


def get_connection():
    """Create (if needed) and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Create tables if needed and upgrade an older (Week 4) database."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            document_type TEXT,
            upload_date TEXT,
            company TEXT,
            invoice_number TEXT,
            total_amount TEXT,
            file_path TEXT,
            text_preview TEXT,
            file_hash TEXT UNIQUE,
            status TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            timestamp TEXT NOT NULL,
            reason TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_doc ON audit_log(document_id)")

    existing = {r["name"] for r in conn.execute("PRAGMA table_info(documents)")}
    is_week4_db = "fields_json" not in existing
    for name, col_type in WORKFLOW_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {col_type}")

    if is_week4_db:
        # Week 4 statuses (Processed / Needs Review / Failed) had no validation behind
        # them. Reset them to "New" so they can be run through the Week 5 workflow.
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in conn.execute("SELECT id, status FROM documents").fetchall():
            conn.execute("UPDATE documents SET status = 'New' WHERE id = ?", (row["id"],))
            conn.execute(
                "INSERT INTO audit_log (document_id, action, previous_status, new_status, "
                "timestamp, reason) VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], "Migrated from Week 4", row["status"], "New", now,
                 "Legacy status reset; run the workflow to validate this document"),
            )
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# CREATE
# ----------------------------------------------------------------------

def insert_document(data: dict) -> int:
    """
    Insert a new document record (file_hash required). Returns the new row's id.
    New documents start in workflow state "New".
    """
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO documents (
            original_filename, stored_filename, document_type, upload_date,
            company, invoice_number, total_amount, file_path,
            text_preview, file_hash, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("original_filename"),
        data.get("stored_filename"),
        data.get("document_type"),
        data.get("upload_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        data.get("company"),
        data.get("invoice_number"),
        data.get("total_amount"),
        data.get("file_path"),
        data.get("text_preview"),
        data.get("file_hash"),
        data.get("status", "New"),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ----------------------------------------------------------------------
# READ
# ----------------------------------------------------------------------

def get_document_by_hash(file_hash: str):
    """Return the existing document row with this hash, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_document_by_id(doc_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def search_documents(keyword: str = "", doc_type: str = "All",
                      status: str = "All", sort_order: str = "Newest") -> list:
    """
    Search/filter/sort documents using SQL directly. Each row also carries the
    latest workflow action (`last_action`) and its timestamp (`last_action_time`).
    """
    query = """
        SELECT d.*, a.action AS last_action, a.timestamp AS last_action_time
        FROM documents d
        LEFT JOIN audit_log a
          ON a.id = (SELECT MAX(id) FROM audit_log WHERE document_id = d.id)
        WHERE 1=1
    """
    params = []

    if keyword:
        like = f"%{keyword}%"
        query += """ AND (
            d.original_filename LIKE ? OR
            d.company LIKE ? OR
            d.invoice_number LIKE ? OR
            d.document_type LIKE ? OR
            d.text_preview LIKE ?
        )"""
        params.extend([like] * 5)

    if doc_type != "All":
        query += " AND d.document_type = ?"
        params.append(doc_type)

    if status != "All":
        query += " AND d.status = ?"
        params.append(status)

    query += " ORDER BY d.upload_date " + ("DESC" if sort_order == "Newest" else "ASC")
    query += ", d.id " + ("DESC" if sort_order == "Newest" else "ASC")

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_documents() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY upload_date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_metrics() -> dict:
    """Numbers for the workflow metrics dashboard."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    by_status = {r[0]: r[1] for r in conn.execute(
        "SELECT status, COUNT(*) FROM documents GROUP BY status")}
    by_type = {r[0] or "Unknown": r[1] for r in conn.execute(
        "SELECT document_type, COUNT(*) FROM documents GROUP BY document_type")}
    avg_seconds = conn.execute(
        "SELECT AVG(processing_seconds) FROM documents WHERE processing_seconds IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "by_status": by_status, "by_type": by_type,
            "avg_processing_seconds": avg_seconds}


# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------

def update_status(doc_id: int, status: str):
    """Raw status write. Prefer workflow.transition(), which validates the change
    and writes the audit log."""
    conn = get_connection()
    conn.execute("UPDATE documents SET status = ? WHERE id = ?", (status, doc_id))
    conn.commit()
    conn.close()


def update_document(doc_id: int, data: dict):
    """Update any subset of fields for a document by id."""
    if not data:
        return
    columns = ", ".join(f"{key} = ?" for key in data.keys())
    values = list(data.values()) + [doc_id]
    conn = get_connection()
    conn.execute(f"UPDATE documents SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# DELETE
# ----------------------------------------------------------------------

def delete_document(doc_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
