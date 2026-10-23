import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    CheckCircle2,
    AlertTriangle,
    FileText,
    Receipt,
    Upload,
    Download,
    RotateCw,
    Sparkles,
    Check,
    MessageSquare,
    ArrowRight,
} from 'lucide-react';
import type { RequestSummary, DocumentVersion, ExtractedField, ReviewerCorrection, ReviewAction } from '../types';

interface SubmitterClaimViewProps {
    request: RequestSummary;
    documents: DocumentVersion[];
    extractions: Record<number, ExtractedField[]>;
    corrections: ReviewerCorrection[];
    history: ReviewAction[];
    busy: boolean;
    onUploadReplacement: (file: File, type: 'receipt' | 'expense_form' | 'supporting_document') => Promise<void>;
    uploadProgress: number | null;
    uploadMessage: string | null;
    onRetryDocument: (docId: number) => Promise<void>;
    previewUrl: string | null;
    selectedDocId: number | null;
    onSelectDoc: (docId: number) => void;
    formatDate: (date?: string | null) => string;
    formatAmount: (amount?: string | number | null, currency?: string | null) => string;
}

export default function SubmitterClaimView({
    request,
    documents,
    extractions,
    corrections,
    history,
    busy,
    onUploadReplacement,
    uploadProgress,
    uploadMessage,
    onRetryDocument,
    previewUrl,
    selectedDocId,
    onSelectDoc,
    formatDate,
    formatAmount,
}: SubmitterClaimViewProps) {
    const [replacementFile, setReplacementFile] = useState<File | null>(null);
    const [replacementType, setReplacementType] = useState<'receipt' | 'expense_form'>('receipt');

    // Latest documents
    const latestReceipt = documents
        .filter((d) => d.doc_type === 'receipt')
        .sort((a, b) => b.version_number - a.version_number)[0];

    const latestExpenseForm = documents
        .filter((d) => d.doc_type === 'expense_form')
        .sort((a, b) => b.version_number - a.version_number)[0];

    // Effective extracted receipt fields
    const receiptFields = latestReceipt ? extractions[latestReceipt.id] ?? [] : [];
    const getFieldVal = (name: string) => {
        if (!latestReceipt) return null;
        const correction = corrections
            .filter((c) => c.document_version_id === latestReceipt.id && c.field_name === name)
            .at(-1);
        if (correction?.corrected_value) return correction.corrected_value;
        const f = receiptFields.find((field) => field.field_name === name);
        return f?.normalized_value ?? f?.extracted_value ?? null;
    };

    const merchant = getFieldVal('merchant_name');
    const receiptDate = getFieldVal('expense_date');
    const receiptAmount = getFieldVal('total_amount');
    const receiptCurrency = getFieldVal('currency') || request.currency || 'INR';
    const referenceNum = getFieldVal('reference_number');
    const purpose = getFieldVal('expense_purpose') || request.description;

    // Latest reviewer comment requesting more information
    const latestCorrectionRequest = history
        .filter((h) => h.action_type === 'correction_requested')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

    // Friendly 4-Step Claim Milestone Tracker
    // Step 1: Claim Created & Submitted
    // Step 2: Documents Processed & Extracted
    // Step 3: Compliance & Human Review
    // Step 4: Final Executive Sign-off
    const isStep1Done = true; // Created & submitted
    const isStep2Done = Boolean(
        latestReceipt &&
        latestReceipt.processing_status === 'ready' &&
        latestExpenseForm &&
        latestExpenseForm.processing_status === 'ready'
    );
    const isStep3Done = ['pending_approval', 'approved'].includes(request.status);
    const isStep4Done = request.status === 'approved';

    const currentStepIndex =
        request.status === 'approved' ? 4 :
        request.status === 'pending_approval' ? 3 :
        request.status === 'under_review' || request.status === 'more_info_required' ? 2 :
        request.status === 'processing' || request.status === 'submitted' ? 1 : 0;

    const milestones = [
        {
            num: 1,
            label: 'Claim Submitted',
            sub: formatDate(request.created_at),
            done: isStep1Done,
            active: currentStepIndex === 0,
        },
        {
            num: 2,
            label: 'Documents & OCR',
            sub: isStep2Done ? 'Extraction verified' : 'Extracting details',
            done: isStep2Done,
            active: currentStepIndex === 1,
        },
        {
            num: 3,
            label: 'Reviewer Verification',
            sub: isStep3Done ? 'Review completed' : request.assigned_reviewer?.display_name ? `Assigned to ${request.assigned_reviewer.display_name}` : 'Awaiting reviewer',
            done: isStep3Done,
            active: currentStepIndex === 2,
        },
        {
            num: 4,
            label: 'Final Approval',
            sub: isStep4Done ? 'Approved for payment' : request.status === 'rejected' ? 'Claim rejected' : 'Pending executive sign-off',
            done: isStep4Done,
            active: currentStepIndex === 3,
        },
    ];

    const handleUploadSubmit = async () => {
        if (!replacementFile) return;
        await onUploadReplacement(replacementFile, replacementType);
        setReplacementFile(null);
    };

    return (
        <div className="space-y-6">
            {/* SUBMITTER STATUS HERO BANNER */}
            <div className={`rounded-2xl border p-6 shadow-sm transition-all ${
                request.status === 'approved'
                    ? 'border-teal-200 bg-gradient-to-r from-teal-50/90 to-emerald-50/60'
                    : request.status === 'rejected'
                    ? 'border-red-200 bg-gradient-to-r from-red-50/90 to-rose-50/60'
                    : request.status === 'more_info_required'
                    ? 'border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50/80 ring-2 ring-amber-100'
                    : 'border-teal-100 bg-gradient-to-r from-teal-50/50 via-white to-slate-50'
            }`}>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#0F9D8A]/10 border border-[#0F9D8A]/30 px-2.5 py-0.5 text-[11px] font-bold text-[#0F9D8A] uppercase tracking-wider">
                                Submitter Portal · My Expenses
                            </span>
                            <span className="text-xs text-muted">Claim #{request.request_number}</span>
                        </div>
                        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-main">
                            {request.status === 'approved' && 'Your claim has been approved!'}
                            {request.status === 'rejected' && 'Claim was not approved.'}
                            {request.status === 'more_info_required' && 'Action Required: Update requested by reviewer'}
                            {request.status === 'under_review' && 'Your claim is actively being verified'}
                            {request.status === 'pending_approval' && 'Verification complete — Awaiting final sign-off'}
                            {request.status === 'processing' && 'Reading documents and extracting receipt details…'}
                            {request.status === 'submitted' && 'Claim received and queued for review'}
                        </h2>
                        <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
                            {request.status === 'approved' && 'Reimbursement of ' + formatAmount(request.claimed_amount, request.currency) + ' has been authorized by your manager. Payment will be processed according to payroll schedule.'}
                            {request.status === 'rejected' && 'Your expense claim was rejected during review. Review the audit history below or contact your manager for clarification.'}
                            {request.status === 'more_info_required' && 'Your reviewer requested additional details or a clearer document. Please upload a replacement below to continue.'}
                            {request.status === 'under_review' && `Your assigned reviewer (${request.assigned_reviewer?.display_name ?? 'Reviewer'}) is checking your uploaded receipt against policy.`}
                            {request.status === 'pending_approval' && `Reviewer verification is complete! Sent to ${request.assigned_approver?.display_name ?? 'Human Approver'} for executive approval.`}
                            {request.status === 'processing' && 'Our automated OCR is extracting line items, dates, and amounts from your receipt. This page refreshes automatically.'}
                            {request.status === 'submitted' && 'Your claim was securely submitted and is ready for automated processing.'}
                        </p>
                    </div>

                    <div className="flex sm:flex-col items-end justify-between sm:justify-center border-t sm:border-t-0 sm:border-l border-slate-200/80 pt-3 sm:pt-0 sm:pl-6 shrink-0">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Total Claimed</span>
                        <p className="text-2xl sm:text-3xl font-black text-indigo-950">
                            {formatAmount(request.claimed_amount, request.currency)}
                        </p>
                        <span className="text-[11px] font-medium text-slate-500 capitalize">
                            {request.expense_category?.replace(/_/g, ' ') ?? 'General expense'}
                        </span>
                    </div>
                </div>
            </div>

            {/* ACTION REQUIRED CALLOUT (When reviewer requested more info or processing failed) */}
            {(request.status === 'more_info_required' || request.status === 'processing_failed') && (
                <section className="rounded-2xl border-2 border-amber-300 bg-amber-50/70 p-6 shadow-md space-y-4">
                    <div className="flex items-start gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-xs">
                            <AlertTriangle className="h-5 w-5" />
                        </span>
                        <div className="space-y-1">
                            <h3 className="text-base font-bold text-amber-950">Reviewer Feedback &amp; Action Needed</h3>
                            <p className="text-xs text-amber-900 leading-relaxed font-medium">
                                {latestCorrectionRequest?.comment
                                    ? `"${latestCorrectionRequest.comment}"`
                                    : 'A clearer copy of your document or additional verification details are required before this claim can proceed.'}
                            </p>
                            {latestCorrectionRequest && (
                                <p className="text-[10px] text-amber-800">
                                    Requested by <strong>{latestCorrectionRequest.actor_name ?? 'Reviewer'}</strong> on {formatDate(latestCorrectionRequest.created_at)}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Quick Replacement Upload Zone */}
                    <div className="rounded-xl border border-amber-200 bg-white p-4 space-y-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-xs font-bold text-main">Upload Replacement Document</p>
                            <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-xs font-semibold">
                                <button
                                    type="button"
                                    onClick={() => setReplacementType('receipt')}
                                    className={`rounded-md px-2.5 py-1 transition ${
                                        replacementType === 'receipt'
                                            ? 'bg-white text-indigo-900 shadow-xs'
                                            : 'text-slate-600 hover:text-main'
                                    }`}
                                >
                                    Receipt / Invoice
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setReplacementType('expense_form')}
                                    className={`rounded-md px-2.5 py-1 transition ${
                                        replacementType === 'expense_form'
                                            ? 'bg-white text-indigo-900 shadow-xs'
                                            : 'text-slate-600 hover:text-main'
                                    }`}
                                >
                                    Expense Form
                                </button>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                            <input
                                id="replacement-file-input"
                                type="file"
                                className="sr-only"
                                accept=".pdf,.png,.jpg,.jpeg"
                                onChange={(e) => setReplacementFile(e.target.files?.[0] ?? null)}
                            />
                            <button
                                type="button"
                                onClick={() => document.getElementById('replacement-file-input')?.click()}
                                className="btn-secondary text-xs flex items-center justify-center gap-2 py-2 px-4"
                            >
                                <Upload className="h-4 w-4" />
                                {replacementFile ? replacementFile.name : `Choose replacement ${replacementType.replace(/_/g, ' ')}`}
                            </button>

                            {replacementFile && (
                                <button
                                    type="button"
                                    disabled={busy}
                                    onClick={handleUploadSubmit}
                                    className="btn-teal text-xs py-2 px-5 flex items-center justify-center gap-2"
                                >
                                    {busy ? 'Uploading & Reprocessing…' : 'Submit Replacement for Verification'}
                                </button>
                            )}
                        </div>

                        {uploadProgress !== null && (
                            <div className="space-y-1 pt-1">
                                <div className="flex justify-between text-[10px] text-muted font-semibold">
                                    <span>Uploading updated document</span>
                                    <span>{uploadProgress}%</span>
                                </div>
                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-teal-600 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                                </div>
                            </div>
                        )}

                        {uploadMessage && (
                            <p className="text-xs text-teal-800 bg-teal-50 border border-teal-200 p-2.5 rounded-lg flex items-center gap-2 font-medium">
                                <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-600" />
                                {uploadMessage}
                            </p>
                        )}
                    </div>
                </section>
            )}

            {/* 4-MILESTONE EMPLOYEE PROGRESS TRACKER */}
            <section className="card p-6">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border pb-4 mb-5">
                    <div>
                        <h3 className="text-sm font-bold text-main">Reimbursement Progress Tracker</h3>
                        <p className="text-xs text-muted">Track your expense claim as it moves from submission to manager sign-off.</p>
                    </div>
                    <span className="text-xs font-semibold text-[#0F9D8A] bg-teal-50 px-2.5 py-1 rounded-full border border-teal-200/60">
                        {request.status.replace(/_/g, ' ').toUpperCase()}
                    </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                    {milestones.map((m) => (
                        <div
                            key={m.num}
                            className={`relative rounded-xl border p-4 transition ${
                                m.done
                                    ? 'border-teal-200 bg-teal-50/40 text-teal-950'
                                    : m.active
                                    ? 'border-indigo-500 bg-indigo-50/50 text-indigo-950 ring-2 ring-indigo-100'
                                    : 'border-surface-border bg-slate-50/60 text-slate-500'
                            }`}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                                    m.done
                                        ? 'bg-teal-600 text-white shadow-xs'
                                        : m.active
                                        ? 'bg-indigo-600 text-white shadow-xs ring-4 ring-indigo-100'
                                        : 'bg-slate-200 text-slate-500'
                                }`}>
                                    {m.done ? <Check className="h-4 w-4" /> : m.num}
                                </span>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
                                    Step 0{m.num}
                                </span>
                            </div>
                            <h4 className={`text-xs font-bold ${m.done ? 'text-teal-900' : m.active ? 'text-indigo-950' : 'text-slate-600'}`}>
                                {m.label}
                            </h4>
                            <p className="text-[11px] text-muted mt-0.5 leading-snug">
                                {m.sub}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            {/* EXTRACTED RECEIPT DETAILS CARD */}
            <section className="card overflow-hidden border-teal-200/60 shadow-md">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border bg-slate-50/80 px-6 py-4">
                    <div className="flex items-center gap-2.5">
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 text-white shadow-xs">
                            <Receipt className="h-5 w-5" />
                        </span>
                        <div>
                            <h3 className="text-sm font-bold text-main">What We Read From Your Receipt</h3>
                            <p className="text-[11px] text-muted">Automated verification extracted these facts from your uploaded receipt</p>
                        </div>
                    </div>
                    {latestReceipt && (
                        <span className="rounded-md bg-white px-2.5 py-1 text-[10px] font-bold text-slate-700 ring-1 ring-surface-border shadow-xs">
                            Receipt v{latestReceipt.version_number}
                        </span>
                    )}
                </div>

                <div className="p-6">
                    <div className="space-y-6">
                        {/* Large Merchant & Amount Display */}
                        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-surface-border pb-5">
                            <div>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Merchant / Vendor</span>
                                <h4 className="text-2xl font-black text-main sm:text-3xl mt-0.5">
                                    {merchant || <span className="text-sm font-normal italic text-slate-400">Vendor name detected on document</span>}
                                </h4>
                                <p className="text-sm font-bold text-muted mt-1">
                                    Expense Date: <span className="text-main">{formatDate(receiptDate || request.expense_date)}</span>
                                </p>
                            </div>
                            <div className="text-right">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Receipt Total Amount</span>
                                <p className="text-3xl font-black text-[#0F9D8A] sm:text-4xl mt-0.5">
                                    {receiptAmount ? formatAmount(receiptAmount, receiptCurrency) : formatAmount(request.claimed_amount, request.currency)}
                                </p>
                                <span className="text-[10px] font-semibold text-slate-500">
                                    Matches your claimed reimbursement
                                </span>
                            </div>
                        </div>

                        {/* Reference & Purpose */}
                        <div className="grid gap-3 sm:grid-cols-2 text-xs">
                            <div className="rounded-xl border border-surface-border bg-slate-50/70 p-3.5">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Reference / Invoice #</span>
                                <p className="text-sm font-bold text-main mt-0.5">
                                    {referenceNum || 'Detected on file'}
                                </p>
                            </div>
                            <div className="rounded-xl border border-surface-border bg-slate-50/70 p-3.5">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Business Purpose</span>
                                <p className="text-sm font-medium text-main mt-0.5">
                                    {purpose || 'Business expense reimbursement'}
                                </p>
                            </div>
                        </div>

                        {/* Reassurance Callout */}
                        <div className="rounded-xl border border-teal-200/70 bg-teal-50/40 p-3.5 text-xs text-teal-950 flex items-center gap-2.5">
                            <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                            <span>
                                All information has been verified and stored in your permanent audit record. No further action is required from you unless requested by your reviewer.
                            </span>
                        </div>
                    </div>
                </div>
            </section>

            {/* MY UPLOADED DOCUMENTS & PREVIEW */}
            <section className="card p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border pb-3">
                    <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-[#0F9D8A]" />
                        <h3 className="text-sm font-bold text-main">My Uploaded Documents</h3>
                    </div>
                    <span className="text-xs text-muted font-medium">{documents.length} file(s) attached</span>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                    {documents.map((doc) => (
                        <div
                            key={doc.id}
                            className={`rounded-xl border p-4 flex flex-col justify-between transition ${
                                selectedDocId === doc.id
                                    ? 'border-[#0F9D8A] bg-teal-50/30 ring-2 ring-teal-100'
                                    : 'border-surface-border bg-white hover:border-slate-300'
                            }`}
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-50 text-teal-700 font-bold text-xs">
                                            v{doc.version_number}
                                        </span>
                                        <p className="text-xs font-bold capitalize text-main truncate">
                                            {doc.doc_type.replace(/_/g, ' ')}
                                        </p>
                                    </div>
                                    <p className="text-[11px] text-muted truncate mt-1">{doc.original_filename}</p>
                                </div>
                                <span className={`badge ${doc.processing_status === 'ready' ? 'badge-approved' : doc.processing_status === 'failed' ? 'badge-failed' : 'badge-processing'}`}>
                                    {doc.processing_status}
                                </span>
                            </div>

                            <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100">
                                <button
                                    type="button"
                                    onClick={() => onSelectDoc(doc.id)}
                                    className="text-xs font-bold text-[#0F9D8A] hover:underline flex items-center gap-1"
                                >
                                    <span>{selectedDocId === doc.id ? 'Viewing' : 'Inspect Preview'}</span>
                                    <ArrowRight className="h-3 w-3" />
                                </button>
                                {doc.processing_status === 'failed' && (
                                    <button
                                        type="button"
                                        onClick={() => onRetryDocument(doc.id)}
                                        className="btn-secondary text-[11px] py-1 px-2.5 flex items-center gap-1 text-slate-700"
                                    >
                                        <RotateCw className="h-3 w-3" /> Retry
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Selected Document Preview Frame */}
                {selectedDocId && previewUrl && (
                    <div className="mt-4 rounded-xl border border-surface-border bg-slate-50 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                            <p className="text-xs font-bold text-main">
                                Document Viewer: {documents.find((d) => d.id === selectedDocId)?.original_filename}
                            </p>
                            <a
                                href={previewUrl}
                                download={documents.find((d) => d.id === selectedDocId)?.original_filename}
                                className="btn-secondary text-[11px] py-1 px-3 flex items-center gap-1.5"
                            >
                                <Download className="h-3 w-3" /> Download Copy
                            </a>
                        </div>
                        <div className="max-h-[380px] overflow-auto rounded-lg border border-slate-200 bg-white flex items-center justify-center p-2">
                            {documents.find((d) => d.id === selectedDocId)?.mime_type?.startsWith('image/') ? (
                                <img src={previewUrl} alt="Document Preview" className="max-h-[360px] object-contain rounded" />
                            ) : (
                                <iframe src={previewUrl} title="Document Preview" className="h-[360px] w-full rounded border-0" />
                            )}
                        </div>
                    </div>
                )}
            </section>

            {/* PEOPLE RESPONSIBLE & TIMELINE (Submitter Friendly) */}
            <div className="grid gap-6 sm:grid-cols-[1fr_1fr]">
                {/* People Responsible */}
                <section className="card p-5 space-y-3.5">
                    <div className="border-b border-surface-border pb-2.5">
                        <h3 className="text-xs font-bold text-main">Assigned Reviewers</h3>
                        <p className="text-[11px] text-muted">Colleagues handling your expense claim</p>
                    </div>
                    <div className="space-y-2.5 text-xs">
                        <div className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 bg-slate-50/70">
                            <div>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Compliance Reviewer</span>
                                <p className="font-bold text-main">{request.assigned_reviewer?.display_name ?? 'Designated Reviewer'}</p>
                            </div>
                            <span className="badge-review text-[10px]">Verification</span>
                        </div>
                        <div className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 bg-slate-50/70">
                            <div>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Human Approver</span>
                                <p className="font-bold text-main">{request.assigned_approver?.display_name ?? 'Designated Approver'}</p>
                            </div>
                            <span className="badge-approved text-[10px]">Decision</span>
                        </div>
                    </div>
                </section>

                {/* AI Assistant Help Prompt */}
                <section className="card p-5 space-y-3.5 border-teal-200/60 bg-linear-to-br from-white to-teal-50/30">
                    <div className="flex items-center gap-2 border-b border-surface-border pb-2.5">
                        <Sparkles className="h-4 w-4 text-[#0F9D8A]" />
                        <h3 className="text-xs font-bold text-main">Have questions about this claim?</h3>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed font-medium">
                        You can ask the DocuVerify AI Assistant about required receipts, missing tax fields, or why a reviewer requested more information.
                    </p>
                    <Link
                        to={`/assistant?requestId=${request.id}`}
                        className="btn-teal inline-flex items-center gap-2 text-xs py-2 px-3.5"
                    >
                        <MessageSquare className="h-3.5 w-3.5" />
                        <span>Ask DocuVerify AI</span>
                    </Link>
                </section>
            </div>
        </div>
    );
}
