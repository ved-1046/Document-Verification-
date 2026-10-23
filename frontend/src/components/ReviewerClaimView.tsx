import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    ClipboardCheck,
    ZoomIn,
    ZoomOut,
    RotateCw,
    Download,
    ShieldAlert,
    Check,
    X,
    AlertTriangle,
    Edit3,
    Send,
    MessageSquare,
    Network,
    History,
    CheckCircle2,
    FileText,
    ChevronDown,
    Sparkles,
} from 'lucide-react';
import type {
    RequestSummary,
    DocumentVersion,
    VerificationCheck,
    ExtractedField,
    ReviewerCorrection,
    ReviewAction,
} from '../types';

interface ReviewerClaimViewProps {
    request: RequestSummary;
    documents: DocumentVersion[];
    checks: VerificationCheck[];
    extractions: Record<number, ExtractedField[]>;
    corrections: ReviewerCorrection[];
    history?: ReviewAction[];
    busy: boolean;
    previewUrl: string | null;
    selectedDocId: number | null;
    onSelectDoc: (docId: number) => void;
    onResolveCheck: (checkId: number, resolution: 'resolved' | 'dismissed', reason?: string) => Promise<void>;
    onCorrectField: (
        docId: number,
        fieldName: string,
        correctedVal: string,
        originalVal: string | null,
        reason: string
    ) => Promise<void>;
    onRequestCorrection: (comment: string) => Promise<void>;
    onCompleteReview: (comment: string) => Promise<void>;
    formatDate: (date?: string | null) => string;
    formatAmount: (amount?: string | number | null, currency?: string | null) => string;
    onOpenGraph: () => void;
    onOpenReplay: () => void;
}

