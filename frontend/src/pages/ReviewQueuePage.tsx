import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    ArrowRight,
    CheckCircle2,
    ClipboardCheck,
    Search,
    ShieldCheck,
    SlidersHorizontal,
    UserRoundCheck,
    Clock,
    Layers,
    AlertCircle,
    Coins,
    RefreshCw,
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { RequestSummary } from '../types';

const statusStyle: Record<string, string> = {
    under_review: 'badge-review',
    pending_approval: 'badge-review',
    more_info_required: 'badge-more-info',
    processing: 'badge-processing',
};

export default function ReviewQueuePage() {
    const [queue, setQueue] = useState<RequestSummary[]>([]);
    const [assignedDrafts, setAssignedDrafts] = useState<RequestSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [draftsError, setDraftsError] = useState<string | null>(null);
    const [query, setQuery] = useState('');
    const { user } = useAuth();

    const isApprover = user?.role === 'approver';

    const fetchQueue = async () => {
        setLoading(true);
        setError(null);
        setDraftsError(null);
        try {
            const draftsRequest =
                user?.role === 'reviewer'
                    ? api.get<RequestSummary[]>('/requests?status=draft')
                    : Promise.resolve({ data: [] as RequestSummary[] });

            const [queueResult, draftsResult] = await Promise.allSettled([
                api.get<RequestSummary[]>('/requests/review-queue'),
                draftsRequest,
            ]);

            if (queueResult.status === 'fulfilled') {
                setQueue(queueResult.value.data);
            } else {
                const failure = queueResult.reason as { response?: { data?: { detail?: string } } };
                setError(failure?.response?.data?.detail ?? 'Could not load the queue. Check your role authorization and connection.');
            }
            if (draftsResult.status === 'fulfilled') {
                setAssignedDrafts(draftsResult.value.data);
            } else {
                const failure = draftsResult.reason as { response?: { data?: { detail?: string } } };
                setDraftsError(failure?.response?.data?.detail ?? 'Could not check for assigned drafts.');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user) {
            void fetchQueue();
        }
    }, [user?.id, user?.role]);

    const filtered = useMemo(
        () =>
            queue.filter((request) =>
                `${request.request_number} ${request.title} ${request.submitter_name ?? ''} ${request.expense_category}`
                    .toLowerCase()
                    .includes(query.toLowerCase())
            ),
        [queue, query]
    );

    const totalClaimedValue = useMemo(() => {
        return queue.reduce((sum, r) => sum + Number(r.claimed_amount || 0), 0);
    }, [queue]);

    const activeReviewCount = useMemo(() => {
        return queue.filter((r) => r.status === 'under_review' || r.status === 'pending_approval').length;
    }, [queue]);

    const moreInfoCount = useMemo(() => {
        return queue.filter((r) => r.status === 'more_info_required').length;
    }, [queue]);

    const theme = isApprover
        ? {
              pill: 'text-[#7656D6] bg-violet-50 border-violet-200',
              icon: ShieldCheck,
              title: 'Decision Center',
              heading: 'Decision Queue',
              subtitle: 'Make informed decisions using verified evidence and review findings.',
              actionLabel: 'Inspect & Decide',
              actionColor: 'text-[#7656D6] hover:text-[#6845C9]',
              borderFocus: 'focus:border-[#7656D6]',
              cardHover: 'hover:border-violet-200',
              interactiveCard: 'card-interactive-violet',
              accentBg: 'bg-violet-50 text-[#7656D6] ring-violet-200/50',
          }
        : {
              pill: 'text-[#3478F6] bg-blue-50 border-blue-200',
              icon: ClipboardCheck,
              title: 'Verification Center',
              heading: 'Review Queue',
              subtitle: 'Check documents, investigate mismatches, and record your findings.',
              actionLabel: 'Review Evidence',
              actionColor: 'text-[#3478F6] hover:text-[#2563EB]',
              borderFocus: 'focus:border-[#3478F6]',
              cardHover: 'hover:border-blue-200',
              interactiveCard: 'card-interactive-blue',
              accentBg: 'bg-blue-50 text-[#3478F6] ring-blue-200/50',
          };

    return (
        <div className="page-wrap space-y-7">
            <header className="animate-fade-in-up flex flex-wrap items-end justify-between gap-4">
                <div>
                    <p className={`mb-2 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[.15em] shadow-xs ${theme.pill}`}>
                        <theme.icon className="h-3.5 w-3.5" />
                        {theme.title}
                    </p>
                    <h1 className="text-2xl font-bold tracking-tight text-main sm:text-3xl">{theme.heading}</h1>
                    <p className="mt-1 text-sm text-muted">{theme.subtitle}</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={fetchQueue}
                        disabled={loading}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-surface-border bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-xs hover:bg-slate-50 transition active:scale-95 disabled:opacity-50"
                        title="Refresh queue items"
                    >
                        <RefreshCw className={`h-3.5 w-3.5 text-indigo-600 ${loading ? 'animate-spin' : ''}`} />
                        <span>Refresh</span>
                    </button>
                    <div className="flex items-center gap-2.5 rounded-xl border border-surface-border bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-xs">
                        <UserRoundCheck className="h-4 w-4 text-indigo-600" />
                        <span>
                            {loading
                                ? 'Loading queue…'
                                : error
                                  ? 'Queue unavailable'
                                  : `${queue.length} ${queue.length === 1 ? 'request' : 'requests'} awaiting action`}
                        </span>
                    </div>
                </div>
            </header>

            {/* Queue Metrics Summary Cards with Lift on Hover */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-fade-in-up-delay-100">
                <article className={`${theme.interactiveCard} p-5`}>
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Awaiting Action</p>
                        <span className={`rounded-lg p-2 ring-1 ${theme.accentBg}`}>
                            <Layers className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-main">
                        {loading ? '—' : queue.length}
                    </p>
                    <p className="mt-2 text-[11px] text-muted">Total claims in your action queue</p>
                </article>

                <article className="card-interactive-teal p-5">
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Under Review</p>
                        <span className="rounded-lg bg-teal-50 p-2 text-[#0F9D8A] ring-1 ring-teal-200/50">
                            <Clock className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-[#0F9D8A]">
                        {loading ? '—' : activeReviewCount}
                    </p>
                    <p className="mt-2 text-[11px] text-muted">Ready for human audit &amp; checks</p>
                </article>

                <article className="card-interactive-amber p-5">
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Needs Attention</p>
                        <span className="rounded-lg bg-amber-50 p-2 text-[#D97706] ring-1 ring-amber-200/50">
                            <AlertCircle className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-[#D97706]">
                        {loading ? '—' : moreInfoCount}
                    </p>
                    <p className="mt-2 text-[11px] text-muted">Awaiting submitter info/clarification</p>
                </article>

                <article className="card-interactive p-5">
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Total Queue Value</p>
                        <span className="rounded-lg bg-slate-100 p-2 text-slate-700 ring-1 ring-slate-200">
                            <Coins className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-2xl font-extrabold tracking-tight text-main">
                        {loading ? '—' : `₹${Math.round(totalClaimedValue).toLocaleString()}`}
                    </p>
                    <p className="mt-2 text-[11px] text-muted">Cumulative claimed reimbursement</p>
                </article>
            </div>

            {error && (
                <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700">
                    {error} <button className="ml-2 font-bold underline" onClick={() => window.location.reload()}>Retry</button>
                </div>
            )}

            {draftsError && (
                <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
                    {draftsError}
                </div>
            )}

            {!isApprover && assignedDrafts.length > 0 && (
                <section className="rounded-2xl border border-indigo-200 bg-indigo-50/60 p-5 shadow-xs">
                    <div className="flex items-center gap-2 mb-1">
                        <Clock className="h-4 w-4 text-indigo-700" />
                        <h2 className="text-xs font-bold text-indigo-950">Assigned claims not submitted yet ({assignedDrafts.length})</h2>
                    </div>
                    <p className="text-xs leading-relaxed text-indigo-900 font-medium">
                        Draft claims remain with the submitter until they finish required details and submit them for review.
                    </p>
                    <ul className="mt-3.5 space-y-2">
                        {assignedDrafts.map((draft) => (
                            <li
                                key={draft.id}
                                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-200/80 bg-white/90 px-4 py-2.5 text-xs shadow-2xs"
                            >
                                <span>
                                    <strong className="text-main">{draft.request_number}</strong> · {draft.title}{' '}
                                    <span className="ml-1.5 rounded-md bg-slate-100 px-2 py-0.5 text-[9px] font-bold text-slate-600">
                                        Draft
                                    </span>
                                </span>
                                <Link className="font-bold text-indigo-700 hover:underline" to={`/requests/${draft.id}`}>
                                    View draft <ArrowRight className="ml-1 inline h-3 w-3" />
                                </Link>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <section className="card overflow-hidden animate-fade-in-up-delay-200">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border px-6 py-4">
                    <div>
                        <h2 className="text-sm font-bold text-main">{isApprover ? 'Awaiting Final Executive Decision' : 'Awaiting Review & Verification'}</h2>
                        <p className="mt-0.5 text-xs text-muted">Filtered strictly by your assigned role permissions.</p>
                    </div>
                    <label className="relative w-full sm:w-64">
                        <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                        <input
                            className={`form-input py-2 pl-9 text-xs ${theme.borderFocus}`}
                            type="search"
                            placeholder="Search request or submitter"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                        />
                    </label>
                </div>

                {loading ? (
                    <div className="space-y-3 p-6">
                        {[0, 1, 2].map((row) => (
                            <div key={row} className="h-14 animate-pulse rounded-xl bg-slate-100" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-700">
                            <CheckCircle2 className="h-6 w-6" />
                        </span>
                        <h3 className="mt-4 text-sm font-bold text-main">
                            {queue.length ? 'No matches found' : "You're all caught up"}
                        </h3>
                        <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-muted">
                            {queue.length
                                ? 'Try adjusting your search criteria.'
                                : isApprover
                                  ? 'No claims are currently pending executive approval.'
                                  : 'No requests currently require your review.'}
                        </p>
                        {query && (
                            <button
                                className="mt-3 text-xs font-bold text-indigo-700 hover:underline"
                                onClick={() => setQuery('')}
                            >
                                Clear search
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[760px] text-left text-xs">
                            <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-muted">
                                <tr>
                                    <th className="px-6 py-3.5">Claim # & Title</th>
                                    <th className="px-4 py-3.5">{isApprover ? 'Claimant' : 'Submitter'}</th>
                                    <th className="px-4 py-3.5">Category</th>
                                    <th className="px-4 py-3.5">{isApprover ? 'Reimbursement Payout' : 'Claimed Amount'}</th>
                                    <th className="px-4 py-3.5">Submitted</th>
                                    <th className="px-4 py-3.5">{isApprover ? 'Review Verdict' : 'Status'}</th>
                                    <th className="px-6 py-3.5 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-border">
                                {filtered.map((request) => (
                                    <tr key={request.id} className="hover:bg-slate-50/80 transition-colors">
                                        <td className="px-6 py-4">
                                            <Link
                                                to={`/requests/${request.id}`}
                                                className={`font-bold text-main ${isApprover ? 'hover:text-[#8B5CF6]' : 'hover:text-indigo-700'}`}
                                            >
                                                {request.request_number}
                                            </Link>
                                            <p className="mt-0.5 max-w-[200px] truncate text-[11px] text-muted">
                                                {request.title}
                                            </p>
                                        </td>
                                        <td className="px-4 py-4 text-slate-600 font-medium">{request.submitter_name ?? '—'}</td>
                                        <td className="px-4 py-4 capitalize text-slate-600 font-medium">
                                            {request.expense_category?.replace(/_/g, ' ') ?? 'Other'}
                                        </td>
                                        <td className="px-4 py-4 font-bold text-main">
                                            {request.claimed_amount == null
                                                ? '—'
                                                : `${request.currency ?? 'INR'} ${Number(request.claimed_amount).toLocaleString()}`}
                                        </td>
                                        <td className="px-4 py-4 text-muted font-medium">
                                            {request.submitted_at
                                                ? new Date(request.submitted_at).toLocaleDateString()
                                                : new Date(request.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-4 py-4">
                                            {isApprover && request.status === 'pending_approval' ? (
                                                <span className="badge-review flex items-center gap-1 w-fit">
                                                    <CheckCircle2 className="h-3 w-3 text-violet-600" />
                                                    <span>Verified by Reviewer</span>
                                                </span>
                                            ) : (
                                                <span className={statusStyle[request.status] ?? 'badge-draft'}>
                                                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                    {request.status.replace(/_/g, ' ')}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <Link
                                                className={`inline-flex items-center gap-1 font-bold text-xs ${theme.actionColor}`}
                                                to={`/requests/${request.id}`}
                                            >
                                                <span>{theme.actionLabel}</span>
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

            <div className="flex items-start gap-3 rounded-2xl border border-indigo-200/70 bg-indigo-50/50 p-4 text-xs text-indigo-950 font-medium shadow-xs">
                <SlidersHorizontal className="mt-0.5 h-4 w-4 shrink-0 text-indigo-700" />
                <p className="leading-relaxed">
                    Verification flags are automated signals to aid human review. Inspect original documents, extracted values,
                    bounding box coordinates, and historical audit entries before taking an action.
                </p>
            </div>
        </div>
    );
}
