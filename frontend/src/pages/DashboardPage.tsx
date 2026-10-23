import { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    AlertCircle,
    AlertTriangle,
    ArrowRight,
    CheckCircle2,
    ClipboardCheck,
    Clock3,
    FilePlus2,
    FileText,
    History,
    ShieldAlert,
    ShieldCheck,
    UserCheck,
    XCircle,
    RotateCcw,
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { DashboardSummary, HealthResponse, RequestSummary, RequestStatus } from '../types';

const StatusDonut = lazy(() => import('../components/StatusDonut'));

const STATUS_META: Record<RequestStatus, { label: string; color: string; badge: string }> = {
    draft: { label: 'Draft', color: '#697386', badge: 'badge-draft' },
    submitted: { label: 'Submitted', color: '#4F46E5', badge: 'badge-submitted' },
    processing: { label: 'Processing', color: '#D97706', badge: 'badge-processing' },
    under_review: { label: 'Under review', color: '#4F46E5', badge: 'badge-review' },
    pending_approval: { label: 'Pending approval', color: '#8B5CF6', badge: 'badge-review' },
    more_info_required: { label: 'Needs info', color: '#D97706', badge: 'badge-more-info' },
    approved: { label: 'Approved', color: '#0F9D8A', badge: 'badge-approved' },
    rejected: { label: 'Rejected', color: '#DC4545', badge: 'badge-rejected' },
    processing_failed: { label: 'Processing failed', color: '#DC4545', badge: 'badge-failed' },
};

export default function DashboardPage() {
    const { user } = useAuth();
    const userRole = user?.role ?? 'submitter';
    const isSubmitter = userRole === 'submitter';
    const isReviewer = userRole === 'reviewer';
    const isApprover = userRole === 'approver';
    const isAdmin = userRole === 'admin';

    const [health, setHealth] = useState<HealthResponse | null>(null);
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [requests, setRequests] = useState<RequestSummary[]>([]);
    const [assignedDrafts, setAssignedDrafts] = useState<RequestSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [summaryError, setSummaryError] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;

        const requestsPromise =
            isSubmitter || isAdmin
                ? api.get<RequestSummary[]>('/requests')
                : api.get<RequestSummary[]>('/requests/review-queue');

        const draftsPromise = isReviewer
            ? api.get<RequestSummary[]>('/requests?status=draft')
            : Promise.resolve({ data: [] as RequestSummary[] });

        Promise.allSettled([
            api.get<HealthResponse>('/health'),
            api.get<DashboardSummary>('/dashboard/summary'),
            requestsPromise,
            draftsPromise,
        ]).then(([h, s, r, d]) => {
            if (!alive) return;
            if (h.status === 'fulfilled') setHealth(h.value.data);

            if (s.status === 'fulfilled') setSummary(s.value.data);
            else setSummaryError('Workspace metrics could not be loaded.');

            if (r.status === 'fulfilled') {
                setRequests(r.value.data);
                setError(null);
            } else {
                const failure = r.reason as { response?: { status?: number; data?: { detail?: string } } };
                const detail = failure?.response?.data?.detail;
                if (typeof detail === 'string') setError(detail);
                else if (failure?.response?.status) setError(`API error (HTTP ${failure.response.status}).`);
                else setError('Could not reach the API. Check your connection and try again.');
            }

            if (d.status === 'fulfilled') setAssignedDrafts(d.value.data);
        }).finally(() => {
            if (alive) setLoading(false);
        });

        return () => {
            alive = false;
        };
    }, [user?.id, userRole, isSubmitter, isReviewer, isAdmin]);

    const greeting = user?.display_name?.split(' ')[0] ?? 'there';

    // Submitter specific data splits
    const submitterDrafts = useMemo(
        () => requests.filter((r) => r.status === 'draft'),
        [requests]
    );
    const submitterNeedsAction = useMemo(
        () => requests.filter((r) => r.status === 'more_info_required' || r.status === 'processing_failed'),
        [requests]
    );
    const submitterInProgress = useMemo(
        () => requests.filter((r) => ['submitted', 'processing', 'under_review', 'pending_approval'].includes(r.status)),
        [requests]
    );
    const submitterApproved = useMemo(
        () => requests.filter((r) => r.status === 'approved'),
        [requests]
    );

    // Total spend calculated from requests
    const totalSpend = useMemo(() => {
        return requests.reduce((acc, r) => {
            const val = parseFloat(String(r.claimed_amount || '0'));
            return acc + (isNaN(val) ? 0 : val);
        }, 0);
    }, [requests]);

    // Chart distribution
    const chartData = useMemo(() => {
        if (!summary) return [];
        return (Object.entries(summary.by_status) as [RequestStatus, number][])
            .filter(([, value]) => value > 0)
            .map(([key, value]) => ({
                name: STATUS_META[key]?.label ?? key,
                value,
                color: STATUS_META[key]?.color ?? '#68738A',
            }));
    }, [summary]);

    // Role themes
    const theme = {
        submitter: {
            pill: 'text-[#0F9D8A] bg-[#E6F7F5] border-[#99E1D7]',
            icon: FileText,
            title: 'My Expenses',
            subtitle: 'Submit and track your expense reimbursement claims.',
            actionBtn: 'btn-teal',
        },
        reviewer: {
            pill: 'text-[#3478F6] bg-blue-50 border-blue-200',
            icon: ClipboardCheck,
            title: 'Verification Center',
            subtitle: 'Check documents, investigate mismatches, and record your findings.',
            actionBtn: 'btn-blue',
        },
        approver: {
            pill: 'text-[#7656D6] bg-violet-50 border-violet-200',
            icon: ShieldCheck,
            title: 'Decision Center',
            subtitle: 'Review findings and make informed decisions.',
            actionBtn: 'btn-violet',
        },
        admin: {
            pill: 'text-[#3478F6] bg-blue-50 border-blue-200',
            icon: ShieldCheck,
            title: 'System Administration',
            subtitle: 'Manage user access, review queues, and system compliance.',
            actionBtn: 'btn-primary',
        },
    }[userRole];

    return (
        <div className="page-wrap space-y-6">
            {/* Compact Header & Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#E2E6EF] pb-4 animate-fade-in-up">
                <div>
                    <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${theme.pill}`}>
                            <theme.icon className="h-3 w-3" />
                            {theme.title}
                        </span>
                        <span className="text-xs text-[#68738A]">·</span>
                        <span className="text-xs text-[#68738A]">Welcome, {greeting}</span>
                    </div>
                    <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#1E293B]">
                        {theme.title}
                    </h1>
                    <p className="mt-0.5 text-xs text-[#64748B]">
                        {theme.subtitle}
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    {isSubmitter && (
                        <Link to="/new-request" className="btn-teal flex items-center gap-2 shadow-sm transition-transform hover:-translate-y-0.5">
                            <FilePlus2 className="h-4 w-4" />
                            <span>New Expense</span>
                        </Link>
                    )}

                    {isReviewer && (
                        <Link to="/review-queue" className="btn-blue flex items-center gap-2 shadow-sm transition-transform hover:-translate-y-0.5">
                            <ClipboardCheck className="h-4 w-4" />
                            <span>Open Review Queue ({requests.length})</span>
                        </Link>
                    )}

                    {isApprover && (
                        <div className="flex items-center gap-2">
                            <Link to="/audit" className="btn-secondary text-xs flex items-center gap-1.5 transition-transform hover:-translate-y-0.5">
                                <History className="h-3.5 w-3.5 text-[#68738A]" />
                                <span>Audit Log</span>
                            </Link>
                            <Link to="/review-queue" className="btn-violet flex items-center gap-2 shadow-sm transition-transform hover:-translate-y-0.5">
                                <ShieldCheck className="h-4 w-4" />
                                <span>Decision Queue ({requests.length})</span>
                            </Link>
                        </div>
                    )}

                    {isAdmin && (
                        <Link to="/settings" className="btn-primary flex items-center gap-2 shadow-sm transition-transform hover:-translate-y-0.5">
                            <UserCheck className="h-4 w-4" />
                            <span>Manage Users & Accounts</span>
                        </Link>
                    )}
                </div>
            </div>

            {/* Compact 5-Step Pipeline Sequence */}
            <div className="rounded-xl border border-[#E3E8F0] bg-white p-3.5 shadow-card animate-fade-in-up-delay-1">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2.5">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-[#697386]">
                        Automated Evidence Intelligence Pipeline
                    </p>
                    <span className="text-[10px] text-[#0F9D8A] font-semibold flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#0F9D8A] animate-pulse" /> Live Verification Engine
                    </span>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-5 text-xs">
                    {[
                        { step: '01', title: 'Upload & Parse', sub: 'PDF & Scans' },
                        { step: '02', title: 'OCR Extraction', sub: 'Universal Tesseract' },
                        { step: '03', title: 'Normalization', sub: 'Merchant & Values' },
                        { step: '04', title: 'Verification', sub: '4-Way Cross-Check' },
                        { step: '05', title: 'Governance', sub: 'Audit Signoff' },
                    ].map((stage) => (
                        <div key={stage.step} className="flex items-center gap-2 rounded-lg bg-[#F5F7FB] p-2 hover:bg-[#EEF2FF]/60 transition-colors">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#4F46E5]">
                                {stage.step}
                            </span>
                            <div className="min-w-0">
                                <p className="truncate text-xs font-bold text-[#20263A]">{stage.title}</p>
                                <p className="truncate text-[10px] text-[#697386]">{stage.sub}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Error notifications */}
            {error && (
                <div role="alert" className="flex items-center justify-between rounded-xl border border-red-200 bg-[#FEF2F2] p-3.5 text-xs text-[#DC4545]">
                    <span className="flex items-center gap-2 font-medium">
                        <AlertCircle className="h-4 w-4 shrink-0 text-[#DC4545]" />
                        {error}
                    </span>
                    <button className="flex items-center gap-1 font-bold underline" onClick={() => window.location.reload()}>
                        <RotateCcw className="h-3 w-3" /> Retry
                    </button>
                </div>
            )}

            {summaryError && (
                <div role="alert" className="rounded-xl border border-amber-200 bg-[#FFFBEB] p-3 text-xs text-amber-900 font-medium">
                    {summaryError}
                </div>
            )}

            {/* SUBMITTER WORKSPACE CONTENT */}
            {isSubmitter && (
                <div className="space-y-6">
                    {/* Action Required Alert (if any) */}
                    {submitterNeedsAction.length > 0 && (
                        <section className="card-warning">
                            <div className="flex items-center justify-between border-b border-amber-200/60 pb-2 mb-3">
                                <div className="flex items-center gap-2 font-bold text-amber-900">
                                    <AlertTriangle className="h-4 w-4 text-[#D97706]" />
                                    <span>Action Required ({submitterNeedsAction.length} {submitterNeedsAction.length === 1 ? 'claim' : 'claims'})</span>
                                </div>
                                <span className="text-[10px] text-amber-800">Reviewer feedback or document issue requires response</span>
                            </div>
                            <div className="divide-y divide-amber-200/50">
                                {submitterNeedsAction.map((claim) => (
                                    <div key={claim.id} className="flex flex-wrap items-center justify-between gap-3 py-2">
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2">
                                                <Link to={`/requests/${claim.id}`} className="font-mono text-xs font-bold text-[#20263A] hover:text-[#4F46E5]">
                                                    {claim.request_number}
                                                </Link>
                                                <span className={STATUS_META[claim.status]?.badge ?? 'badge-more-info'}>
                                                    {STATUS_META[claim.status]?.label ?? claim.status}
                                                </span>
                                            </div>
                                            <p className="truncate text-xs font-medium text-slate-700 mt-0.5">{claim.title}</p>
                                        </div>
                                        <Link
                                            to={`/requests/${claim.id}`}
                                            className="inline-flex items-center gap-1 text-xs font-bold text-amber-900 hover:underline"
                                        >
                                            <span>Resolve Claim</span>
                                            <ArrowRight className="h-3.5 w-3.5" />
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Compact Draft Claims in Progress */}
                    {submitterDrafts.length > 0 && (
                        <section className="card overflow-hidden">
                            <div className="flex items-center justify-between border-b border-[#E3E8F0] px-5 py-3.5 bg-slate-50/50">
                                <div className="flex items-center gap-2">
                                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#E6F7F5] text-[#0F9D8A]">
                                        <FileText className="h-4 w-4" />
                                    </span>
                                    <div>
                                        <h2 className="text-xs font-bold text-[#20263A]">
                                            Draft Claims in Progress ({submitterDrafts.length})
                                        </h2>
                                        <p className="text-[11px] text-[#697386]">
                                            Upload documents or complete details to submit.
                                        </p>
                                    </div>
                                </div>
                                <Link
                                    to="/new-request"
                                    className="text-xs font-semibold text-[#0F9D8A] hover:underline"
                                >
                                    + New draft
                                </Link>
                            </div>
                            <div className="divide-y divide-[#E3E8F0]">
                                {submitterDrafts.slice(0, 4).map((draft) => (
                                    <div key={draft.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 hover:bg-slate-50/60 transition">
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2">
                                                <Link to={`/requests/${draft.id}?step=2`} className="font-mono text-xs font-bold text-[#20263A] hover:text-[#0F9D8A]">
                                                    {draft.request_number}
                                                </Link>
                                                <span className="badge-draft text-[10px]">Draft</span>
                                            </div>
                                            <p className="truncate text-xs font-medium text-[#697386] mt-0.5">{draft.title}</p>
                                        </div>
                                        <div className="flex items-center gap-4 text-xs">
                                            <span className="font-bold text-[#20263A]">
                                                {draft.currency ?? '₹'}{draft.claimed_amount ?? '0.00'}
                                            </span>
                                            <Link
                                                to={`/requests/${draft.id}?step=2`}
                                                className="inline-flex items-center gap-1 text-xs font-bold text-[#0F9D8A] hover:underline"
                                            >
                                                <span>Resume Draft</span>
                                                <ArrowRight className="h-3 w-3" />
                                            </Link>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            {submitterDrafts.length > 4 && (
                                <div className="bg-slate-50/40 px-5 py-2 text-center border-t border-[#E3E8F0]">
                                    <Link to="/requests?status=draft" className="text-xs font-semibold text-[#0F9D8A] hover:underline">
                                        View all {submitterDrafts.length} drafts →
                                    </Link>
                                </div>
                            )}
                        </section>
                    )}

                    {/* Submitter KPI Cards */}
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 animate-fade-in-up-delay-2">
                        <Link to="/requests" className="card-interactive p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Total Portfolio</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#20263A]">{requests.length}</p>
                                </div>
                                <span className="rounded-lg bg-slate-100 p-2 text-slate-700">
                                    <FileText className="h-4 w-4" />
                                </span>
                            </div>
                            <div className="mt-3 flex items-center justify-between border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">
                                <span>All-time claims</span>
                                {totalSpend > 0 && <span className="font-bold text-[#20263A]">₹{totalSpend.toLocaleString()}</span>}
                            </div>
                        </Link>

                        <Link to="/requests?status=draft" className="card-interactive-amber p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Drafts in Progress</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#D97706]">{submitterDrafts.length}</p>
                                </div>
                                <span className="rounded-lg bg-[#FFFBEB] p-2 text-[#D97706]">
                                    <Clock3 className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Awaiting upload or submission</p>
                        </Link>

                        <Link to="/requests?status=under_review" className="card-interactive-indigo p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Under Review</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#4F46E5]">{submitterInProgress.length}</p>
                                </div>
                                <span className="rounded-lg bg-[#EEF2FF] p-2 text-[#4F46E5]">
                                    <ClipboardCheck className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Active extraction & reviewer audit</p>
                        </Link>

                        <Link to="/requests?status=approved" className="card-interactive-teal p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Approved Spend</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#0F9D8A]">{submitterApproved.length}</p>
                                </div>
                                <span className="rounded-lg bg-[#E6F7F5] p-2 text-[#0F9D8A]">
                                    <CheckCircle2 className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Authorized and finalized claims</p>
                        </Link>
                    </div>

                    {/* Submitter Claims Table & Workflow Guide */}
                    <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr] animate-fade-in-up-delay-3">
                        <section className="card min-w-0">
                            <div className="flex items-center justify-between border-b border-[#E3E8F0] px-5 py-3.5">
                                <div>
                                    <h2 className="text-sm font-bold text-[#20263A]">My Recent Claims</h2>
                                    <p className="text-xs text-[#697386]">Status and next steps for your reimbursement requests</p>
                                </div>
                                <Link to="/requests" className="text-xs font-bold text-[#0F9D8A] hover:underline transition-colors">
                                    View all ({requests.length}) →
                                </Link>
                            </div>

                            {loading ? (
                                <div className="space-y-3 p-5">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="h-11 animate-pulse rounded-lg bg-slate-100" />
                                    ))}
                                </div>
                            ) : requests.length === 0 ? (
                                <div className="px-6 py-12 text-center">
                                    <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                                        <FileText className="h-5 w-5" />
                                    </span>
                                    <h3 className="mt-3 text-sm font-bold text-[#20263A]">No claims yet</h3>
                                    <p className="mx-auto mt-1 max-w-xs text-xs text-[#68738A]">
                                        Create your first expense reimbursement claim to begin.
                                    </p>
                                    <Link to="/new-request" className="btn-teal mt-4 inline-flex items-center gap-1.5 text-xs">
                                        <FilePlus2 className="h-3.5 w-3.5" />
                                        <span>New Claim</span>
                                    </Link>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full min-w-[560px] text-left text-xs">
                                        <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-[#68738A]">
                                            <tr>
                                                <th className="px-5 py-3">Claim # & Title</th>
                                                <th className="px-4 py-3">Category</th>
                                                <th className="px-4 py-3">Amount</th>
                                                <th className="px-4 py-3">Status</th>
                                                <th className="px-4 py-3 text-right">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#E3E8F0]">
                                            {requests.slice(0, 5).map((req) => (
                                                <tr key={req.id} className="hover:bg-slate-50/70 transition-colors">
                                                    <td className="px-5 py-3">
                                                        <Link to={`/requests/${req.id}`} className="font-bold text-[#20263A] hover:text-[#0F9D8A]">
                                                            {req.request_number}
                                                        </Link>
                                                        <p className="mt-0.5 max-w-[180px] truncate text-[11px] text-[#697386]">{req.title}</p>
                                                    </td>
                                                    <td className="px-4 py-3 capitalize text-slate-600 font-medium">
                                                        {req.expense_category?.replace(/_/g, ' ') ?? 'Other'}
                                                    </td>
                                                    <td className="px-4 py-3 font-bold text-[#20263A]">
                                                        {req.claimed_amount == null
                                                            ? '—'
                                                            : `${req.currency ?? 'INR'} ${Number(req.claimed_amount).toLocaleString()}`}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={STATUS_META[req.status]?.badge ?? 'badge-draft'}>
                                                            {STATUS_META[req.status]?.label ?? req.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-right">
                                                        <Link
                                                            to={`/requests/${req.id}`}
                                                            className="inline-flex items-center gap-1 font-bold text-[#0F9D8A] hover:underline"
                                                        >
                                                            <span>Open</span>
                                                            <ArrowRight className="h-3 w-3" />
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>

                        <div className="space-y-6">
                            {/* Status Distribution */}
                            {summary && chartData.length > 0 && (
                                <section className="card p-5 space-y-3.5">
                                    <div className="border-b border-[#E3E8F0] pb-2.5">
                                        <h2 className="text-sm font-bold text-[#20263A]">Status Distribution</h2>
                                        <p className="text-xs text-[#697386]">Live breakdown across your portfolio</p>
                                    </div>
                                    <Suspense fallback={<div className="h-[180px] animate-pulse bg-slate-50" />}>
                                        <StatusDonut data={chartData} total={summary.total_requests} />
                                    </Suspense>
                                </section>
                            )}

                            {/* Submitter Quick Guide Card */}
                            <section className="card p-5 space-y-3.5">
                                <h2 className="text-sm font-bold text-[#20263A]">How Reimbursement Works</h2>
                                <ol className="space-y-2.5 text-xs text-[#697386]">
                                    <li className="flex items-start gap-2">
                                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#E6F7F5] font-bold text-[#0F9D8A] text-[10px]">
                                            1
                                        </span>
                                        <span>
                                            <strong className="text-[#20263A]">Create draft:</strong> Enter basic expense info and select your reviewer.
                                        </span>
                                    </li>
                                    <li className="flex items-start gap-2">
                                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#E6F7F5] font-bold text-[#0F9D8A] text-[10px]">
                                            2
                                        </span>
                                        <span>
                                            <strong className="text-[#20263A]">Upload documents:</strong> Provide your signed expense form and receipt.
                                        </span>
                                    </li>
                                    <li className="flex items-start gap-2">
                                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#E6F7F5] font-bold text-[#0F9D8A] text-[10px]">
                                            3
                                        </span>
                                        <span>
                                            <strong className="text-[#20263A]">Automatic OCR:</strong> The system extracts merchant, date, amount, and reference.
                                        </span>
                                    </li>
                                    <li className="flex items-start gap-2">
                                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#E6F7F5] font-bold text-[#0F9D8A] text-[10px]">
                                            4
                                        </span>
                                        <span>
                                            <strong className="text-[#20263A]">Submit:</strong> Confirm extracted values match and send for review.
                                        </span>
                                    </li>
                                </ol>
                                <div className="rounded-lg border border-[#99E1D7] bg-[#E6F7F5]/50 p-2.5 text-[11px] text-[#0B6D5F] font-medium">
                                    💡 Need help with a claim? Use the <strong>AI Assistant</strong> to ask questions about your documents and checks.
                                </div>
                            </section>
                        </div>
                    </div>
                </div>
            )}

            {/* REVIEWER WORKSPACE CONTENT */}
            {isReviewer && (
                <div className="space-y-6">
                    {/* Assigned drafts advance notice */}
                    {assignedDrafts.length > 0 && (
                        <div className="rounded-xl border border-[#C7D2FE] bg-[#EEF2FF]/40 p-4 shadow-card">
                            <div className="flex items-start gap-3">
                                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#EEF2FF] text-[#4F46E5]">
                                    <Clock3 className="h-4 w-4" />
                                </span>
                                <div className="flex-1">
                                    <h2 className="text-xs font-bold text-[#20263A]">
                                        Upcoming Claims Assigned to You ({assignedDrafts.length})
                                    </h2>
                                    <p className="text-[11px] text-[#697386]">
                                        Submitters are preparing these draft claims. They will enter your review queue once submitted.
                                    </p>
                                    <ul className="mt-2.5 divide-y divide-[#E3E8F0] rounded-lg border border-[#E3E8F0] bg-white">
                                        {assignedDrafts.map((d) => (
                                            <li key={d.id} className="flex items-center justify-between p-2.5 text-xs">
                                                <span>
                                                    <strong className="text-[#20263A]">{d.request_number}</strong> — {d.title} ({d.submitter_name ?? 'Submitter'})
                                                </span>
                                                <Link to={`/requests/${d.id}`} className="font-bold text-[#4F46E5] hover:underline">
                                                    Inspect draft →
                                                </Link>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Reviewer Metrics */}
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 animate-fade-in-up-delay-2">
                        <Link to="/review-queue" className="card-interactive-indigo p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Awaiting Your Review</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#4F46E5]">{requests.length}</p>
                                </div>
                                <span className="rounded-lg bg-[#EEF2FF] p-2 text-[#4F46E5]">
                                    <ClipboardCheck className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Claims currently assigned to you</p>
                        </Link>

                        <div className="card-interactive-amber p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Open Rule Flags</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#D97706]">
                                        {summary?.common_check_issues.reduce((sum, i) => sum + i.count, 0) ?? 0}
                                    </p>
                                </div>
                                <span className="rounded-lg bg-[#FFFBEB] p-2 text-[#D97706]">
                                    <ShieldAlert className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Automated mismatch or missing signals</p>
                        </div>

                        <Link to="/requests?status=draft" className="card-interactive p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Upcoming Drafts</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#20263A]">{assignedDrafts.length}</p>
                                </div>
                                <span className="rounded-lg bg-slate-100 p-2 text-slate-600">
                                    <Clock3 className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Assigned drafts awaiting submission</p>
                        </Link>

                        <div className="card-interactive p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Workspace Total</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#20263A]">
                                        {summary?.total_requests ?? requests.length}
                                    </p>
                                </div>
                                <span className="rounded-lg bg-slate-100 p-2 text-slate-600">
                                    <FileText className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E2E6EF] pt-2 text-[11px] text-[#68738A]">Claims across the organization</p>
                        </div>
                    </div>

                    {/* Review Queue Table */}
                    <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr] animate-fade-in-up-delay-3">
                        <section className="card min-w-0">
                            <div className="flex items-center justify-between border-b border-[#E3E8F0] px-5 py-3.5">
                                <div>
                                    <h2 className="text-sm font-bold text-[#20263A]">Assigned Claims To Review</h2>
                                    <p className="text-xs text-[#697386]">Directly assigned to you for verification</p>
                                </div>
                                <Link to="/review-queue" className="text-xs font-bold text-[#4F46E5] hover:underline transition-colors">
                                    Open queue ({requests.length}) →
                                </Link>
                            </div>

                            {loading ? (
                                <div className="space-y-3 p-5">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="h-11 animate-pulse rounded-lg bg-slate-100" />
                                    ))}
                                </div>
                            ) : requests.length === 0 ? (
                                <div className="px-6 py-12 text-center">
                                    <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-[#E6F7F5] text-[#0F9D8A]">
                                        <CheckCircle2 className="h-5 w-5" />
                                    </span>
                                    <h3 className="mt-3 text-sm font-bold text-[#20263A]">All caught up</h3>
                                    <p className="mx-auto mt-1 max-w-xs text-xs text-[#697386]">
                                        No claims are currently waiting in your review queue.
                                    </p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full min-w-[580px] text-left text-xs">
                                        <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-[#697386]">
                                            <tr>
                                                <th className="px-5 py-3">Claim # & Title</th>
                                                <th className="px-4 py-3">Submitter</th>
                                                <th className="px-4 py-3">Amount</th>
                                                <th className="px-4 py-3">Status</th>
                                                <th className="px-4 py-3 text-right">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#E3E8F0]">
                                            {requests.slice(0, 5).map((req) => (
                                                <tr key={req.id} className="hover:bg-slate-50/70 transition-colors">
                                                    <td className="px-5 py-3">
                                                        <Link to={`/requests/${req.id}`} className="font-bold text-[#20263A] hover:text-[#4F46E5]">
                                                            {req.request_number}
                                                        </Link>
                                                        <p className="mt-0.5 max-w-[180px] truncate text-[11px] text-[#697386]">{req.title}</p>
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-600 font-medium">
                                                        {req.submitter_name ?? '—'}
                                                    </td>
                                                    <td className="px-4 py-3 font-bold text-[#20263A]">
                                                        {req.claimed_amount == null
                                                            ? '—'
                                                            : `${req.currency ?? 'INR'} ${Number(req.claimed_amount).toLocaleString()}`}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={STATUS_META[req.status]?.badge ?? 'badge-draft'}>
                                                            {STATUS_META[req.status]?.label ?? req.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-right">
                                                        <Link
                                                            to={`/requests/${req.id}`}
                                                            className="inline-flex items-center gap-1 font-bold text-[#4F46E5] hover:underline"
                                                        >
                                                            <span>Review</span>
                                                            <ArrowRight className="h-3 w-3" />
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>

                        <div className="space-y-6">
                            {/* Queue Distribution */}
                            {summary && chartData.length > 0 && (
                                <section className="card p-5 space-y-3.5">
                                    <div className="border-b border-[#E3E8F0] pb-2.5">
                                        <h2 className="text-sm font-bold text-[#20263A]">Queue Distribution</h2>
                                        <p className="text-xs text-[#697386]">Live breakdown across active claims</p>
                                    </div>
                                    <Suspense fallback={<div className="h-[180px] animate-pulse bg-slate-50" />}>
                                        <StatusDonut data={chartData} total={summary.total_requests} />
                                    </Suspense>
                                </section>
                            )}

                            {/* Open Verification Flags */}
                            <section className="card p-5 space-y-3.5">
                                <div className="border-b border-[#E3E8F0] pb-3">
                                    <h2 className="text-sm font-bold text-[#20263A]">Active Verification Signals</h2>
                                    <p className="text-xs text-[#697386]">Flags requiring reviewer verification</p>
                                </div>
                                {summary?.common_check_issues && summary.common_check_issues.length > 0 ? (
                                    <ul className="divide-y divide-[#E3E8F0]">
                                        {summary.common_check_issues.map((issue) => (
                                            <li key={issue.check_type} className="flex items-center justify-between py-2 text-xs">
                                                <span className="flex items-center gap-2 capitalize text-slate-700 font-medium">
                                                    <span className="flex h-5 w-5 items-center justify-center rounded-md bg-[#FFFBEB] text-[#D97706]">
                                                        <AlertCircle className="h-3.5 w-3.5" />
                                                    </span>
                                                    {issue.check_type.replace(/_/g, ' ')}
                                                </span>
                                                <span className="rounded-md bg-slate-100 px-2 py-0.5 font-bold text-[#20263A]">
                                                    {issue.count}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="text-xs text-[#697386]">No active verification issues detected.</p>
                                )}
                                <div className="rounded-lg border border-[#C7D2FE] bg-[#EEF2FF]/50 p-2.5 text-[11px] text-[#312E81] font-medium leading-relaxed">
                                    ℹ️ Flags are evidence signals. Open any request to view OCR overlays, inspect bounding boxes, or record authorized corrections with required reasons.
                                </div>
                            </section>
                        </div>
                    </div>
                </div>
            )}

            {/* APPROVER WORKSPACE CONTENT */}
            {isApprover && (
                <div className="space-y-6">
                    {/* Approver Metrics */}
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 animate-fade-in-up-delay-2">
                        <Link to="/review-queue" className="card-interactive-violet p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Awaiting Your Decision</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#8B5CF6]">{requests.length}</p>
                                </div>
                                <span className="rounded-lg bg-[#F5F3FF] p-2 text-[#8B5CF6]">
                                    <ShieldCheck className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Reviewed and pending final sign-off</p>
                        </Link>

                        <div className="card-interactive-teal p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Approved Claims</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#0F9D8A]">
                                        {summary?.by_status.approved ?? 0}
                                    </p>
                                </div>
                                <span className="rounded-lg bg-[#E6F7F5] p-2 text-[#0F9D8A]">
                                    <CheckCircle2 className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Claims approved across workspace</p>
                        </div>

                        <div className="card-interactive p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Rejected Claims</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#DC4545]">
                                        {summary?.by_status.rejected ?? 0}
                                    </p>
                                </div>
                                <span className="rounded-lg bg-[#FEF2F2] p-2 text-[#DC4545]">
                                    <XCircle className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Rejected with documented reasoning</p>
                        </div>

                        <div className="card-interactive p-4 sm:p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wider text-[#697386]">Total In Workspace</p>
                                    <p className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-[#20263A]">
                                        {summary?.total_requests ?? 0}
                                    </p>
                                </div>
                                <span className="rounded-lg bg-slate-100 p-2 text-slate-600">
                                    <FileText className="h-4 w-4" />
                                </span>
                            </div>
                            <p className="mt-3 border-t border-[#E3E8F0] pt-2 text-[11px] text-[#697386]">Full claim volume</p>
                        </div>
                    </div>

                    {/* Approver Decision Queue & Status Distribution */}
                    <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr] animate-fade-in-up-delay-3">
                        <section className="card min-w-0">
                            <div className="flex items-center justify-between border-b border-[#E3E8F0] px-5 py-3.5">
                                <div>
                                    <h2 className="text-sm font-bold text-[#20263A]">Claims Awaiting Executive Decision</h2>
                                    <p className="text-xs text-[#697386]">Verification complete — review findings and approve or reject</p>
                                </div>
                                <Link to="/review-queue" className="text-xs font-bold text-[#8B5CF6] hover:underline transition-colors">
                                    Open queue ({requests.length}) →
                                </Link>
                            </div>

                            {loading ? (
                                <div className="space-y-3 p-5">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="h-11 animate-pulse rounded-lg bg-slate-100" />
                                    ))}
                                </div>
                            ) : requests.length === 0 ? (
                                <div className="px-6 py-12 text-center">
                                    <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-[#E6F7F5] text-[#0F9D8A]">
                                        <CheckCircle2 className="h-5 w-5" />
                                    </span>
                                    <h3 className="mt-3 text-sm font-bold text-[#20263A]">No decisions pending</h3>
                                    <p className="mx-auto mt-1 max-w-xs text-xs text-[#697386]">
                                        All reviewed claims have been processed.
                                    </p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full min-w-[580px] text-left text-xs">
                                        <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-[#697386]">
                                            <tr>
                                                <th className="px-5 py-3">Claim # & Title</th>
                                                <th className="px-4 py-3">Submitter</th>
                                                <th className="px-4 py-3">Amount</th>
                                                <th className="px-4 py-3">Review State</th>
                                                <th className="px-4 py-3 text-right">Decision</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#E3E8F0]">
                                            {requests.slice(0, 5).map((req) => (
                                                <tr key={req.id} className="hover:bg-slate-50/70 transition-colors">
                                                    <td className="px-5 py-3">
                                                        <Link to={`/requests/${req.id}`} className="font-bold text-[#20263A] hover:text-[#8B5CF6]">
                                                            {req.request_number}
                                                        </Link>
                                                        <p className="mt-0.5 max-w-[180px] truncate text-[11px] text-[#697386]">{req.title}</p>
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-600 font-medium">
                                                        {req.submitter_name ?? '—'}
                                                    </td>
                                                    <td className="px-4 py-3 font-bold text-[#20263A]">
                                                        {req.claimed_amount == null
                                                            ? '—'
                                                            : `${req.currency ?? 'INR'} ${Number(req.claimed_amount).toLocaleString()}`}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className="badge-review">
                                                            Review complete
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-right">
                                                        <Link
                                                            to={`/requests/${req.id}`}
                                                            className="inline-flex items-center gap-1 font-bold text-[#8B5CF6] hover:underline"
                                                        >
                                                            <span>Inspect & Decide</span>
                                                            <ArrowRight className="h-3 w-3" />
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>

                        {/* Status Donut & Compliance */}
                        <section className="card p-5 space-y-3.5">
                            <div className="border-b border-[#E3E8F0] pb-3">
                                <h2 className="text-sm font-bold text-[#20263A]">Status Distribution</h2>
                                <p className="text-xs text-[#697386]">Live breakdown across all claims</p>
                            </div>
                            {!summary || chartData.length === 0 ? (
                                <div className="grid h-[200px] place-items-center text-xs text-[#697386]">
                                    Claim distribution will appear when claims are loaded.
                                </div>
                            ) : (
                                <Suspense fallback={<div className="h-[200px] animate-pulse bg-slate-50" />}>
                                    <StatusDonut data={chartData} total={summary.total_requests} />
                                </Suspense>
                            )}
                            <div className="border-t border-[#E3E8F0] pt-3">
                                <Link
                                    to="/audit"
                                    className="flex items-center justify-between rounded-lg border border-[#DDD6FE] bg-[#F5F3FF]/50 p-2.5 text-xs font-bold text-[#6D28D9] hover:bg-[#F5F3FF] transition-colors"
                                >
                                    <span className="flex items-center gap-2">
                                        <History className="h-4 w-4 text-[#8B5CF6]" />
                                        <span>Inspect Immutable Audit Trail</span>
                                    </span>
                                    <ArrowRight className="h-3.5 w-3.5 text-[#8B5CF6]" />
                                </Link>
                            </div>
                        </section>
                    </div>
                </div>
            )}

            {/* Health footer */}
            {health && (
                <div className="flex items-center justify-between text-[11px] text-[#697386] pt-2 border-t border-[#E3E8F0]">
                    <span className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-[#0F9D8A]" />
                        Backend {health.status === 'ok' ? 'operational' : 'degraded'} · OCR: {health.features.ocr_engine}
                    </span>
                    <span>DocuVerify AI · Certified Role Governance</span>
                </div>
            )}
        </div>
    );
}
