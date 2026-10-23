import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    ShieldCheck,
    CheckCircle2,
    XCircle,
    Receipt,
    Eye,
    EyeOff,
    History,
    Network,
    AlertTriangle,
    UserCheck,
    Sparkles,
    Clock,
} from 'lucide-react';
import type {
    RequestSummary,
    DocumentVersion,
    VerificationCheck,
    ReviewerCorrection,
    ReviewAction,
} from '../types';

interface ApproverClaimViewProps {
    request: RequestSummary;
    documents: DocumentVersion[];
    checks: VerificationCheck[];
    corrections: ReviewerCorrection[];
    history: ReviewAction[];
    busy: boolean;
    previewUrl: string | null;
    selectedDocId: number | null;
    onSelectDoc: (docId: number) => void;
    onApproveOrReject: (decision: 'approve' | 'reject', comment: string) => Promise<void>;
    formatDate: (date?: string | null) => string;
    formatAmount: (amount?: string | number | null, currency?: string | null) => string;
    onOpenGraph: () => void;
    onOpenReplay: () => void;
}

export default function ApproverClaimView({
    request,
    documents,
    checks,
    corrections,
    history,
    busy,
    previewUrl,
    selectedDocId,
    onSelectDoc,
    onApproveOrReject,
    formatDate,
    formatAmount,
    onOpenGraph,
    onOpenReplay,
}: ApproverClaimViewProps) {
    const [decisionComment, setDecisionComment] = useState('');
    const [confirmModal, setConfirmModal] = useState<'approve' | 'reject' | null>(null);
    const [showDocuments, setShowDocuments] = useState(false);

    // Reviewer's completion note from history
    const reviewCompletedAction = history
        .filter((h) => h.action_type === 'review_completed')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

    // Final approval / rejection action from history
    const finalDecisionAction = history
        .filter((h) => h.action_type === 'approved' || h.action_type === 'rejected')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

    // Current checks and flags
    const currentChecks = checks.filter((c) => (c as { is_current?: boolean }).is_current !== false);
    const openFlagsCount = currentChecks.filter((c) => c.result === 'flag' && c.resolution_status === 'open').length;
    const passedChecksCount = currentChecks.filter((c) => c.result === 'pass').length;
    const resolvedFlagsCount = currentChecks.filter(
        (c) => c.result === 'flag' && (c.resolution_status === 'resolved' || c.resolution_status === 'dismissed')
    ).length;

    const handleExecuteDecision = async (decision: 'approve' | 'reject') => {
        if (!decisionComment.trim()) return;
        await onApproveOrReject(decision, decisionComment.trim());
        setConfirmModal(null);
    };

    return (
        <div className="space-y-6">
            {/* APPROVER EXECUTIVE HERO BANNER:
                Clear visual summary of Claim Amount, Review Result, Status, Authority */}
            <div className="rounded-2xl border border-violet-200/80 bg-gradient-to-r from-[#14213D] via-[#2E1065] to-[#4C1D95] p-6 text-white shadow-md">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-500/25 border border-violet-400/30 px-3 py-0.5 text-[11px] font-bold text-violet-300 uppercase tracking-wider">
                                <ShieldCheck className="h-3.5 w-3.5" />
                                Approver Decision Center
                            </span>
                            <span className="text-xs text-violet-200">Financial Authorization</span>
                        </div>
                        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                            Claim #{request.request_number} · {request.title}
                        </h1>
                        <p className="text-xs text-violet-200/80">
                            Claimant: <strong className="text-white">{request.submitter?.display_name ?? request.submitter_name}</strong> · Category: <span className="capitalize">{request.expense_category?.replace(/_/g, ' ')}</span> · Submitted: {formatDate(request.created_at)}
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                        <Link
                            to={`/assistant?requestId=${request.id}`}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600/90 hover:bg-violet-600 px-3.5 py-2 text-xs font-bold text-white transition shadow-xs"
                            title="Open AI Assistant for executive summary"
                        >
                            <Sparkles className="h-4 w-4 text-violet-200" />
                            <span>Ask AI Assistant</span>
                        </Link>
                        <button
                            type="button"
                            onClick={onOpenGraph}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-white hover:bg-white/20 transition shadow-xs"
                        >
                            <Network className="h-4 w-4 text-violet-300" />
                            <span>Evidence Impact Graph</span>
                        </button>
                        <button
                            type="button"
                            onClick={onOpenReplay}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-white hover:bg-white/20 transition shadow-xs"
                        >
                            <History className="h-4 w-4 text-violet-300" />
                            <span>Decision Replay</span>
                        </button>
                    </div>
                </div>

                {/* KPI Summary Cards */}
                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-white/10 pt-4 text-xs">
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-violet-300 font-semibold">Claim Amount</span>
                        <p className="text-2xl sm:text-3xl font-black text-white mt-0.5">
                            {formatAmount(request.claimed_amount, request.currency)}
                        </p>
                    </div>
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-violet-300 font-semibold">Review Result</span>
                        {reviewCompletedAction ? (
                            <p className="text-lg font-bold text-teal-300 mt-0.5 flex items-center gap-1">
                                <CheckCircle2 className="h-4 w-4 text-teal-400 shrink-0" />
                                <span>Verified by {request.assigned_reviewer?.display_name ?? 'Reviewer'}</span>
                            </p>
                        ) : (
                            <p className="text-lg font-bold text-amber-300 mt-0.5 flex items-center gap-1">
                                <Clock className="h-4 w-4 text-amber-400 shrink-0" />
                                <span>Under Review ({request.assigned_reviewer?.display_name ?? 'Riley Reviewer'})</span>
                            </p>
                        )}
                    </div>
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-violet-300 font-semibold">Risk Classification</span>
                        <p className={`text-lg font-bold mt-0.5 flex items-center gap-1 ${openFlagsCount === 0 ? 'text-teal-300' : 'text-amber-300'}`}>
                            {openFlagsCount === 0 ? (
                                <>
                                    <ShieldCheck className="h-4 w-4 text-teal-400 shrink-0" /> Low Risk (0 open flags)
                                </>
                            ) : (
                                <>
                                    <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" /> {openFlagsCount} open issue(s)
                                </>
                            )}
                        </p>
                    </div>
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-violet-300 font-semibold">Current Status</span>
                        <p className="text-lg font-bold text-violet-200 mt-0.5 capitalize">
                            {request.status.replace(/_/g, ' ')}
                        </p>
                    </div>
                </div>
            </div>

            {/* SINGLE CONSOLIDATED EXECUTIVE FINDINGS & REVIEW SUMMARY */}
            <section className="card p-6 border-violet-200 shadow-md space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border pb-3">
                    <div className="flex items-center gap-2.5">
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#7656D6] text-white shadow-xs">
                            <UserCheck className="h-5 w-5" />
                        </span>
                        <div>
                            <h2 className="text-base font-bold text-slate-900">Review Findings &amp; Verification Evidence</h2>
                            <p className="text-xs text-muted">Documented audit results from {request.assigned_reviewer?.display_name ?? 'Assigned Reviewer'}</p>
                        </div>
                    </div>
                    {reviewCompletedAction && (
                        <span className="text-xs text-muted font-medium">
                            Reviewed on {formatDate(reviewCompletedAction.created_at)}
                        </span>
                    )}
                </div>

                {/* Reviewer's Official Finding Statement */}
                <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7656D6]">
                        Reviewer's Note
                    </span>
                    <p className="text-xs text-slate-900 leading-relaxed font-semibold">
                        {reviewCompletedAction?.comment
                            ? `"${reviewCompletedAction.comment}"`
                            : request.status === 'under_review'
                            ? `Verification is currently in progress. ${request.assigned_reviewer?.display_name ?? 'Reviewer'} has not yet submitted the completed review.`
                            : 'No reviewer note recorded.'}
                    </p>
                </div>

                {/* Important Verification Findings */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#0F9D8A] block">
                            Matched Checks
                        </span>
                        <p className="text-slate-800 font-medium">
                            {passedChecksCount} automated check(s) passed successfully.
                        </p>
                    </div>
                    <div className="rounded-xl border border-violet-200 bg-violet-50/40 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#7656D6] block">
                            Resolved Discrepancies
                        </span>
                        <p className="text-slate-800 font-medium">
                            {resolvedFlagsCount} flag(s) resolved with documented rationale.
                        </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 block">
                            Evidence Corrections
                        </span>
                        <p className="text-slate-800 font-medium">
                            {corrections.length > 0 ? `${corrections.length} correction(s) recorded.` : 'No manual field corrections needed.'}
                        </p>
                    </div>
                </div>

                {/* Recorded Corrections (if any exist) */}
                {corrections.length > 0 && (
                    <div className="space-y-2 pt-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
                            Recorded Corrections Detail ({corrections.length})
                        </span>
                        <div className="space-y-2 text-xs">
                            {corrections.map((corr) => (
                                <div
                                    key={corr.id}
                                    className="rounded-xl border border-slate-200 bg-slate-50/80 p-3 flex flex-wrap items-center justify-between gap-2"
                                >
                                    <div>
                                        <strong className="text-slate-900 capitalize">{corr.field_name.replace(/_/g, ' ')}: </strong>
                                        <span className="text-slate-400 line-through mr-2">{corr.original_extracted_value ?? '∅'}</span>
                                        <span className="font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                                            {corr.corrected_value}
                                        </span>
                                        <p className="text-[10px] text-muted mt-1">Audit reason: "{corr.reason}"</p>
                                    </div>
                                    <span className="text-[10px] font-semibold text-slate-500">
                                        Corrected by {corr.reviewer_name}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </section>

            {/* VERIFICATION CHECKS & AUDIT FINDINGS DRILLDOWN (Requirement 10: Approver sees unresolved issues) */}
            <section className="card p-6 border-slate-200 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-surface-border pb-3">
                    <div className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-[#7656D6]" />
                        <h2 className="text-sm font-bold text-slate-900">
                            Automated Verification Checks &amp; Discrepancies ({currentChecks.length})
                        </h2>
                    </div>
                    <span className="text-[11px] font-semibold text-muted">
                        {passedChecksCount} passed · {openFlagsCount} open issue(s) · {resolvedFlagsCount} resolved
                    </span>
                </div>

                {openFlagsCount > 0 && (
                    <div className="rounded-xl border border-amber-300 bg-amber-50/90 p-4 text-xs text-amber-950 flex items-start gap-3 shadow-xs">
                        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                            <strong className="font-bold">Unresolved Discrepancy Detected</strong>
                            <p className="text-amber-900 leading-relaxed font-medium">
                                This claim contains {openFlagsCount} open issue(s) that have not been resolved.
                                As an executive approver, you are required to inspect the issues below before making a financial decision.
                                Claims with open issues cannot be approved until addressed, though you may reject the claim.
                            </p>
                        </div>
                    </div>
                )}

                <div className="space-y-2.5">
                    {currentChecks.map((c) => {
                        const isOpenFlag = c.result === 'flag' && c.resolution_status === 'open';
                        const isResolved = c.resolution_status === 'resolved' || c.resolution_status === 'dismissed';

                        return (
                            <div
                                key={c.id}
                                className={`rounded-xl border p-4 text-xs transition space-y-2 ${
                                    isOpenFlag
                                        ? 'border-amber-300 bg-amber-50/40 shadow-xs'
                                        : isResolved
                                        ? 'border-violet-200 bg-violet-50/30'
                                        : 'border-slate-200 bg-white'
                                }`}
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2.5">
                                        <span
                                            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-white text-xs ${
                                                isOpenFlag ? 'bg-amber-500' : isResolved ? 'bg-violet-600' : 'bg-teal-600'
                                            }`}
                                        >
                                            {isOpenFlag ? (
                                                <AlertTriangle className="h-3.5 w-3.5" />
                                            ) : isResolved ? (
                                                <ShieldCheck className="h-3.5 w-3.5" />
                                            ) : (
                                                <CheckCircle2 className="h-3.5 w-3.5" />
                                            )}
                                        </span>
                                        <span className="font-bold text-slate-900 capitalize">
                                            {c.rule_name.replace(/_/g, ' ')}
                                        </span>
                                    </div>
                                    <span
                                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold border uppercase tracking-wider ${
                                            isOpenFlag
                                                ? 'bg-amber-100 text-amber-900 border-amber-300'
                                                : isResolved
                                                ? 'bg-violet-100 text-violet-900 border-violet-300'
                                                : 'bg-teal-50 text-teal-800 border-teal-200'
                                        }`}
                                    >
                                        {isOpenFlag ? 'Open Issue' : isResolved ? 'Resolved by Reviewer' : 'Matched & Verified'}
                                    </span>
                                </div>
                                <p className="text-slate-700 leading-relaxed font-medium pl-8">
                                    {c.explanation}
                                </p>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* SUPPORTING DOCUMENTS DRILLDOWN */}
            <section className="card p-5 space-y-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Receipt className="h-4 w-4 text-[#7656D6]" />
                        <h2 className="text-sm font-bold text-slate-900">Supporting Documents ({documents.length})</h2>
                    </div>
                    <button
                        type="button"
                        onClick={() => setShowDocuments(!showDocuments)}
                        className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
                    >
                        {showDocuments ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        <span>{showDocuments ? 'Hide Documents' : 'Inspect Documents'}</span>
                    </button>
                </div>

                {showDocuments && (
                    <div className="pt-3 border-t border-surface-border space-y-4">
                        <div className="flex gap-2">
                            {documents.map((doc) => (
                                <button
                                    key={doc.id}
                                    type="button"
                                    onClick={() => onSelectDoc(doc.id)}
                                    className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                                        selectedDocId === doc.id
                                            ? 'bg-[#7656D6] text-white shadow-xs'
                                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                                    }`}
                                >
                                    {doc.doc_type === 'receipt' ? 'Receipt' : 'Expense Form'} v{doc.version_number}
                                </button>
                            ))}
                        </div>

                        {selectedDocId && previewUrl && (
                            <div className="rounded-xl border border-slate-200 bg-slate-900 p-2 flex items-center justify-center max-h-[380px] overflow-auto">
                                {documents.find((d) => d.id === selectedDocId)?.mime_type?.startsWith('image/') ? (
                                    <img src={previewUrl} alt="Document" className="max-h-[360px] object-contain rounded" />
                                ) : (
                                    <iframe src={previewUrl} title="Document" className="h-[360px] w-full rounded bg-white" />
                                )}
                            </div>
                        )}
                    </div>
                )}
            </section>

            {/* EXECUTIVE DECISION SIGN-OFF STATION:
                Handles pending_approval, under_review, approved, rejected without contradictory text */}
            {request.status === 'pending_approval' ? (
                <section className="card p-6 border-2 border-violet-300 bg-gradient-to-b from-white to-violet-50/30 shadow-xl space-y-5">
                    <div className="border-b border-surface-border pb-3">
                        <h2 className="text-base font-bold text-slate-900">Executive Authorization</h2>
                        <p className="text-xs text-muted">
                            As the designated approver ({request.assigned_approver?.display_name}), your decision authorizes corporate funds disbursement.
                        </p>
                    </div>

                    <div className="space-y-4">
                        {openFlagsCount > 0 && (
                            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950 flex items-start gap-3 shadow-xs">
                                <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                                <div className="space-y-1">
                                    <strong className="font-bold">Approval Blocked by Open Discrepancy:</strong>
                                    <p className="text-amber-900 font-medium">
                                        This claim cannot be approved while {openFlagsCount} verification issue(s) remain open.
                                        You may reject the claim with a documented rationale, or return it to the reviewer for resolution.
                                    </p>
                                </div>
                            </div>
                        )}

                        <div>
                            <label className="block text-xs font-bold text-slate-900 mb-1.5">
                                Executive Sign-Off Note / Decision Reason <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                id="decision-comment"
                                className="form-input text-xs min-h-[90px]"
                                placeholder="Record your decision rationale (e.g. 'Approved for reimbursement based on verified receipts and corporate expense policy')."
                                value={decisionComment}
                                onChange={(e) => setDecisionComment(e.target.value)}
                            />
                            <span className="text-[10px] text-muted">This sign-off note is permanently preserved in the immutable audit trail.</span>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 pt-2">
                            <button
                                type="button"
                                disabled={busy || openFlagsCount > 0 || !decisionComment.trim()}
                                onClick={() => setConfirmModal('approve')}
                                className="btn-primary bg-[#7656D6] hover:bg-violet-800 text-xs py-2.5 px-6 flex items-center gap-2 shadow-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                                title={openFlagsCount > 0 ? 'Cannot approve while open issues remain unresolved' : undefined}
                            >
                                <CheckCircle2 className="h-4 w-4" />
                                <span>Authorize &amp; Approve Claim</span>
                            </button>

                            <button
                                type="button"
                                disabled={busy || !decisionComment.trim()}
                                onClick={() => setConfirmModal('reject')}
                                className="btn-secondary text-red-700 border-red-200 hover:bg-red-50 text-xs py-2.5 px-6 flex items-center gap-2 font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <XCircle className="h-4 w-4 text-red-600" />
                                <span>Reject Claim</span>
                            </button>
                        </div>
                    </div>
                </section>
            ) : request.status === 'under_review' ? (
                <section className="card p-6 border border-slate-200 bg-slate-50/80 shadow-sm space-y-3">
                    <div className="flex items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                            <Clock className="h-5 w-5" />
                        </span>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Claim Currently Under Review</h3>
                            <p className="text-xs text-muted">
                                Assigned Reviewer: <strong className="text-slate-800">{request.assigned_reviewer?.display_name ?? 'Riley Reviewer'}</strong>
                            </p>
                        </div>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed font-medium">
                        This claim is currently undergoing verification by {request.assigned_reviewer?.display_name ?? 'the assigned reviewer'}.
                        Executive authorization actions (Approve &amp; Reject) will become active in this Decision Center once the reviewer completes their verification and submits the claim for approval.
                    </p>
                </section>
            ) : request.status === 'approved' ? (
                <div className="rounded-2xl border-2 border-teal-300 bg-teal-50/70 p-6 shadow-md flex items-center gap-4">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#0F9D8A] text-white shadow-xs">
                        <CheckCircle2 className="h-6 w-6" />
                    </span>
                    <div className="space-y-1">
                        <h3 className="text-base font-bold text-teal-950">Claim Officially Approved</h3>
                        <p className="text-xs text-teal-900 leading-relaxed font-medium">
                            {finalDecisionAction?.comment
                                ? `"${finalDecisionAction.comment}"`
                                : `Authorized for reimbursement of ${formatAmount(request.claimed_amount, request.currency)} by ${request.assigned_approver?.display_name}.`}
                        </p>
                        {finalDecisionAction && (
                            <p className="text-[10px] text-teal-800 font-semibold">
                                Certified by {finalDecisionAction.actor_name} on {formatDate(finalDecisionAction.created_at)}
                            </p>
                        )}
                    </div>
                </div>
            ) : request.status === 'rejected' ? (
                <div className="rounded-2xl border-2 border-red-300 bg-red-50/70 p-6 shadow-md flex items-center gap-4">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#DC2626] text-white shadow-xs">
                        <XCircle className="h-6 w-6" />
                    </span>
                    <div className="space-y-1">
                        <h3 className="text-base font-bold text-red-950">Claim Rejected</h3>
                        <p className="text-xs text-red-900 leading-relaxed font-medium">
                            {finalDecisionAction?.comment ? `Recorded Reason: "${finalDecisionAction.comment}"` : 'This claim was rejected by executive authority with documented rationale.'}
                        </p>
                        {finalDecisionAction && (
                            <p className="text-[10px] text-red-800 font-semibold">
                                Recorded by {finalDecisionAction.actor_name} on {formatDate(finalDecisionAction.created_at)}
                            </p>
                        )}
                    </div>
                </div>
            ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700 flex items-center justify-between">
                    <span>
                        Claim is currently <strong>{request.status.replace(/_/g, ' ')}</strong>. Awaiting reviewer verification before executive sign-off can occur.
                    </span>
                    <span className="text-muted font-medium">Reviewer: {request.assigned_reviewer?.display_name}</span>
                </div>
            )}

            {/* CONFIRMATION MODAL */}
            {confirmModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
                    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
                        <div className="flex items-center gap-3">
                            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white ${
                                confirmModal === 'approve' ? 'bg-[#7656D6]' : 'bg-[#DC2626]'
                            }`}>
                                {confirmModal === 'approve' ? <ShieldCheck className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
                            </span>
                            <div>
                                <h3 className="text-base font-bold text-slate-900">
                                    {confirmModal === 'approve' ? 'Confirm Reimbursement Approval' : 'Confirm Claim Rejection'}
                                </h3>
                                <p className="text-xs text-muted">
                                    Claim #{request.request_number}
                                </p>
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs space-y-2">
                            <div className="flex justify-between">
                                <span className="text-muted">Claimant:</span>
                                <strong className="text-slate-900">{request.submitter?.display_name ?? request.submitter_name}</strong>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted">Amount:</span>
                                <strong className="text-violet-900 text-sm">{formatAmount(request.claimed_amount, request.currency)}</strong>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted">Recorded Rationale:</span>
                                <span className="text-slate-900 italic truncate max-w-[200px]">"{decisionComment}"</span>
                            </div>
                        </div>

                        <p className="text-xs text-slate-600 leading-relaxed font-medium">
                            {confirmModal === 'approve'
                                ? 'This action is final and will record your executive authorization in the compliance audit trail.'
                                : 'Rejecting this claim will conclude the reimbursement workflow with documented reasoning.'}
                        </p>

                        <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                            <button
                                type="button"
                                onClick={() => setConfirmModal(null)}
                                className="btn-secondary text-xs py-2 px-4"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                disabled={busy}
                                onClick={() => handleExecuteDecision(confirmModal)}
                                className={`text-xs py-2 px-5 font-bold rounded-xl text-white transition ${
                                    confirmModal === 'approve'
                                        ? 'bg-[#7656D6] hover:bg-violet-800'
                                        : 'bg-[#DC2626] hover:bg-red-700'
                                }`}
                            >
                                {busy ? 'Submitting…' : confirmModal === 'approve' ? 'Authorize Payment' : 'Reject Claim'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
