import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
    ArrowLeft,
    FileCheck2,
    Receipt,
    Upload,
    Sparkles,
    AlertCircle,
    X,
} from 'lucide-react';
import api from '../services/api';
import type { RequestSummary, UserSummary } from '../types';

export default function NewRequestPage() {
    const navigate = useNavigate();

    // Upload & form state — NO redundant manual expense details required upfront
    const [receiptFile, setReceiptFile] = useState<File | null>(null);
    const [supportingFile, setSupportingFile] = useState<File | null>(null);
    const [showSupportingUpload, setShowSupportingUpload] = useState(false);
    const [category, setCategory] = useState('travel');
    const [purpose, setPurpose] = useState('');

    // Assignees state
    const [assignees, setAssignees] = useState<UserSummary[]>([]);
    const [assigneesLoading, setAssigneesLoading] = useState(true);
    const [assigneesError, setAssigneesError] = useState<string | null>(null);
    const [reviewerId, setReviewerId] = useState('');
    const [approverId, setApproverId] = useState('');

    // Submit state
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [uploadProgressMsg, setUploadProgressMsg] = useState<string | null>(null);

    async function loadAssignees() {
        setAssigneesLoading(true);
        setAssigneesError(null);
        try {
            const response = await api.get<UserSummary[]>('/users/eligible-assignees');
            if (!Array.isArray(response.data)) throw new Error('Unexpected response format.');
            const valid = response.data.filter((person) =>
                Number.isInteger(person.id) && typeof person.display_name === 'string' &&
                (person.role === 'reviewer' || person.role === 'approver'),
            );
            setAssignees(valid);

            const reviewers = valid.filter((p) => p.role === 'reviewer');
            const approvers = valid.filter((p) => p.role === 'approver');
            const defaultRev = reviewers.find((p) => p.id === 5 || p.display_name.toLowerCase().includes('example')) ?? reviewers[0];
            if (defaultRev) setReviewerId(String(defaultRev.id));
            const defaultApp = approvers.find((p) => p.id === 6 || p.display_name.toLowerCase().includes('example')) ?? approvers[0];
            if (defaultApp) setApproverId(String(defaultApp.id));
        } catch (err) {
            const requestError = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
            const status = requestError.response?.status;
            const detail = requestError.response?.data?.detail;
            if (detail) setAssigneesError(detail);
            else if (status === 403) setAssigneesError('Account not authorized to load assignees. Sign in as submitter.');
            else setAssigneesError('Could not reach backend on port 8080. Check connection.');
        } finally {
            setAssigneesLoading(false);
        }
    }

    useEffect(() => { void loadAssignees(); }, []);

    const reviewerOptions = assignees.filter((person) => person.role === 'reviewer');
    const approverOptions = assignees.filter((person) => person.role === 'approver');

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setError(null);

        if (!receiptFile) {
            setError('Please select a receipt or invoice document to upload.');
            return;
        }

        if (!reviewerId) {
            setError('Please select an active reviewer.');
            return;
        }
        if (!approverId) {
            setError('Please select an active approver.');
            return;
        }
        if (reviewerId === approverId) {
            setError('Reviewer and approver must be different people.');
            return;
        }

        setLoading(true);
        setUploadProgressMsg('Creating claim draft…');

        try {
            // 1. Create the request draft without forcing manual amount/date entry
            const res = await api.post<RequestSummary>('/requests', {
                title: 'Expense Reimbursement',
                description: purpose.trim() || undefined,
                request_type: 'expense_reimbursement',
                expense_category: category,
                currency: 'INR',
                assigned_reviewer_id: Number(reviewerId),
                assigned_approver_id: Number(approverId),
            });

            const newRequestId = res.data.id;

            // 2. Upload Receipt
            setUploadProgressMsg('Uploading receipt and initializing OCR extraction…');
            const receiptData = new FormData();
            receiptData.append('doc_type', 'receipt');
            receiptData.append('file', receiptFile);
            await api.post(`/requests/${newRequestId}/documents`, receiptData);

            // 3. Upload Supporting Form if selected
            if (supportingFile) {
                setUploadProgressMsg('Uploading supporting document…');
                const formDocData = new FormData();
                formDocData.append('doc_type', 'expense_form');
                formDocData.append('file', supportingFile);
                await api.post(`/requests/${newRequestId}/documents`, formDocData);
            }

            // 4. Navigate directly to the claim page where OCR results are displayed
            setUploadProgressMsg('Extraction started! Opening claim…');
            navigate(`/requests/${newRequestId}`);
        } catch (err) {
            const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(typeof message === 'string' ? message : 'Failed to create claim. Check your connection and try again.');
            setLoading(false);
            setUploadProgressMsg(null);
        }
    }

    return (
        <div className="page-wrap mx-auto max-w-4xl space-y-7 pb-12">
            {/* Header */}
            <header className="animate-fade-in-up">
                <Link to="/dashboard" className="mb-4 inline-flex items-center gap-2 text-xs font-semibold text-muted hover:text-main transition-colors">
                    <ArrowLeft className="h-4 w-4" /> Back to Dashboard
                </Link>
                <div className="flex items-center gap-3">
                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-[#0F9D8A] ring-1 ring-teal-200/60 shadow-xs">
                        <Receipt className="h-6 w-6" />
                    </span>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-main">New Expense Claim</h1>
                        <p className="mt-0.5 text-xs text-muted">
                            Upload your receipt or invoice. DocuVerify AI automatically reads and extracts the merchant, amount, date, and currency.
                        </p>
                    </div>
                </div>
            </header>

            {/* Error Message */}
            {(error || assigneesError) && (
                <div className="rounded-xl border border-red-200 bg-red-50/80 p-4 text-xs text-red-900 flex items-start gap-3 shadow-xs">
                    <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <strong className="font-bold">Cannot proceed: </strong>
                        <span>{error || assigneesError}</span>
                    </div>
                </div>
            )}
            {false && (
                <div className="rounded-xl border border-red-200 bg-red-50/80 p-4 text-xs text-red-900 flex items-start gap-3 shadow-xs">
                    <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <strong className="font-bold">Cannot proceed: </strong>
                        <span>{error}</span>
                    </div>
                </div>
            )}

            {/* Main Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
                {/* 1. DOCUMENT UPLOAD AREA (Primary Action) */}
                <section className="card p-6 space-y-5 border-indigo-200/70 shadow-sm">
                    <div className="flex items-center justify-between border-b border-surface-border pb-3">
                        <div className="flex items-center gap-2">
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-white text-xs font-bold">1</span>
                            <h2 className="text-base font-bold text-main">Upload Receipt or Invoice</h2>
                            <span className="text-red-500 font-bold">*</span>
                        </div>
                        <span className="text-[11px] font-semibold text-teal-700 bg-teal-50 border border-teal-200 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                            <Sparkles className="h-3 w-3" /> Auto-extracts details
                        </span>
                    </div>

                    {/* Receipt Dropzone */}
                    {!receiptFile ? (
                        <div
                            onClick={() => document.getElementById('receipt-input')?.click()}
                            className="group relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/70 p-8 text-center transition hover:border-indigo-500 hover:bg-indigo-50/40 cursor-pointer"
                        >
                            <input
                                id="receipt-input"
                                type="file"
                                className="sr-only"
                                accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                                onChange={(e) => {
                                    if (e.target.files?.[0]) setReceiptFile(e.target.files[0]);
                                }}
                            />
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-indigo-600 shadow-xs ring-1 ring-slate-200 group-hover:scale-105 transition-transform">
                                <Upload className="h-6 w-6" />
                            </div>
                            <p className="mt-3 text-sm font-bold text-main">
                                Drop receipt or click to browse
                            </p>
                            <p className="mt-1 text-xs text-muted max-w-sm">
                                Supports PNG, JPG, or PDF (up to 20 MB). OCR will automatically detect merchant, amount, date, and currency.
                            </p>
                        </div>
                    ) : (
                        <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-4 flex items-center justify-between shadow-xs">
                            <div className="flex items-center gap-3 min-w-0">
                                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white shadow-xs">
                                    <Receipt className="h-5 w-5" />
                                </span>
                                <div className="min-w-0">
                                    <p className="text-xs font-bold text-teal-950 truncate">{receiptFile.name}</p>
                                    <p className="text-[11px] text-teal-700 font-medium">
                                        {(receiptFile.size / 1024 / 1024).toFixed(2)} MB · Ready for automatic extraction
                                    </p>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => setReceiptFile(null)}
                                className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                                title="Remove file"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    )}

                    {/* Optional Supporting Document / Expense Form */}
                    <div className="pt-2 border-t border-surface-border">
                        {!showSupportingUpload && !supportingFile ? (
                            <button
                                type="button"
                                onClick={() => setShowSupportingUpload(true)}
                                className="text-xs font-semibold text-indigo-700 hover:text-indigo-900 inline-flex items-center gap-1.5"
                            >
                                + Attach Expense Form or Additional Proof (Optional)
                            </button>
                        ) : (
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-bold text-main flex items-center gap-1.5">
                                        <FileCheck2 className="h-4 w-4 text-indigo-600" />
                                        Supporting Document / Expense Form (Optional)
                                    </label>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setSupportingFile(null);
                                            setShowSupportingUpload(false);
                                        }}
                                        className="text-[11px] text-muted hover:text-slate-700"
                                    >
                                        Hide
                                    </button>
                                </div>

                                {!supportingFile ? (
                                    <div
                                        onClick={() => document.getElementById('supporting-input')?.click()}
                                        className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-center cursor-pointer hover:border-slate-400"
                                    >
                                        <input
                                            id="supporting-input"
                                            type="file"
                                            className="sr-only"
                                            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                                            onChange={(e) => {
                                                if (e.target.files?.[0]) setSupportingFile(e.target.files[0]);
                                            }}
                                        />
                                        <p className="text-xs font-semibold text-slate-700">Click to attach supporting document (PDF, PNG, JPG)</p>
                                    </div>
                                ) : (
                                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 flex items-center justify-between">
                                        <span className="text-xs font-semibold text-main truncate max-w-sm">{supportingFile.name}</span>
                                        <button
                                            type="button"
                                            onClick={() => setSupportingFile(null)}
                                            className="text-xs text-red-600 hover:underline font-semibold"
                                        >
                                            Remove
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </section>

                {/* 2. REPUTATION & WORKFLOW DETAILS (Reviewer, Approver, Purpose) */}
                <section className="card p-6 space-y-5">
                    <div className="flex items-center gap-2 border-b border-surface-border pb-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-slate-800 text-xs font-bold">2</span>
                        <h2 className="text-base font-bold text-main">Reviewer & Approval Routing</h2>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                        {/* Assigned Reviewer */}
                        <div>
                            <label className="text-[11px] font-bold uppercase tracking-wider text-muted block mb-1.5">
                                Assigned Reviewer <span className="text-red-500">*</span>
                            </label>
                            <select
                                value={reviewerId}
                                onChange={(e) => setReviewerId(e.target.value)}
                                className="form-input text-xs py-2 w-full"
                                disabled={assigneesLoading}
                            >
                                <option value="">Select a reviewer</option>
                                {reviewerOptions.map((r) => (
                                    <option key={r.id} value={r.id}>
                                        {r.display_name} ({r.role})
                                    </option>
                                ))}
                            </select>
                            <p className="mt-1 text-[10px] text-muted">
                                Performs document verification and compliance checks.
                            </p>
                        </div>

                        {/* Human Approver */}
                        <div>
                            <label className="text-[11px] font-bold uppercase tracking-wider text-muted block mb-1.5">
                                Final Approver <span className="text-red-500">*</span>
                            </label>
                            <select
                                value={approverId}
                                onChange={(e) => setApproverId(e.target.value)}
                                className="form-input text-xs py-2 w-full"
                                disabled={assigneesLoading}
                            >
                                <option value="">Select an approver</option>
                                {approverOptions.map((a) => (
                                    <option key={a.id} value={a.id}>
                                        {a.display_name} ({a.role})
                                    </option>
                                ))}
                            </select>
                            <p className="mt-1 text-[10px] text-muted">
                                Executive who authorizes reimbursement payment.
                            </p>
                        </div>
                    </div>

                    {/* Category & Business Purpose */}
                    <div className="grid gap-4 sm:grid-cols-3 pt-2">
                        <div>
                            <label className="text-[11px] font-bold uppercase tracking-wider text-muted block mb-1.5">
                                Expense Category
                            </label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="form-input text-xs py-2 w-full"
                            >
                                <option value="travel">Travel</option>
                                <option value="meals">Meals & Dining</option>
                                <option value="lodging">Lodging & Hotel</option>
                                <option value="supplies">Office Supplies</option>
                                <option value="software">Software & Tech</option>
                                <option value="other">Other Business Expense</option>
                            </select>
                        </div>

                        <div className="sm:col-span-2">
                            <label className="text-[11px] font-bold uppercase tracking-wider text-muted block mb-1.5">
                                Business Purpose / Note (Optional)
                            </label>
                            <input
                                type="text"
                                value={purpose}
                                onChange={(e) => setPurpose(e.target.value)}
                                placeholder="e.g. Client lunch with partner team, travel to Bangalore conference"
                                className="form-input text-xs py-2 w-full"
                            />
                        </div>
                    </div>
                </section>

                {/* Submit Action Station */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
                    <p className="text-xs text-muted">
                        No manual amount or date entry needed now. You will review extracted figures in the next step.
                    </p>
                    <button
                        type="submit"
                        disabled={loading || !receiptFile}
                        className="btn-primary w-full sm:w-auto px-8 py-3 text-sm font-bold flex items-center justify-center gap-2 shadow-md hover:shadow-lg disabled:opacity-50"
                    >
                        {loading ? (
                            <span>{uploadProgressMsg ?? 'Processing…'}</span>
                        ) : (
                            <>
                                <Sparkles className="h-4 w-4" />
                                <span>Upload Receipt & Auto-Extract Details →</span>
                            </>
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
}