export default function ReviewerClaimView({
    request,
    documents,
    checks,
    extractions,
    corrections,
    busy,
    previewUrl,
    selectedDocId,
    onSelectDoc,
    onResolveCheck,
    onCorrectField,
    onRequestCorrection,
    onCompleteReview,
    formatDate,
    formatAmount,
    onOpenGraph,
    onOpenReplay,
}: ReviewerClaimViewProps) {
    // Document viewer controls
    const [zoom, setZoom] = useState(1);
    const [rotation, setRotation] = useState(0);

    // Review outcome action form state
    const [actionComment, setActionComment] = useState('');
    const [activeActionTab, setActiveActionTab] = useState<'forward' | 'request_info'>('forward');

    // Field correction modal state
    const [correctingField, setCorrectingField] = useState<{
        docId: number;
        fieldName: string;
        currentValue: string;
        originalValue: string | null;
    } | null>(null);
    const [correctedValue, setCorrectedValue] = useState('');
    const [correctionReason, setCorrectionReason] = useState('');
    const [correctionError, setCorrectionError] = useState<string | null>(null);

    // Resolution modal state (ensures reviewer records reason to resolve/dismiss)
    const [resolvingCheck, setResolvingCheck] = useState<{
        checkId: number;
        mode: 'resolved' | 'dismissed';
        title: string;
    } | null>(null);
    const [resolutionReason, setResolutionReason] = useState('');
    const [resolutionError, setResolutionError] = useState<string | null>(null);

    const latestReceipt = documents
        .filter((d) => d.doc_type === 'receipt')
        .sort((a, b) => b.version_number - a.version_number)[0];

    const activeDoc = documents.find((d) => d.id === selectedDocId) ?? latestReceipt ?? documents[0];

    // Helper for effective field values
    const getEffectiveValue = (
        docId: number,
        fieldName: string
    ): { value: string | null; isCorrected: boolean; original: string | null; reason: string | null } => {
        const corr = corrections.filter((c) => c.document_version_id === docId && c.field_name === fieldName).at(-1);
        const f = (extractions[docId] ?? []).find((field) => field.field_name === fieldName);
        const extracted = f?.normalized_value ?? f?.extracted_value ?? null;
        if (corr?.corrected_value) {
            return { value: corr.corrected_value, isCorrected: true, original: extracted, reason: corr.reason ?? null };
        }
        return { value: extracted, isCorrected: false, original: null, reason: null };
    };

    const emptyEff = { value: null, isCorrected: false, original: null, reason: null };

    // Receipt values
    const receiptMerchantEff = latestReceipt ? getEffectiveValue(latestReceipt.id, 'merchant_name') : emptyEff;
    const receiptAmountEff = latestReceipt ? getEffectiveValue(latestReceipt.id, 'total_amount') : emptyEff;
    const receiptDateEff = latestReceipt ? getEffectiveValue(latestReceipt.id, 'expense_date') : emptyEff;
    const receiptCurrencyEff = latestReceipt ? getEffectiveValue(latestReceipt.id, 'currency') : emptyEff;

    // Discrepancy calculations
    const claimedAmtNum = request.claimed_amount != null ? parseFloat(String(request.claimed_amount)) : null;
    const receiptAmtNum = receiptAmountEff.value != null ? parseFloat(String(receiptAmountEff.value).replace(/,/g, '')) : null;
    const hasAmountMismatch =
        claimedAmtNum !== null &&
        receiptAmtNum !== null &&
        !isNaN(claimedAmtNum) &&
        !isNaN(receiptAmtNum) &&
        Math.abs(claimedAmtNum - receiptAmtNum) > 0.01;
    const amountDelta = claimedAmtNum !== null && receiptAmtNum !== null ? claimedAmtNum - receiptAmtNum : 0;

    const hasDateMismatch = Boolean(
        request.expense_date &&
        receiptDateEff.value &&
        request.expense_date.trim() !== receiptDateEff.value.trim()
    );

    // Verification check stats
    const openFlags = checks.filter((c) => c.result === 'flag' && c.resolution_status === 'open');
    const passedChecks = checks.filter((c) => c.result === 'pass');
    const resolvedFlags = checks.filter((c) => c.result === 'flag' && c.resolution_status !== 'open');

    // Document zoom handlers
    const zoomIn = () => setZoom((z) => Math.min(2.5, z + 0.25));
    const zoomOut = () => setZoom((z) => Math.max(0.5, z - 0.25));
    const resetZoom = () => {
        setZoom(1);
        setRotation(0);
    };
    const rotate = () => setRotation((r) => (r + 90) % 360);

    const handleOpenCorrection = (docId: number, fieldName: string) => {
        const eff = getEffectiveValue(docId, fieldName);
        setCorrectingField({
            docId,
            fieldName,
            currentValue: eff.value ?? '',
            originalValue: eff.original,
        });
        setCorrectedValue(eff.value ?? '');
        setCorrectionReason('');
        setCorrectionError(null);
    };

    const handleSaveCorrection = async () => {
        if (!correctingField) return;
        if (!correctedValue.trim()) {
            setCorrectionError('Corrected value is required.');
            return;
        }
        if (!correctionReason.trim()) {
            setCorrectionError('Audit reason is required for field correction.');
            return;
        }
        try {
            await onCorrectField(
                correctingField.docId,
                correctingField.fieldName,
                correctedValue.trim(),
                correctingField.originalValue,
                correctionReason.trim()
            );
            setCorrectingField(null);
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setCorrectionError(typeof msg === 'string' ? msg : 'Correction failed.');
        }
    };

    const handleOpenResolution = (checkId: number, mode: 'resolved' | 'dismissed', title: string) => {
        setResolvingCheck({ checkId, mode, title });
        setResolutionReason('');
        setResolutionError(null);
    };

    const handleSaveResolution = async () => {
        if (!resolvingCheck) return;
        if (!resolutionReason.trim()) {
            setResolutionError('An audit reason is required to resolve or dismiss this verification flag.');
            return;
        }
        try {
            await onResolveCheck(resolvingCheck.checkId, resolvingCheck.mode, resolutionReason.trim());
            setResolvingCheck(null);
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setResolutionError(typeof msg === 'string' ? msg : 'Could not resolve check.');
        }
    };

    const isDocUnreadable = activeDoc?.processing_status === 'failed';

    return (
        <div className="space-y-6">
            {/* SIMPLIFIED REVIEWER TOP HEADER:
                Only shows: Claim ID & title, Claim amount, Extracted receipt amount, Open issues, Current status */}
            <div className="rounded-2xl border border-blue-200/80 bg-gradient-to-r from-[#14213D] via-[#1E293B] to-[#1E3A8A] p-6 text-white shadow-md">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="space-y-1">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/25 border border-blue-400/30 px-3 py-0.5 text-[11px] font-bold text-blue-300 uppercase tracking-wider">
                            <ClipboardCheck className="h-3.5 w-3.5" />
                            Reviewer Workspace
                        </span>
                        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                            Claim #{request.request_number} · {request.title}
                        </h1>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                        <Link
                            to={`/assistant?requestId=${request.id}`}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600/90 hover:bg-violet-600 px-3.5 py-2 text-xs font-bold text-white transition shadow-xs"
                            title="Open AI Assistant to audit this claim"
                        >
                            <Sparkles className="h-4 w-4 text-violet-200" />
                            <span>Ask AI Assistant</span>
                        </Link>
                        <button
                            type="button"
                            onClick={onOpenGraph}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-white hover:bg-white/20 transition shadow-xs"
                        >
                            <Network className="h-4 w-4 text-blue-300" />
                            <span>Evidence Impact Graph</span>
                        </button>
                        <button
                            type="button"
                            onClick={onOpenReplay}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-white hover:bg-white/20 transition shadow-xs"
                        >
                            <History className="h-4 w-4 text-blue-300" />
                            <span>Decision Replay</span>
                        </button>
                    </div>
                </div>

                {/* KPI Ribbon: Claim amount, Extracted receipt amount, Open issues, Current status */}
                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-white/10 pt-4">
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-blue-200 font-semibold">Claim Amount</span>
                        <p className="text-2xl sm:text-3xl font-black text-white mt-0.5">
                            {formatAmount(request.claimed_amount, request.currency)}
                        </p>
                    </div>
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-blue-200 font-semibold">Extracted Receipt Amount</span>
                        <p className="text-2xl sm:text-3xl font-black text-white mt-0.5">
                            {receiptAmountEff.value ? formatAmount(receiptAmountEff.value, request.currency) : (
                                <span className="text-lg text-slate-300 font-medium">Not detected</span>
                            )}
                        </p>
                    </div>
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-blue-200 font-semibold">Open Issues</span>
                        <p className={`text-2xl sm:text-3xl font-black mt-0.5 ${openFlags.length > 0 ? 'text-[#F59E0B]' : 'text-[#0F9D8A]'}`}>
                            {openFlags.length} {openFlags.length === 1 ? 'issue' : 'issues'}
                        </p>
                    </div>
                    <div>
                        <span className="text-[11px] uppercase tracking-wider text-blue-200 font-semibold">Current Status</span>
                        <p className="text-xl sm:text-2xl font-bold text-blue-100 mt-0.5 capitalize">
                            {request.status.replace(/_/g, ' ')}
                        </p>
                    </div>
                </div>
            </div>

            {/* SIDE-BY-SIDE WORKBENCH:
                Left: Original Document Preview
                Right: Simplified OCR Comparison Table */}
            <div className="grid gap-6 lg:grid-cols-2">
                {/* LEFT PANE: ORIGINAL DOCUMENT PREVIEW */}
                <section className="card flex flex-col overflow-hidden border-slate-200 shadow-md">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border bg-slate-50/90 px-4 py-3">
                        <div className="flex items-center gap-1.5 overflow-x-auto">
                            {documents.map((doc) => (
                                <button
                                    key={doc.id}
                                    type="button"
                                    onClick={() => onSelectDoc(doc.id)}
                                    className={`rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                                        selectedDocId === doc.id
                                            ? 'bg-[#3478F6] text-white shadow-xs'
                                            : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                                    }`}
                                >
                                    {doc.doc_type === 'receipt' ? 'Receipt' : doc.doc_type === 'expense_form' ? 'Expense Form' : 'Document'} v{doc.version_number}
                                </button>
                            ))}
                        </div>

                        {/* Viewer Control Buttons: Zoom & Rotate */}
                        <div className="flex items-center gap-1">
                            <button
                                type="button"
                                onClick={zoomIn}
                                title="Zoom In"
                                className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-200 transition"
                            >
                                <ZoomIn className="h-4 w-4" />
                            </button>
                            <button
                                type="button"
                                onClick={zoomOut}
                                title="Zoom Out"
                                className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-200 transition"
                            >
                                <ZoomOut className="h-4 w-4" />
                            </button>
                            <button
                                type="button"
                                onClick={resetZoom}
                                title="Reset Zoom"
                                className="rounded-lg px-2 py-1 text-[10px] font-bold text-slate-600 hover:bg-slate-200 transition"
                            >
                                {Math.round(zoom * 100)}%
                            </button>
                            <button
                                type="button"
                                onClick={rotate}
                                title="Rotate 90°"
                                className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-200 transition"
                            >
                                <RotateCw className="h-4 w-4" />
                            </button>
                            {previewUrl && (
                                <a
                                    href={previewUrl}
                                    download={activeDoc?.original_filename}
                                    title="Download File"
                                    className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-200 transition"
                                >
                                    <Download className="h-4 w-4" />
                                </a>
                            )}
                        </div>
                    </div>

                    {/* Document Display Canvas */}
                    <div className="relative min-h-[440px] max-h-[540px] flex-1 overflow-auto bg-slate-900/90 p-4 flex items-center justify-center">
                        {isDocUnreadable ? (
                            <div className="text-center p-6 bg-red-950/60 border border-red-500/40 rounded-2xl max-w-sm text-red-200">
                                <AlertTriangle className="mx-auto h-8 w-8 text-[#F97373] mb-2" />
                                <h4 className="text-sm font-bold text-white">Document Unreadable</h4>
                                <p className="text-xs text-red-200 mt-1 leading-relaxed">
                                    The OCR engine was unable to parse readable text from this scan. You may request a clearer replacement from the employee below.
                                </p>
                            </div>
                        ) : previewUrl ? (
                            activeDoc?.mime_type?.startsWith('image/') ? (
                                <img
                                    src={previewUrl}
                                    alt="Source Document"
                                    style={{
                                        transform: `scale(${zoom}) rotate(${rotation}deg)`,
                                        transition: 'transform 0.15s ease-out',
                                    }}
                                    className="max-h-[500px] object-contain shadow-2xl rounded"
                                />
                            ) : (
                                <iframe
                                    src={previewUrl}
                                    title="PDF Document"
                                    className="h-[500px] w-full rounded border-0 bg-white"
                                />
                            )
                        ) : (
                            <div className="text-center text-slate-400 text-xs">
                                <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
                                <p>Select a document version above to inspect source evidence.</p>
                            </div>
                        )}
                    </div>

                    {/* Canvas Sub-footer */}
                    <div className="flex items-center justify-between border-t border-surface-border bg-slate-50 px-4 py-2 text-[11px] text-muted">
                        <span>Viewing: <strong className="text-main">{activeDoc?.original_filename}</strong></span>
                        <span className="capitalize">
                            Status: <strong className={isDocUnreadable ? 'text-[#F97373]' : 'text-teal-700'}>{activeDoc?.processing_status}</strong>
                        </span>
                    </div>
                </section>

                {/* RIGHT PANE: SIMPLIFIED OCR COMPARISON TABLE
                    Shows only Merchant, Amount, Date, Currency
                    Each row: Claim value, Receipt value, Result */}
                <section className="card flex flex-col overflow-hidden border-slate-200 shadow-md">
                    <div className="border-b border-surface-border bg-slate-50/90 px-5 py-3 flex items-center justify-between">
                        <div>
                            <h2 className="text-sm font-bold text-slate-900">
                                OCR Verification Comparison
                            </h2>
                            <p className="text-[11px] text-muted">Comparing employee claimed details with extracted receipt tokens</p>
                        </div>
                        <span className="rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-[10px] font-bold text-[#3478F6]">
                            Deterministic Match
                        </span>
                    </div>

                    <div className="p-5 space-y-4 overflow-y-auto max-h-[540px]">
                        {/* 4-ROW SIMPLIFIED OCR COMPARISON TABLE */}
                        <div className="rounded-xl border border-slate-200 overflow-hidden shadow-2xs">
                            <table className="w-full text-left text-xs border-collapse">
                                <thead>
                                    <tr className="border-b border-slate-200 bg-slate-100 text-[10px] uppercase font-bold text-slate-600">
                                        <th className="py-2.5 px-3">Field</th>
                                        <th className="py-2.5 px-3">Claim Value</th>
                                        <th className="py-2.5 px-3">Receipt Value</th>
                                        <th className="py-2.5 px-3 text-right">Result</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 bg-white">
                                    {/* 1. Merchant */}
                                    <tr>
                                        <td className="py-3 px-3 font-semibold text-slate-900">Merchant</td>
                                        <td className="py-3 px-3 text-slate-600">{request.expense_category?.replace(/_/g, ' ') || 'General'}</td>
                                        <td className="py-3 px-3 font-medium text-slate-900">
                                            {receiptMerchantEff.value || <span className="text-slate-400 italic">Not detected</span>}
                                        </td>
                                        <td className="py-3 px-3 text-right">
                                            {receiptMerchantEff.isCorrected ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold text-[#7656D6] border border-violet-200">
                                                    Resolved
                                                </span>
                                            ) : receiptMerchantEff.value ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-[#0F9D8A] border border-teal-200">
                                                    <CheckCircle2 className="h-3 w-3" /> Matched
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-[#F59E0B] border border-amber-200">
                                                    Missing information
                                                </span>
                                            )}
                                        </td>
                                    </tr>

                                    {/* 2. Amount */}
                                    <tr>
                                        <td className="py-3 px-3 font-semibold text-slate-900">Amount</td>
                                        <td className="py-3 px-3 text-slate-600">{formatAmount(claimedAmtNum, request.currency)}</td>
                                        <td className="py-3 px-3 font-medium text-slate-900">
                                            {receiptAmtNum !== null ? formatAmount(receiptAmtNum, request.currency) : (
                                                <span className="text-slate-400 italic">Not detected</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-3 text-right">
                                            {receiptAmountEff.isCorrected ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold text-[#7656D6] border border-violet-200">
                                                    Resolved
                                                </span>
                                            ) : hasAmountMismatch ? (
                                                <div className="flex flex-col items-end">
                                                    <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-bold text-[#F97373] border border-red-200">
                                                        <X className="h-3 w-3" /> Needs review
                                                    </span>
                                                    <span className="text-[10px] font-bold text-red-600 mt-0.5">
                                                        Diff: {formatAmount(Math.abs(amountDelta), request.currency)}
                                                    </span>
                                                </div>
                                            ) : receiptAmtNum !== null ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-[#0F9D8A] border border-teal-200">
                                                    <CheckCircle2 className="h-3 w-3" /> Matched
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-[#F59E0B] border border-amber-200">
                                                    Missing information
                                                </span>
                                            )}
                                        </td>
                                    </tr>

                                    {/* 3. Date */}
                                    <tr>
                                        <td className="py-3 px-3 font-semibold text-slate-900">Date</td>
                                        <td className="py-3 px-3 text-slate-600">{formatDate(request.expense_date)}</td>
                                        <td className="py-3 px-3 font-medium text-slate-900">
                                            {receiptDateEff.value ? formatDate(receiptDateEff.value) : (
                                                <span className="text-slate-400 italic">Not detected</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-3 text-right">
                                            {receiptDateEff.isCorrected ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold text-[#7656D6] border border-violet-200">
                                                    Resolved
                                                </span>
                                            ) : hasDateMismatch ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-[#F59E0B] border border-amber-200">
                                                    <AlertTriangle className="h-3 w-3" /> Needs review
                                                </span>
                                            ) : receiptDateEff.value ? (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-[#0F9D8A] border border-teal-200">
                                                    <CheckCircle2 className="h-3 w-3" /> Matched
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-[#F59E0B] border border-amber-200">
                                                    Missing information
                                                </span>
                                            )}
                                        </td>
                                    </tr>

                                    {/* 4. Currency */}
                                    <tr>
                                        <td className="py-3 px-3 font-semibold text-slate-900">Currency</td>
                                        <td className="py-3 px-3 text-slate-600">{request.currency || 'INR'}</td>
                                        <td className="py-3 px-3 font-medium text-slate-900">
                                            {receiptCurrencyEff.value || request.currency || 'INR'}
                                        </td>
                                        <td className="py-3 px-3 text-right">
                                            <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-[#0F9D8A] border border-teal-200">
                                                <CheckCircle2 className="h-3 w-3" /> Matched
                                            </span>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        {/* EXPANDABLE SECTION: VIEW EXTRACTION DETAILS (Hides raw tokens, technical metadata) */}
                        <details className="group rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 shadow-2xs">
                            <summary className="cursor-pointer text-xs font-bold text-slate-700 hover:text-slate-900 flex items-center justify-between select-none">
                                <span className="flex items-center gap-2">
                                    <Edit3 className="h-3.5 w-3.5 text-[#3478F6]" />
                                    <span>View extraction details &amp; record field corrections</span>
                                </span>
                                <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" />
                            </summary>

                            <div className="mt-3 pt-3 border-t border-slate-200 space-y-3">
                                {[
                                    { name: 'merchant_name', label: 'Merchant / Vendor', eff: receiptMerchantEff, docId: latestReceipt?.id },
                                    { name: 'total_amount', label: 'Total Amount', eff: receiptAmountEff, docId: latestReceipt?.id, isCurrency: true },
                                    { name: 'expense_date', label: 'Expense Date', eff: receiptDateEff, docId: latestReceipt?.id, isDate: true },
                                    { name: 'reference_number', label: 'Reference / Invoice #', eff: latestReceipt ? getEffectiveValue(latestReceipt.id, 'reference_number') : emptyEff, docId: latestReceipt?.id },
                                ].map(({ name, label, eff, docId, isCurrency, isDate }) => {
                                    if (!docId) return null;
                                    return (
                                        <div
                                            key={name}
                                            className="rounded-lg border border-slate-200 bg-white p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                                        >
                                            <div className="space-y-0.5 min-w-0">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-[10px] font-bold uppercase text-slate-500">{label}</span>
                                                    {eff.isCorrected && (
                                                        <span className="rounded-full bg-violet-100 text-[#7656D6] px-1.5 py-0.2 text-[9px] font-bold">
                                                            Reviewer Corrected
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-xs font-mono font-bold text-slate-900">
                                                    {isCurrency && eff.value ? formatAmount(eff.value, request.currency) : isDate && eff.value ? formatDate(eff.value) : eff.value || <span className="text-slate-400 font-sans italic font-normal">Not detected</span>}
                                                </p>
                                                {eff.isCorrected && eff.reason && (
                                                    <p className="text-[10px] text-violet-700 italic">Audit rationale: "{eff.reason}"</p>
                                                )}
                                            </div>

                                            {request.status === 'under_review' && (
                                                <button
                                                    type="button"
                                                    onClick={() => handleOpenCorrection(docId, name)}
                                                    className="btn-secondary text-[11px] py-1 px-2.5 self-start sm:self-center flex items-center gap-1 shrink-0"
                                                >
                                                    <Edit3 className="h-3 w-3 text-[#3478F6]" />
                                                    <span>Correct</span>
                                                </button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </details>
                    </div>
                </section>
            </div>

            {/* FIELD CORRECTION MODAL */}
            {correctingField && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
                    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
                        <div className="flex items-center justify-between border-b border-surface-border pb-3">
                            <div className="flex items-center gap-2">
                                <Edit3 className="h-4 w-4 text-[#3478F6]" />
                                <h3 className="text-sm font-bold text-slate-900">
                                    Correct Field: <span className="capitalize">{correctingField.fieldName.replace(/_/g, ' ')}</span>
                                </h3>
                            </div>
                            <button
                                type="button"
                                onClick={() => setCorrectingField(null)}
                                className="text-slate-400 hover:text-slate-600"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        <div className="space-y-3 text-xs">
                            <div>
                                <label className="block text-slate-600 font-semibold mb-1">Original Extracted Value</label>
                                <p className="rounded-lg bg-slate-100 p-2.5 font-mono text-slate-700">
                                    {correctingField.currentValue || '<Not Detected>'}
                                </p>
                            </div>

                            <div>
                                <label className="block text-slate-900 font-bold mb-1">Verified Value <span className="text-red-500">*</span></label>
                                <input
                                    type="text"
                                    className="form-input text-xs"
                                    value={correctedValue}
                                    onChange={(e) => setCorrectedValue(e.target.value)}
                                    placeholder="Enter verified correct value"
                                />
                            </div>

                            <div>
                                <label className="block text-slate-900 font-bold mb-1">Audit Reason for Correction <span className="text-red-500">*</span></label>
                                <textarea
                                    className="form-input text-xs min-h-[70px]"
                                    value={correctionReason}
                                    onChange={(e) => setCorrectionReason(e.target.value)}
                                    placeholder="e.g. Verified amount directly from clear receipt line item."
                                />
                            </div>

                            {correctionError && (
                                <p className="text-red-600 text-xs font-semibold">{correctionError}</p>
                            )}
                        </div>

                        <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                            <button
                                type="button"
                                onClick={() => setCorrectingField(null)}
                                className="btn-secondary text-xs py-1.5 px-3"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                disabled={busy}
                                onClick={handleSaveCorrection}
                                className="btn-primary text-xs py-1.5 px-4"
                            >
                                {busy ? 'Saving…' : 'Save Verified Value'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* RESOLUTION REASON MODAL (Enforces mandatory reason when Reviewer resolves or dismisses flags) */}
            {resolvingCheck && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
                    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
                        <div className="flex items-center justify-between border-b border-surface-border pb-3">
                            <div className="flex items-center gap-2">
                                <ShieldAlert className="h-5 w-5 text-[#F59E0B]" />
                                <h3 className="text-sm font-bold text-slate-900">
                                    {resolvingCheck.mode === 'resolved' ? 'Record Issue Resolution' : 'Dismiss Flag'}
                                </h3>
                            </div>
                            <button
                                type="button"
                                onClick={() => setResolvingCheck(null)}
                                className="text-slate-400 hover:text-slate-600"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        <div className="space-y-3 text-xs">
                            <p className="text-slate-700">
                                Resolving issue: <strong className="text-slate-900 capitalize">{resolvingCheck.title.replace(/_/g, ' ')}</strong>
                            </p>
                            <div>
                                <label className="block text-slate-900 font-bold mb-1">
                                    Audit Reason / Action Taken <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    className="form-input text-xs min-h-[80px]"
                                    value={resolutionReason}
                                    onChange={(e) => setResolutionReason(e.target.value)}
                                    placeholder="Explain how this issue was verified or why it was dismissed (e.g. 'Manually verified merchant name on printed receipt header')."
                                />
                            </div>

                            {resolutionError && (
                                <p className="text-red-600 text-xs font-semibold">{resolutionError}</p>
                            )}
                        </div>

                        <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                            <button
                                type="button"
                                onClick={() => setResolvingCheck(null)}
                                className="btn-secondary text-xs py-1.5 px-3"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                disabled={busy}
                                onClick={handleSaveResolution}
                                className="btn-primary text-xs py-1.5 px-4"
                            >
                                {busy ? 'Saving…' : 'Record Resolution'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* AUTOMATED VERIFICATION FLAGS & RESOLUTION SECTION */}
            <section className="card p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border pb-4">
                    <div className="flex items-center gap-2.5">
                        <span className="rounded-xl bg-amber-50 p-2 text-[#F59E0B] border border-amber-200">
                            <ShieldAlert className="h-5 w-5" />
                        </span>
                        <div>
                            <h2 className="text-base font-bold text-slate-900">Verification Flags &amp; Findings</h2>
                            <p className="text-xs text-muted">All open issues must be resolved with documented reasoning before forwarding to approver.</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-bold">
                        <span className="rounded-full bg-teal-50 px-2.5 py-1 text-[#0F9D8A] border border-teal-200">
                            {passedChecks.length} Matched
                        </span>
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[#F59E0B] border border-amber-200">
                            {openFlags.length} Needs Review
                        </span>
                        <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[#7656D6] border border-violet-200">
                            {resolvedFlags.length} Resolved
                        </span>
                    </div>
                </div>

                <div className="space-y-3">
                    {checks.map((c) => {
                        const isResolved = c.resolution_status === 'resolved' || c.resolution_status === 'dismissed';
                        const isPass = c.result === 'pass';
                        const isOpenFlag = c.result === 'flag' && !isResolved;

                        return (
                            <div
                                key={c.id}
                                className={`rounded-xl border p-4 text-xs transition ${
                                    isOpenFlag
                                        ? 'border-amber-300 bg-amber-50/50 shadow-xs'
                                        : isPass
                                        ? 'border-teal-100 bg-teal-50/20'
                                        : 'border-slate-200 bg-slate-50/50'
                                }`}
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="flex items-center gap-2">
                                        <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                                            isPass ? 'bg-teal-100 text-teal-800' : isResolved ? 'bg-violet-100 text-violet-800' : 'bg-amber-100 text-amber-800'
                                        }`}>
                                            {isPass || isResolved ? '✓' : '!'}
                                        </span>
                                        <strong className="text-slate-900 capitalize">{c.check_type.replace(/_/g, ' ')}</strong>
                                    </div>
                                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                                        isResolved
                                            ? 'bg-violet-50 text-violet-800 border-violet-200'
                                            : isPass
                                            ? 'bg-teal-50 text-teal-800 border-teal-200'
                                            : 'bg-amber-50 text-amber-800 border-amber-200'
                                    }`}>
                                        {isResolved ? 'Resolved' : isPass ? 'Matched' : 'Needs review'}
                                    </span>
                                </div>

                                <p className="text-slate-700 mt-2 font-medium leading-relaxed pl-8">
                                    {c.explanation}
                                </p>

                                {/* Reviewer Action: Opens Reason Modal */}
                                {request.status === 'under_review' && isOpenFlag && (
                                    <div className="mt-3.5 pl-8 flex flex-wrap gap-2">
                                        <button
                                            type="button"
                                            disabled={busy}
                                            onClick={() => handleOpenResolution(c.id, 'resolved', c.check_type)}
                                            className="btn-teal text-xs py-1.5 px-3 flex items-center gap-1.5"
                                        >
                                            <Check className="h-3.5 w-3.5" />
                                            <span>Resolve Issue</span>
                                        </button>
                                        <button
                                            type="button"
                                            disabled={busy}
                                            onClick={() => handleOpenResolution(c.id, 'dismissed', c.check_type)}
                                            className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 text-slate-700"
                                        >
                                            <X className="h-3.5 w-3.5" />
                                            <span>Dismiss Issue</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* REVIEWER DECISION & OUTCOME ACTION CENTER */}
            {request.status === 'under_review' ? (
                <section className="card p-6 border-blue-200 bg-gradient-to-b from-white to-blue-50/20 shadow-lg space-y-5">
                    <div className="border-b border-surface-border pb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <h2 className="text-base font-bold text-slate-900">Record Verification Decision</h2>
                            <p className="text-xs text-muted">Complete the verification review or return the claim to the employee for updates.</p>
                        </div>
                        <div className="inline-flex rounded-xl bg-slate-100 p-1 text-xs font-semibold">
                            <button
                                type="button"
                                onClick={() => setActiveActionTab('forward')}
                                className={`rounded-lg px-3.5 py-1.5 transition ${
                                    activeActionTab === 'forward'
                                        ? 'bg-[#3478F6] text-white shadow-xs'
                                        : 'text-slate-600 hover:text-slate-900'
                                }`}
                            >
                                Send for Approval
                            </button>
                            <button
                                type="button"
                                onClick={() => setActiveActionTab('request_info')}
                                className={`rounded-lg px-3.5 py-1.5 transition ${
                                    activeActionTab === 'request_info'
                                        ? 'bg-[#F59E0B] text-white shadow-xs'
                                        : 'text-slate-600 hover:text-slate-900'
                                }`}
                            >
                                Request More Info
                            </button>
                        </div>
                    </div>

                    {activeActionTab === 'forward' ? (
                        <div className="space-y-4">
                            {openFlags.length > 0 ? (
                                <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950 flex items-center gap-3">
                                    <AlertTriangle className="h-5 w-5 text-[#F59E0B] shrink-0" />
                                    <span>
                                        You have <strong>{openFlags.length} open verification flag(s)</strong>. You must resolve or dismiss them above with a documented reason before forwarding to the approver.
                                    </span>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/60 p-4 text-xs text-teal-950 flex items-center gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-[#0F9D8A] shrink-0" />
                                    <span>
                                        All verification checks verified. Provide your official review summary for the executive approver.
                                    </span>
                                </div>
                            )}

                            <div>
                                <label className="block text-xs font-bold text-slate-900 mb-1.5">
                                    Review Summary Note for Approver <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    className="form-input text-xs min-h-[90px]"
                                    placeholder="e.g. Verified against itemized receipts. Currency conversion confirmed. All flags resolved."
                                    value={actionComment}
                                    onChange={(e) => setActionComment(e.target.value)}
                                />
                            </div>

                            <button
                                type="button"
                                disabled={busy || openFlags.length > 0 || !actionComment.trim()}
                                onClick={() => onCompleteReview(actionComment)}
                                className="btn-primary text-xs py-2.5 px-6 flex items-center gap-2"
                            >
                                <Send className="h-4 w-4" />
                                <span>{busy ? 'Forwarding…' : 'Complete Review & Forward to Approver'}</span>
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 text-xs text-amber-950">
                                This will change the claim status to <strong>More Info Required</strong> and return it to the submitter ({request.submitter?.display_name}) with your specific instructions.
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-900 mb-1.5">
                                    Instructions for Submitter <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    className="form-input text-xs min-h-[90px]"
                                    placeholder="Explain exactly what document or detail needs to be updated (e.g. 'Receipt photo is cut off; please upload full invoice showing tax break-down')."
                                    value={actionComment}
                                    onChange={(e) => setActionComment(e.target.value)}
                                />
                            </div>

                            <button
                                type="button"
                                disabled={busy || !actionComment.trim()}
                                onClick={() => onRequestCorrection(actionComment)}
                                className="btn-secondary text-amber-800 border-amber-300 hover:bg-amber-50 text-xs py-2.5 px-6 flex items-center gap-2 font-bold"
                            >
                                <MessageSquare className="h-4 w-4 text-amber-600" />
                                <span>{busy ? 'Requesting Update…' : 'Return Claim to Submitter for Updates'}</span>
                            </button>
                        </div>
                    )}
                </section>
            ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700 flex items-center justify-between">
                    <span>
                        Claim review stage completed. Current status: <strong className="text-slate-900 capitalize">{request.status.replace(/_/g, ' ')}</strong>
                    </span>
                    <span className="text-muted font-medium">Assigned Approver: {request.assigned_approver?.display_name}</span>
                </div>
            )}
        </div>
    );
}
