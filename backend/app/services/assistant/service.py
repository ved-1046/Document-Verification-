"""
Grounded AI assistant — Gemini when configured, deterministic fallback otherwise.

Role-aware assistance for Submitter, Reviewer, and Approver.
Never mutates records or makes approval decisions.
"""
from decimal import Decimal
import logging
import re
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.request import Request, RequestStatus
from app.models.document_version import DocumentVersion, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.reviewer_correction import ReviewerCorrection
from app.models.verification_check import VerificationCheck, CheckResult
from app.models.review_action import ReviewAction
from app.services.request_service import assert_can_view
from app.models.user import User

logger = logging.getLogger(__name__)

POLICY_SNIPPET = (
    "Expense reimbursements require a completed expense form and receipt. "
    "Amounts on the form and receipt should match. Missing fields must be corrected "
    "before approval. Final approval is always performed by an authorized human Approver."
)


def _build_context(db: Session, req: Request) -> str:
    """Build a rich, grounded evidence context string from database records."""
    parts = [
        f"Claim #{req.request_number} (ID {req.id}):",
        f"Title: {req.title!r}",
        f"Status: {req.status.value}",
        f"Expense Category: {req.expense_category or 'General'}",
        f"Expense Purpose: {req.description or req.expense_category or 'General business expense'}",
        f"Claimed Amount: {req.currency or 'INR'} {req.claimed_amount if req.claimed_amount is not None else 'Not entered'}",
        f"Claimed Expense Date: {req.expense_date.isoformat() if req.expense_date else 'Not entered'}",
        f"Currency: {req.currency or 'INR'}",
        f"Submitter: {req.submitter.display_name} ({req.submitter.email})",
        f"Assigned Reviewer: {req.assigned_reviewer.display_name if req.assigned_reviewer else 'None assigned'}",
        f"Assigned Approver: {req.assigned_approver.display_name if req.assigned_approver else 'None assigned'}",
        f"Corporate Expense Policy: {POLICY_SNIPPET}",
    ]

    # Documents and OCR extractions
    docs = db.query(DocumentVersion).filter(DocumentVersion.request_id == req.id).order_by(DocumentVersion.version_number.asc()).all()
    parts.append(f"\nUploaded Documents ({len(docs)} file versions):")
    if not docs:
        parts.append("  (No documents uploaded yet)")
    for doc in docs:
        parts.append(
            f"- Document ID {doc.id} [{doc.doc_type.value} v{doc.version_number}]: "
            f"file={doc.original_filename!r}, processing_status={doc.processing_status.value}."
        )
        if doc.processing_error:
            parts.append(f"  Quality Alert / Error: {doc.processing_error}")

        run = (
            db.query(ExtractionRun)
            .filter(
                ExtractionRun.document_version_id == doc.id,
                ExtractionRun.status == ExtractionStatus.success,
            )
            .order_by(ExtractionRun.started_at.desc())
            .first()
        )
        if run:
            fields = (
                db.query(ExtractedField)
                .filter(
                    ExtractedField.extraction_run_id == run.id,
                    ExtractedField.field_name != "_raw_page_text",
                )
                .all()
            )
            if fields:
                field_strs = [f"{f.field_name}={f.normalized_value or f.extracted_value!r}" for f in fields]
                parts.append(f"  Extracted fields via OCR: {', '.join(field_strs)}")
            else:
                parts.append("  Extracted fields via OCR: (None detected)")

    # Reviewer Corrections
    corrections = db.query(ReviewerCorrection).filter(ReviewerCorrection.request_id == req.id).all()
    if corrections:
        parts.append(f"\nReviewer Corrections ({len(corrections)} manual adjustments):")
        for c in corrections:
            parts.append(
                f"- Field '{c.field_name}' adjusted from OCR value {c.original_extracted_value!r} "
                f"to corrected value {c.corrected_value!r}. Reason: {c.reason or 'Reviewer adjustment'}."
            )

    # Verification Checks
    checks = (
        db.query(VerificationCheck)
        .filter(
            VerificationCheck.request_id == req.id,
            VerificationCheck.is_current.is_(True),
        )
        .all()
    )
    parts.append(f"\nVerification Rule Results ({len(checks)} active checks):")
    if not checks:
        parts.append("  (No verification checks run yet)")
    for ch in checks:
        parts.append(
            f"- Check [{ch.check_type.value}] -> Result: {ch.result.value.upper()} (Severity: {ch.severity.value}, Resolution: {ch.resolution_status.value}). "
            f"Explanation: {ch.explanation} "
            f"Evidence: {ch.evidence_references or 'None'}."
        )

    # Review Action History
    actions = (
        db.query(ReviewAction)
        .filter(ReviewAction.request_id == req.id)
        .order_by(ReviewAction.created_at.asc())
        .all()
    )
    if actions:
        parts.append(f"\nReview & Approval Audit Trail ({len(actions)} actions):")
        for a in actions:
            actor_name = a.actor.display_name if a.actor else "System"
            parts.append(
                f"- Action {a.action_type.value} by {actor_name} on {a.created_at.strftime('%Y-%m-%d %H:%M UTC')}: "
                f"transitioned status from '{a.previous_status}' to '{a.new_status}'. "
                f"Note/Comment: {a.comment or 'None provided'}."
            )

    return "\n".join(parts)


