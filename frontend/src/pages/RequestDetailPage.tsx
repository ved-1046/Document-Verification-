import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
    AlertTriangle,
    ArrowLeft,
    ArrowRight,
    CheckCircle2,
    Download,
    Receipt,
    FileCheck2,
    Send,
    RotateCw,
    History,
    Upload,
    Network,
    AlertCircle,
    Sparkles,
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import EvidenceImpactGraph from '../components/EvidenceImpactGraph';
import DecisionReplayTimeline from '../components/DecisionReplayTimeline';
import SubmitterClaimView from '../components/SubmitterClaimView';
import ReviewerClaimView from '../components/ReviewerClaimView';
import ApproverClaimView from '../components/ApproverClaimView';
import type {
    DocumentVersion,
    RequestSummary,
    RequestStatus,
    ReviewAction,
    UserRole,
    UserSummary,
    VerificationCheck,
    ExtractedField,
    HealthResponse,
    ReviewerCorrection,
    EvidenceGraphResponse,
    DecisionReplayResponse,
} from '../types';

const STATUS_LABEL: Record<RequestStatus, string> = {
    draft: 'Draft',
    submitted: 'Submitted',
    processing: 'Processing',
    under_review: 'Under review',
    pending_approval: 'Pending approver decision',
    more_info_required: 'More info required',
    approved: 'Approved',
    rejected: 'Rejected',
    processing_failed: 'Processing failed',
};

// Formats YYYY-MM-DD or DD/MM/YYYY into human-readable e.g. "22 October 2026"
function formatExpenseDate(raw?: string | null): string {
    if (!raw) return '';
    const trimmed = raw.trim();
    const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (isoMatch) {
        const [, year, month, day] = isoMatch;
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        const mIdx = parseInt(month, 10) - 1;
        if (mIdx >= 0 && mIdx < 12) {
            return `${parseInt(day, 10)} ${monthNames[mIdx]} ${year}`;
        }
    }
    const slashMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (slashMatch) {
        const [, day, month, year] = slashMatch;
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        const mIdx = parseInt(month, 10) - 1;
        if (mIdx >= 0 && mIdx < 12) {
            return `${parseInt(day, 10)} ${monthNames[mIdx]} ${year}`;
        }
    }
    return trimmed;
}

// Formats numeric amount with currency symbol e.g. "₹450.00", "$450.00"
function formatReceiptAmount(amount?: string | number | null, currency?: string | null): string {
    if (amount == null || amount === '') return '';
    const cleanStr = String(amount).replace(/,/g, '').trim();
    const num = parseFloat(cleanStr);
    if (isNaN(num)) return `${currency ? currency + ' ' : ''}${amount}`.trim();
    const formattedNum = num.toFixed(2);
    const curr = (currency ?? '').toUpperCase().trim();
    if (curr === 'INR' || curr === 'RS' || curr === 'RS.' || curr === '₹') {
        return `₹${formattedNum}`;
    }
    if (curr === 'USD' || curr === '$') {
        return `$${formattedNum}`;
    }
    if (curr === 'EUR' || curr === '€') {
        return `€${formattedNum}`;
    }
    if (curr === 'GBP' || curr === '£') {
        return `£${formattedNum}`;
    }
    return `${currency ? currency + ' ' : ''}${formattedNum}`;
}

// Retrieves the effective field value, prioritizing reviewer corrections
function getFieldEffectiveValue(
    docId: number | undefined,
    fieldName: string,
    fields: ExtractedField[],
    corrections: ReviewerCorrection[]
): { value: string | null; isCorrected: boolean; originalValue: string | null } {
    if (!docId) return { value: null, isCorrected: false, originalValue: null };
    const correction = corrections
        .filter((c) => c.document_version_id === docId && c.field_name === fieldName)
        .at(-1);
    const field = fields.find((f) => f.field_name === fieldName);
    const extracted = field?.normalized_value ?? field?.extracted_value ?? null;
    if (correction?.corrected_value) {
        return {
            value: correction.corrected_value,
            isCorrected: true,
            originalValue: extracted,
        };
    }
    return {
        value: extracted && extracted.trim() ? extracted.trim() : null,
        isCorrected: false,
        originalValue: null,
    };
}

