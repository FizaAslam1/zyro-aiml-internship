"""
AI Document Intelligence & Workflow Platform - Week 5
Zyroo Internship Program

New in Week 5: workflow states + audit log, validation, rule-based workflow
engine, human review queue, batch processing, workflow search/filters and a
metrics dashboard.

This file contains UI code only. The logic lives in:
  pipeline.py (read/classify/extract/store/batch), workflow.py (states + rules),
  validator.py (field validation), audit.py (history), database.py (SQLite).
"""

import os
import json

import pandas as pd
import streamlit as st

import audit
import database as db
import pipeline
import workflow

db.init_db()
pipeline.ensure_folders()

st.set_page_config(page_title="AI Document Intelligence - Week 5", page_icon="📁", layout="wide")

STATUS_ICONS = {
    "New": "⚪", "Processing": "🔵", "Needs Review": "🟡", "Approved": "🟢",
    "Rejected": "🟠", "Completed": "✅", "Failed": "🔴",
}


# ----------------------------------------------------------------------
# UI HELPERS
# ----------------------------------------------------------------------

def status_badge(status: str) -> str:
    return f"{STATUS_ICONS.get(status, '⚪')} {status}"


def flash(kind: str, message: str):
    """Show a message after st.rerun() (normal messages vanish on rerun)."""
    st.session_state["flash"] = (kind, message)


def show_flash():
    item = st.session_state.pop("flash", None)
    if item:
        getattr(st, item[0])(item[1])