def _get_role_prompt_instruction(role: str) -> str:
    """Return tailored system instructions for the active user role."""
    if role == "submitter":
        return (
            "The user is the Submitter who filed this claim.\n"
            "- Explain why this claim needs attention in polite, clear, non-technical language.\n"
            "- Clearly identify missing or unreadable information from uploaded documents.\n"
            "- Explain discrepancies (e.g. amount or date differences) calmly and constructively without accusatory language.\n"
            "- Provide clear, actionable recommendations on what the Submitter should correct, enter, or upload."
        )
    elif role == "reviewer":
        return (
            "The user is the Reviewer auditing this claim.\n"
            "- Summarise verification findings (missing fields, amount discrepancies, date differences) with precision.\n"
            "- Highlight mismatched, missing, or unreadable document evidence.\n"
            "- Help compare claim line items against extracted document tokens.\n"
            "- Suggest specific investigative questions or documentation to request from the Submitter.\n"
            "- Help draft clear, objective notes to send to the Submitter when requesting corrections."
        )
    elif role == "approver":
        return (
            "The user is the executive Approver deciding whether to approve or reject this claim.\n"
            "- Provide an executive summary of the claim, expense purpose, total amount, and attached evidence.\n"
            "- Summarise the Reviewer's findings, corrections, and any review comments.\n"
            "- Highlight unresolved discrepancies, missing evidence, or compliance risks.\n"
            "- Clearly outline the key business factors and policy considerations the Approver should weigh before deciding.\n"
            "- CRITICAL RULE: You must NEVER make an approval or rejection decision yourself. Explicitly state that the final decision rests solely with the authorized human Approver."
        )
    return "Provide balanced, grounded assistance based strictly on verified claim evidence."


