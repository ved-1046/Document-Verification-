"""
ChangeMap — compare extracted fields between consecutive document versions.

When a submitter replaces a document, reviewers see which fields changed,
which stayed the same, and which became unreadable.
"""
from sqlalchemy.orm import Session

from app.models.document_version import DocumentVersion, DocType
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.services.document_processing.normalizer import FIELD_NAMES


def _latest_fields_for_doc(db: Session, doc_id: int) -> tuple[dict[str, str | None] | None, str]:
    run = (
        db.query(ExtractionRun)
        .filter(ExtractionRun.document_version_id == doc_id)
        .order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc())
        .first()
    )
    if not run or run.status != ExtractionStatus.success:
        return None, run.status.value if run else "not_started"

    fields = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.extraction_run_id == run.id,
            ExtractedField.field_name != "_raw_page_text",
        )
        .all()
    )
    out = {name: None for name in FIELD_NAMES}
    for f in fields:
        if f.field_name in out:
            out[f.field_name] = f.normalized_value or f.extracted_value
    return out, "success"


def _diff_pair(old: dict[str, str | None], new: dict[str, str | None],
               old_id: int, new_id: int) -> list[dict]:
    diffs: list[dict] = []
    for name in FIELD_NAMES:
        ov, nv = old.get(name), new.get(name)
        if ov is None and nv is None:
            continue
        if ov is None and nv is not None:
            status = "added"
        elif ov is not None and nv is None:
            status = "removed" if ov else "unreadable"
        elif ov == nv:
            status = "unchanged"
        else:
            status = "changed"
        diffs.append({
            "field_name": name,
            "old_value": ov,
            "new_value": nv,
            "status": status,
            "old_version_id": old_id,
            "new_version_id": new_id,
        })
    return diffs


def build_changemap(db: Session, request_id: int) -> dict:
    """Return per-doc-type field diffs between the two most recent versions."""
    result: list[dict] = []
    for doc_type in DocType:
        versions = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.request_id == request_id,
                DocumentVersion.doc_type == doc_type,
            )
            .order_by(DocumentVersion.version_number.asc(), DocumentVersion.id.asc())
            .all()
        )
        if len(versions) < 2:
            continue
        prev, curr = versions[-2], versions[-1]
        old_fields, old_status = _latest_fields_for_doc(db, prev.id)
        new_fields, new_status = _latest_fields_for_doc(db, curr.id)
        comparison_status = (
            "ready" if old_fields is not None and new_fields is not None
            else "failed" if "failed" in {old_status, new_status}
            else "processing"
        )
        result.append({
            "doc_type": doc_type.value,
            "previous_version_id": prev.id,
            "current_version_id": curr.id,
            "previous_extraction_status": old_status,
            "current_extraction_status": new_status,
            "field_diffs": (
                _diff_pair(old_fields, new_fields, prev.id, curr.id)
                if old_fields is not None and new_fields is not None else []
            ),
            "comparison_status": comparison_status,
        })
    return {"request_id": request_id, "changes": result}
