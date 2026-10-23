import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ClipboardCheck, Filter, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { AuditEntry } from '../types';

export default function AuditTrailPage() {
    const { user } = useAuth();
    const [events, setEvents] = useState<AuditEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState('');
    const [typeFilter, setTypeFilter] = useState('all');

    const isApprover = user?.role === 'approver';

    function fetchAudit() {
        setLoading(true);
        setError(null);
        api.get<AuditEntry[]>('/audit')
            .then((res) => {
                setEvents(res.data);
            })
            .catch((err) => {
                const status = (err as { response?: { status?: number } }).response?.status;
                if (status === 403) {
                    setError('Access restricted: Audit log access is reserved for approvers and administrators.');
                } else {
                    setError('Unable to load the compliance audit log. Please check your connection and retry.');
                }
            })
            .finally(() => setLoading(false));
    }

    useEffect(() => {
        fetchAudit();
    }, []);

    const filtered = useMemo(() => {
        return events.filter((e) => {
            const matchesType = typeFilter === 'all' || e.event_type.toLowerCase() === typeFilter.toLowerCase();
            const textToMatch = `${e.event_type} ${e.summary ?? ''} ${e.request_id ?? ''} ${e.entity_type ?? ''}`.toLowerCase();
            const matchesSearch = !search || textToMatch.includes(search.toLowerCase());
            return matchesType && matchesSearch;
        });
    }, [events, typeFilter, search]);

    return (
        <div className="page-wrap space-y-7">
            <header className="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.15em] text-violet-700 shadow-xs">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {isApprover ? 'Approver Compliance & Governance' : 'System Audit Trail'}
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-main sm:text-3xl">
                        Audit Trail & Decision History
                    </h1>
                    <p className="mt-1 text-sm text-muted">
                        Immutable chronological trail of extraction milestones, reviewer actions, and binding decisions.
                    </p>
                </div>
                <button
                    onClick={fetchAudit}
                    disabled={loading}
                    className="btn-secondary flex items-center gap-2 text-xs"
                >
                    <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                    <span>Refresh Log</span>
                </button>
            </header>

            {error && (
                <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700">
                    {error}
                </div>
            )}

            <div className="card overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border px-6 py-4">
                    <div>
                        <h2 className="text-sm font-bold text-main">Recorded Compliance Events</h2>
                        <p className="text-xs text-muted">
                            {filtered.length} {filtered.length === 1 ? 'event' : 'events'} recorded in immutable audit log
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <div className="relative min-w-[220px]">
                            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                            <input
                                type="search"
                                placeholder="Search by claim ID or detail…"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="form-input py-2 pl-9 text-xs"
                            />
                        </div>
                        <div className="relative">
                            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                            <select
                                value={typeFilter}
                                onChange={(e) => setTypeFilter(e.target.value)}
                                className="form-input py-2 pl-9 pr-4 text-xs"
                            >
                                <option value="all">All event types</option>
                                <option value="request_created">Request created</option>
                                <option value="document_uploaded">Document uploaded</option>
                                <option value="ocr_completed">OCR completed</option>
                                <option value="checks_executed">Checks executed</option>
                                <option value="correction_requested">Correction requested</option>
                                <option value="field_corrected">Field corrected</option>
                                <option value="review_completed">Review completed</option>
                                <option value="approved">Approved</option>
                                <option value="rejected">Rejected</option>
                            </select>
                        </div>
                    </div>
                </div>

                {loading ? (
                    <div className="space-y-3 p-6">
                        {[1, 2, 3, 4].map((i) => (
                            <div key={i} className="h-12 animate-pulse rounded-xl bg-slate-100" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                            <ClipboardCheck className="h-6 w-6" />
                        </span>
                        <h3 className="mt-4 text-sm font-bold text-main">No audit events found</h3>
                        <p className="mx-auto mt-1 max-w-sm text-xs text-muted leading-relaxed">
                            {events.length > 0
                                ? 'No events matched your search or filter parameters.'
                                : 'Audit entries will appear as documents are processed and reviewed.'}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[760px] text-left text-xs">
                            <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-muted">
                                <tr>
                                    <th className="px-6 py-3.5">Event ID & Timestamp</th>
                                    <th className="px-4 py-3.5">Event Type</th>
                                    <th className="px-4 py-3.5">Associated Claim</th>
                                    <th className="px-4 py-3.5">Actor / Entity</th>
                                    <th className="px-6 py-3.5">Change Summary</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-border">
                                {filtered.map((item) => (
                                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                                        <td className="px-6 py-4">
                                            <span className="font-mono font-bold text-main">#{item.id}</span>
                                            <p className="mt-0.5 text-[10px] text-muted font-medium">
                                                {new Date(item.created_at).toLocaleString()}
                                            </p>
                                        </td>
                                        <td className="px-4 py-4">
                                            <span
                                                className={`rounded-md px-2.5 py-1 text-[10px] font-bold capitalize ${
                                                    item.event_type.includes('approved')
                                                        ? 'bg-teal-50 text-teal-700 ring-1 ring-teal-200'
                                                        : item.event_type.includes('rejected')
                                                          ? 'bg-red-50 text-red-700 ring-1 ring-red-200'
                                                          : item.event_type.includes('corrected')
                                                            ? 'bg-violet-50 text-violet-700 ring-1 ring-violet-200'
                                                            : 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200'
                                                }`}
                                            >
                                                {item.event_type.replace(/_/g, ' ')}
                                            </span>
                                        </td>
                                        <td className="px-4 py-4">
                                            {item.request_id ? (
                                                <Link
                                                    to={`/requests/${item.request_id}`}
                                                    className="inline-flex items-center gap-1 font-bold text-indigo-700 hover:underline"
                                                >
                                                    Claim #{item.request_id}
                                                    <ArrowRight className="h-3 w-3" />
                                                </Link>
                                            ) : (
                                                <span className="text-muted">—</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-4 text-slate-700 font-medium">
                                            {item.actor_id ? `User #${item.actor_id}` : 'System Engine'}
                                            {item.entity_type && (
                                                <span className="ml-1 text-[10px] text-muted">
                                                    ({item.entity_type})
                                                </span>
                                            )}
                                        </td>
                                        <td className="max-w-[340px] px-6 py-4 text-slate-700 font-medium">
                                            <p className="truncate" title={item.summary ?? undefined}>
                                                {item.summary ?? '—'}
                                            </p>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