def _fallback_answer_structured(req: Request, db: Session, question: str, role: str) -> Tuple[str, List[str]]:
    """
    Deterministic synthesis grounded strictly in database facts.
    Never hallucinates or exposes internal diagnostics.
    """
    citations = ["Verified claim record", "Document OCR extraction", "Rule checks (A/B/C)", "Review audit trail"]
    q_lower = question.lower()

    docs = db.query(DocumentVersion).filter(DocumentVersion.request_id == req.id).order_by(DocumentVersion.version_number.asc()).all()
    checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.request_id == req.id, VerificationCheck.is_current.is_(True))
        .all()
    )
    corrections = db.query(ReviewerCorrection).filter(ReviewerCorrection.request_id == req.id).all()
    actions = db.query(ReviewAction).filter(ReviewAction.request_id == req.id).order_by(ReviewAction.created_at.asc()).all()

    # Field extraction map
    field_map = {}
    for doc in docs:
        run = (
            db.query(ExtractionRun)
            .filter(ExtractionRun.document_version_id == doc.id, ExtractionRun.status == ExtractionStatus.success)
            .order_by(ExtractionRun.started_at.desc())
            .first()
        )
        if run:
            for f in db.query(ExtractedField).filter(ExtractedField.extraction_run_id == run.id).all():
                if f.field_name != "_raw_page_text":
                    field_map[f.field_name] = f.normalized_value or f.extracted_value

    status_raw = req.status.value
    status_name = req.status.value.replace("_", " ")
    currency = req.currency or "INR"

    # Document quality evaluation
    failed_docs = [d for d in docs if d.processing_status == ProcessingStatus.failed]
    flagged_checks = [c for c in checks if c.result in (CheckResult.flag, "fail")]
    amt_check = next((c for c in checks if c.check_type.value == "amount_mismatch"), None)
    date_check = next((c for c in checks if c.check_type.value == "date_mismatch"), None)
    missing_check = next((c for c in checks if c.check_type.value == "missing_field"), None)

    # Missing elements evaluation
    missing_items = []
    has_receipt = any(d.doc_type.value == "receipt" for d in docs)
    if not has_receipt:
        missing_items.append("Receipt: No receipt document has been uploaded yet.")
    elif failed_docs:
        for fd in failed_docs:
            if fd.doc_type.value == "receipt":
                missing_items.append(f"Receipt extraction: The receipt '{fd.original_filename}' could not be read ({fd.processing_error or 'unreadable'}).")

    if not field_map.get("total_amount") and req.claimed_amount is None:
        missing_items.append("Expense Amount: Total amount was not detected in documents and has not been entered.")
    if not field_map.get("expense_date") and req.expense_date is None:
        missing_items.append("Transaction Date: Date was not detected in documents and has not been entered.")
    if not field_map.get("merchant_name") and not field_map.get("merchant"):
        missing_items.append("Merchant Name: Merchant or vendor name was not identified.")

    # Identify question intent
    is_missing_q = any(w in q_lower for w in ["missing", "require", "need", "complete", "incomplete", "information", "which"])
    is_flag_q = any(w in q_lower for w in ["flag", "issue", "problem", "why", "mismatch", "warning", "attention"])
    is_compare_q = any(w in q_lower for w in ["compare", "difference", "discrepancy", "receipt", "match", "amounts"])
    is_status_q = any(w in q_lower for w in ["status", "stage", "where", "progress", "next"])
    is_questions_for_sub_q = any(w in q_lower for w in ["ask", "question", "suggest", "investigate", "inquire"])
    is_approver_decision_q = any(w in q_lower for w in ["decide", "approve", "reject", "consider", "decision", "risk", "factor"])

    # Check for queries asking about non-existent or unmentioned details (missing evidence honesty)
    known_fields = {
        "amount", "total", "sum", "cost", "price", "date", "when", "day", "time",
        "merchant", "store", "vendor", "shop", "cafe", "restaurant", "seller",
        "status", "stage", "progress", "state", "title", "category", "purpose",
        "reason", "why", "flag", "mismatch", "missing", "difference", "discrepancy",
        "issue", "attention", "document", "receipt", "form", "file", "scan", "upload",
        "version", "reviewer", "approver", "submitter", "action", "history", "note",
        "comment", "correction", "fix", "rule", "check", "policy", "suggest", "ask",
        "investigate", "decide", "decision", "approve", "reject", "consider", "risk",
        "currency", "inr", "rupee", "dollar", "evidence", "findings", "item"
    }
    words_in_q = set(re.findall(r"\b[a-zA-Z]{3,}\b", q_lower))
    non_common_words = words_in_q - {
        "what", "which", "where", "how", "this", "that", "the", "for", "with", "from",
        "and", "are", "can", "could", "would", "should", "tell", "show", "give", "please",
        "about", "claim", "expense", "there", "any"
    }
    if non_common_words and not (non_common_words & known_fields):
        topic = " ".join(list(non_common_words)[:3])
        return (
            f"The provided claim evidence does not contain information regarding '{topic}'. "
            f"The uploaded documents and verified records for #{req.request_number} only cover "
            f"the merchant name, claimed amount ({currency} {req.claimed_amount}), expense date ({req.expense_date}), "
            f"and business purpose ('{req.description or req.expense_category or 'General'}').",
            citations,
        )

    lines: List[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # SUBMITTER PERSPECTIVE
    # ─────────────────────────────────────────────────────────────────────────
    if role == "submitter":
        if is_flag_q or is_missing_q or (req.status == RequestStatus.more_info_required):
            lines.append(f"### Claim #{req.request_number} Attention Notice")
            lines.append(f"Your claim is currently in **{status_name}** status.")
            
            # Discrepancies
            if amt_check and amt_check.result == CheckResult.flag:
                lines.append(f"\n- **Amount Discrepancy:** {amt_check.explanation}")
            if date_check and date_check.result == CheckResult.flag:
                lines.append(f"\n- **Date Discrepancy:** {date_check.explanation}")

            # Missing or unreadable info
            if missing_items:
                lines.append("\n**Items Needing Attention:**")
                for item in missing_items:
                    lines.append(f"- {item}")
            elif not flagged_checks and not failed_docs:
                lines.append("\nAll required document fields have been verified successfully.")

            # Actionable suggestions
            lines.append("\n**What you should do:**")
            if failed_docs:
                lines.append("- Click 'Upload Clearer Document' or 'Replace Document' to upload a crisp, high-resolution photo or PDF.")
            if missing_items and any("Amount" in m or "Date" in m for m in missing_items):
                lines.append("- Enter any missing required fields in Step 2 of the claim workspace.")
            if amt_check and amt_check.result == CheckResult.flag:
                lines.append("- If the receipt amount differs from your claimed amount, verify whether tips or taxes were included, or adjust the claimed amount.")
            if req.status == RequestStatus.draft:
                lines.append("- Once ready, review your details and click 'Submit Claim for Review'.")
            elif req.status == RequestStatus.more_info_required:
                lines.append("- Address the reviewer's note and re-submit your claim for review.")

        elif is_status_q:
            lines.append(f"### Current Claim Status: {status_name}")
            lines.append(f"- **Claim:** #{req.request_number} — {req.title}")
            lines.append(f"- **Claimed Amount:** {currency} {req.claimed_amount or 'Not specified'}")
            lines.append(f"- **Documents on File:** {len(docs)} uploaded")
            lines.append(f"- **Assigned Reviewer:** {req.assigned_reviewer.display_name if req.assigned_reviewer else 'Pending assignment'}")
            if req.status == RequestStatus.draft:
                lines.append("\n**Next Step:** Ensure all required receipts are uploaded and click 'Submit Claim for Review'.")
            elif req.status in (RequestStatus.submitted, RequestStatus.under_review):
                lines.append("\n**Next Step:** Your reviewer is currently checking the documents and verification checks.")
            elif req.status == RequestStatus.pending_approval:
                lines.append("\n**Next Step:** Your reviewer has completed review; the claim is awaiting final approval from the Approver.")
            elif req.status == RequestStatus.approved:
                lines.append("\n**Next Step:** This claim has been approved for reimbursement.")

        else:
            lines.append(f"### Claim Overview for #{req.request_number}")
            lines.append(f"- **Title:** {req.title}")
            lines.append(f"- **Status:** {status_name}")
            lines.append(f"- **Merchant:** {field_map.get('merchant_name') or field_map.get('merchant') or 'Not identified'}")
            lines.append(f"- **Claimed Amount:** {currency} {req.claimed_amount or field_map.get('total_amount', 'Not specified')}")
            lines.append(f"- **Date:** {req.expense_date or field_map.get('expense_date', 'Not specified')}")
            if flagged_checks:
                lines.append(f"\n⚠️ Note: There are {len(flagged_checks)} verification flags requiring attention before approval.")

    # ─────────────────────────────────────────────────────────────────────────
    # REVIEWER PERSPECTIVE
    # ─────────────────────────────────────────────────────────────────────────
    elif role == "reviewer":
        if is_questions_for_sub_q:
            lines.append("### Suggested Inquiries for Submitter")
            if amt_check and amt_check.result == CheckResult.flag:
                lines.append(f"- **Amount Difference:** Ask submitter: 'The uploaded receipt indicates {currency} {field_map.get('total_amount', 'different amount')} while {currency} {req.claimed_amount} was claimed. Please clarify if tips, gratuity, or separate items account for the difference.'")
            if date_check and date_check.result == CheckResult.flag:
                lines.append(f"- **Date Difference:** Ask submitter: 'The receipt date is {field_map.get('expense_date')} whereas the claim date was submitted as {req.expense_date}. Please confirm the exact date of expenditure.'")
            if failed_docs:
                lines.append("- **Document Quality:** Request: 'The receipt scan was unreadable or low resolution. Please provide a clear, full-page photo of the itemized receipt.'")
            if not lines or len(lines) == 1:
                lines.append("- All standard checks have passed. You may verify whether the expense purpose adheres to company travel and entertainment policies.")

        elif is_compare_q or is_flag_q:
            lines.append(f"### Verification Comparison & Findings: Claim #{req.request_number}")
            lines.append(f"- **Claimed Amount:** {currency} {req.claimed_amount}")
            lines.append(f"- **Receipt Extracted Amount:** {currency} {field_map.get('total_amount', 'Not detected')}")
            lines.append(f"- **Claimed Date:** {req.expense_date}")
            lines.append(f"- **Receipt Extracted Date:** {field_map.get('expense_date', 'Not detected')}")
            lines.append(f"- **Extracted Merchant:** {field_map.get('merchant_name') or field_map.get('merchant', 'Not detected')}")

            lines.append("\n**Active Verification Rules:**")
            if checks:
                for ch in checks:
                    res_badge = "PASSED" if ch.result == CheckResult.pass_ else ("FLAGGED" if ch.result == CheckResult.flag else "INFO")
                    lines.append(f"- **{ch.rule_name or ch.check_type.value}** [{res_badge}]: {ch.explanation}")
            else:
                lines.append("- No automated verification checks on file.")

            if corrections:
                lines.append("\n**Reviewer Field Corrections:**")
                for c in corrections:
                    lines.append(f"- Corrected `{c.field_name}` from '{c.original_extracted_value}' to '{c.corrected_value}' (Reason: {c.reason})")

        else:
            lines.append(f"### Reviewer Summary for Claim #{req.request_number}")
            lines.append(f"- **Submitter:** {req.submitter.display_name}")
            lines.append(f"- **Status:** {status_name}")
            lines.append(f"- **Claimed:** {currency} {req.claimed_amount or '0.00'} ({req.expense_category or 'General'})")
            lines.append(f"- **Receipt Extraction:** {currency} {field_map.get('total_amount', 'Not detected')}")
            lines.append(f"- **Open Verification Flags:** {len(flagged_checks)}")
            if failed_docs:
                lines.append(f"- **Document Alerts:** {len(failed_docs)} document(s) failed automated OCR reading.")
            lines.append("\n**Recommendation:** Cross-reference receipt line items and resolve any open flags before completing review.")

    # ─────────────────────────────────────────────────────────────────────────
    # APPROVER PERSPECTIVE
    # ─────────────────────────────────────────────────────────────────────────
    elif role == "approver":
        lines.append(f"### Executive Claim & Evidence Summary (#{req.request_number})")
        lines.append(f"- **Claimant:** {req.submitter.display_name} ({req.submitter.email})")
        lines.append(f"- **Title / Purpose:** {req.title} — {req.description or req.expense_category or 'General business expense'}")
        lines.append(f"- **Claimed Amount:** {currency} {req.claimed_amount or '0.00'}")
        lines.append(f"- **Assigned Reviewer:** {req.assigned_reviewer.display_name if req.assigned_reviewer else 'None'}")
        lines.append(f"- **Current Status:** {status_name}")

        # Reviewer findings & corrections
        reviewer_actions = [a for a in actions if a.action_type.value in ("complete_review", "request_correction")]
        if reviewer_actions:
            latest_action = reviewer_actions[-1]
            lines.append(f"\n**Reviewer Notes:** \"{latest_action.comment or 'Reviewer completed checks with no special notes.'}\"")
        elif req.status == RequestStatus.pending_approval:
            lines.append("\n**Reviewer Notes:** Review completed; submitted for executive sign-off.")

        # Discrepancies and risks
        lines.append("\n**Verification Findings & Risk Factors:**")
        if flagged_checks:
            lines.append(f"- ⚠️ There are **{len(flagged_checks)} open flags**:")
            for ch in flagged_checks:
                lines.append(f"  * {ch.rule_name or ch.check_type.value}: {ch.explanation}")
        else:
            lines.append("- ✅ All automated verification checks (missing fields, amount match, date match) have PASSED.")

        if failed_docs:
            lines.append(f"- ⚠️ **Document Alert:** {len(failed_docs)} document version(s) failed OCR extraction.")

        # Factors to consider
        lines.append("\n**Key Factors to Consider Before Deciding:**")
        lines.append(f"1. **Policy Adherence:** Does {currency} {req.claimed_amount} fall within the departmental budget for '{req.expense_category or 'expenses'}'?")
        lines.append("2. **Evidence Completeness:** Has a valid, readable receipt been inspected and validated?")
        lines.append("3. **Discrepancy Resolution:** Have all amount differences and reviewer questions been satisfactorily addressed?")

        # Non-delegable decision authority reminder
        lines.append("\n**Decision Authority Reminder:** The DocuVerify AI Assistant does not make approval decisions. The final decision to approve or reject this claim rests solely with you as the authorized Approver.")

    else:
        lines.append(f"### Claim #{req.request_number} Summary")
        lines.append(f"- Status: {status_name}")
        lines.append(f"- Amount: {currency} {req.claimed_amount or field_map.get('total_amount', 'Not specified')}")
        lines.append(f"- Merchant: {field_map.get('merchant_name') or 'Not identified'}")

    return "\n".join(lines), citations


def _gemini_answer(context: str, question: str, role: str) -> Tuple[str, List[str]]:
    """Query Google Gemini with role-specific system prompt and strict grounding."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key, transport="rest")
    candidate_models = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-flash-latest"]

    role_instruction = _get_role_prompt_instruction(role)
    system_prompt = (
        "You are DocuVerify AI, an expert, objective, and grounded assistant for corporate expense verification.\n"
        f"You are strictly assisting a user with the role: {role.upper()}.\n\n"
        "ROLE-SPECIFIC GUIDANCE:\n"
        f"{role_instruction}\n\n"
        "CORE GROUNDING AND RELIABILITY RULES:\n"
        "1. STRICT GROUNDING: Answer using ONLY the verified facts and evidence in the CONTEXT below. Never fabricate, assume, or extrapolate facts.\n"
        "2. DISTINGUISH EVIDENCE: Clearly distinguish between (a) Claimed values entered by the user, (b) Extracted values read by OCR from uploaded files, and (c) Verified or corrected values approved by reviewers.\n"
        "3. MISSING EVIDENCE: Never treat missing information as a match. If a required field or document was not found or is unreadable, explicitly report it as missing.\n"
        "4. HONESTY: If the context does not contain the answer to the user's question, state clearly: 'The provided claim evidence does not contain this information.' Do not guess or invent details.\n"
        "5. CONFLICTS: If values conflict (e.g. amount discrepancy), clearly explain the conflict and state the exact figures.\n"
        "6. DECISION AUTHORITY: The assistant must NEVER make an approval or rejection decision. If the user asks whether to approve or if it is approved, remind them that final decision authority rests solely with the authorized human Approver.\n"
        "7. FORMATTING: Present answers cleanly with concise markdown paragraphs and bullet points. Do NOT include technical database dumps, internal IDs, or provider diagnostics.\n"
    )

    full_prompt = f"{system_prompt}\n\nCONTEXT:\n{context}\n\nQUESTION FROM {role.upper()}:\n{question}"

    last_err = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt, request_options={"timeout": 10.0})
            if response and response.text:
                return response.text.strip(), [f"Gemini ({model_name}) grounded on claim evidence"]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def get_suggested_questions(db: Session, req: Request, role: str) -> List[str]:
    """Generate dynamic, context-aware suggested questions for the active role."""
    checks = db.query(VerificationCheck).filter(VerificationCheck.request_id == req.id, VerificationCheck.is_current.is_(True)).all()
    has_flags = any(c.result in (CheckResult.flag, "fail") for c in checks)
    has_failed_docs = db.query(DocumentVersion).filter(DocumentVersion.request_id == req.id, DocumentVersion.processing_status == ProcessingStatus.failed).count() > 0

    if role == "submitter":
        if has_flags or has_failed_docs:
            return [
                "What do I need to fix on this claim?",
                "Why was my claim flagged?",
                "Which documents or fields are missing?",
                "What is the current status of my claim?",
            ]
        return [
            "Are all my documents verified?",
            "What is the current status of my claim?",
            "Which information was extracted from my receipt?",
            "What happens next after submitting?",
        ]

    elif role == "reviewer":
        if has_flags:
            return [
                "Summarise all verification findings and flags.",
                "Compare the claimed details with the receipt evidence.",
                "What questions or corrections should I ask the submitter?",
                "Are there any unreadable documents or missing fields?",
            ]
        return [
            "Summarise verification findings for this claim.",
            "Compare claimed amount against receipt extraction.",
            "What questions should I investigate before completing review?",
            "Are all required documents present and legible?",
        ]

    elif role == "approver":
        return [
            "Summarise this claim and the reviewer's findings.",
            "Are there any unresolved discrepancies or risk factors?",
            "What factors should I consider before deciding?",
            "Is all required evidence present and verified?",
        ]

    return [
        "What is the status of this claim?",
        "What evidence is attached?",
        "Are there any verification flags?",
        "What are the claimed amounts?",
    ]


def answer_question(db: Session, user: User, request_id: int, question: str) -> dict:
    """Entry point for asking questions about a claim."""
    req = db.get(Request, request_id)
    if not req:
        raise ValueError("Request not found")
    assert_can_view(user, req)

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    context = _build_context(db, req)

    if settings.gemini_available:
        try:
            answer, citations = _gemini_answer(context, question, role_str)
            mode = "llm"
        except Exception as e:
            logger.warning("Gemini failed, falling back to deterministic synthesis: %s", e)
            answer, citations = _fallback_answer_structured(req, db, question, role_str)
            mode = "fallback"
    else:
        answer, citations = _fallback_answer_structured(req, db, question, role_str)
        mode = "fallback"

    return {
        "answer": answer,
        "citations": citations,
        "mode": mode,
        "request_id": request_id,
        "role": role_str,
    }
