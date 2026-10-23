import { useState } from 'react';
import {
    Award,
    Clock,
    FileText,
    History,
    RefreshCw,
    Send,
    ShieldAlert,
    ShieldCheck,
    Sparkles,
    UserCheck,
    XCircle,
    ChevronDown,
    AlertTriangle,
} from 'lucide-react';
import type {
    DecisionReplayEvent,
    DecisionReplayResponse,
    UserRole,
} from '../types';

interface DecisionReplayTimelineProps {
    replayData: DecisionReplayResponse | null;
    loading: boolean;
    error: string | null;
    onRefresh: () => void;
    userRole?: UserRole;
}

export default function DecisionReplayTimeline({
    replayData,
    loading,
    error,
    onRefresh,
}: DecisionReplayTimelineProps) {
    const [filterCategory, setFilterCategory] = useState<string>('all');

    if (loading) {
        return (
            <div className="card p-12 text-center space-y-3 shadow-xs">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto text-[#3478F6]" />
                <h3 className="text-base font-bold text-slate-900">Loading Decision Replay…</h3>
                <p className="text-xs text-slate-500">Retrieving authentic recorded timeline events and audit logs.</p>
            </div>
        );
    }

    if (error || !replayData) {
        return (
            <div className="card p-8 border-red-200 bg-red-50/50 space-y-3 text-center shadow-xs">
                <AlertTriangle className="h-8 w-8 text-red-600 mx-auto" />
                <h3 className="text-sm font-bold text-red-950">Could not load Decision Replay</h3>
                <p className="text-xs text-red-700">{error || 'No recorded timeline events available for this request.'}</p>
                <button
                    type="button"
                    onClick={onRefresh}
                    className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 border border-slate-200 shadow-2xs hover:bg-slate-50"
                >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>Try again</span>
                </button>
            </div>
        );
    }

    const events = replayData.events ?? [];

    const filteredEvents = filterCategory === 'all'
        ? events
        : events.filter((e) => e.category === filterCategory);

    // Map each event type to a clear icon and standard label
    const getEventPresentation = (event: DecisionReplayEvent) => {
        const cat = event.category;
        const titleLower = event.title.toLowerCase();

        if (titleLower.includes('created') || titleLower.includes('draft')) {
            return {
                icon: FileText,
                iconBg: 'bg-blue-100 text-[#3478F6]',
                standardLabel: 'Claim Created',
                badgeText: 'Created',
                badgeClass: 'bg-blue-50 text-[#3478F6] border-blue-200',
            };
        }
        if (titleLower.includes('upload') || titleLower.includes('document')) {
            return {
                icon: FileText,
                iconBg: 'bg-teal-100 text-[#0F9D8A]',
                standardLabel: 'Document Uploaded',
                badgeText: 'Uploaded',
                badgeClass: 'bg-teal-50 text-[#0F9D8A] border-teal-200',
            };
        }
        if (titleLower.includes('extract') || titleLower.includes('ocr')) {
            return {
                icon: Sparkles,
                iconBg: 'bg-indigo-100 text-[#3478F6]',
                standardLabel: 'Information Extracted',
                badgeText: 'Extracted',
                badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
            };
        }
        if (titleLower.includes('verification') || titleLower.includes('check') || cat === 'verification') {
            const isWarning = event.status_badge === 'warning' || event.status_badge === 'error';
            return {
                icon: isWarning ? ShieldAlert : ShieldCheck,
                iconBg: isWarning ? 'bg-amber-100 text-[#F59E0B]' : 'bg-teal-100 text-[#0F9D8A]',
                standardLabel: 'Verification Completed',
                badgeText: isWarning ? 'Needs review' : 'Matched',
                badgeClass: isWarning ? 'bg-amber-50 text-[#F59E0B] border-amber-200' : 'bg-teal-50 text-[#0F9D8A] border-teal-200',
            };
        }
        if (titleLower.includes('correction') || titleLower.includes('finding') || titleLower.includes('reviewed')) {
            return {
                icon: UserCheck,
                iconBg: 'bg-violet-100 text-[#7656D6]',
                standardLabel: 'Reviewer Findings Recorded',
                badgeText: 'Resolved',
                badgeClass: 'bg-violet-50 text-[#7656D6] border-violet-200',
            };
        }
        if (titleLower.includes('submit') || titleLower.includes('forward') || titleLower.includes('approval')) {
            return {
                icon: Send,
                iconBg: 'bg-blue-100 text-[#3478F6]',
                standardLabel: 'Sent for Approval',
                badgeText: 'Pending Sign-off',
                badgeClass: 'bg-blue-50 text-[#3478F6] border-blue-200',
            };
        }
        if (titleLower.includes('approved')) {
            return {
                icon: Award,
                iconBg: 'bg-teal-100 text-[#0F9D8A]',
                standardLabel: 'Decision Recorded: Approved',
                badgeText: 'Approved',
                badgeClass: 'bg-teal-50 text-[#0F9D8A] border-teal-200',
            };
        }
        if (titleLower.includes('reject')) {
            return {
                icon: XCircle,
                iconBg: 'bg-red-100 text-[#DC2626]',
                standardLabel: 'Decision Recorded: Rejected',
                badgeText: 'Rejected',
                badgeClass: 'bg-red-50 text-red-700 border-red-200',
            };
        }

        return {
            icon: Clock,
            iconBg: 'bg-slate-100 text-slate-700',
            standardLabel: event.title,
            badgeText: event.category,
            badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
        };
    };

    const formatDate = (iso: string) => {
        try {
            const date = new Date(iso);
            return date.toLocaleString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return iso;
        }
    };

    return (
        <div className="space-y-6">
            {/* TOP HEADER */}
            <div className="rounded-2xl border border-blue-200/80 bg-gradient-to-r from-[#14213D] via-[#1E293B] to-[#1E3A8A] p-6 text-white shadow-md">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="space-y-1">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/25 border border-blue-400/30 px-3 py-0.5 text-[11px] font-bold text-blue-300 uppercase tracking-wider">
                            <History className="h-3.5 w-3.5" />
                            Chronological Decision Replay
                        </span>
                        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                            Claim #{replayData.request_number}
                        </h1>
                        <p className="text-xs text-blue-200/80">
                            Showing {events.length} actual recorded event{events.length !== 1 ? 's' : ''} in immutable chronological order.
                        </p>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            onClick={onRefresh}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-white hover:bg-white/20 transition shadow-xs"
                        >
                            <RefreshCw className="h-4 w-4 text-blue-300" />
                            <span>Refresh History</span>
                        </button>
                    </div>
                </div>

                {/* Filter chips */}
                <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-white/10 pt-4">
                    <span className="text-[11px] font-semibold text-blue-200 mr-1">Filter by category:</span>
                    {[
                        { id: 'all', label: 'All Events' },
                        { id: 'lifecycle', label: 'Lifecycle' },
                        { id: 'document', label: 'Documents' },
                        { id: 'verification', label: 'Verification' },
                        { id: 'review', label: 'Review' },
                        { id: 'decision', label: 'Decisions' },
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            type="button"
                            onClick={() => setFilterCategory(tab.id)}
                            className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                                filterCategory === tab.id
                                    ? 'bg-white text-slate-900 shadow-xs'
                                    : 'bg-white/10 text-blue-100 hover:bg-white/20'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* CHRONOLOGICAL EVENT TIMELINE */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
                <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
                    <div>
                        <h2 className="text-base font-bold text-slate-900">Recorded Audit Events</h2>
                        <p className="text-xs text-muted">Each action is verified, timestamped, and stored permanently.</p>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">
                        {filteredEvents.length} event{filteredEvents.length !== 1 ? 's' : ''} displayed
                    </span>
                </div>

                <div className="relative pl-6 space-y-8 before:absolute before:left-3 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
                    {filteredEvents.map((event, idx) => {
                        const presentation = getEventPresentation(event);
                        const Icon = presentation.icon;

                        return (
                            <div key={event.id || idx} className="relative group">
                                {/* Dot on vertical line */}
                                <span className={`absolute -left-[30px] top-1.5 flex h-7 w-7 items-center justify-center rounded-full ring-4 ring-white shadow-xs ${presentation.iconBg}`}>
                                    <Icon className="h-3.5 w-3.5" />
                                </span>

                                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2 hover:bg-white transition-all shadow-2xs">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-sm font-bold text-slate-900">
                                                {presentation.standardLabel}
                                            </h3>
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${presentation.badgeClass}`}>
                                                {presentation.badgeText}
                                            </span>
                                        </div>
                                        <span className="text-xs font-medium text-slate-500">
                                            {formatDate(event.timestamp)}
                                        </span>
                                    </div>

                                    {/* Event Summary / Description */}
                                    <p className="text-xs text-slate-700 leading-relaxed font-normal">
                                        {event.comment || event.action || event.title}
                                    </p>

                                    {event.actor?.display_name && (
                                        <p className="text-[11px] text-slate-500 font-medium">
                                            Recorded by <strong className="text-slate-800">{event.actor.display_name}</strong> ({event.actor.role})
                                        </p>
                                    )}

                                    {/* EXPANDABLE SECTION FOR AUDIT EVENT IDS, INTERNAL IDENTIFIERS & TECHNICAL METADATA */}
                                    <details className="group/details mt-2 pt-2 border-t border-slate-200/80">
                                        <summary className="cursor-pointer text-[11px] font-semibold text-slate-500 hover:text-slate-800 flex items-center justify-between select-none">
                                            <span>View technical audit details</span>
                                            <ChevronDown className="h-3.5 w-3.5 text-slate-400 transition-transform group-open/details:rotate-180" />
                                        </summary>
                                        <div className="mt-2 rounded-lg bg-slate-900 p-3 font-mono text-[10px] text-slate-200 space-y-1">
                                            <p><span className="text-slate-400">Event ID:</span> {event.id}</p>
                                            <p><span className="text-slate-400">Category:</span> {event.category}</p>
                                            <p><span className="text-slate-400">Timestamp:</span> {event.timestamp}</p>
                                            {event.metadata && (
                                                <div className="pt-1 border-t border-slate-800 text-[10px]">
                                                    <span className="text-slate-400">Metadata:</span>
                                                    <pre className="whitespace-pre-wrap mt-0.5 text-slate-300">
                                                        {JSON.stringify(event.metadata, null, 2)}
                                                    </pre>
                                                </div>
                                            )}
                                        </div>
                                    </details>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
