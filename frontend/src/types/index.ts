/**
 * Shared TypeScript types mirroring the backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/*.py
 */

// ── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = 'submitter' | 'reviewer' | 'approver' | 'admin';

export type RequestStatus =
    | 'draft'
    | 'submitted'
    | 'processing'
    | 'under_review'
    | 'pending_approval'
    | 'more_info_required'
    | 'approved'
    | 'rejected'
    | 'processing_failed';

export type RequestType = 'expense_reimbursement';

export type DocType = 'expense_form' | 'receipt' | 'supporting_document';

export type ProcessingStatus = 'pending' | 'processing' | 'ready' | 'failed';

export type CheckType = 'missing_field' | 'amount_mismatch' | 'date_mismatch';

export type CheckResult = 'pass' | 'flag' | 'info' | 'error';

export type CheckSeverity = 'low' | 'medium' | 'high';

export type ResolutionStatus = 'open' | 'resolved' | 'dismissed';

export type ReviewActionType =
    | 'submitted'
    | 'assigned'
    | 'correction_requested'
    | 'correction_submitted'
    | 'field_corrected'
    | 'review_completed'
    | 'approved'
    | 'rejected'
    | 'reprocessed';

// ── Domain types ─────────────────────────────────────────────────────────────

export interface User {
    id: number;
    display_name: string;
    email: string;
    role: UserRole;
    is_active: boolean;
    created_at: string;
}

export interface RequestSummary {
    id: number;
    request_number: string;
    request_type: RequestType;
    title: string;
    description?: string;
    expense_category: string;
    claimed_amount?: string | number | null;
    expense_date?: string | null;
    currency: string;
    submitter_name?: string | null;
    submitter_id: number;
    assigned_reviewer_id?: number;
    assigned_approver_id?: number;
    assigned_reviewer?: UserSummary | null;
    assigned_approver?: UserSummary | null;
    submitter?: UserSummary | null;
    status: RequestStatus;
    created_at: string;
    updated_at: string;
    submitted_at?: string;
}

export interface DocumentVersion {
    id: number;
    request_id: number;
    doc_type: DocType;
    original_filename: string;
    mime_type: string;
    file_size: number;
    version_number: number;
    uploader_id: number;
    uploader_name?: string;
    uploaded_at: string;
    processing_status: ProcessingStatus;
    processing_error?: string;
}

export interface ExtractedField {
    id: number;
    extraction_run_id?: number;
    field_name: string;
    extracted_value?: string;
    normalized_value?: string;
    page_number?: number;
    bounding_box?: string;
    confidence?: number;
}

export interface VerificationCheck {
    id: number;
    request_id: number;
    check_type: CheckType;
    rule_name: string;
    result: CheckResult;
    severity: CheckSeverity;
    explanation: string;
    evidence_references?: string;
    created_at: string;
    resolution_status: ResolutionStatus;
}

export interface ReviewAction {
    id: number;
    request_id?: number;
    actor_id: number;
    actor_name?: string;
    action_type: ReviewActionType;
    comment?: string;
    previous_status?: string;
    new_status?: string;
    created_at: string;
}

export interface ReviewerCorrection {
    id: number;
    request_id: number;
    document_version_id: number;
    field_name: string;
    original_extracted_value?: string;
    corrected_value: string;
    reviewer_id: number;
    reviewer_name?: string;
    reason?: string;
    created_at: string;
}

export interface UserSummary {
    id: number;
    display_name: string;
    role: UserRole;
}

export interface ManagedUser extends User {
    temporary_password?: string;
}

// ── API response shapes ───────────────────────────────────────────────────────

export interface AuthToken {
    access_token: string;
    token_type: string;
}

export interface HealthResponse {
    status: 'ok' | 'degraded' | 'error';
    timestamp: string;
    version: string;
    environment: string;
    database: { status: string; detail?: string };
    features: { gemini_available: boolean; ocr_engine: string; max_upload_mb?: number };
}

export interface DashboardSummary {
    total_requests: number;
    by_status: Record<RequestStatus, number>;
    review_queue_count?: number;
    common_check_issues: Array<{ check_type: CheckType; count: number }>;
    avg_turnaround_hours?: number;
}

export interface DocumentHistoryEntry {
    id: number;
    request_id: number;
    request_number: string;
    request_title: string;
    request_status: RequestStatus;
    doc_type: DocType;
    version_number: number;
    original_filename: string;
    mime_type: string;
    file_size: number;
    uploader_id: number;
    uploader_name?: string;
    uploaded_at: string;
    processing_status: ProcessingStatus;
    processing_error?: string;
}

export interface AssistantResponse {
    answer: string;
    citations: string[];
    mode: 'llm' | 'fallback';
    request_id: number;
}

export interface AuditEntry {
    id: number;
    event_type: string;
    actor_id?: number | null;
    request_id?: number | null;
    entity_type?: string | null;
    entity_id?: number | null;
    summary?: string | null;
    created_at: string;
}

export interface APIError {
    detail: string;
}

export interface FieldDiff {
    field_name: string;
    old_value?: string;
    new_value?: string;
    status: 'changed' | 'unchanged' | 'added' | 'removed' | 'unreadable';
    old_version_id?: number;
    new_version_id?: number;
}

// ── Evidence Impact Graph ────────────────────────────────────────────────────

export type GraphNodeType = 'document' | 'field' | 'finding' | 'decision';
export type GraphNodeStatus = 'verified' | 'warning' | 'error' | 'ready' | 'pending' | 'detected' | 'info';

export interface GraphNode {
    id: string;
    type: GraphNodeType;
    label: string;
    status: GraphNodeStatus;
    data: Record<string, any>;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    label?: string;
    status?: string;
}

export interface EvidenceGraphResponse {
    request_id: number;
    request_number: string;
    request_status: RequestStatus;
    nodes: GraphNode[];
    edges: GraphEdge[];
    summary: {
        total_documents: number;
        total_extracted_fields: number;
        high_confidence_fields: number;
        total_findings: number;
        passed_findings: number;
        flagged_findings: number;
        error_findings: number;
        resolved_findings: number;
        readiness_state: string;
        impact_summary: string;
    };
}


// ── Decision Replay ──────────────────────────────────────────────────────────

export type ReplayCategory = 'lifecycle' | 'document' | 'verification' | 'review' | 'decision';
export type ReplayStatusBadge = 'pass' | 'warning' | 'error' | 'info' | 'teal';

export interface DecisionReplayEvent {
    id: string;
    sequence_number: number;
    timestamp: string;
    event_type: string;
    category: ReplayCategory;
    title: string;
    action: string;
    actor: {
        id: number;
        display_name: string;
        email: string;
        role: string;
    } | null;
    status_badge: ReplayStatusBadge;
    comment: string | null;
    transition: {
        previous_status: string | null;
        new_status: string | null;
    } | null;
    request_state_at_event: {
        status: string;
        is_historical_state_available: boolean;
        state_source: string;
    };
    metadata: Record<string, unknown>;
}

export interface DecisionReplayResponse {
    request_id: number;
    request_number: string;
    current_status: RequestStatus;
    total_events: number;
    events: DecisionReplayEvent[];
    summary: {
        created_at: string | null;
        submitted_at: string | null;
        final_decision_at: string | null;
        final_decision: 'approved' | 'rejected' | null;
        total_documents_uploaded: number;
        total_corrections_made: number;
        total_review_cycles: number;
        current_stage: string;
    };
}
