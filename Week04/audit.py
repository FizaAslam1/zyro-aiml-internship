"""
audit.py
Workflow history / audit logging (Week 5).

Every important workflow event is stored in the `audit_log` table so a
document's full history can be traced:
    document_id, action, previous_status, new_status, timestamp, reason
"""

from datetime import datetime

import database as db


def log_event(document_id: int, action: str, previous_status, new_status,
              reason: str = "", conn=None) -> None:
    """
    Record one audit event.
    If `conn` is given the row is written on that connection WITHOUT committing,
    so the caller can commit it together with a status update (one transaction).
    """
    own = conn is None
    if own:
        conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_log (document_id, action, previous_status, "
            "new_status, timestamp, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, action, previous_status, new_status,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason or ""),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def get_history(document_id: int) -> list:
    """All events for one document, oldest first."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE document_id = ? ORDER BY id ASC",
        (document_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_events(limit: int = 50) -> list:
    """Latest events across all documents, newest first."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT a.*, d.original_filename FROM audit_log a "
        "LEFT JOIN documents d ON d.id = a.document_id "
        "ORDER BY a.id DESC LIMIT ?", (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
