import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, FilePlus2, FileText, Search, SlidersHorizontal, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import api from '../services/api';
import type { RequestStatus, RequestSummary } from '../types';

const badge: Record<RequestStatus, string> = {
    draft: 'badge-draft',
    submitted: 'badge-submitted',
    processing: 'badge-processing',
    under_review: 'badge-review',
    pending_approval: 'badge-review',
    more_info_required: 'badge-more-info',
    approved: 'badge-approved',
    rejected: 'badge-rejected',
    processing_failed: 'badge-failed',
};

const filterTabs: Array<{ id: string; label: string }> = [
    { id: 'all', label: 'All Claims' },
    { id: 'draft', label: 'Drafts' },
    { id: 'processing', label: 'Processing' },
    { id: 'under_review', label: 'Under Review' },
    { id: 'more_info_required', label: 'Needs Info' },
    { id: 'approved', label: 'Approved' },
    { id: 'rejected', label: 'Rejected' },
];

export default function MyRequestsPage() {
    const [requests, setRequests] = useState<RequestSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [query, setQuery] = useState('');
    const [status, setStatus] = useState('all');

    useEffect(() => {
        api.get<RequestSummary[]>('/requests')
            .then((response) => setRequests(response.data))
            .catch(() => setError('Could not load your requests. Check the connection and try again.'))
            .finally(() => setLoading(false));
    }, []);

    const filtered = useMemo(
        () =>
            requests.filter(
                (request) =>
                    (status === 'all' || request.status === status) &&
                    `${request.request_number} ${request.title} ${request.expense_category}`
                        .toLowerCase()
                        .includes(query.toLowerCase())
            ),
        [requests, status, query]
    );

    const count = (value: string) =>
        value === 'all' ? requests.length : requests.filter((request) => request.status === value).length;

    const inProgressCount = useMemo(
        () => requests.filter((r) => ['submitted', 'processing', 'under_review', 'pending_approval'].includes(r.status)).length,
        [requests]
    );

    const needsAttentionCount = useMemo(
        () => requests.filter((r) => ['more_info_required', 'processing_failed'].includes(r.status)).length,
        [requests]
    );

    const approvedCount = useMemo(
        () => requests.filter((r) => r.status === 'approved').length,
        [requests]
    );

    return (
        <div className="page-wrap space-y-7">
            {/* Header */}
            <header className="flex flex-wrap items-end justify-between gap-4 animate-fade-in-up">
                <div>
                    <p className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.15em] text-teal-700 shadow-xs">
                        <FileText className="h-3.5 w-3.5" />
                        Submitter Workspace
                    </p>
                    <h1 className="text-2xl font-bold tracking-tight text-main sm:text-3xl">My Expense Claims</h1>
                    <p className="mt-1 text-sm text-muted">
                        Review claim progress, uploaded verification evidence, and required actions.
                    </p>
                </div>
                <Link to="/new-request" className="btn-teal flex items-center gap-2 shadow-sm transition-transform hover:-translate-y-0.5">
                    <FilePlus2 className="h-4 w-4" />
                    <span>New Expense Claim</span>
                </Link>
            </header>

            {/* Quick KPI stats with Interactive Lift & Click-to-Filter */}
            <div className="grid gap-4 sm:grid-cols-4 animate-fade-in-up-delay-1">
                <button
                    type="button"
                    onClick={() => setStatus('all')}
                    className="card-interactive-teal p-5 text-left"
                >
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Total Claims</p>
                        <span className="rounded-lg bg-teal-50 p-2 text-teal-700 ring-1 ring-teal-200/50">
                            <FileText className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-main">{loading ? '—' : requests.length}</p>
                    <p className="mt-2 text-[11px] text-muted font-medium">Claims in your submitter account</p>
                </button>

                <button
                    type="button"
                    onClick={() => setStatus('under_review')}
                    className="card-interactive-indigo p-5 text-left"
                >
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">In Progress</p>
                        <span className="rounded-lg bg-indigo-50 p-2 text-indigo-700 ring-1 ring-indigo-200/50">
                            <Clock className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-indigo-600">
                        {loading ? '—' : inProgressCount}
                    </p>
                    <p className="mt-2 text-[11px] text-muted font-medium">Under OCR or human review</p>
                </button>

                <button
                    type="button"
                    onClick={() => setStatus('more_info_required')}
                    className="card-interactive-amber p-5 text-left"
                >
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Needs Attention</p>
                        <span className="rounded-lg bg-amber-50 p-2 text-amber-800 ring-1 ring-amber-200/50">
                            <AlertTriangle className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-amber-700">
                        {loading ? '—' : needsAttentionCount}
                    </p>
                    <p className="mt-2 text-[11px] text-muted font-medium">Corrections or info requested</p>
                </button>

                <button
                    type="button"
                    onClick={() => setStatus('approved')}
                    className="card-interactive-teal p-5 text-left"
                >
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Approved</p>
                        <span className="rounded-lg bg-teal-50 p-2 text-teal-700 ring-1 ring-teal-200/50">
                            <CheckCircle2 className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-teal-600">
                        {loading ? '—' : approvedCount}
                    </p>
                    <p className="mt-2 text-[11px] text-muted font-medium">Ready for reimbursement</p>
                </button>
            </div>

            {error && (
                <div role="alert" className="rounded-xl border border-red-200 bg-[#FEF2F2] p-4 text-xs text-[#DC4545] font-semibold">
                    {error} <button className="ml-2 font-bold underline" onClick={() => window.location.reload()}>Retry</button>
                </div>
            )}

            {/* Claims Table Card */}
            <section className="card overflow-hidden">
                <div className="border-b border-surface-border p-4 sm:px-6">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <div>
                            <h2 className="text-sm font-bold text-main">Your Submitted Requests</h2>
                            <p className="mt-0.5 text-xs text-muted">
                                {filtered.length} {filtered.length === 1 ? 'claim' : 'claims'} shown · Live API records
                            </p>
                        </div>
                        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
                            <label className="relative min-w-[200px] flex-1 sm:flex-none">
                                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                                <input
                                    className="form-input py-2 pl-9 text-xs"
                                    type="search"
                                    placeholder="Search claims…"
                                    value={query}
                                    onChange={(event) => setQuery(event.target.value)}
                                />
                            </label>
                            <label className="relative">
                                <SlidersHorizontal className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                                <select
                                    className="form-input py-2 pl-9 pr-4 text-xs font-semibold"
                                    value={status}
                                    onChange={(event) => setStatus(event.target.value)}
                                >
                                    <option value="all">All statuses ({count('all')})</option>
                                    <option value="draft">Draft ({count('draft')})</option>
                                    <option value="processing">Processing ({count('processing')})</option>
                                    <option value="under_review">Under review ({count('under_review')})</option>
                                    <option value="more_info_required">Needs info ({count('more_info_required')})</option>
                                    <option value="approved">Approved ({count('approved')})</option>
                                    <option value="rejected">Rejected ({count('rejected')})</option>
                                </select>
                            </label>
                        </div>
                    </div>

                    {/* Filter Pills */}
                    <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-100">
                        {filterTabs.map((tab) => {
                            const active = status === tab.id;
                            const tabCount = count(tab.id);
                            return (
                                <button
                                    key={tab.id}
                                    type="button"
                                    onClick={() => setStatus(tab.id)}
                                    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-semibold transition ${
                                        active
                                            ? 'bg-teal-700 text-white shadow-xs'
                                            : 'bg-slate-100/80 text-slate-600 hover:bg-slate-200/70 hover:text-main'
                                    }`}
                                >
                                    <span>{tab.label}</span>
                                    <span
                                        className={`rounded-full px-1.5 py-0.2 text-[10px] font-bold ${
                                            active ? 'bg-teal-800 text-teal-100' : 'bg-slate-200 text-slate-700'
                                        }`}
                                    >
                                        {tabCount}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {loading ? (
                    <div className="space-y-3 p-6">
                        {[0, 1, 2].map((row) => (
                            <div key={row} className="h-14 animate-pulse rounded-xl bg-slate-100" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                            <FileText className="h-6 w-6" />
                        </span>
                        <h3 className="mt-4 text-sm font-bold text-main">
                            {requests.length ? 'No matching claims' : 'Nothing here yet'}
                        </h3>
                        <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-muted">
                            {requests.length
                                ? 'Adjust your search or filter to find a claim.'
                                : 'Your submitted expense claims will appear here.'}
                        </p>
                        {!requests.length && (
                            <Link className="btn-teal mt-4 inline-flex items-center gap-2" to="/new-request">
                                <FilePlus2 className="h-4 w-4" />
                                <span>Create Expense Claim</span>
                            </Link>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[780px] text-left text-xs">
                            <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-muted">
                                <tr>
                                    <th className="px-6 py-3.5">Request</th>
                                    <th className="px-4 py-3.5">Category</th>
                                    <th className="px-4 py-3.5">Amount</th>
                                    <th className="px-4 py-3.5">Expense date</th>
                                    <th className="px-4 py-3.5">Status</th>
                                    <th className="px-4 py-3.5">Last updated</th>
                                    <th className="px-6 py-3.5 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-border">
                                {filtered.map((request) => (
                                    <tr key={request.id} className="hover:bg-slate-50/80 transition-colors">
                                        <td className="px-6 py-4">
                                            <Link
                                                to={`/requests/${request.id}`}
                                                className="font-bold text-main hover:text-teal-700"
                                            >
                                                {request.request_number}
                                            </Link>
                                            <p className="mt-0.5 max-w-[200px] truncate text-[11px] text-muted">
                                                {request.title}
                                            </p>
                                        </td>
                                        <td className="px-4 py-4 capitalize text-slate-600 font-medium">
                                            {request.expense_category?.replace(/_/g, ' ') ?? 'Other'}
                                        </td>
                                        <td className="px-4 py-4 font-bold text-main">
                                            {request.claimed_amount == null
                                                 ? '—'
                                                 : `${request.currency ?? 'INR'} ${Number(request.claimed_amount).toLocaleString()}`}
                                        </td>
                                        <td className="px-4 py-4 text-muted font-medium">
                                            {request.expense_date
                                                ? new Date(request.expense_date).toLocaleDateString()
                                                : '—'}
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className={badge[request.status]}>
                                                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                {request.status.replace(/_/g, ' ')}
                                            </span>
                                        </td>
                                        <td className="px-4 py-4 text-muted font-medium">
                                            {new Date(request.updated_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <Link
                                                aria-label={`Open ${request.request_number}`}
                                                to={`/requests/${request.id}`}
                                                className="inline-flex items-center gap-1 font-bold text-teal-700 hover:underline"
                                            >
                                                <span>View</span>
                                                <ArrowRight className="h-3.5 w-3.5" />
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </div>
    );
}
