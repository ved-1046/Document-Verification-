import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { History, FileText, Search, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';
import api from '../services/api';
import type { DocumentHistoryEntry } from '../types';

export default function DocumentHistoryPage() {
    const [entries, setEntries] = useState<DocumentHistoryEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        api.get<DocumentHistoryEntry[]>('/documents/history')
            .then((r) => setEntries(r.data))
            .finally(() => setLoading(false));
    }, []);

    const filtered = useMemo(() => {
        return entries.filter((e) => {
            const text = `${e.request_number} ${e.request_title ?? ''} ${e.original_filename} ${e.doc_type}`.toLowerCase();
            return !search || text.includes(search.toLowerCase());
        });
    }, [entries, search]);

    return (
        <div className="page-wrap space-y-7">
            <header className="animate-fade-in-up flex flex-wrap items-end justify-between gap-4">
                <div>
                    <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.15em] text-indigo-700 shadow-xs">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        Compliance Archive · Immutable Versioning
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-main sm:text-3xl">Document Version History</h1>
                    <p className="mt-1 text-sm text-muted">
                        All document versions are preserved. Original uploads and replacements appear here for authorized review.
                    </p>
                </div>
            </header>

            {/* Metrics with 3-5px hover lift */}
            <div className="grid gap-4 sm:grid-cols-3 animate-fade-in-up-delay-100">
                <article className="card-interactive-indigo p-5">
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Total Versions</p>
                        <span className="rounded-lg bg-indigo-50 p-2 text-indigo-700 ring-1 ring-indigo-200/50">
                            <History className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-main">{loading ? '—' : entries.length}</p>
                    <p className="mt-2 text-[11px] text-muted">Preserved immutable files in storage</p>
                </article>

                <article className="card-interactive-teal p-5">
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Ready &amp; Extracted</p>
                        <span className="rounded-lg bg-teal-50 p-2 text-[#0F9D8A] ring-1 ring-teal-200/50">
                            <CheckCircle2 className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-[#0F9D8A]">
                        {loading ? '—' : entries.filter((e) => e.processing_status === 'ready').length}
                    </p>
                    <p className="mt-2 text-[11px] text-muted">Successfully processed via OCR</p>
                </article>

                <article className="card-interactive-violet p-5">
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Unique Claims</p>
                        <span className="rounded-lg bg-violet-50 p-2 text-[#8B5CF6] ring-1 ring-violet-200/50">
                            <FileText className="h-4 w-4" />
                        </span>
                    </div>
                    <p className="mt-2 text-3xl font-extrabold tracking-tight text-main">
                        {loading ? '—' : new Set(entries.map((e) => e.request_id)).size}
                    </p>
                    <p className="mt-2 text-[11px] text-muted">Requests with versioned evidence</p>
                </article>
            </div>

            <section className="card overflow-hidden animate-fade-in-up-delay-200">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border px-6 py-4">
                    <div>
                        <h2 className="text-sm font-bold text-main">Versioned Artifacts</h2>
                        <p className="text-xs text-muted">
                            {filtered.length} {filtered.length === 1 ? 'file' : 'files'} in archive
                        </p>
                    </div>
                    <div className="relative min-w-[220px]">
                        <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                        <input
                            type="search"
                            placeholder="Search by file or claim…"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="form-input py-2 pl-9 text-xs"
                        />
                    </div>
                </div>

                {loading ? (
                    <div className="space-y-3 p-6">
                        {[0, 1, 2].map((i) => (
                            <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-100" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="card-body flex flex-col items-center py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 mb-3">
                            <History className="w-6 h-6 text-slate-400" />
                        </span>
                        <h2 className="text-sm font-bold text-main mb-1">No document history found</h2>
                        <p className="text-muted text-xs max-w-md leading-relaxed">
                            {entries.length > 0
                                ? 'No documents matched your search query.'
                                : 'All document versions are preserved. Original uploads and replacements appear here — nothing is deleted on resubmission.'}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[760px] text-left text-xs">
                            <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-muted">
                                <tr>
                                    <th className="px-6 py-3.5">Associated Claim</th>
                                    <th className="px-4 py-3.5">Document Type &amp; Filename</th>
                                    <th className="px-4 py-3.5">Version</th>
                                    <th className="px-4 py-3.5">Uploaded</th>
                                    <th className="px-4 py-3.5">Status</th>
                                    <th className="px-6 py-3.5 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-border">
                                {filtered.map((e) => (
                                    <tr key={e.id} className="hover:bg-slate-50/80 transition-colors">
                                        <td className="px-6 py-4">
                                            <Link to={`/requests/${e.request_id}`} className="font-bold text-main hover:text-indigo-700">
                                                {e.request_number}
                                            </Link>
                                            <div className="text-[11px] text-muted truncate max-w-[200px]" title={e.request_title ?? undefined}>{e.request_title}</div>
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className="font-bold capitalize text-main">{e.doc_type.replace(/_/g, ' ')}</span>
                                            <p className="text-[11px] text-muted font-mono truncate max-w-[220px]" title={e.original_filename}>{e.original_filename}</p>
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className="rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700 ring-1 ring-blue-200">
                                                v{e.version_number}
                                            </span>
                                        </td>
                                        <td className="px-4 py-4 text-muted font-medium">
                                            {new Date(e.uploaded_at).toLocaleString()}
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className={`badge ${e.processing_status === 'ready' ? 'bg-teal-50 text-[#0F9D8A] ring-teal-200' : e.processing_status === 'failed' ? 'bg-red-50 text-[#DC4545] ring-red-200' : 'bg-amber-50 text-[#D97706] ring-amber-200'}`}>
                                                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                {e.processing_status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <Link
                                                to={`/requests/${e.request_id}`}
                                                className="inline-flex items-center gap-1 font-bold text-indigo-700 hover:underline"
                                            >
                                                <span>Inspect</span>
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