export default function RequestDetailPage() {
    const { id } = useParams<{ id: string }>();
    const [searchParams, setSearchParams] = useSearchParams();
    const requestId = Number(id);
    const hasNumericId = Number.isInteger(requestId) && requestId > 0;
    const { user } = useAuth();

    const [request, setRequest] = useState<RequestSummary | null>(null);
    const [documents, setDocuments] = useState<DocumentVersion[]>([]);
    const [checks, setChecks] = useState<VerificationCheck[]>([]);
    const [history, setHistory] = useState<ReviewAction[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [actionComment, setActionComment] = useState('');
    const [uploadType, setUploadType] = useState<'expense_form' | 'receipt' | 'supporting_document'>('expense_form');
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [busy, setBusy] = useState(false);
    const [extractions, setExtractions] = useState<Record<number, ExtractedField[]>>({});
    const [maxUploadMb, setMaxUploadMb] = useState<number | null>(null);
    const [uploadProgress, setUploadProgress] = useState<number | null>(null);
    const [uploadMessage, setUploadMessage] = useState<string | null>(null);
    const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [corrections, setCorrections] = useState<ReviewerCorrection[]>([]);
    const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
    const [graphData, setGraphData] = useState<EvidenceGraphResponse | null>(null);
    const [replayData, setReplayData] = useState<DecisionReplayResponse | null>(null);
    const [activeView, setActiveView] = useState<'details' | 'graph' | 'replay'>('details');
    const [adminRoleView, setAdminRoleView] = useState<'submitter' | 'reviewer' | 'approver' | null>(null);
    const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
    const submittingRef = useRef(false);

    // Assignee editing in draft mode
    // Claim details editing & missing fields input
    const [isEditingDetails, setIsEditingDetails] = useState(false);
    const [editAmount, setEditAmount] = useState('');
    const [editDate, setEditDate] = useState('');
    const [editTitle, setEditTitle] = useState('');
    const [editCategory, setEditCategory] = useState('travel');
    const [editCurrency, setEditCurrency] = useState('INR');
    const [editDescription, setEditDescription] = useState('');
    const [savingDetails, setSavingDetails] = useState(false);
    const [detailsSaveError, setDetailsSaveError] = useState<string | null>(null);
    const [detailsSaveSuccess, setDetailsSaveSuccess] = useState<string | null>(null);
    const [isEditingAssignees, setIsEditingAssignees] = useState(false);
    const [assigneeList, setAssigneeList] = useState<UserSummary[]>([]);
    const [selectedReviewerId, setSelectedReviewerId] = useState<string>('');
    const [selectedApproverId, setSelectedApproverId] = useState<string>('');
    const [assigneeSaveError, setAssigneeSaveError] = useState<string | null>(null);
    const [assigneeSaving, setAssigneeSaving] = useState(false);

    // Guided workflow wizard step (1 to 4)
    const initialStep = Math.max(1, Math.min(4, Number(searchParams.get('step')) || 2));
    const [wizardStep, setWizardStepState] = useState<number>(initialStep);

    const setWizardStep = (step: number) => {
        setWizardStepState(step);
        setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.set('step', String(step));
            return next;
        }, { replace: true });
    };

    const load = useCallback(async (silent = false) => {
        if (!id) {
            setError('A request ID or request number is required.');
            setLoading(false);
            return;
        }
        if (!silent) {
            setLoading(true);
            setError(null);
        }
        try {
            const reqRes = hasNumericId
                ? await api.get<RequestSummary>(`/requests/${requestId}`)
                : await api.get<RequestSummary>('/requests/lookup', { params: { request_number: id } });
            setRequest(reqRes.data);
            if (reqRes.data.claimed_amount != null) setEditAmount(String(reqRes.data.claimed_amount));
            if (reqRes.data.expense_date) setEditDate(reqRes.data.expense_date);
            if (reqRes.data.title) setEditTitle(reqRes.data.title);
            if (reqRes.data.expense_category) setEditCategory(reqRes.data.expense_category);
            if (reqRes.data.currency) setEditCurrency(reqRes.data.currency);
            if (reqRes.data.description) setEditDescription(reqRes.data.description);
            const [docsRes, checksRes, histRes, healthRes, correctionsRes, graphRes, replayRes] = await Promise.allSettled([
                api.get<DocumentVersion[]>(`/requests/${reqRes.data.id}/documents`),
                api.get<VerificationCheck[]>(`/requests/${reqRes.data.id}/checks`),
                api.get<ReviewAction[]>(`/requests/${reqRes.data.id}/history`),
                api.get<HealthResponse>('/health'),
                api.get<ReviewerCorrection[]>(`/requests/${reqRes.data.id}/corrections`),
                api.get<EvidenceGraphResponse>(`/requests/${reqRes.data.id}/evidence-graph`),
                api.get<DecisionReplayResponse>(`/requests/${reqRes.data.id}/decision-replay`),
            ]);
            const docs = docsRes.status === 'fulfilled' ? docsRes.value.data : [];
            setDocuments(docs);
            setSelectedDocId((current) => docs.some((doc) => doc.id === current) ? current : docs.find((doc) => doc.processing_status === 'ready')?.id ?? docs[0]?.id ?? null);
            setChecks(checksRes.status === 'fulfilled' ? checksRes.value.data : []);
            setHistory(histRes.status === 'fulfilled' ? histRes.value.data : []);
            setCorrections(correctionsRes.status === 'fulfilled' ? correctionsRes.value.data : []);
            if (graphRes.status === 'fulfilled') setGraphData(graphRes.value.data);
            if (replayRes.status === 'fulfilled') setReplayData(replayRes.value.data);
            if (healthRes.status === 'fulfilled') setMaxUploadMb(healthRes.value.data.features.max_upload_mb ?? null);
            const extracted = await Promise.allSettled(docs.map((doc) =>
                api.get<{ fields?: ExtractedField[] }>(`/documents/${doc.id}/extraction`),
            ));
            setExtractions(Object.fromEntries(extracted.flatMap((result, index) =>
                result.status === 'fulfilled' ? [[docs[index].id, result.value.data.fields ?? []]] : [],
            )));
            if (docsRes.status === 'rejected') {
                setError('The request loaded, but supporting documents could not be retrieved. Refresh or contact an administrator.');
            }
        } catch (err) {
            const failure = err as { response?: { status?: number; data?: { detail?: string } } };
            const status = failure?.response?.status;
            const detail = failure?.response?.data?.detail;
            if (detail) setError(detail);
            else if (status === 403) setError('You do not have permission to view this request.');
            else if (status === 404) setError('This request could not be found. Check the request number or return to your dashboard.');
            else if (status === 422) setError('The request identifier is invalid. Open the request from its list or use its full request number.');
            else if (status && status >= 500) setError('The server could not load this request. Please try again.');
            else if (!failure?.response) setError('Could not reach the API. Check that the backend is running on port 8080.');
            else setError('Failed to load request details.');
        } finally {
            if (!silent) setLoading(false);
        }
    }, [id, requestId, hasNumericId]);

    useEffect(() => {
        load();
    }, [load]);

    const hasActiveProcessing = request?.status === 'processing' || documents.some((doc) => doc.processing_status === 'pending' || doc.processing_status === 'processing');
    useEffect(() => {
        if (!hasActiveProcessing) return;
        const timer = window.setInterval(() => { void load(true); }, 2000);
        return () => window.clearInterval(timer);
    }, [hasActiveProcessing, load]);

    useEffect(() => {
        let url: string | null = null;
        let cancelled = false;
        if (selectedDocId !== null) {
            api.get(`/documents/${selectedDocId}/download`, { responseType: 'blob' }).then((result) => {
                url = URL.createObjectURL(result.data);
                if (cancelled) URL.revokeObjectURL(url);
                else setPreviewUrl(url);
            }).catch(() => {
                setPreviewUrl(null);
            });
        } else setPreviewUrl(null);
        return () => { cancelled = true; if (url) URL.revokeObjectURL(url); };
    }, [selectedDocId]);

    const role = user?.role as UserRole | undefined;
    const isSubmitter = role === 'submitter' && request?.submitter_id === user?.id;
    const isApprover = role === 'approver';
    const isReviewer = role === 'reviewer';
    const recordId = request?.id ?? requestId;

    async function submitDraft() {
        if (submittingRef.current) return;
        submittingRef.current = true;
        setBusy(true);
        setError(null);
        setSubmitSuccess(null);
        try {
            await api.post(`/requests/${recordId}/submit`);
            setSubmitSuccess(
                `✓ Claim ${request?.request_number ?? ''} submitted successfully! Your claim has been forwarded to ${request?.assigned_reviewer?.display_name ?? 'your assigned reviewer'} for review.`
            );
            await load(true);
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof msg === 'string' ? msg : 'Submission failed. Please verify that all required documents and details are complete.');
        } finally {
            setBusy(false);
            submittingRef.current = false;
        }
    }

    async function startEditingAssignees() {
        setIsEditingAssignees(true);
        setAssigneeSaveError(null);
        try {
            const res = await api.get<UserSummary[]>('/users/eligible-assignees');
            setAssigneeList(res.data);
            if (request?.assigned_reviewer_id) setSelectedReviewerId(String(request.assigned_reviewer_id));
            else {
                const defRev = res.data.find((p) => p.role === 'reviewer' && (p.id === 5 || p.display_name.toLowerCase().includes('example')));
                if (defRev) setSelectedReviewerId(String(defRev.id));
            }
            if (request?.assigned_approver_id) setSelectedApproverId(String(request.assigned_approver_id));
            else {
                const defApp = res.data.find((p) => p.role === 'approver' && (p.id === 6 || p.display_name.toLowerCase().includes('example')));
                if (defApp) setSelectedApproverId(String(defApp.id));
            }
        } catch (err) {
            setAssigneeSaveError('Could not load eligible assignees list.');
        }
    }

    async function saveClaimDetails(e?: React.FormEvent) {
        if (e) e.preventDefault();
        setSavingDetails(true);
        setDetailsSaveError(null);
        setDetailsSaveSuccess(null);
        try {
            await api.patch(`/requests/${recordId}`, {
                title: editTitle.trim() || undefined,
                claimed_amount: editAmount ? editAmount : undefined,
                expense_date: editDate || undefined,
                expense_category: editCategory || undefined,
                currency: editCurrency || undefined,
                description: editDescription.trim() || undefined,
            });
            setDetailsSaveSuccess('Claim details updated and verification checks refreshed.');
            setIsEditingDetails(false);
            await load(true);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setDetailsSaveError(typeof msg === 'string' ? msg : 'Failed to update claim details.');
        } finally {
            setSavingDetails(false);
        }
    }
    async function saveAssignees() {
        if (!selectedReviewerId || !selectedApproverId) {
            setAssigneeSaveError('Please select both a reviewer and an approver.');
            return;
        }
        if (selectedReviewerId === selectedApproverId) {
            setAssigneeSaveError('Reviewer and approver must be different people.');
            return;
        }
        setAssigneeSaving(true);
        setAssigneeSaveError(null);
        try {
            await api.patch(`/requests/${recordId}/assignment`, {
                assigned_reviewer_id: Number(selectedReviewerId),
                assigned_approver_id: Number(selectedApproverId),
            });
            setIsEditingAssignees(false);
            await load(true);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setAssigneeSaveError(typeof msg === 'string' ? msg : 'Failed to update assignees.');
        } finally {
            setAssigneeSaving(false);
        }
    }

    async function uploadDocument() {
        if (!uploadFile) return;
        if (maxUploadMb !== null && uploadFile.size > maxUploadMb * 1024 * 1024) {
            setError(`This file exceeds the ${maxUploadMb} MB upload limit.`);
            return;
        }
        const form = new FormData();
        form.append('doc_type', uploadType);
        form.append('file', uploadFile);
        setBusy(true);
        setUploadMessage(null);
        setUploadProgress(0);
        setError(null);
        try {
            const uploaded = await api.post<DocumentVersion>(`/requests/${recordId}/documents`, form, {
                onUploadProgress: (event) => {
                    if (event.total) setUploadProgress(Math.round((event.loaded / event.total) * 100));
                },
            });
            setUploadFile(null);
            setUploadMessage(`${uploaded.data.original_filename} uploaded successfully. Extraction is now running.`);
            await load();
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof msg === 'string' ? msg : 'Upload failed.');
        } finally {
            setBusy(false);
            setUploadProgress(null);
        }
    }

    async function requestCorrection(customComment?: string) {
        const comment = customComment || actionComment;
        if (!comment.trim()) {
            setError('Comment is required to request correction.');
            return;
        }
        setBusy(true);
        try {
            await api.post(`/requests/${recordId}/request-correction`, { comment });
            setActionComment('');
            await load();
        } catch {
            setError('Could not request correction.');
        } finally {
            setBusy(false);
        }
    }

    async function approveOrReject(decision: 'approve' | 'reject', customComment?: string) {
        const comment = customComment || actionComment;
        if (!comment.trim()) {
            setError('A decision reason (comment) is required.');
            return;
        }
        if (!customComment && !window.confirm(decision === 'approve' ? 'Approve this request? This records a final decision.' : 'Reject this request? The reason will be recorded in its history.')) return;
        setBusy(true);
        try {
            await api.post(`/requests/${recordId}/${decision}`, { comment });
            setActionComment('');
            await load();
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof msg === 'string' ? msg : `${decision} failed.`);
        } finally {
            setBusy(false);
        }
    }

    async function completeReview(customComment?: string) {
        const comment = customComment || actionComment;
        if (!comment.trim()) { setError('Add a review summary before sending this claim for approval.'); return; }
        setBusy(true);
        try { await api.post(`/requests/${recordId}/complete-review`, { comment }); setActionComment(''); await load(); }
        catch (e: unknown) { const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail; setError(typeof msg === 'string' ? msg : 'Could not complete the review.'); }
        finally { setBusy(false); }
    }

    async function uploadReplacement(file: File, type: 'receipt' | 'expense_form' | 'supporting_document') {
        if (maxUploadMb !== null && file.size > maxUploadMb * 1024 * 1024) {
            setError(`This file exceeds the ${maxUploadMb} MB upload limit.`);
            return;
        }
        const form = new FormData();
        form.append('doc_type', type);
        form.append('file', file);
        setBusy(true);
        setUploadMessage(null);
        setUploadProgress(0);
        setError(null);
        try {
            const uploaded = await api.post<DocumentVersion>(`/requests/${recordId}/documents`, form, {
                onUploadProgress: (event) => {
                    if (event.total) setUploadProgress(Math.round((event.loaded / event.total) * 100));
                },
            });
            setUploadMessage(`${uploaded.data.original_filename} uploaded successfully. Extraction is now running.`);
            await load();
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof msg === 'string' ? msg : 'Upload failed.');
            throw e;
        } finally {
            setBusy(false);
            setUploadProgress(null);
        }
    }

    async function correctField(
        docId: number,
        fieldName: string,
        correctedVal: string,
        originalVal: string | null,
        reason: string
    ) {
        setBusy(true);
        setError(null);
        try {
            await api.post(`/requests/${recordId}/corrections`, {
                document_version_id: docId,
                field_name: fieldName,
                corrected_value: correctedVal,
                original_extracted_value: originalVal,
                reason: reason,
            });
            await load();
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : 'Could not save field correction.');
            throw err;
        } finally {
            setBusy(false);
        }
    }

    async function resolveCheck(checkId: number, resolution: 'resolved' | 'dismissed', reason?: string) {
        setBusy(true);
        setError(null);
        try {
            await api.post(`/requests/${recordId}/resolve-check`, { resolution_status: resolution, reason: reason?.trim() }, { params: { check_id: checkId } });
            await load();
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : 'Could not update the verification finding.');
        } finally {
            setBusy(false);
        }
    }

    async function retryDocument(documentId: number) {
        setBusy(true);
        setError(null);
        try {
            await api.post(`/documents/${documentId}/reprocess`);
            setUploadMessage('Processing retry queued. This page will refresh while extraction runs.');
            await load();
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : 'Could not retry document processing.');
        } finally {
            setBusy(false);
        }
    }

    if (loading) {
        return (
            <div className="page-wrap flex min-h-[400px] items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-3 border-indigo-600 border-t-transparent" />
                    <p className="text-xs font-semibold text-muted">Retrieving verified claim evidence…</p>
                </div>
            </div>
        );
    }

    if (error && !request) {
        return (
            <div className="page-wrap mx-auto max-w-3xl space-y-4">
                <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 shadow-xs">
                    <p className="font-bold">{error}</p>
                </div>
                <Link to="/requests" className="btn-secondary inline-flex text-xs">
                    ← Back to requests
                </Link>
            </div>
        );
    }

    if (!request) return null;

    const selectedDocument = documents.find((document) => document.id === selectedDocId) ?? null;

    const latestDocument = (type: DocumentVersion['doc_type']) => documents
        .filter((document) => document.doc_type === type)
        .reduce<DocumentVersion | null>((latest, document) => !latest || document.version_number > latest.version_number || (document.version_number === latest.version_number && document.id > latest.id) ? document : latest, null);

    const latestReceipt = latestDocument('receipt');
    const latestExpenseForm = latestDocument('expense_form');

    // Extracted receipt fields (filtering out raw OCR tokens)
    const receiptFields = latestReceipt ? (extractions[latestReceipt.id] ?? []).filter((f) => f.field_name !== '_raw_page_text') : [];
    const receiptMerchantEff = getFieldEffectiveValue(latestReceipt?.id, 'merchant_name', receiptFields, corrections);
    const receiptDateEff = getFieldEffectiveValue(latestReceipt?.id, 'expense_date', receiptFields, corrections);
    const receiptAmountEff = getFieldEffectiveValue(latestReceipt?.id, 'total_amount', receiptFields, corrections);
    const receiptCurrencyEff = getFieldEffectiveValue(latestReceipt?.id, 'currency', receiptFields, corrections);
    const receiptRefEff = getFieldEffectiveValue(latestReceipt?.id, 'reference_number', receiptFields, corrections);

    const receiptMerchant = receiptMerchantEff.value;
    const receiptDateFormatted = formatExpenseDate(receiptDateEff.value);
    const receiptCurrency = receiptCurrencyEff.value || request.currency || 'INR';
    const receiptAmountFormatted = formatReceiptAmount(receiptAmountEff.value, receiptCurrency);
    const receiptReference = receiptRefEff.value;

    // Extracted form fields
    const formFields = latestExpenseForm ? (extractions[latestExpenseForm.id] ?? []).filter((f) => f.field_name !== '_raw_page_text') : [];
    const formEmployeeEff = getFieldEffectiveValue(latestExpenseForm?.id, 'employee_name', formFields, corrections);
    const formAmountEff = getFieldEffectiveValue(latestExpenseForm?.id, 'total_amount', formFields, corrections);
    const formDateEff = getFieldEffectiveValue(latestExpenseForm?.id, 'expense_date', formFields, corrections);

    // Verification findings
    const amountMismatchCheck = checks.find(
        (c) => c.check_type === 'amount_mismatch' && c.result === 'flag' && c.resolution_status === 'open'
    );
    const missingFieldCheck = checks.find(
        (c) => c.check_type === 'missing_field' && c.result === 'flag' && c.resolution_status === 'open'
    );

    // Modern 4-step workflow completion conditions
    const hasReadyDoc = Boolean(
        (latestExpenseForm && latestExpenseForm.processing_status === 'ready') ||
        (latestReceipt && latestReceipt.processing_status === 'ready')
    );
    const hasPendingDoc = documents.some((doc) => doc.processing_status === 'processing' || doc.processing_status === 'pending');
    const hasFailedDoc = documents.some((doc) => doc.processing_status === 'failed');

    // Step 1: Upload Documents (complete when at least 1 document uploaded and ready)
    const isStep1Complete = hasReadyDoc && !hasPendingDoc && !hasFailedDoc;

    // Step 2: Extracted Details & Missing Fields (complete when amount and date are confirmed)
    const isStep2Complete = Boolean(
        isStep1Complete &&
        request.claimed_amount != null &&
        Number(request.claimed_amount) > 0 &&
        request.expense_date &&
        request.assigned_reviewer_id &&
        request.assigned_approver_id
    );

    // Step 3: Verification Checks (complete when checks have been run)
    const isStep3Complete = Boolean(isStep2Complete && checks.length > 0);

    // Step 4: Submitted (complete when status is no longer draft)
    const isStep4Complete = request.status !== 'draft';

    // Reason why submission is currently disabled
    let submissionBlockReason: string | null = null;
    if (!latestReceipt && !latestExpenseForm) {
        submissionBlockReason = 'Please upload a receipt or expense document in Step 1.';
    } else if (hasPendingDoc) {
        submissionBlockReason = 'Your document is still being processed. Please wait for OCR extraction to complete.';
    } else if (hasFailedDoc) {
        submissionBlockReason = latestReceipt?.processing_error || "Document processing failed. Please upload a clearer copy in Step 1.";
    } else if (!request.claimed_amount) {
        submissionBlockReason = 'Please confirm or enter the claimed amount in Step 2.';
    } else if (!request.expense_date) {
        submissionBlockReason = 'Please confirm or select the expense date in Step 2.';
    } else if (!request.assigned_reviewer_id || !request.assigned_approver_id) {
        submissionBlockReason = 'Please select an active reviewer and approver in Step 2.';
    }

    const isDraftMode = isSubmitter && ['draft', 'more_info_required'].includes(request.status);

    return (
        <div className="page-wrap space-y-7">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <Link to="/dashboard" className="rounded-xl border border-surface-border bg-white p-2 text-muted hover:text-main shadow-xs transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <p className="mb-1 text-[10px] font-bold uppercase tracking-[.15em] text-indigo-700">
                            Expense reimbursement · {request.expense_category?.replace(/_/g, ' ') ?? 'Other'}
                        </p>
                        <h1 className="text-2xl font-bold tracking-tight text-main">{request.request_number}</h1>
                        <p className="mt-0.5 text-xs text-muted">{request.title}</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <Link
                        to={`/assistant?requestId=${request.id}`}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-violet-200 bg-violet-50 px-3.5 py-1.5 text-xs font-bold text-[#7656D6] hover:bg-violet-100 transition shadow-2xs"
                        title="Open AI Assistant for this claim"
                    >
                        <Sparkles className="h-3.5 w-3.5 text-[#7656D6]" />
                        <span>Ask AI Assistant</span>
                    </Link>
                    <span className={`px-3 py-1 text-xs font-bold ${request.status === 'approved' ? 'badge-approved' : request.status === 'rejected' || request.status === 'processing_failed' ? 'badge-failed' : request.status === 'more_info_required' ? 'badge-more-info' : request.status === 'under_review' || request.status === 'pending_approval' ? 'badge-review' : request.status === 'processing' ? 'badge-processing' : 'badge-submitted'}`}>
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />{STATUS_LABEL[request.status]}
                    </span>
                </div>
            </div>

            {/* View Switcher Tabs */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border pb-3">
                <div className="inline-flex rounded-xl bg-slate-200/60 p-1 shadow-inner">
                    <button
                        type="button"
                        onClick={() => setActiveView('details')}
                        className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
                            activeView === 'details'
                                ? 'bg-white text-main shadow-xs'
                                : 'text-muted hover:text-main'
                        }`}
                    >
                        <FileCheck2 className="h-4 w-4 text-indigo-600" />
                        {isDraftMode ? 'Guided Claim Workflow' : 'Claim Details & Verification'}
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveView('graph')}
                        className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
                            activeView === 'graph'
                                ? 'bg-white text-indigo-700 shadow-xs'
                                : 'text-muted hover:text-main'
                        }`}
                    >
                        <Network className="h-4 w-4 text-indigo-600" />
                        <span>Evidence Impact Graph</span>
                        {graphData && (graphData.summary.flagged_findings + graphData.summary.error_findings) > 0 && (
                            <span className="ml-1 inline-flex items-center justify-center rounded-full bg-amber-100 px-2 py-0.2 text-[10px] font-bold text-amber-800">
                                {graphData.summary.flagged_findings + graphData.summary.error_findings} issue{graphData.summary.flagged_findings + graphData.summary.error_findings > 1 ? 's' : ''}
                            </span>
                        )}
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveView('replay')}
                        className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
                            activeView === 'replay'
                                ? 'bg-white text-indigo-700 shadow-xs'
                                : 'text-muted hover:text-main'
                        }`}
                    >
                        <History className="h-4 w-4 text-indigo-600" />
                        <span>Decision Replay</span>
                        {replayData && replayData.total_events > 0 && (
                            <span className="ml-1 inline-flex items-center justify-center rounded-full bg-slate-200 px-2 py-0.2 text-[10px] font-bold text-slate-700">
                                {replayData.total_events}
                            </span>
                        )}
                    </button>
                </div>

                {activeView === 'details' && (
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={() => setActiveView('replay')}
                            className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 hover:text-indigo-900 transition-colors"
                        >
                            <History className="h-3.5 w-3.5" />
                            <span>Decision Replay Timeline →</span>
                        </button>
                        <span className="text-slate-300">•</span>
                        <button
                            type="button"
                            onClick={() => setActiveView('graph')}
                            className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 hover:text-indigo-900 transition-colors"
                        >
                            <Network className="h-3.5 w-3.5" />
                            <span>Evidence Graph →</span>
                        </button>
                    </div>
                )}
            </div>

            {submitSuccess && (
                <div className="flex items-start justify-between gap-2.5 p-4 rounded-xl bg-teal-50 text-teal-800 text-xs border border-teal-200 shadow-xs animate-fade-in-up" role="status">
                    <div className="flex items-start gap-2.5">
                        <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-teal-600" />
                        <div>
                            <p className="font-bold text-teal-900">Submission Confirmed</p>
                            <p className="mt-0.5 font-medium">{submitSuccess}</p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => setSubmitSuccess(null)}
                        className="text-teal-700 hover:text-teal-900 font-bold ml-2 text-sm"
                    >
                        ✕
                    </button>
                </div>
            )}

            {error && (
                <div className="flex items-start gap-2.5 p-4 rounded-xl bg-red-50 text-red-700 text-xs border border-red-200" role="alert">
                    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span className="font-semibold">{error}</span>
                </div>
            )}

            {/* View Content: Graph, Decision Replay, or Claim Details */}
            {activeView === 'graph' ? (
                <EvidenceImpactGraph
                    graphData={graphData}
                    loading={loading}
                    error={error}
                    onRefresh={() => load(true)}
                    onSelectDocument={(docId) => {
                        setSelectedDocId(docId);
                        setActiveView('details');
                    }}
                    userRole={user?.role}
                />
            ) : activeView === 'replay' ? (
                <DecisionReplayTimeline
                    replayData={replayData}
                    loading={loading}
                    error={error}
                    onRefresh={() => load(true)}
                    userRole={user?.role}
                />
            ) : isDraftMode ? (
                <div className="space-y-6">
                    {/* 4-Step Progress Indicator */}
                    <div className="card p-5">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-surface-border pb-3">
                            <div>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                                    Guided Claim Workflow
                                </span>
                                <h2 className="text-base font-bold text-main">
                                    Step {wizardStep} of 4: {
                                        wizardStep === 1 ? 'Upload documents' :
                                        wizardStep === 2 ? 'Review extracted details' :
                                        wizardStep === 3 ? 'Document verification' :
                                        'Review and submit'
                                    }
                                </h2>
                            </div>
                            <p className="text-xs font-semibold text-muted">
                                Draft claim saved · You control when to submit
                            </p>
                        </div>

                        {/* Interactive Step Buttons */}
                        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                            {[
                                { num: 1, label: 'Upload documents', complete: isStep1Complete },
                                { num: 2, label: 'Extracted details', complete: isStep2Complete },
                                { num: 3, label: 'Verification', complete: isStep3Complete },
                                { num: 4, label: 'Submit', complete: isStep4Complete },
                            ].map(({ num, label, complete }) => {
                                const current = wizardStep === num;
                                return (
                                    <button
                                        key={num}
                                        type="button"
                                        onClick={() => setWizardStep(num)}
                                        className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${
                                            current
                                                ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 ring-2 ring-indigo-100 shadow-xs'
                                                : complete
                                                ? 'border-teal-200 bg-teal-50/40 text-teal-950 hover:bg-teal-50/70'
                                                : 'border-surface-border bg-white text-muted hover:bg-slate-50'
                                        }`}
                                    >
                                        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                                            complete
                                                ? 'bg-teal-600 text-white'
                                                : current
                                                ? 'bg-indigo-700 text-white shadow-xs'
                                                : 'bg-slate-200 text-slate-600'
                                        }`}>
                                            {complete ? '✓' : num}
                                        </span>
                                        <div className="min-w-0 flex-1">
                                            <p className={`truncate text-xs font-bold ${current ? 'text-indigo-950' : complete ? 'text-teal-900' : 'text-main'}`}>
                                                {label}
                                            </p>
                                            <p className="text-[10px] text-muted">
                                                {complete ? 'Completed' : current ? 'In progress' : 'Upcoming'}
                                            </p>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* STEP 1: Upload documents */}
                    {wizardStep === 1 && (
                        <section className="card p-6 space-y-5">
                            <div className="border-b border-surface-border pb-3">
                                <h3 className="text-base font-bold text-main">Step 1 — Upload documents</h3>
                                <p className="mt-1 text-xs text-muted">
                                    Upload your receipt or invoice. DocuVerify AI automatically extracts merchant, date, amount, and currency.
                                </p>
                            </div>

                            {/* Notice distinguishing uploading from submitting */}
                            <div className="rounded-xl border border-indigo-200/70 bg-indigo-50/50 p-4 text-xs leading-relaxed text-indigo-950 font-medium">
                                <strong>How it works:</strong> Uploading runs automated OCR extraction. In Step 2, you will review the extracted details and fill any missing information before submitting.
                            </div>

                            {/* Document Cards explaining state & action */}
                            <div className="grid gap-4 md:grid-cols-2">
                                {/* 1. Receipt / Invoice (Primary) */}
                                {(() => {
                                    const latest = latestReceipt;
                                    const cleanFields = latest ? (extractions[latest.id] ?? []).filter((f) => f.field_name !== '_raw_page_text') : [];
                                    const isFailed = latest?.processing_status === 'failed';
                                    const isProcessing = latest?.processing_status === 'processing' || latest?.processing_status === 'pending';
                                    const isReady = latest?.processing_status === 'ready';

                                    return (
                                        <div className="rounded-xl border border-surface-border bg-slate-50/60 p-4 space-y-3">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-indigo-700 shadow-xs ring-1 ring-slate-200">
                                                        <Receipt className="h-4 w-4" />
                                                    </span>
                                                    <div>
                                                        <h4 className="text-xs font-bold text-main">Receipt or Invoice <span className="text-red-600">*</span></h4>
                                                        <p className="text-[10px] text-muted">Proof showing merchant, date & total amount</p>
                                                    </div>
                                                </div>
                                                {latest ? (
                                                    <span className={`badge ${isReady ? 'bg-teal-50 text-teal-700 ring-teal-200' : isFailed ? 'bg-red-50 text-red-700 ring-red-200' : 'bg-amber-50 text-amber-800 ring-amber-200'}`}>
                                                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                        {latest.processing_status}
                                                    </span>
                                                ) : (
                                                    <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-bold text-muted ring-1 ring-surface-border">
                                                        Required
                                                    </span>
                                                )}
                                            </div>

                                            {/* Error Message banner if failed (Blank, Blurry, Unreadable) */}
                                            {isFailed && (
                                                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-900 space-y-1.5">
                                                    <p className="font-bold flex items-center gap-1.5 text-red-800">
                                                        <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                                                        Document could not be extracted
                                                    </p>
                                                    <p className="text-[11px] leading-relaxed text-red-700 font-medium">
                                                        {latest.processing_error || "This document could not be read. Please upload a clearer copy or scan."}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Details & States */}
                                            <div className="rounded-xl bg-white p-3 text-[11px] space-y-1.5 border border-surface-border shadow-xs">
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Filename:</span>
                                                    <span className="font-semibold text-main truncate max-w-[170px]">{latest?.original_filename ?? 'None uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Upload status:</span>
                                                    <span className="font-semibold text-main">{latest ? `Uploaded (v${latest.version_number})` : 'Not uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Extraction status:</span>
                                                    <span className="font-semibold text-main">
                                                        {isReady
                                                            ? `Extracted (${cleanFields.length} fields)`
                                                            : isProcessing
                                                            ? 'Reading document text…'
                                                            : isFailed
                                                            ? 'Extraction failed'
                                                            : 'Waiting for upload'}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Action buttons */}
                                            <div className="flex flex-col gap-2 pt-1">
                                                {isFailed && (
                                                    <button
                                                        type="button"
                                                        className="btn-secondary text-[11px] py-1.5 px-3 w-full flex items-center justify-center gap-1.5"
                                                        onClick={() => retryDocument(latest.id)}
                                                    >
                                                        <RotateCw className="h-3 w-3" /> Retry extraction
                                                    </button>
                                                )}

                                                <input
                                                    id="upload-file-receipt"
                                                    type="file"
                                                    className="sr-only"
                                                    accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                                                    onChange={(e) => {
                                                        setUploadType('receipt');
                                                        setUploadFile(e.target.files?.[0] ?? null);
                                                    }}
                                                />
                                                <button
                                                    type="button"
                                                    className="btn-secondary w-full text-xs py-2 flex items-center justify-center gap-1.5"
                                                    onClick={() => document.getElementById('upload-file-receipt')?.click()}
                                                >
                                                    <Upload className="h-3.5 w-3.5" />
                                                    {isFailed ? 'Upload clearer photo / scan' : latest ? 'Upload replacement receipt' : 'Choose receipt file'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })()}

                                {/* 2. Expense Form / Supporting Document (Optional) */}
                                {(() => {
                                    const latest = latestExpenseForm;
                                    const cleanFields = latest ? (extractions[latest.id] ?? []).filter((f) => f.field_name !== '_raw_page_text') : [];
                                    const isFailed = latest?.processing_status === 'failed';
                                    const isProcessing = latest?.processing_status === 'processing' || latest?.processing_status === 'pending';
                                    const isReady = latest?.processing_status === 'ready';

                                    return (
                                        <div className="rounded-xl border border-surface-border bg-slate-50/60 p-4 space-y-3">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-indigo-700 shadow-xs ring-1 ring-slate-200">
                                                        <FileCheck2 className="h-4 w-4" />
                                                    </span>
                                                    <div>
                                                        <h4 className="text-xs font-bold text-main">Expense Form (Optional)</h4>
                                                        <p className="text-[10px] text-muted">Completed reimbursement form if applicable</p>
                                                    </div>
                                                </div>
                                                {latest ? (
                                                    <span className={`badge ${isReady ? 'bg-teal-50 text-teal-700 ring-teal-200' : isFailed ? 'bg-red-50 text-red-700 ring-red-200' : 'bg-amber-50 text-amber-800 ring-amber-200'}`}>
                                                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                        {latest.processing_status}
                                                    </span>
                                                ) : (
                                                    <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-bold text-slate-500 ring-1 ring-surface-border">
                                                        Optional
                                                    </span>
                                                )}
                                            </div>

                                            {isFailed && (
                                                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-900 space-y-1.5">
                                                    <p className="font-bold flex items-center gap-1.5 text-red-800">
                                                        <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                                                        Document could not be extracted
                                                    </p>
                                                    <p className="text-[11px] leading-relaxed text-red-700 font-medium">
                                                        {latest.processing_error || "Could not extract this document. Upload a clearer scan or PDF."}
                                                    </p>
                                                </div>
                                            )}

                                            <div className="rounded-xl bg-white p-3 text-[11px] space-y-1.5 border border-surface-border shadow-xs">
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Filename:</span>
                                                    <span className="font-semibold text-main truncate max-w-[170px]">{latest?.original_filename ?? 'None uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Upload status:</span>
                                                    <span className="font-semibold text-main">{latest ? `Uploaded (v${latest.version_number})` : 'Not uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Extraction status:</span>
                                                    <span className="font-semibold text-main">
                                                        {isReady
                                                            ? `Extracted (${cleanFields.length} fields)`
                                                            : isProcessing
                                                            ? 'Reading document text…'
                                                            : isFailed
                                                            ? 'Extraction failed'
                                                            : 'Not attached'}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex flex-col gap-2 pt-1">
                                                {isFailed && (
                                                    <button
                                                        type="button"
                                                        className="btn-secondary text-[11px] py-1.5 px-3 w-full flex items-center justify-center gap-1.5"
                                                        onClick={() => retryDocument(latest.id)}
                                                    >
                                                        <RotateCw className="h-3 w-3" /> Retry extraction
                                                    </button>
                                                )}

                                                <input
                                                    id="upload-file-form"
                                                    type="file"
                                                    className="sr-only"
                                                    accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                                                    onChange={(e) => {
                                                        setUploadType('expense_form');
                                                        setUploadFile(e.target.files?.[0] ?? null);
                                                    }}
                                                />
                                                <button
                                                    type="button"
                                                    className="btn-secondary w-full text-xs py-2 flex items-center justify-center gap-1.5"
                                                    onClick={() => document.getElementById('upload-file-form')?.click()}
                                                >
                                                    <Upload className="h-3.5 w-3.5" />
                                                    {latest ? 'Upload replacement form' : 'Attach expense form'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })()}
                            </div>

                            {/* File Upload Trigger Modal/Box */}
                            {uploadFile && (
                                <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-xs font-bold text-main">
                                                Selected for {uploadType.replace(/_/g, ' ')}:
                                            </p>
                                            <p className="text-xs text-slate-600 font-medium">
                                                {uploadFile.name} ({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)
                                            </p>
                                        </div>
                                        <button
                                            type="button"
                                            className="text-xs font-bold text-slate-500 hover:text-red-600 transition-colors"
                                            onClick={() => setUploadFile(null)}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                    {uploadProgress !== null && (
                                        <div className="space-y-1">
                                            <div className="flex justify-between text-[10px] text-muted font-semibold">
                                                <span>Uploading to server</span>
                                                <span>{uploadProgress}%</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                                                <div className="h-full bg-indigo-600 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                                            </div>
                                        </div>
                                    )}
                                    <button
                                        type="button"
                                        className="btn-primary w-full text-xs"
                                        disabled={busy}
                                        onClick={uploadDocument}
                                    >
                                        {busy ? 'Uploading…' : 'Start Secure Upload'}
                                    </button>
                                </div>
                            )}

                            {uploadMessage && (
                                <p className="flex items-center gap-2 text-xs text-teal-800 bg-teal-50 border border-teal-200 p-3 rounded-xl font-medium">
                                    <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-600" />
                                    {uploadMessage}
                                </p>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <span className="text-xs text-muted">
                                    {hasReadyDoc ? '✓ Document ready. Proceed to review extracted figures.' : 'Upload receipt to start extraction.'}
                                </span>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    disabled={!hasReadyDoc}
                                    onClick={() => setWizardStep(2)}
                                >
                                    Continue to Review Extracted Information
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>
                        </section>
                    )}

                    {/* STEP 2: Review extracted details & fill missing information */}
                    {wizardStep === 2 && (
                        <section className="card p-6 space-y-6">
                            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border pb-3">
                                <div>
                                    <h3 className="text-base font-bold text-main">Step 2 — Review Extracted Information</h3>
                                    <p className="mt-1 text-xs text-muted">
                                        Review the figures detected by OCR. If any required information was not found, enter it below.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setIsEditingDetails(!isEditingDetails)}
                                    className="btn-secondary text-xs py-1.5 px-3"
                                >
                                    {isEditingDetails ? 'Hide Edit Form' : 'Edit / Correct Details'}
                                </button>
                            </div>

                            {detailsSaveSuccess && (
                                <p className="text-xs text-teal-800 bg-teal-50 border border-teal-200 p-3 rounded-xl font-medium flex items-center gap-2">
                                    <CheckCircle2 className="h-4 w-4 text-teal-600" />
                                    {detailsSaveSuccess}
                                </p>
                            )}

                            {/* Required fields banner: missing vs complete */}
                            {(!request.claimed_amount || !request.expense_date) ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 space-y-2 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        Additional Required Information Needed
                                    </p>
                                    <p className="text-slate-700 leading-relaxed">
                                        Some required fields could not be automatically detected from your document (e.g. {!request.claimed_amount ? 'claimed amount' : ''}{!request.claimed_amount && !request.expense_date ? ' and ' : ''}{!request.expense_date ? 'expense date' : ''}). Please fill them in below to proceed.
                                    </p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-950 space-y-1.5 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-teal-900">
                                        <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                                        All Required Expense Details Detected & Ready
                                    </p>
                                    <p className="text-slate-700 leading-relaxed font-medium">
                                        We extracted the amount, date, and merchant. You can proceed directly to verification, or adjust any value using the form below.
                                    </p>
                                </div>
                            )}

                            {/* Prominent Extracted Figures Card */}
                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
                                <div className="rounded-xl border border-surface-border bg-slate-50/80 p-4">
                                    <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Merchant / Vendor</span>
                                    <span className="text-sm font-bold text-main mt-1 block truncate">
                                        {receiptMerchant || <span className="text-slate-400 font-normal italic">Not detected</span>}
                                    </span>
                                </div>
                                <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
                                    <span className="text-[10px] text-indigo-700 block font-bold uppercase tracking-wider">Claimed Amount</span>
                                    <span className="text-base font-extrabold text-indigo-950 mt-1 block">
                                        {request.claimed_amount != null ? `${request.currency ?? 'INR'} ${Number(request.claimed_amount).toLocaleString()}` : <span className="text-amber-700 font-bold">Needs entry</span>}
                                    </span>
                                </div>
                                <div className="rounded-xl border border-surface-border bg-slate-50/80 p-4">
                                    <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Expense Date</span>
                                    <span className="text-sm font-bold text-main mt-1 block">
                                        {request.expense_date ? formatExpenseDate(request.expense_date) : <span className="text-amber-700 font-bold">Needs entry</span>}
                                    </span>
                                </div>
                                <div className="rounded-xl border border-surface-border bg-slate-50/80 p-4">
                                    <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Currency</span>
                                    <span className="text-sm font-bold text-main mt-1 block">
                                        {request.currency || 'INR'}
                                    </span>
                                </div>
                            </div>

                            {/* Inline Edit Form for Missing or Corrected Details */}
                            {(isEditingDetails || !request.claimed_amount || !request.expense_date) && (
                                <form onSubmit={saveClaimDetails} className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5 space-y-4">
                                    <div className="flex items-center justify-between border-b border-indigo-100 pb-2">
                                        <h4 className="text-xs font-bold text-indigo-950">
                                            {(!request.claimed_amount || !request.expense_date) ? 'Enter Missing Expense Details' : 'Edit Claim Information'}
                                        </h4>
                                        {detailsSaveError && <p className="text-[11px] text-red-600 font-semibold">{detailsSaveError}</p>}
                                    </div>

                                    <div className="grid gap-3 sm:grid-cols-3">
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Claim Amount ({editCurrency}) <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="number"
                                                step="0.01"
                                                min="0.01"
                                                required
                                                value={editAmount}
                                                onChange={(e) => setEditAmount(e.target.value)}
                                                placeholder="e.g. 450.00"
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Expense Date <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                required
                                                value={editDate}
                                                onChange={(e) => setEditDate(e.target.value)}
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Category
                                            </label>
                                            <select
                                                value={editCategory}
                                                onChange={(e) => setEditCategory(e.target.value)}
                                                className="form-input text-xs py-1.5 w-full"
                                            >
                                                <option value="travel">Travel</option>
                                                <option value="meals">Meals & Dining</option>
                                                <option value="lodging">Lodging & Hotel</option>
                                                <option value="supplies">Office Supplies</option>
                                                <option value="software">Software & Tech</option>
                                                <option value="other">Other</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid gap-3 sm:grid-cols-2">
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Claim Title
                                            </label>
                                            <input
                                                type="text"
                                                value={editTitle}
                                                onChange={(e) => setEditTitle(e.target.value)}
                                                placeholder="e.g. Starbucks Reimbursement"
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Purpose / Description (Optional)
                                            </label>
                                            <input
                                                type="text"
                                                value={editDescription}
                                                onChange={(e) => setEditDescription(e.target.value)}
                                                placeholder="e.g. Client coffee meeting"
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                    </div>

                                    <div className="flex justify-end gap-2 pt-1">
                                        <button
                                            type="submit"
                                            disabled={savingDetails || !editAmount || !editDate}
                                            className="btn-primary text-xs py-1.5 px-4 font-bold"
                                        >
                                            {savingDetails ? 'Saving…' : 'Save Details'}
                                        </button>
                                    </div>
                                </form>
                            )}

                            {/* Assignee Routing & Reviewer Assignment Card */}
                            <div className="rounded-xl border border-surface-border bg-slate-50/70 p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-bold text-main uppercase tracking-wider">Approval Routing</h4>
                                    {!isEditingAssignees && isSubmitter && (
                                        <button
                                            type="button"
                                            onClick={startEditingAssignees}
                                            className="text-[11px] font-bold text-indigo-700 hover:underline"
                                        >
                                            Change Assignees
                                        </button>
                                    )}
                                </div>

                                {isEditingAssignees ? (
                                    <div className="space-y-3 pt-2">
                                        {assigneeSaveError && <p className="text-[11px] text-red-600 font-semibold">{assigneeSaveError}</p>}
                                        <div className="grid gap-3 sm:grid-cols-2">
                                            <div>
                                                <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                    Assigned Reviewer
                                                </label>
                                                <select
                                                    value={selectedReviewerId}
                                                    onChange={(e) => setSelectedReviewerId(e.target.value)}
                                                    className="form-input text-xs py-1.5"
                                                    disabled={assigneeSaving}
                                                >
                                                    <option value="">Select a reviewer</option>
                                                    {assigneeList.filter((a) => a.role === 'reviewer').map((rev) => (
                                                        <option key={rev.id} value={rev.id}>
                                                            {rev.display_name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                    Human Approver
                                                </label>
                                                <select
                                                    value={selectedApproverId}
                                                    onChange={(e) => setSelectedApproverId(e.target.value)}
                                                    className="form-input text-xs py-1.5"
                                                    disabled={assigneeSaving}
                                                >
                                                    <option value="">Select an approver</option>
                                                    {assigneeList.filter((a) => a.role === 'approver').map((app) => (
                                                        <option key={app.id} value={app.id}>
                                                            {app.display_name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                        </div>
                                        <div className="flex justify-end gap-2 pt-1">
                                            <button
                                                type="button"
                                                onClick={() => setIsEditingAssignees(false)}
                                                className="btn-secondary text-xs py-1 px-3"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="button"
                                                onClick={saveAssignees}
                                                disabled={assigneeSaving}
                                                className="btn-primary text-xs py-1 px-3"
                                            >
                                                {assigneeSaving ? 'Saving…' : 'Save Assignees'}
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="grid gap-3 sm:grid-cols-2 text-xs">
                                        <div>
                                            <span className="text-muted block text-[10px]">Reviewer:</span>
                                            <strong className="text-main font-bold">{request.assigned_reviewer?.display_name ?? 'Not assigned'}</strong>
                                        </div>
                                        <div>
                                            <span className="text-muted block text-[10px]">Approver:</span>
                                            <strong className="text-main font-bold">{request.assigned_approver?.display_name ?? 'Not assigned'}</strong>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => setWizardStep(1)}
                                >
                                    ← Back: Documents
                                </button>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    disabled={!request.claimed_amount || !request.expense_date}
                                    onClick={() => setWizardStep(3)}
                                >
                                    Continue to Verification
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>
                        </section>
                    )}

                    {/* STEP 3: Automated document verification & comparison */}
                    {wizardStep === 3 && (
                        <section className="space-y-6">
                            {/* Plain-Language Status Alert */}
                            {amountMismatchCheck && amountMismatchCheck.result === 'flag' && amountMismatchCheck.resolution_status === 'open' ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 space-y-1.5 shadow-xs">
                                    <div className="flex items-center gap-2 font-bold text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        <span>Amount difference detected between documents.</span>
                                    </div>
                                    <p className="leading-relaxed text-slate-700">
                                        {amountMismatchCheck.explanation}
                                    </p>
                                    <p className="text-slate-800 font-semibold pt-1">
                                        <strong>Note:</strong> A mismatch requires reviewer verification. It does not mean your claim is rejected. You can return to Step 1 or Step 2 to make adjustments if needed.
                                    </p>
                                </div>
                            ) : missingFieldCheck && missingFieldCheck.result === 'flag' && missingFieldCheck.resolution_status === 'open' ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 space-y-1.5 shadow-xs">
                                    <div className="flex items-center gap-2 font-bold text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        <span>Some document fields could not be confidently read.</span>
                                    </div>
                                    <p className="leading-relaxed text-slate-700">
                                        {missingFieldCheck.explanation}
                                    </p>
                                    <p className="text-slate-800 font-semibold pt-1">
                                        <strong>Note:</strong> A human reviewer will inspect the uploaded document to verify these details.
                                    </p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-950 shadow-xs">
                                    <div className="flex items-center gap-2 font-bold text-teal-900">
                                        <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                                        <span>Automated verification complete. All readable information verified.</span>
                                    </div>
                                    <p className="mt-1 text-slate-700 font-medium">
                                        Review the verification summary below and proceed to Step 4 to submit.
                                    </p>
                                </div>
                            )}

                            {/* Clean Document Summary Card */}
                            <div className="card overflow-hidden border-indigo-200/70 shadow-md">
                                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border bg-slate-50/80 px-6 py-4">
                                    <div className="flex items-center gap-2.5">
                                        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-xs">
                                            <Receipt className="h-4 w-4" />
                                        </span>
                                        <div>
                                            <h3 className="text-sm font-bold text-main">Receipt Information</h3>
                                            <p className="text-[10px] text-muted">Summary of extracted receipt data</p>
                                        </div>
                                    </div>
                                    {latestReceipt && (
                                        <span className="rounded-md bg-white px-2.5 py-1 text-[10px] font-bold text-slate-700 ring-1 ring-surface-border shadow-xs">
                                            Receipt v{latestReceipt.version_number}
                                        </span>
                                    )}
                                </div>
                                <div className="p-6">
                                    <div className="space-y-4">
                                        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-surface-border pb-4">
                                            <div>
                                                <h4 className="text-2xl font-black text-main sm:text-3xl">
                                                    {receiptMerchant || <span className="text-sm font-normal italic text-slate-400">Merchant not detected</span>}
                                                </h4>
                                                <p className="mt-1 text-sm font-bold text-muted">
                                                    {receiptDateFormatted || <span className="text-xs font-normal italic text-slate-400">Date not detected</span>}
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-3xl font-black text-indigo-950 sm:text-4xl">
                                                    {receiptAmountFormatted || <span className="text-sm font-normal italic text-slate-400">Amount not detected</span>}
                                                </p>
                                            </div>
                                        </div>
                                        {receiptReference && (
                                            <p className="text-xs text-slate-700 font-medium">
                                                Reference / Invoice #: <strong className="text-main">{receiptReference}</strong>
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Comparison Side-by-Side if expense form is uploaded */}
                            {latestExpenseForm && (
                                <div className="card p-5">
                                    <h4 className="text-xs font-bold text-main mb-3">Expense Form Comparison</h4>
                                    <div className="grid gap-3 sm:grid-cols-3 text-xs">
                                        <div className="rounded-xl border border-surface-border bg-slate-50/80 p-3">
                                            <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Employee Name</span>
                                            <span className="font-bold text-main mt-0.5 block">{formEmployeeEff.value || 'Not detected'}</span>
                                        </div>
                                        <div className="rounded-xl border border-surface-border bg-slate-50/80 p-3">
                                            <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Form Amount</span>
                                            <span className="font-bold text-main mt-0.5 block">
                                                {formAmountEff.value ? formatReceiptAmount(formAmountEff.value, request.currency ?? 'INR') : 'Not detected'}
                                            </span>
                                        </div>
                                        <div className="rounded-xl border border-surface-border bg-slate-50/80 p-3">
                                            <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Form Date</span>
                                            <span className="font-bold text-main mt-0.5 block">
                                                {formDateEff.value ? formatExpenseDate(formDateEff.value) : 'Not detected'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Document Preview */}
                            {selectedDocument && previewUrl && (
                                <div className="card p-5">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="text-xs font-bold text-main">Visual Preview: {selectedDocument.original_filename}</h4>
                                        <a href={previewUrl} download={selectedDocument.original_filename} className="btn-secondary text-[11px] py-1.5 px-3">
                                            <Download className="h-3 w-3" /> Download
                                        </a>
                                    </div>
                                    <div className="max-h-[380px] overflow-auto rounded-xl border border-surface-border bg-slate-50 flex items-center justify-center p-2">
                                        {selectedDocument.mime_type?.startsWith('image/') ? (
                                            <img src={previewUrl} alt="Preview" className="max-h-[360px] object-contain rounded-lg shadow-xs" />
                                        ) : (
                                            <iframe src={previewUrl} title="Document Preview" className="h-[360px] w-full rounded-lg" />
                                        )}
                                    </div>
                                </div>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => setWizardStep(2)}
                                >
                                    ← Back: Extracted Details
                                </button>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    onClick={() => setWizardStep(4)}
                                >
                                    Continue to Submit
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>
                        </section>
                    )}

                    {/* STEP 4: Review and submit */}
                    {wizardStep === 4 && (
                        <section className="card p-6 space-y-6">
                            <div className="border-b border-surface-border pb-3">
                                <h3 className="text-base font-bold text-main">Step 4 — Review and submit</h3>
                                <p className="mt-1 text-xs text-muted">
                                    Confirm the claim details and submit for reviewer evaluation and executive sign-off.
                                </p>
                            </div>

                            {/* Claim Summary */}
                            <div className="rounded-xl border border-surface-border bg-slate-50/70 p-4 space-y-3">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted">Claim Summary</h4>
                                <dl className="grid gap-2 sm:grid-cols-2 text-xs">
                                    <div><span className="text-muted">Claim Number:</span> <strong className="text-main ml-1">{request.request_number}</strong></div>
                                    <div><span className="text-muted">Claim Title:</span> <strong className="text-main ml-1">{request.title}</strong></div>
                                    <div><span className="text-muted">Total Claimed:</span> <strong className="text-indigo-950 font-bold ml-1">{request.currency ?? 'INR'} {Number(request.claimed_amount ?? 0).toLocaleString()}</strong></div>
                                    <div><span className="text-muted">Expense Date:</span> <strong className="text-main ml-1">{request.expense_date ? formatExpenseDate(request.expense_date) : '—'}</strong></div>
                                    <div><span className="text-muted">Assigned Reviewer:</span> <strong className="text-main ml-1">{request.assigned_reviewer?.display_name ?? '—'}</strong></div>
                                    <div><span className="text-muted">Human Approver:</span> <strong className="text-main ml-1">{request.assigned_approver?.display_name ?? '—'}</strong></div>
                                </dl>
                            </div>

                            {/* Pre-Submission Checklist */}
                            <div className="space-y-3">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted">Submission Checklist</h4>
                                <div className="space-y-2 text-xs">
                                    <div className="flex items-center gap-2.5">
                                        <span className={latestReceipt?.processing_status === 'ready' || latestExpenseForm?.processing_status === 'ready' ? 'flex h-5 w-5 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-bold text-[11px]' : 'flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-400 font-bold text-[11px]'}>
                                            {latestReceipt?.processing_status === 'ready' || latestExpenseForm?.processing_status === 'ready' ? '✓' : '○'}
                                        </span>
                                        <span className={latestReceipt?.processing_status === 'ready' || latestExpenseForm?.processing_status === 'ready' ? 'text-main font-semibold' : 'text-muted'}>
                                            Expense document verified & extracted
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <span className={request.claimed_amount != null && request.expense_date ? 'flex h-5 w-5 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-bold text-[11px]' : 'flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-400 font-bold text-[11px]'}>
                                            {request.claimed_amount != null && request.expense_date ? '✓' : '○'}
                                        </span>
                                        <span className={request.claimed_amount != null && request.expense_date ? 'text-main font-semibold' : 'text-muted'}>
                                            Expense amount ({request.currency ?? 'INR'} {request.claimed_amount}) and date confirmed
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <span className={request.assigned_reviewer_id && request.assigned_approver_id ? 'flex h-5 w-5 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-bold text-[11px]' : 'flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-400 font-bold text-[11px]'}>
                                            {request.assigned_reviewer_id && request.assigned_approver_id ? '✓' : '○'}
                                        </span>
                                        <span className={request.assigned_reviewer_id && request.assigned_approver_id ? 'text-main font-semibold' : 'text-muted'}>
                                            Active reviewer and approver designated
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Submission Readiness Alert */}
                            {submissionBlockReason ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-950 space-y-1.5 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        Submission requirement pending:
                                    </p>
                                    <p className="text-slate-700 font-medium pl-6">{submissionBlockReason}</p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-950 space-y-1.5 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-teal-900">
                                        <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                                        All requirements met. Ready to submit for review.
                                    </p>
                                    <p className="text-slate-700 leading-relaxed font-medium pl-6">
                                        When you select Submit Claim, your claim is sent to your assigned reviewer ({request.assigned_reviewer?.display_name}). You can track its progress through human review and final approval.
                                    </p>
                                </div>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => setWizardStep(3)}
                                >
                                    ← Back: Verification
                                </button>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    disabled={busy || Boolean(submissionBlockReason)}
                                    onClick={submitDraft}
                                >
                                    {busy ? (
                                        'Submitting claim…'
                                    ) : (
                                        <>
                                            <Send className="h-4 w-4" />
                                            Submit claim for review
                                        </>
                                    )}
                                </button>
                            </div>
                        </section>
                    )}
                    {/* Expandable Technical Audit Drawer */}
                    <div className="text-center pt-2">
                        <button
                            type="button"
                            className="text-xs text-muted hover:text-main underline font-medium"
                            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                        >
                            {showTechnicalDetails ? 'Hide technical audit trail' : 'Show technical audit trail and raw checks'}
                        </button>
                    </div>

                    {showTechnicalDetails && (
                        <div className="space-y-4 pt-2">
                            <div className="card p-5">
                                <h4 className="text-xs font-bold text-main mb-3">Automated Verification Checks</h4>
                                <div className="space-y-2 text-xs">
                                    {checks.map((c) => (
                                        <div key={c.id} className="p-3 border border-surface-border rounded-xl bg-slate-50/50">
                                            <p className="font-bold text-main">{c.check_type}: {c.result}</p>
                                            <p className="text-muted mt-0.5">{c.explanation}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Admin Perspective Switcher */}
                    {user?.role === 'admin' && (
                        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl border border-indigo-200 bg-indigo-50/70 text-xs shadow-xs">
                            <span className="font-bold text-indigo-950">
                                🛡️ Admin Inspection Perspective:
                            </span>
                            <div className="inline-flex rounded-xl bg-white p-1 shadow-xs border border-indigo-200">
                                <button
                                    type="button"
                                    onClick={() => setAdminRoleView('submitter')}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${(adminRoleView || 'submitter') === 'submitter' ? 'bg-[#0F9D8A] text-white shadow-xs' : 'text-slate-600 hover:text-main'}`}
                                >
                                    Submitter View
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setAdminRoleView('reviewer')}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${adminRoleView === 'reviewer' ? 'bg-[#4F46E5] text-white shadow-xs' : 'text-slate-600 hover:text-main'}`}
                                >
                                    Reviewer View
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setAdminRoleView('approver')}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${adminRoleView === 'approver' ? 'bg-[#8B5CF6] text-white shadow-xs' : 'text-slate-600 hover:text-main'}`}
                                >
                                    Approver View
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Role-Dedicated Views */}
                    {(adminRoleView ? adminRoleView === 'reviewer' : isReviewer) ? (
                        <ReviewerClaimView
                            request={request}
                            documents={documents}
                            checks={checks}
                            extractions={extractions}
                            corrections={corrections}
                            history={history}
                            busy={busy}
                            previewUrl={previewUrl}
                            selectedDocId={selectedDocId}
                            onSelectDoc={(docId) => setSelectedDocId(docId)}
                            onResolveCheck={(checkId, resolution, reason) => resolveCheck(checkId, resolution, reason)}
                            onCorrectField={(docId, fieldName, correctedVal, originalVal, reason) =>
                                correctField(docId, fieldName, correctedVal, originalVal, reason)
                            }
                            onRequestCorrection={(comment) => requestCorrection(comment)}
                            onCompleteReview={(comment) => completeReview(comment)}
                            formatDate={formatExpenseDate}
                            formatAmount={formatReceiptAmount}
                            onOpenGraph={() => setActiveView('graph')}
                            onOpenReplay={() => setActiveView('replay')}
                        />
                    ) : (adminRoleView ? adminRoleView === 'approver' : isApprover) ? (
                        <ApproverClaimView
                            request={request}
                            documents={documents}
                            checks={checks}
                            corrections={corrections}
                            history={history}
                            busy={busy}
                            previewUrl={previewUrl}
                            selectedDocId={selectedDocId}
                            onSelectDoc={(docId) => setSelectedDocId(docId)}
                            onApproveOrReject={(decision, comment) => approveOrReject(decision, comment)}
                            formatDate={formatExpenseDate}
                            formatAmount={formatReceiptAmount}
                            onOpenGraph={() => setActiveView('graph')}
                            onOpenReplay={() => setActiveView('replay')}
                        />
                    ) : (
                        <SubmitterClaimView
                            request={request}
                            documents={documents}
                            extractions={extractions}
                            corrections={corrections}
                            history={history}
                            busy={busy}
                            onUploadReplacement={(file, type) => uploadReplacement(file, type)}
                            uploadProgress={uploadProgress}
                            uploadMessage={uploadMessage}
                            onRetryDocument={(docId) => retryDocument(docId)}
                            previewUrl={previewUrl}
                            selectedDocId={selectedDocId}
                            onSelectDoc={(docId) => setSelectedDocId(docId)}
                            formatDate={formatExpenseDate}
                            formatAmount={formatReceiptAmount}
                        />
                    )}
                </div>
            )}
        </div>
    );
}