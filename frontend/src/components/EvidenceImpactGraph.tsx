import { useState, useMemo } from 'react';
import {
    AlertCircle,
    FileText,
    RefreshCw,
    ShieldAlert,
    Sparkles,
    UserCheck,
    ChevronDown,
} from 'lucide-react';
import type {
    EvidenceGraphResponse,
    GraphNode,
    UserRole,
} from '../types';

interface EvidenceImpactGraphProps {
    graphData: EvidenceGraphResponse | null;
    loading?: boolean;
    error?: string | null;
    onRefresh?: () => void;
    onSelectDocument?: (documentId: number) => void;
    userRole?: UserRole;
}

export default function EvidenceImpactGraph({
    graphData,
    loading = false,
    error = null,
    onRefresh,
    onSelectDocument,
}: EvidenceImpactGraphProps) {
    const [activeCard, setActiveCard] = useState<'document' | 'extracted' | 'verification' | 'decision'>('verification');

    // Categorize nodes
    const { docNodes, fieldNodes, findingNodes, decisionNode } = useMemo<{
        docNodes: GraphNode[];
        fieldNodes: GraphNode[];
        findingNodes: GraphNode[];
        decisionNode: GraphNode | null;
    }>(() => {
        if (!graphData?.nodes) {
            return { docNodes: [], fieldNodes: [], findingNodes: [], decisionNode: null };
        }
        const docs: GraphNode[] = [];
        const fields: GraphNode[] = [];
        const findings: GraphNode[] = [];
        let decision: GraphNode | null = null;

        graphData.nodes.forEach((n) => {
            if (n.type === 'document') docs.push(n);
            else if (n.type === 'field') fields.push(n);
            else if (n.type === 'finding') findings.push(n);
            else if (n.type === 'decision') decision = n;
        });

        return { docNodes: docs, fieldNodes: fields, findingNodes: findings, decisionNode: decision };
    }, [graphData]);

    // Primary receipt document if present
    const primaryDoc = docNodes[0];

    // Key extracted fields
    const merchantField = fieldNodes.find((f) => f.data?.field_name === 'merchant_name');
    const amountField = fieldNodes.find((f) => f.data?.field_name === 'total_amount');
    const dateField = fieldNodes.find((f) => f.data?.field_name === 'expense_date');

    const merchantVal = merchantField?.data?.effective_value || merchantField?.data?.extracted_value || 'Not detected';
    const extractedAmountVal = amountField?.data?.effective_value || amountField?.data?.extracted_value || null;
    const expenseDateVal = dateField?.data?.effective_value || dateField?.data?.extracted_value || 'Not detected';

    // Claim comparison details from decision node or summary
    const claimedAmount = decisionNode?.data?.claimed_amount;
    const currency = decisionNode?.data?.currency || 'INR';
    const workflowStatus = decisionNode?.data?.workflow_status || graphData?.request_status || 'draft';

    const openFlags = findingNodes.filter(
        (f) => (f.data?.result === 'flag' || f.status === 'warning' || f.status === 'error') &&
               f.data?.resolution_status !== 'resolved' && f.data?.resolution_status !== 'dismissed'
    );

    // Amount variance computation
    const claimedAmtNum = claimedAmount != null ? parseFloat(String(claimedAmount)) : null;
    const extractedAmtNum = extractedAmountVal != null ? parseFloat(String(extractedAmountVal).replace(/,/g, '')) : null;
    const hasAmountVariance =
        claimedAmtNum !== null &&
        extractedAmtNum !== null &&
        !isNaN(claimedAmtNum) &&
        !isNaN(extractedAmtNum) &&
        Math.abs(claimedAmtNum - extractedAmtNum) > 0.01;
    const amountDelta = claimedAmtNum !== null && extractedAmtNum !== null ? claimedAmtNum - extractedAmtNum : 0;

    // Decision state calculations
    // Rule: Never show "Ready for approval" when required verification is incomplete.
    // If a final decision has not been recorded, display "Awaiting decision".
    let decisionHeaderStatus = 'Awaiting decision';
    let decisionBadgeClass = 'bg-amber-50 text-amber-800 border-amber-200';
    let nextStepText = 'Reviewer investigation required';

    if (workflowStatus === 'approved') {
        decisionHeaderStatus = 'Approved';
        decisionBadgeClass = 'bg-teal-50 text-teal-800 border-teal-200';
        nextStepText = 'Reimbursement payment authorized';
    } else if (workflowStatus === 'rejected') {
        decisionHeaderStatus = 'Rejected';
        decisionBadgeClass = 'bg-red-50 text-red-800 border-red-200';
        nextStepText = 'Claim closed with documented rejection';
    } else if (workflowStatus === 'pending_approval') {
        decisionHeaderStatus = 'Awaiting decision';
        decisionBadgeClass = 'bg-violet-50 text-violet-800 border-violet-200';
        nextStepText = 'Awaiting executive approver sign-off';
    } else if (workflowStatus === 'under_review') {
        decisionHeaderStatus = 'Awaiting decision';
        if (openFlags.length > 0) {
            decisionBadgeClass = 'bg-amber-50 text-amber-800 border-amber-200';
            nextStepText = `Reviewer investigation required (${openFlags.length} open flag${openFlags.length > 1 ? 's' : ''})`;
        } else {
            decisionBadgeClass = 'bg-blue-50 text-blue-800 border-blue-200';
            nextStepText = 'Reviewer sign-off pending (automated checks clear)';
        }
    } else {
        decisionHeaderStatus = 'Awaiting decision';
        decisionBadgeClass = 'bg-slate-100 text-slate-700 border-slate-200';
        nextStepText = 'Submit claim to begin verification';
    }

    if (loading) {
        return (
            <div className="card p-12 text-center shadow-xs">
                <RefreshCw className="mx-auto h-8 w-8 animate-spin text-[#3478F6]" />
                <h3 className="mt-4 text-base font-bold text-slate-800">Loading Evidence Impact Graph…</h3>
                <p className="mt-1 text-xs text-slate-500">Connecting document tokens to verification rules and decisions.</p>
            </div>
        );
    }

    if (error || !graphData) {
        return (
            <div className="card p-8 text-center border-red-200 bg-red-50/50 shadow-xs">
                <AlertCircle className="mx-auto h-8 w-8 text-red-600" />
                <h3 className="mt-3 text-sm font-bold text-red-900">Could not load Evidence Impact Graph</h3>
                <p className="mt-1 text-xs text-red-700">{error || 'No graph evidence available for this request.'}</p>
                {onRefresh && (
                    <button
                        type="button"
                        onClick={onRefresh}
                        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 border border-slate-200 shadow-2xs hover:bg-slate-50"
                    >
                        <RefreshCw className="h-3.5 w-3.5" />
                        <span>Retry</span>
                    </button>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header info */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#3478F6]">Deterministic Audit Sequence</span>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">Evidence Impact Graph</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                        Clean 4-stage pipeline connecting source documents to extracted facts, verification rules, and final decisions.
                    </p>
                </div>
                {onRefresh && (
                    <button
                        type="button"
                        onClick={onRefresh}
                        className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-xl bg-slate-100 hover:bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition"
                    >
                        <RefreshCw className="h-3.5 w-3.5 text-slate-500" />
                        <span>Refresh Pipeline</span>
                    </button>
                )}
            </div>

            {/* 4-STAGE INTERACTIVE SEQUENCE: DOCUMENT → EXTRACTED DETAILS → VERIFICATION → DECISION */}
            <div className="grid grid-cols-1 md:grid-cols-4 items-stretch gap-3">
                {/* 1. DOCUMENT CARD */}
                <button
                    type="button"
                    onClick={() => setActiveCard('document')}
                    className={`text-left rounded-2xl p-5 border transition-all flex flex-col justify-between ${
                        activeCard === 'document'
                            ? 'border-[#3478F6] bg-blue-50/40 ring-2 ring-[#3478F6]/20 shadow-md'
                            : 'border-slate-200 bg-white hover:border-slate-300 shadow-xs'
                    }`}
                >
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-100 text-[#3478F6]">
                                <FileText className="h-4 w-4" />
                            </span>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 1</span>
                        </div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#3478F6] block">
                            Document
                        </span>
                        <h4 className="text-base font-bold text-slate-900 leading-snug">
                            {primaryDoc?.label || 'Source Receipt'}
                        </h4>
                        <p className="text-xs text-slate-600 truncate">
                            {primaryDoc?.data?.original_filename || 'No document attached'}
                        </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            primaryDoc?.status === 'ready'
                                ? 'bg-teal-50 text-teal-800 border-teal-200'
                                : primaryDoc?.status === 'error'
                                ? 'bg-red-50 text-red-800 border-red-200'
                                : 'bg-slate-100 text-slate-700 border-slate-200'
                        }`}>
                            {primaryDoc?.status === 'ready' ? 'Ready' : primaryDoc?.status === 'error' ? 'Document unreadable' : 'Processing'}
                        </span>
                        <span className="text-[11px] font-semibold text-[#3478F6]">Click to inspect</span>
                    </div>
                </button>

                {/* 2. EXTRACTED DETAILS CARD */}
                <button
                    type="button"
                    onClick={() => setActiveCard('extracted')}
                    className={`text-left rounded-2xl p-5 border transition-all flex flex-col justify-between ${
                        activeCard === 'extracted'
                            ? 'border-[#0F9D8A] bg-teal-50/40 ring-2 ring-[#0F9D8A]/20 shadow-md'
                            : 'border-slate-200 bg-white hover:border-slate-300 shadow-xs'
                    }`}
                >
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-teal-100 text-[#0F9D8A]">
                                <Sparkles className="h-4 w-4" />
                            </span>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 2</span>
                        </div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#0F9D8A] block">
                            Extracted Details
                        </span>
                        <h4 className="text-base font-bold text-slate-900 truncate">
                            {merchantVal}
                        </h4>
                        <div className="text-xs text-slate-700 space-y-0.5">
                            <p>Amount: <strong className="text-slate-900">{extractedAmountVal ? `${currency} ${extractedAmountVal}` : 'Not detected'}</strong></p>
                            <p className="text-slate-500">Date: {expenseDateVal}</p>
                        </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span className="text-[10px] font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                            {fieldNodes.length} facts extracted
                        </span>
                        <span className="text-[11px] font-semibold text-[#0F9D8A]">Click to inspect</span>
                    </div>
                </button>

                {/* 3. VERIFICATION CARD */}
                <button
                    type="button"
                    onClick={() => setActiveCard('verification')}
                    className={`text-left rounded-2xl p-5 border transition-all flex flex-col justify-between ${
                        activeCard === 'verification'
                            ? 'border-[#F59E0B] bg-amber-50/40 ring-2 ring-[#F59E0B]/20 shadow-md'
                            : 'border-slate-200 bg-white hover:border-slate-300 shadow-xs'
                    }`}
                >
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-100 text-[#F59E0B]">
                                <ShieldAlert className="h-4 w-4" />
                            </span>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 3</span>
                        </div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#F59E0B] block">
                            Verification
                        </span>
                        <h4 className="text-base font-bold text-slate-900">
                            Comparison
                        </h4>
                        <div className="text-xs text-slate-700 space-y-0.5">
                            <p>Claim: <strong>{currency} {claimedAmount ?? '—'}</strong></p>
                            <p className={hasAmountVariance ? 'text-red-600 font-bold' : 'text-teal-700 font-semibold'}>
                                {hasAmountVariance
                                    ? `Difference: ${currency} ${Math.abs(amountDelta).toFixed(2)}`
                                    : 'Difference: None (Matched)'}
                            </p>
                        </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            openFlags.length > 0 ? 'bg-amber-50 text-amber-800 border-amber-200' : 'bg-teal-50 text-teal-800 border-teal-200'
                        }`}>
                            {openFlags.length > 0 ? `${openFlags.length} open flag` : 'Checks verified'}
                        </span>
                        <span className="text-[11px] font-semibold text-[#F59E0B]">Click to inspect</span>
                    </div>
                </button>

                {/* 4. DECISION CARD */}
                <button
                    type="button"
                    onClick={() => setActiveCard('decision')}
                    className={`text-left rounded-2xl p-5 border transition-all flex flex-col justify-between ${
                        activeCard === 'decision'
                            ? 'border-[#7656D6] bg-violet-50/40 ring-2 ring-[#7656D6]/20 shadow-md'
                            : 'border-slate-200 bg-white hover:border-slate-300 shadow-xs'
                    }`}
                >
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-100 text-[#7656D6]">
                                <UserCheck className="h-4 w-4" />
                            </span>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 4</span>
                        </div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#7656D6] block">
                            Decision
                        </span>
                        <h4 className="text-base font-bold text-slate-900 leading-snug">
                            {decisionHeaderStatus}
                        </h4>
                        <div className="text-xs text-slate-600 space-y-0.5">
                            <p className="font-semibold text-slate-800">Next step:</p>
                            <p className="text-[11px] leading-tight text-slate-600 line-clamp-2">
                                {nextStepText}
                            </p>
                        </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${decisionBadgeClass}`}>
                            {workflowStatus.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[11px] font-semibold text-[#7656D6]">Click to inspect</span>
                    </div>
                </button>
            </div>

            {/* INTERACTIVE EVIDENCE INSPECTION DRAWER */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
                    <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Detailed Evidence Drilldown</span>
                        <h3 className="text-base font-bold text-slate-900 capitalize">
                            {activeCard === 'document' && 'Stage 1: Document Version Evidence'}
                            {activeCard === 'extracted' && 'Stage 2: Extracted Information & Confidence'}
                            {activeCard === 'verification' && 'Stage 3: Automated Verification Check Findings'}
                            {activeCard === 'decision' && 'Stage 4: Workflow Decision & Resolution Path'}
                        </h3>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">
                        {activeCard === 'document' && `${docNodes.length} file(s) recorded`}
                        {activeCard === 'extracted' && `${fieldNodes.length} field(s) on file`}
                        {activeCard === 'verification' && `${findingNodes.length} check(s) evaluated`}
                        {activeCard === 'decision' && `Status: ${workflowStatus}`}
                    </span>
                </div>

                {/* STAGE 1 DRILLDOWN */}
                {activeCard === 'document' && (
                    <div className="space-y-3">
                        <p className="text-xs text-slate-600 leading-relaxed">
                            These original files were uploaded by the claimant and preserved immutably for compliance auditing.
                        </p>
                        <div className="grid gap-3 sm:grid-cols-2">
                            {docNodes.map((doc) => (
                                <div key={doc.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <strong className="text-xs font-bold text-slate-900">{doc.label}</strong>
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                            doc.status === 'ready' ? 'bg-teal-50 text-teal-800 border-teal-200' : 'bg-red-50 text-red-800 border-red-200'
                                        }`}>
                                            {doc.data?.processing_status || doc.status}
                                        </span>
                                    </div>
                                    <p className="text-xs text-slate-600 font-mono truncate">{doc.data?.original_filename}</p>
                                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                                        <span>Size: {doc.data?.file_size ? `${(doc.data.file_size / 1024).toFixed(1)} KB` : '—'}</span>
                                        <span>Type: {doc.data?.mime_type || 'PDF/Image'}</span>
                                    </div>
                                    {onSelectDocument && doc.data?.document_id && (
                                        <button
                                            type="button"
                                            onClick={() => onSelectDocument(doc.data.document_id)}
                                            className="w-full mt-2 rounded-lg bg-white border border-slate-200 py-1.5 text-xs font-bold text-[#3478F6] hover:bg-slate-50 transition"
                                        >
                                            Inspect in Document Viewer
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* STAGE 2 DRILLDOWN */}
                {activeCard === 'extracted' && (
                    <div className="space-y-3">
                        <p className="text-xs text-slate-600 leading-relaxed">
                            OCR text tokens parsed by the deterministic normalization engine. Fields can be verified and corrected with recorded justification.
                        </p>
                        <div className="rounded-xl border border-slate-200 overflow-hidden">
                            <table className="w-full text-left text-xs border-collapse">
                                <thead>
                                    <tr className="bg-slate-100 text-[10px] font-bold uppercase text-slate-600 border-b border-slate-200">
                                        <th className="py-2.5 px-3">Field Name</th>
                                        <th className="py-2.5 px-3">Effective Value</th>
                                        <th className="py-2.5 px-3">Status</th>
                                        <th className="py-2.5 px-3">Correction Details</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 bg-white">
                                    {fieldNodes.map((field) => (
                                        <tr key={field.id} className="hover:bg-slate-50/60">
                                            <td className="py-2 px-3 font-semibold text-slate-900 capitalize">
                                                {field.data?.field_name?.replace(/_/g, ' ') || field.label}
                                            </td>
                                            <td className="py-2 px-3 font-mono font-medium text-slate-900">
                                                {field.data?.effective_value || field.data?.extracted_value || <span className="text-slate-400 italic font-sans">Not detected</span>}
                                            </td>
                                            <td className="py-2 px-3">
                                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                                    field.data?.is_corrected
                                                        ? 'bg-violet-50 text-violet-800 border-violet-200'
                                                        : field.status === 'verified'
                                                        ? 'bg-teal-50 text-teal-800 border-teal-200'
                                                        : 'bg-slate-100 text-slate-700 border-slate-200'
                                                }`}>
                                                    {field.data?.is_corrected ? 'Resolved / Corrected' : 'Matched'}
                                                </span>
                                            </td>
                                            <td className="py-2 px-3 text-[11px] text-slate-600">
                                                {field.data?.is_corrected ? (
                                                    <span>Reason: "{field.data.correction_reason}"</span>
                                                ) : (
                                                    <span className="text-slate-400">Direct extraction</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* STAGE 3 DRILLDOWN */}
                {activeCard === 'verification' && (
                    <div className="space-y-3">
                        <p className="text-xs text-slate-600 leading-relaxed">
                            Deterministic rule evaluation results. Flags require explicit reviewer disposition before executive approval.
                        </p>
                        <div className="space-y-2">
                            {findingNodes.map((finding) => {
                                const isFlag = finding.data?.result === 'flag';
                                const isPass = finding.data?.result === 'pass';
                                const isResolved = finding.data?.resolution_status === 'resolved' || finding.data?.resolution_status === 'dismissed';
                                return (
                                    <div
                                        key={finding.id}
                                        className={`rounded-xl border p-3.5 text-xs transition ${
                                            isFlag && !isResolved
                                                ? 'border-amber-300 bg-amber-50/60'
                                                : isPass
                                                ? 'border-teal-200 bg-teal-50/30'
                                                : 'border-slate-200 bg-slate-50/50'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="flex items-center gap-2">
                                                <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                                                    isPass || isResolved ? 'bg-teal-100 text-teal-800' : 'bg-amber-100 text-amber-800'
                                                }`}>
                                                    {isPass || isResolved ? '✓' : '!'}
                                                </span>
                                                <strong className="text-slate-900 capitalize">
                                                    {finding.data?.check_type?.replace(/_/g, ' ') || finding.label}
                                                </strong>
                                            </div>
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                                isResolved
                                                    ? 'bg-violet-50 text-violet-800 border-violet-200'
                                                    : isPass
                                                    ? 'bg-teal-50 text-teal-800 border-teal-200'
                                                    : 'bg-amber-50 text-amber-800 border-amber-200'
                                            }`}>
                                                {isResolved ? 'Resolved' : isPass ? 'Matched' : 'Needs review'}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-slate-700 pl-7 leading-relaxed">
                                            {finding.data?.explanation || 'Verification rule executed against stored document records.'}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* STAGE 4 DRILLDOWN */}
                {activeCard === 'decision' && (
                    <div className="space-y-3">
                        <p className="text-xs text-slate-600 leading-relaxed">
                            Current authority checkpoint and recorded decisions for this expense claim.
                        </p>
                        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3 text-xs">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Assigned Reviewer</span>
                                    <p className="font-bold text-slate-900 mt-0.5">{decisionNode?.data?.assigned_reviewer_name || 'Designated Reviewer'}</p>
                                </div>
                                <div>
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Sign-Off Approver</span>
                                    <p className="font-bold text-slate-900 mt-0.5">{decisionNode?.data?.assigned_approver_name || 'Designated Approver'}</p>
                                </div>
                            </div>
                            <div className="pt-2 border-t border-slate-200">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Workflow Summary</span>
                                <p className="font-medium text-slate-800 mt-0.5 leading-relaxed">
                                    {decisionNode?.data?.impact_summary || graphData.summary?.impact_summary || 'Claim is moving through the verified approval sequence.'}
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* EXPANDABLE SECTION FOR RAW TECHNICAL GRAPH METADATA */}
            <details className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
                <summary className="cursor-pointer text-xs font-bold text-slate-600 hover:text-slate-900 flex items-center justify-between select-none">
                    <span>View advanced node graph details ({graphData.nodes.length} nodes, {graphData.edges.length} edges)</span>
                    <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" />
                </summary>
                <div className="mt-3 pt-3 border-t border-slate-100 text-xs space-y-2">
                    <p className="text-[11px] text-slate-500">
                        Total documents: {graphData.summary?.total_documents} · Extracted fields: {graphData.summary?.total_extracted_fields} · Checks: {graphData.summary?.total_findings} · Resolved: {graphData.summary?.resolved_findings}
                    </p>
                    <div className="max-h-48 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-[10px] text-slate-200">
                        {JSON.stringify({ summary: graphData.summary, node_ids: graphData.nodes.map(n => n.id) }, null, 2)}
                    </div>
                </div>
            </details>
        </div>
    );
}
