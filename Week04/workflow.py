"""
workflow.py
Workflow states, transition rules and the rule-based decision engine (Week 5).

This module has NO Streamlit code. app.py only calls it.

    Upload -> Process -> Classify -> Extract -> Validate -> Apply Rules
           -> Review / Approve / Reject -> Complete -> Audit History
"""

from dataclasses import dataclass, field

import audit
import database as db

# ----------------------------------------------------------------------
# STATES + VALID TRANSITIONS
# ----------------------------------------------------------------------

NEW = "New"
PROCESSING = "Processing"
NEEDS_REVIEW = "Needs Review"
APPROVED = "Approved"
REJECTED = "Rejected"
COMPLETED = "Completed"
FAILED = "Failed"        # processing error (no text / storage problem); can be retried

STATES = [NEW, PROCESSING, NEEDS_REVIEW, APPROVED, REJECTED, COMPLETED, FAILED]

ALLOWED_TRANSITIONS = {
    NEW: {PROCESSING},
    PROCESSING: {NEEDS_REVIEW, COMPLETED, FAILED},
    NEEDS_REVIEW: {APPROVED, REJECTED, PROCESSING},   # PROCESSING = re-run the workflow
    APPROVED: {COMPLETED},
    REJECTED: set(),                                  # final
    COMPLETED: set(),                                 # final
    FAILED: {PROCESSING},                             # retry
}

# Documents in these states may be (re)run through the workflow (batch / retry)
RUNNABLE_STATES = {NEW, NEEDS_REVIEW, FAILED}


class InvalidTransition(Exception):
    """Raised when a state change is not allowed."""


def can_transition(current: str, new: str) -> bool:
    return new in ALLOWED_TRANSITIONS.get(current, set())


def transition(doc_id: int, new_status: str, action: str, reason: str = "") -> None:
    """
    Move a document to `new_status` if the transition is valid, and write the
    audit event in the SAME database transaction as the status change.
    """
    doc = db.get_document_by_id(doc_id)
    if doc is None:
        raise ValueError(f"Document {doc_id} not found")
    previous = doc["status"]

    if not can_transition(previous, new_status):
        raise InvalidTransition(f"Invalid transition: {previous} -> {new_status}")

    conn = db.get_connection()
    try:
        cur = conn.execute(
            "UPDATE documents SET status = ? WHERE id = ? AND status = ?",
            (new_status, doc_id, previous),
        )
        if cur.rowcount == 0:  # someone else changed it in between
            raise InvalidTransition(f"Document {doc_id} is no longer in state {previous}")
        audit.log_event(doc_id, action, previous, new_status, reason, conn=conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ----------------------------------------------------------------------
# RULE-BASED DECISION ENGINE
# Edit the settings / RULES list below to change behaviour - no UI changes.
# ----------------------------------------------------------------------

# Classifications with confidence BELOW this go to Needs Review.
# Only used when the classifier actually returns a confidence value.
# (The current rule-based classifier returns none, so this is skipped.)
CONFIDENCE_THRESHOLD = 0.70


@dataclass
class Decision:
    action: str                      # "needs_review" or "complete"
    reason: str
    review_reasons: list = field(default_factory=list)


def _rule_unknown_type(doc_type, validation, confidence, threshold):
    if doc_type not in ("Invoice", "Resume"):
        return "Unrecognised document type"


def _rule_missing_fields(doc_type, validation, confidence, threshold):
    if validation["missing"]:
        return "Missing required fields: " + ", ".join(validation["missing"])


def _rule_invalid_fields(doc_type, validation, confidence, threshold):
    if validation["invalid"]:
        details = "; ".join(f"{k} ({v})" for k, v in validation["invalid"].items())
        return "Invalid fields: " + details


def _rule_low_confidence(doc_type, validation, confidence, threshold):
    if confidence is not None and confidence < threshold:   # never invent a confidence
        return f"Low classification confidence ({confidence:.2f} < {threshold:.2f})"


RULES = [_rule_unknown_type, _rule_missing_fields, _rule_invalid_fields, _rule_low_confidence]


def decide(document_type: str, validation: dict, confidence=None,
           threshold: float = CONFIDENCE_THRESHOLD) -> Decision:
    """Apply every rule. Any triggered rule sends the document to review."""
    reasons = []
    for rule in RULES:
        reason = rule(document_type, validation, confidence, threshold)
        if reason:
            reasons.append(reason)
    if reasons:
        return Decision("needs_review", " | ".join(reasons), reasons)
    return Decision("complete", "All validation rules passed", [])


# ----------------------------------------------------------------------
# HUMAN REVIEW ACTIONS
# ----------------------------------------------------------------------

def approve_document(doc_id: int, note: str = "") -> None:
    transition(doc_id, APPROVED, "Approved by reviewer", (note or "").strip())
    transition(doc_id, COMPLETED, "Workflow completed", "Completed after approval")


def reject_document(doc_id: int, reason: str) -> None:
    if not (reason or "").strip():
        raise ValueError("A reason is required to reject a document")
    transition(doc_id, REJECTED, "Rejected by reviewer", reason.strip())