def fields_table(doc: dict):
    fields = json.loads(doc.get("fields_json") or "{}")
    results = json.loads(doc.get("validation_json") or "{}").get("results", {})
    if not fields:
        st.caption("No extracted fields stored yet (run the workflow for this document).")
        return
    icon = lambda r: ("✅ " if r == "OK" else "⚠️ " if r.startswith(("Warning", "Not provided"))
                      else "❌ " if r else "") + r
    rows = [{"Field": k, "Extracted value": str(v), "Validation": icon(results.get(k, ""))}
            for k, v in fields.items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def history_table(doc_id: int):
    history = audit.get_history(doc_id)
    if not history:
        st.caption("No history recorded.")
        return
    st.dataframe(pd.DataFrame(history)[
        ["timestamp", "action", "previous_status", "new_status", "reason"]
    ].rename(columns={"previous_status": "from", "new_status": "to"}),
        hide_index=True)


def show_document_detail(doc: dict, key_prefix: str):
    """key_prefix must be unique per call site so widget keys never clash.
    (No st.expander in here - this is shown inside expanders and they can't nest.)"""
    st.subheader(f"📄 {doc['original_filename']}")
    st.write(status_badge(doc["status"]))
    if doc.get("review_reason"):
        st.info(f"**Reason:** {doc['review_reason']}")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Document Type:** {doc['document_type']}")
        conf = doc.get("confidence")
        st.write("**Classifier confidence:** " +
                 (f"{conf:.2f}" if conf is not None else "not provided by classifier"))
        st.write(f"**Upload Date:** {doc['upload_date']}")
        st.write(f"**Company:** {doc['company'] or 'Not Found'}")
    with col2:
        st.write(f"**Invoice Number:** {doc['invoice_number'] or 'Not Found'}")
        st.write(f"**Total Amount:** {doc['total_amount'] or 'Not Found'}")
        st.write(f"**File Path:** `{doc['file_path']}`")
        if doc.get("last_action"):
            st.write(f"**Latest action:** {doc['last_action']} ({doc['last_action_time']})")

    st.write("**Extracted fields & validation:**")
    fields_table(doc)

    st.write("**Text Preview:**")
    st.text(doc["text_preview"] or "(no preview available)")

    st.write("**Workflow history:**")
    history_table(doc["id"])

    if doc["file_path"] and os.path.exists(doc["file_path"]):
        with open(doc["file_path"], "rb") as f:
            st.download_button(
                "⬇️ Download Original File",
                data=f.read(),
                file_name=doc["original_filename"],
                key=f"{key_prefix}_download_{doc['id']}",
            )
    else:
        st.warning("Stored file not found on disk.")


def reset_filters():
    st.session_state["f_keyword"] = ""
    st.session_state["f_type"] = "All"
    st.session_state["f_status"] = "All"
    st.session_state["f_sort"] = "Newest"


# ----------------------------------------------------------------------
# PAGE
# ----------------------------------------------------------------------

st.title(" AI Document Intelligence & Workflow Platform")
st.caption("Zyroo Internship Program • Week 5 • Advanced Document Workflow & Automation")
show_flash()

tab_upload, tab_browse, tab_review, tab_batch, tab_metrics = st.tabs(
    ["📤 Upload", "🔎 Search & Workflow", "🧑‍⚖️ Review Queue", "⚙️ Batch Processing", "📊 Metrics"]
)

# ------------------------- UPLOAD TAB ----------------------------------
with tab_upload:
    st.write("Upload a PDF or image. It is processed, validated, passed through the "
             "workflow rules and either completed automatically or sent to human review.")

    uploaded_files = st.file_uploader(
        "Upload document(s)", type=list(pipeline.ALLOWED_EXTENSIONS),
        accept_multiple_files=True,
    )

    # Streamlit re-runs this script on every click. Remember what was already
    # processed so a re-run does not re-process files or log fake "duplicates".
    processed = st.session_state.setdefault("processed_uploads", {})

    for uploaded_file in uploaded_files or []:
        st.divider()
        upload_key = f"{uploaded_file.name}-{pipeline.compute_file_hash(uploaded_file.getvalue())}"
        if upload_key not in processed:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                processed[upload_key] = pipeline.process_upload(uploaded_file)
        result = processed[upload_key]

        if not result["ok"]:
            st.error(f"❌ {uploaded_file.name}: {result['message']}")
            continue

        if result.get("duplicate"):
            st.warning(f"⚠️ Duplicate detected for **{uploaded_file.name}** — already stored as "
                       f"**{result['record']['original_filename']}**.")
            continue

        record = db.get_document_by_id(result["doc_id"])
        outcome = result["outcome"]
        if outcome["status"] == workflow.COMPLETED:
            st.success(f"✅ {uploaded_file.name} passed all rules and was completed automatically.")
        elif outcome["status"] == workflow.NEEDS_REVIEW:
            st.warning(f"🟡 {uploaded_file.name} was sent to the Review Queue: {outcome['reason']}")
        else:
            st.error(f"🔴 {uploaded_file.name} failed processing: {outcome['reason']}")

        st.write(f"**Document Type:** {record['document_type']}  |  "
                 f"**Status:** {status_badge(record['status'])}")
        st.write(f"*Extraction method: {result['extraction_method']}*")
        fields_table(record)
        with st.expander("View extracted text"):
            st.text(result["full_text"])

# ------------------------- SEARCH & WORKFLOW TAB -------------------------
with tab_browse:
    st.write("Search, filter and browse documents with their workflow status and latest action.")

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        keyword = st.text_input("Search (filename, type, company, invoice #...)", key="f_keyword")
    with col2:
        doc_type_filter = st.selectbox("Document Type", ["All", "Invoice", "Resume", "Other"],
                                       key="f_type")
    with col3:
        status_filter = st.selectbox("Workflow Status", ["All"] + workflow.STATES, key="f_status")
    with col4:
        sort_order = st.selectbox("Sort", ["Newest", "Oldest"], key="f_sort")

    st.button("🧹 Clear Filters", on_click=reset_filters)

    results = db.search_documents(keyword=keyword, doc_type=doc_type_filter,
                                  status=status_filter, sort_order=sort_order)
    st.write(f"**{len(results)} document(s) found**")

    if not results:
        st.info("No documents match your search/filters.")
    for doc in results:
        with st.expander(
            f"{STATUS_ICONS.get(doc['status'], '⚪')} {doc['original_filename']} — "
            f"{doc['document_type']} — {doc['status']} — "
            f"{doc['last_action'] or 'no action'} ({doc['last_action_time'] or '-'})"
        ):
            show_document_detail(doc, key_prefix=f"browse_{doc['id']}")

# ------------------------- REVIEW QUEUE TAB -----------------------------
with tab_review:
    st.write("Documents with missing, invalid or uncertain information wait here for a human decision.")
    queue = db.search_documents(status=workflow.NEEDS_REVIEW, sort_order="Oldest")
    st.write(f"**{len(queue)} document(s) waiting for review**")

    if not queue:
        st.success("The review queue is empty.")

    for i, doc in enumerate(queue):
        with st.expander(f"{doc['original_filename']} — {doc['document_type']} — "
                         f"{doc['review_reason'] or 'needs review'}", expanded=(i == 0)):
            st.write(f"**Filename:** {doc['original_filename']}")
            st.write(f"**Document type:** {doc['document_type']}   |   "
                     f"**Status:** {status_badge(doc['status'])}")
            st.warning(f"**Review reason:** {doc['review_reason'] or 'Not recorded'}")
            fields_table(doc)
            st.text(doc["text_preview"] or "(no preview available)")

            note = st.text_input("Reviewer note (required when rejecting)",
                                 key=f"review_note_{doc['id']}")
            approve_col, reject_col = st.columns(2)

            if approve_col.button("✅ Approve", key=f"approve_{doc['id']}"):
                try:
                    workflow.approve_document(doc["id"], note)
                    flash("success", f"{doc['original_filename']} approved and completed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not approve: {e}")

            if reject_col.button("❌ Reject", key=f"reject_{doc['id']}"):
                if not note.strip():
                    st.error("Please enter a short reason before rejecting.")
                else:
                    try:
                        workflow.reject_document(doc["id"], note)
                        flash("success", f"{doc['original_filename']} rejected.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not reject: {e}")

# ------------------------- BATCH TAB ------------------------------------
with tab_batch:
    st.write("Select stored documents and run the same workflow rules for each of them. "
             "Only **New**, **Needs Review** and **Failed** documents can be (re)run.")

    all_docs = db.get_all_documents()
    options = {f"#{d['id']} — {d['original_filename']} — {d['status']}": d["id"] for d in all_docs}
    runnable = [label for label, doc_id in options.items()
                if next(d for d in all_docs if d["id"] == doc_id)["status"]
                in workflow.RUNNABLE_STATES]

    select_all = st.checkbox(f"Select all runnable documents ({len(runnable)})")
    selected = st.multiselect("Documents", list(options),
                              default=runnable if select_all else [])

    if st.button("▶️ Run workflow on selected", disabled=not selected):
        bar = st.progress(0.0)
        st.session_state["batch"] = pipeline.run_batch(
            [options[label] for label in selected], progress=bar.progress)
        bar.empty()

    batch = st.session_state.get("batch")
    if batch:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Processed (auto-completed)", batch["processed"])
        c2.metric("Sent to review", batch["review"])
        c3.metric("Failed", batch["failed"])
        c4.metric("Skipped", batch["skipped"])
        st.dataframe(pd.DataFrame(batch["results"]).rename(columns={
            "id": "ID", "filename": "File", "outcome": "Result", "reason": "Reason"}),
            hide_index=True)

# ------------------------- METRICS TAB ----------------------------------
with tab_metrics:
    m = db.get_metrics()
    by_status = m["by_status"]
    handled = sum(by_status.get(s, 0) for s in
                  (workflow.NEEDS_REVIEW, workflow.APPROVED, workflow.REJECTED, workflow.COMPLETED))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total documents", m["total"])
    c2.metric("Processed", handled, help="Documents that went through the workflow "
              "successfully (Needs Review, Approved, Rejected or Completed).")
    c3.metric("Needing review", by_status.get(workflow.NEEDS_REVIEW, 0))
    c4.metric("Failed", by_status.get(workflow.FAILED, 0))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Approved", by_status.get(workflow.APPROVED, 0))
    c6.metric("Rejected", by_status.get(workflow.REJECTED, 0))
    c7.metric("Completed", by_status.get(workflow.COMPLETED, 0))
    c8.metric("Avg processing time",
              f"{m['avg_processing_seconds']:.2f}s" if m["avg_processing_seconds"] is not None else "n/a",
              help="Measured around read + classify + extract. n/a until a document is processed.")

    left, right = st.columns(2)
    with left:
        st.write("**Documents by type**")
        if m["by_type"]:
            st.bar_chart(pd.Series(m["by_type"], name="documents"))
    with right:
        st.write("**Documents by status**")
        if by_status:
            st.bar_chart(pd.Series(by_status, name="documents"))
