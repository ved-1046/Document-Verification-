"""
Evidence Impact Graph Builder service.

Builds a structured directed graph connecting:
1. Uploaded Documents (DocumentVersion)
2. Extracted Fields (ExtractedField + ReviewerCorrection)
3. Verification Findings (VerificationCheck)
4. Decision Impact (Request status + workflow resolution)

All nodes, scores, and relationships are computed from genuine database records.
No simulated or fabricated data is ever injected.
"""
from typing import Any, Dict, List, Optional, Set
import json
from sqlalchemy.orm import Session

from app.models.document_version import DocumentVersion, DocType, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.verification_check import (
    VerificationCheck, CheckType, CheckResult, CheckSeverity, ResolutionStatus,
)
from app.models.reviewer_correction import ReviewerCorrection
from app.models.request import Request, RequestStatus
from app.models.user import User


def build_evidence_graph(db: Session, request_id: int) -> Dict[str, Any]:
    """
    Construct the complete Evidence Impact Graph data structure for a request.
    """
    req = db.get(Request, request_id)
    if not req:
        return {"error": "Request not found", "nodes": [], "edges": []}

    # 1. Fetch all documents for this request
    docs = db.query(DocumentVersion).filter(
        DocumentVersion.request_id == request_id
    ).order_by(DocumentVersion.uploaded_at.asc(), DocumentVersion.version_number.asc()).all()

    # 2. Fetch all corrections for this request
    corrections = db.query(ReviewerCorrection).filter(
        ReviewerCorrection.request_id == request_id
    ).all()
    corrections_map: Dict[tuple[int, str], ReviewerCorrection] = {
        (c.document_version_id, c.field_name): c for c in corrections
    }

    # 3. Fetch all current verification checks
    checks = db.query(VerificationCheck).filter(
        VerificationCheck.request_id == request_id,
        VerificationCheck.is_current.is_(True),
    ).order_by(VerificationCheck.created_at.asc()).all()

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    field_node_ids_by_name_and_doc: Dict[tuple[int, str], str] = {}
    field_node_ids_by_name: Dict[str, List[str]] = {}

    total_extracted_fields = 0
    high_confidence_fields = 0

    # ── 1. Create Document Nodes & Field Nodes ────────────────────────────────
    for doc in docs:
        doc_node_id = f"doc_{doc.id}"
        doc_type_label = doc.doc_type.value.replace("_", " ").title()
        doc_status = "ready" if doc.processing_status == ProcessingStatus.ready else (
            "error" if doc.processing_status == ProcessingStatus.failed else "pending"
        )

        nodes.append({
            "id": doc_node_id,
            "type": "document",
            "label": f"{doc_type_label} v{doc.version_number}",
            "status": doc_status,
            "data": {
                "document_id": doc.id,
                "doc_type": doc.doc_type.value,
                "version_number": doc.version_number,
                "original_filename": doc.original_filename,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "processing_status": doc.processing_status.value,
                "processing_error": doc.processing_error,
            },
        })

        # Fetch latest extraction run for this document
        latest_run = db.query(ExtractionRun).filter(
            ExtractionRun.document_version_id == doc.id
        ).order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc()).first()

        if latest_run and latest_run.status == ExtractionStatus.success:
            fields = db.query(ExtractedField).filter(
                ExtractedField.extraction_run_id == latest_run.id
            ).all()

            for field in fields:
                # Filter out internal raw text pseudo-fields
                if field.field_name == "_raw_page_text":
                    continue

                total_extracted_fields += 1
                if field.confidence is not None and field.confidence >= 0.85:
                    high_confidence_fields += 1

                field_node_id = f"field_{doc.id}_{field.field_name}"
                field_node_ids_by_name_and_doc[(doc.id, field.field_name)] = field_node_id
                field_node_ids_by_name.setdefault(field.field_name, []).append(field_node_id)

                correction = corrections_map.get((doc.id, field.field_name))
                is_corrected = correction is not None
                effective_val = correction.corrected_value if is_corrected else (
                    field.normalized_value or field.extracted_value
                )

                field_status = "verified" if (
                    is_corrected or (field.confidence is not None and field.confidence >= 0.8)
                ) else ("warning" if (field.confidence is not None and field.confidence < 0.6) else "detected")

                clean_name = field.field_name.replace("_", " ").title()

                nodes.append({
                    "id": field_node_id,
                    "type": "field",
                    "label": clean_name,
                    "status": field_status,
                    "data": {
                        "field_id": field.id,
                        "field_name": field.field_name,
                        "display_name": clean_name,
                        "extracted_value": field.extracted_value,
                        "normalized_value": field.normalized_value,
                        "effective_value": effective_val,
                        "confidence": field.confidence,
                        "bounding_box": field.bounding_box,
                        "page_number": field.page_number,
                        "document_id": doc.id,
                        "document_type": doc.doc_type.value,
                        "is_corrected": is_corrected,
                        "corrected_value": correction.corrected_value if correction else None,
                        "correction_reason": correction.reason if correction else None,
                    },
                })

                # Edge from Document to Field
                edges.append({
                    "id": f"edge_{doc_node_id}_{field_node_id}",
                    "source": doc_node_id,
                    "target": field_node_id,
                    "label": "extracted",
                    "status": field_status,
                })

    # ── 2. Create Verification Finding Nodes & Connect to Fields ──────────────
    passed_findings = 0
    flagged_findings = 0
    error_findings = 0
    resolved_findings = 0

    for check in checks:
        check_node_id = f"check_{check.id}"

        if check.result == CheckResult.pass_:
            passed_findings += 1
            check_status = "verified"
        elif check.result == CheckResult.flag:
            flagged_findings += 1
            check_status = "resolved" if check.resolution_status in (ResolutionStatus.resolved, ResolutionStatus.dismissed) else "warning"
        elif check.result == CheckResult.error:
            error_findings += 1
            check_status = "resolved" if check.resolution_status in (ResolutionStatus.resolved, ResolutionStatus.dismissed) else "error"
        else:
            check_status = "info"

        if check.resolution_status in (ResolutionStatus.resolved, ResolutionStatus.dismissed):
            resolved_findings += 1

        check_label = check.rule_name.replace("_", " ").title()
        if "Missing" in check_label or check.check_type == CheckType.missing_field:
            check_label = "Required Fields Check"
        elif "Amount" in check_label or check.check_type == CheckType.amount_mismatch:
            check_label = "Amount Match Check"
        elif "Date" in check_label or check.check_type == CheckType.date_mismatch:
            check_label = "Date Match Check"

        nodes.append({
            "id": check_node_id,
            "type": "finding",
            "label": check_label,
            "status": check_status,
            "data": {
                "check_id": check.id,
                "check_type": check.check_type.value,
                "rule_name": check.rule_name,
                "result": check.result.value,
                "severity": check.severity.value,
                "explanation": check.explanation,
                "evidence_references": check.evidence_references,
                "resolution_status": check.resolution_status.value,
                "created_at": check.created_at.isoformat() if check.created_at else None,
            },
        })

        # Connect check to relevant field(s) or document(s)
        connected_to_field = False
        target_field_names: Set[str] = set()

        if check.check_type == CheckType.amount_mismatch:
            target_field_names.update(["total_amount", "amount", "claimed_amount"])
        elif check.check_type == CheckType.date_mismatch:
            target_field_names.update(["expense_date", "date"])
        elif check.check_type == CheckType.missing_field:
            # Parse evidence references if possible
            if check.evidence_references:
                try:
                    refs = json.loads(check.evidence_references)
                    if isinstance(refs, list):
                        for ref in refs:
                            if isinstance(ref, dict):
                                target_field_names.update(ref.get("missing_fields", []))
                                target_field_names.update(ref.get("found_fields", []))
                except Exception:
                    pass

        # Try to connect with specific field nodes
        for fname in target_field_names:
            field_ids = field_node_ids_by_name.get(fname, [])
            for fid in field_ids:
                connected_to_field = True
                edges.append({
                    "id": f"edge_{fid}_{check_node_id}",
                    "source": fid,
                    "target": check_node_id,
                    "label": "verified by",
                    "status": check_status,
                })

        # Fallback: if check did not connect to a specific field, connect to document
        if not connected_to_field:
            target_doc_id: Optional[int] = None
            if check.evidence_references:
                try:
                    refs = json.loads(check.evidence_references)
                    if isinstance(refs, list) and refs and isinstance(refs[0], dict):
                        target_doc_id = refs[0].get("doc_version_id")
                except Exception:
                    pass

            if target_doc_id and f"doc_{target_doc_id}" in [n["id"] for n in nodes]:
                edges.append({
                    "id": f"edge_doc_{target_doc_id}_{check_node_id}",
                    "source": f"doc_{target_doc_id}",
                    "target": check_node_id,
                    "label": "checked",
                    "status": check_status,
                })
            else:
                # Connect from first available document node if any
                for n in nodes:
                    if n["type"] == "document":
                        edges.append({
                            "id": f"edge_{n['id']}_{check_node_id}",
                            "source": n["id"],
                            "target": check_node_id,
                            "label": "checked",
                            "status": check_status,
                        })
                        break

    # ── 3. Create Decision Impact Node ────────────────────────────────────────
    decision_node_id = f"decision_{req.id}"
    req_status = req.status.value

    # Compute decision impact readiness
    open_unresolved_flags = flagged_findings - (
        len([c for c in checks if c.result == CheckResult.flag and c.resolution_status in (ResolutionStatus.resolved, ResolutionStatus.dismissed)])
    )
    open_unresolved_errors = error_findings - (
        len([c for c in checks if c.result == CheckResult.error and c.resolution_status in (ResolutionStatus.resolved, ResolutionStatus.dismissed)])
    )

    if req.status == RequestStatus.approved:
        decision_status = "verified"
        decision_label = "Approved & Authorized"
        impact_summary = "Claim has received final executive approval. All verification evidence was reviewed and authorized."
    elif req.status == RequestStatus.rejected:
        decision_status = "error"
        decision_label = "Claim Rejected"
        impact_summary = "Claim was rejected based on verification findings or documentation discrepancies."
    elif req.status == RequestStatus.more_info_required:
        decision_status = "warning"
        decision_label = "Action Required from Submitter"
        impact_summary = "Reviewer has flagged discrepancies or missing evidence and requested submitter corrections."
    elif req.status == RequestStatus.under_review:
        if open_unresolved_flags > 0 or open_unresolved_errors > 0:
            decision_status = "warning"
            decision_label = "Under Review (Flags Pending)"
            impact_summary = f"{open_unresolved_flags + open_unresolved_errors} open verification signal(s) require reviewer inspection before approval."
        else:
            decision_status = "verified"
            decision_label = "Under Review (Checks Clear)"
            impact_summary = "All automated checks passed. Reviewer can complete review and send to approver."
    elif req.status == RequestStatus.pending_approval:
        decision_status = "verified" if (open_unresolved_flags == 0 and open_unresolved_errors == 0) else "warning"
        decision_label = "Awaiting Executive Decision"
        impact_summary = "Review completed. Approver can examine evidence chain and record final binding decision."
    elif req.status == RequestStatus.draft:
        decision_status = "pending"
        decision_label = "Draft Claim"
        impact_summary = "Draft claim in progress. Submitter must upload required documents and submit for review."
    else:
        decision_status = "pending"
        decision_label = req_status.replace("_", " ").title()
        impact_summary = f"Claim is currently in {req_status} state."

    reviewer_user = db.get(User, req.assigned_reviewer_id) if req.assigned_reviewer_id else None
    approver_user = db.get(User, req.assigned_approver_id) if req.assigned_approver_id else None

    nodes.append({
        "id": decision_node_id,
        "type": "decision",
        "label": decision_label,
        "status": decision_status,
        "data": {
            "request_id": req.id,
            "request_number": req.request_number,
            "request_title": req.title,
            "claimed_amount": req.claimed_amount,
            "currency": req.currency,
            "workflow_status": req.status.value,
            "impact_summary": impact_summary,
            "open_flags": max(0, open_unresolved_flags),
            "open_errors": max(0, open_unresolved_errors),
            "resolved_findings": resolved_findings,
            "passed_findings": passed_findings,
            "total_checks": len(checks),
            "assigned_reviewer_name": reviewer_user.display_name if reviewer_user else None,
            "assigned_approver_name": approver_user.display_name if approver_user else None,
            "is_ready_for_approval": (req.status == RequestStatus.pending_approval and open_unresolved_errors == 0),
        },
    })

    # Connect all checks to Decision node
    for check in checks:
        check_node_id = f"check_{check.id}"
        edges.append({
            "id": f"edge_{check_node_id}_{decision_node_id}",
            "source": check_node_id,
            "target": decision_node_id,
            "label": "influences",
            "status": "warning" if (check.result != CheckResult.pass_ and check.resolution_status == ResolutionStatus.open) else "verified",
        })

    # If there are no checks yet (e.g. in draft), connect document nodes or request directly
    if not checks and docs:
        for doc in docs:
            edges.append({
                "id": f"edge_doc_{doc.id}_{decision_node_id}",
                "source": f"doc_{doc.id}",
                "target": decision_node_id,
                "label": "uploaded for",
                "status": "pending",
            })

    return {
        "request_id": req.id,
        "request_number": req.request_number,
        "request_status": req.status.value,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_documents": len(docs),
            "total_extracted_fields": total_extracted_fields,
            "high_confidence_fields": high_confidence_fields,
            "total_findings": len(checks),
            "passed_findings": passed_findings,
            "flagged_findings": flagged_findings,
            "error_findings": error_findings,
            "resolved_findings": resolved_findings,
            "readiness_state": decision_label,
            "impact_summary": impact_summary,
        },
    }
