"""
database.py
SQLite database layer for the AI Document Intelligence & Workflow Platform.
Keeps all database logic separate from the Streamlit interface (app.py).
"""

import sqlite3
from datetime import datetime

DB_PATH = "documents.db"


def get_connection():
    """Create (if needed) and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Create the documents table if it doesn't already exist."""
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
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# CREATE
# ----------------------------------------------------------------------

def insert_document(data: dict) -> int:
    """
    Insert a new document record.
    `data` should contain keys matching the table columns (file_hash required).
    Returns the new row's id.
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
        data.get("status"),
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
    Search/filter/sort documents using SQL directly (not loading everything
    into Python first).
    """
    query = "SELECT * FROM documents WHERE 1=1"
    params = []

    if keyword:
        like = f"%{keyword}%"
        query += """ AND (
            original_filename LIKE ? OR
            company LIKE ? OR
            invoice_number LIKE ? OR
            document_type LIKE ? OR
            text_preview LIKE ?
        )"""
        params.extend([like, like, like, like, like])

    if doc_type != "All":
        query += " AND document_type = ?"
        params.append(doc_type)

    if status != "All":
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY upload_date " + ("DESC" if sort_order == "Newest" else "ASC")

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_documents() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY upload_date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------

def update_status(doc_id: int, status: str):
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
