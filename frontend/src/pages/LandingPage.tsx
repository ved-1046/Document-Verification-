import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    ArrowDown,
    ArrowRight,
    Check,
    CheckCircle2,
    ChevronRight,
    FileText,
    GitCompare,
    History,
    LockKeyhole,
    Network,
    ScanLine,
    ShieldCheck,
    UploadCloud,
    UserRoundCheck,
    ClipboardCheck,
    Bot,
    AlertTriangle,
} from 'lucide-react';

const pipelineSteps = [
    {
        number: '01',
        title: 'Upload Documents',
        desc: 'Submitter adds claim details and uploads receipts, invoices, and supporting expense documentation.',
        icon: UploadCloud,
        tone: 'bg-teal-50 text-[#0F9D8A] border-teal-200',
    },
    {
        number: '02',
        title: 'Universal OCR Extraction',
        desc: 'Tesseract OCR engine extracts merchant names, dates, amounts, and reference codes with token confidence.',
        icon: ScanLine,
        tone: 'bg-blue-50 text-[#3478F6] border-blue-200',
    },
    {
        number: '03',
        title: 'Cross-Document Verification',
        desc: 'Automated rules compare claimed amounts against extracted receipt figures, calculating exact variances.',
        icon: GitCompare,
        tone: 'bg-amber-50 text-amber-700 border-amber-200',
    },
    {
        number: '04',
        title: 'Human Reviewer Audit',
        desc: 'Assigned reviewer inspects evidence side-by-side, resolves open flags, and records auditable corrections.',
        icon: UserRoundCheck,
        tone: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    },
    {
        number: '05',
        title: 'Final Approver Decision',
        desc: 'Authorized executive reviews financial risk, inspects the audit trail, and records binding sign-off.',
        icon: ClipboardCheck,
        tone: 'bg-violet-50 text-[#7656D6] border-violet-200',
    },
];

const featureCards = [
    {
        title: 'Universal Extraction',
        desc: 'Captures key receipt metadata, merchant names, dates, line items, and totals automatically using multi-engine OCR.',
        icon: ScanLine,
        status: 'Live Feature',
        statusColor: 'bg-emerald-500/10 text-emerald-700 border-emerald-300',
        tone: 'from-blue-500/10 to-transparent',
    },
    {
        title: 'Cross-Document Verification',
        desc: 'Compares claim submissions with uploaded receipts in real time, detecting amount discrepancies down to the cent.',
        icon: GitCompare,
        status: 'Live Feature',
        statusColor: 'bg-emerald-500/10 text-emerald-700 border-emerald-300',
        tone: 'from-teal-500/10 to-transparent',
    },
    {
        title: 'Evidence Impact Graph',
        desc: 'Interactive visual graph illustrating the exact dependency chain from raw image tokens to the final reimbursement decision.',
        icon: Network,
        status: 'Interactive',
        statusColor: 'bg-indigo-500/10 text-indigo-700 border-indigo-300',
        tone: 'from-indigo-500/10 to-transparent',
    },
    {
        title: 'Decision Replay',
        desc: 'Step-by-step timeline that reconstructs every reviewer action, status change, and field adjustment in chronological order.',
        icon: History,
        status: 'Interactive',
        statusColor: 'bg-indigo-500/10 text-indigo-700 border-indigo-300',
        tone: 'from-violet-500/10 to-transparent',
    },
    {
        title: 'Grounded AI Assistant',
        desc: 'Google Gemini integration that answers claim questions with strict grounding on stored OCR facts and policy evidence.',
        icon: Bot,
        status: 'Live Feature',
        statusColor: 'bg-emerald-500/10 text-emerald-700 border-emerald-300',
        tone: 'from-purple-500/10 to-transparent',
    },
    {
        title: 'Version History & Audit Trail',
        desc: 'Tamper-evident audit ledger preserving previous document versions, reviewer corrections, and reason logs indefinitely.',
        icon: ShieldCheck,
        status: 'Live Feature',
        statusColor: 'bg-emerald-500/10 text-emerald-700 border-emerald-300',
        tone: 'from-emerald-500/10 to-transparent',
    },
];

const roleWorkspaces = [
    {
        role: 'Submitter',
        badge: 'Employee Workspace',
        title: 'My Expenses',
        accentColor: '#0F9D8A',
        borderColor: 'border-[#0F9D8A]/30 hover:border-[#0F9D8A]',
        buttonClass: 'btn-teal',
        icon: UploadCloud,
        description:
            'A streamlined expense portal where claimants submit reimbursement forms, upload digital receipts, and track approval status through a friendly 4-milestone roadmap.',
        keyPoints: [
            'Drag-and-drop receipt and form upload',
            'Instant OCR extraction feedback with confidence score',
            'Real-time milestone tracking from draft to payment',
            'Guided document re-upload when more info is requested',
        ],
        loginRole: 'submitter',
    },
    {
        role: 'Reviewer',
        badge: 'Finance Auditor Workspace',
        title: 'Review Workbench',
        accentColor: '#3478F6',
        borderColor: 'border-[#3478F6]/30 hover:border-[#3478F6]',
        buttonClass: 'btn-primary',
        icon: ScanLine,
        description:
            'A high-density audit workbench designed for finance compliance teams. Features side-by-side receipt inspection, rotation/zoom, variance detection, and verified corrections.',
        keyPoints: [
            'Side-by-side document inspection canvas with 250% zoom',
            'Cross-document variance calculator (Claimed vs Receipt)',
            'Audited field corrections with mandatory reason logging',
            'One-click forwarding to Approver or request info from submitter',
        ],
        loginRole: 'reviewer',
    },
    {
        role: 'Approver',
        badge: 'Executive Workspace',
        title: 'Executive Decisions',
        accentColor: '#7656D6',
        borderColor: 'border-[#7656D6]/30 hover:border-[#7656D6]',
        buttonClass: 'btn-violet',
        icon: ClipboardCheck,
        description:
            'An executive sign-off center providing corporate controllers and managers with high-level financial risk summaries, reviewer compliance notes, and binding approval authority.',
        keyPoints: [
            'High-level financial exposure and category summaries',
            'Full review completion notes and correction history',
            'On-demand source document inspection modal',
            'Formal binding Approve or Reject with recorded executive comments',
        ],
        loginRole: 'approver',
    },
];

function InteractiveSamplePreview() {
    const [activeTab, setActiveTab] = useState<'match' | 'variance'>('match');

    return (
        <div className="relative mx-auto w-full max-w-[560px] rounded-3xl border border-white/15 bg-white p-6 shadow-2xl transition-all">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4">
                <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-[#3478F6] ring-1 ring-blue-200">
                        <FileText className="h-5 w-5" />
                    </span>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-extrabold text-[#1E293B]">Live Extraction Engine</span>
                            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 ring-1 ring-emerald-200">
                                Active OCR
                            </span>
                        </div>
                        <p className="text-xs text-[#64748B]">Tesseract Multi-Token Parser · Document v1</p>
                    </div>
                </div>

                {/* Tab switcher for demoing both match and mismatch */}
                <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-[11px] font-semibold">
                    <button
                        type="button"
                        onClick={() => setActiveTab('match')}
                        className={`rounded-md px-2.5 py-1 transition ${
                            activeTab === 'match' ? 'bg-white text-[#1E293B] shadow-xs' : 'text-[#64748B]'
                        }`}
                    >
                        Matching Claim
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveTab('variance')}
                        className={`rounded-md px-2.5 py-1 transition ${
                            activeTab === 'variance' ? 'bg-white text-[#1E293B] shadow-xs' : 'text-[#64748B]'
                        }`}
                    >
                        Variance Sample
                    </button>
                </div>
            </div>

            {/* Simulated Document & Extraction Display */}
            <div className="grid gap-4 py-5 sm:grid-cols-[0.9fr_1.1fr]">
                {/* Simulated Scanned Receipt with Laser Beam */}
                <div className="relative flex flex-col justify-between rounded-2xl border border-[#E2E8F0] bg-slate-50/90 p-4 overflow-hidden">
                    {/* Animated Scanning Beam */}
                    <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-transparent via-[#3478F6] to-transparent shadow-[0_0_12px_#3478F6] animate-pulse" />

                    <div>
                        <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[#64748B] mb-2">
                            <span>Scanned Receipt</span>
                            <span className="text-teal-700">Confidence 98%</span>
                        </div>

                        {/* Visual Receipt Paper */}
                        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs">
                            <div className="flex items-center justify-between border-b border-dashed border-slate-200 pb-2">
                                <span className="text-xs font-black tracking-wider text-[#14213D]">ABC STATIONERY</span>
                                <span className="h-2 w-2 rounded-full bg-[#0F9D8A]" />
                            </div>
                            <p className="mt-1.5 text-[10px] text-[#64748B]">Tax Invoice #REC-2026-450</p>
                            <p className="text-[10px] text-[#64748B]">Date: 22 October 2026</p>

                            <div className="my-3 space-y-1.5 border-y border-slate-100 py-2 text-[10px] text-[#1E293B]">
                                <div className="flex justify-between">
                                    <span>Printer Ink Cartridge</span>
                                    <span>₹350.00</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>A4 Paper Ream</span>
                                    <span>₹100.00</span>
                                </div>
                            </div>

                            <div className="flex items-center justify-between font-extrabold text-xs text-[#14213D]">
                                <span>Receipt Total:</span>
                                <span className="text-sm font-black text-[#14213D]">₹450.00</span>
                            </div>
                        </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between rounded-lg bg-teal-50 px-2.5 py-1 text-[11px] font-bold text-teal-800">
                        <span className="flex items-center gap-1">
                            <CheckCircle2 className="h-3.5 w-3.5 text-teal-600" /> 6 Tokens Parsed
                        </span>
                        <span>Tesseract v5</span>
                    </div>
                </div>

                {/* Right Side: Verification Engine Comparison */}
                <div className="space-y-3">
                    <div className="rounded-2xl border border-[#E2E8F0] bg-slate-50/60 p-4 space-y-2.5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-[#1E293B]">Extracted Facts</span>
                            <span className="text-[10px] font-bold text-[#3478F6]">Grounded</span>
                        </div>

                        <dl className="space-y-2 text-xs">
                            <div className="flex items-center justify-between">
                                <dt className="text-[#64748B] font-medium">Merchant</dt>
                                <dd className="font-bold text-[#1E293B]">ABC Stationery</dd>
                            </div>
                            <div className="flex items-center justify-between">
                                <dt className="text-[#64748B] font-medium">Receipt Amount</dt>
                                <dd className="font-black text-[#14213D]">₹450.00</dd>
                            </div>
                            <div className="flex items-center justify-between">
                                <dt className="text-[#64748B] font-medium">Expense Date</dt>
                                <dd className="font-bold text-[#1E293B]">22 Oct 2026</dd>
                            </div>
                            <div className="flex items-center justify-between border-t border-slate-200/80 pt-1.5">
                                <dt className="text-[#64748B] font-medium">Claim Form Value</dt>
                                <dd className="font-bold text-[#1E293B]">
                                    {activeTab === 'match' ? '₹450.00' : '₹500.00'}
                                </dd>
                            </div>
                        </dl>
                    </div>

                    {/* Result Card Based on Active Tab */}
                    {activeTab === 'match' ? (
                        <div className="rounded-2xl border border-teal-200 bg-teal-50/90 p-3.5">
                            <div className="flex items-center gap-2 text-xs font-bold text-teal-900">
                                <CheckCircle2 className="h-4 w-4 text-[#0F9D8A] shrink-0" />
                                <span>Perfect Match · Ready for Review</span>
                            </div>
                            <p className="mt-1 text-[11px] leading-relaxed text-teal-800">
                                Claim amount (₹450.00) matches extracted receipt total (₹450.00) with zero variance.
                            </p>
                        </div>
                    ) : (
                        <div className="rounded-2xl border border-amber-300 bg-amber-50/95 p-3.5">
                            <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                <span>Variance Flagged: ₹50.00 Discrepancy</span>
                            </div>
                            <p className="mt-1 text-[11px] leading-relaxed text-amber-800">
                                Claimed ₹500.00 vs Receipt ₹450.00. Highlighted in Review Workbench for auditor adjustment.
                            </p>
                        </div>
                    )}

                    {/* Sign-off Route */}
                    <div className="flex items-center justify-between rounded-xl bg-slate-100/90 px-3 py-2 text-[11px]">
                        <span className="text-[#64748B] font-medium">Review Pipeline:</span>
                        <div className="flex items-center gap-1.5 font-bold">
                            <span className="text-[#3478F6]">Reviewer</span>
                            <ChevronRight className="h-3 w-3 text-slate-400" />
                            <span className="text-[#7656D6]">Approver</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer Trust Marker */}
            <div className="flex items-center justify-between border-t border-[#E2E8F0] pt-3 text-[11px] text-[#64748B]">
                <span className="flex items-center gap-1.5 font-medium">
                    <LockKeyhole className="h-3.5 w-3.5 text-slate-400" />
                    Cryptographic audit ledger &amp; zero data drift
                </span>
                <span className="font-semibold text-teal-700">Ready to audit</span>
            </div>
        </div>
    );
}

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-[#F5F7FB] text-[#1E293B]">
            {/* Top Navigation Bar */}
            <header className="sticky top-0 z-40 border-b border-white/10 bg-[#14213D] text-white backdrop-blur-md">
                <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
                    {/* Brand Logo */}
                    <Link to="/" className="flex items-center gap-3" aria-label="DocuVerify AI Home">
                        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#3478F6] text-white shadow-sm ring-1 ring-white/20">
                            <ShieldCheck className="h-5 w-5" />
                        </span>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="text-lg font-black tracking-tight text-white">DocuVerify</span>
                                <span className="rounded bg-[#0F9D8A] px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-wider text-white">
                                    AI
                                </span>
                            </div>
                            <p className="text-[10px] text-slate-300 font-medium leading-none">Document Intelligence</p>
                        </div>
                    </Link>

                    {/* Navigation Menu */}
                    <nav className="hidden items-center gap-8 text-sm font-semibold text-slate-300 md:flex">
                        <a href="#features" className="hover:text-white transition-colors">Features</a>
                        <a href="#workflow" className="hover:text-white transition-colors">How It Works</a>
                        <a href="#roles" className="hover:text-white transition-colors">Workspaces</a>
                        <a href="#security" className="hover:text-white transition-colors">Architecture</a>
                    </nav>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-3">
                        <Link
                            to="/login"
                            className="rounded-lg px-4 py-2 text-xs font-bold text-slate-200 hover:text-white hover:bg-white/10 transition"
                        >
                            Sign In
                        </Link>
                        <Link
                            to="/login"
                            className="btn-primary text-xs shadow-md font-bold px-4 py-2.5 flex items-center gap-1.5"
                        >
                            <span>Get Started</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                    </div>
                </div>
            </header>

            {/* HERO SECTION */}
            <section className="relative isolate border-b border-slate-200/80 bg-[#14213D] pt-16 pb-24 text-white overflow-hidden">
                {/* Subtle Background Glow */}
                <div className="pointer-events-none absolute -top-40 right-1/4 h-96 w-96 rounded-full bg-[#3478F6]/15 blur-3xl" />
                <div className="pointer-events-none absolute -bottom-40 left-10 h-96 w-96 rounded-full bg-[#0F9D8A]/15 blur-3xl" />

                <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
                    {/* Hero Left Content */}
                    <div className="space-y-6">
                        <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 text-xs font-bold tracking-wide text-indigo-200">
                            <span className="h-2 w-2 rounded-full bg-[#0F9D8A] animate-pulse" />
                            <span>Enterprise AI Document Auditing</span>
                        </div>

                        <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl lg:text-5xl leading-[1.15] text-white">
                            Every Document.<br />
                            Every Decision.<br />
                            <span className="bg-gradient-to-r from-[#3478F6] via-blue-300 to-[#0F9D8A] bg-clip-text text-transparent">
                                Verified.
                            </span>
                        </h1>

                        <p className="max-w-xl text-base sm:text-lg leading-relaxed text-slate-300 font-normal">
                            AI-powered document verification that detects mismatches, explains risks, and helps teams make informed decisions.
                        </p>

                        {/* Primary & Secondary Call to Actions */}
                        <div className="flex flex-wrap items-center gap-4 pt-2">
                            <Link
                                to="/login"
                                className="btn-primary px-6 py-3.5 text-sm font-bold shadow-lg flex items-center gap-2"
                            >
                                <span>Get Started</span>
                                <ArrowRight className="h-4 w-4" />
                            </Link>

                            <a
                                href="#features"
                                className="btn-secondary bg-white/10 border-white/20 text-white hover:bg-white/20 px-6 py-3.5 text-sm font-bold flex items-center gap-2"
                            >
                                <span>Explore Features</span>
                                <ArrowDown className="h-4 w-4" />
                            </a>
                        </div>

                        {/* Feature Badges */}
                        <div className="flex flex-wrap items-center gap-5 pt-3 text-xs font-semibold text-slate-300">
                            <span className="flex items-center gap-1.5">
                                <Check className="h-4 w-4 text-[#0F9D8A]" />
                                Universal OCR Extraction
                            </span>
                            <span className="flex items-center gap-1.5">
                                <Check className="h-4 w-4 text-[#0F9D8A]" />
                                Cross-Document Variance
                            </span>
                            <span className="flex items-center gap-1.5">
                                <Check className="h-4 w-4 text-[#0F9D8A]" />
                                Grounded Gemini Copilot
                            </span>
                        </div>
                    </div>

                    {/* Hero Right Preview Card */}
                    <div>
                        <InteractiveSamplePreview />
                    </div>
                </div>
            </section>

            {/* 6 CORE FEATURE CARDS */}
            <section id="features" className="mx-auto max-w-7xl px-5 py-24 sm:px-8">
                <div className="mx-auto max-w-2xl text-center space-y-3">
                    <p className="text-xs font-extrabold uppercase tracking-widest text-[#3478F6]">
                        Core Platform Capabilities
                    </p>
                    <h2 className="text-3xl font-extrabold tracking-tight text-[#1E293B] sm:text-4xl">
                        Intelligent Auditing Built for Production
                    </h2>
                    <p className="text-base text-[#64748B]">
                        DocuVerify AI connects raw document scans, mathematical rule validation, and human sign-offs into a single auditable workflow.
                    </p>
                </div>

                <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {featureCards.map((feat) => {
                        const Icon = feat.icon;
                        return (
                            <article
                                key={feat.title}
                                className="group relative rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-[#3478F6]/40 hover:shadow-md"
                            >
                                <div className="flex items-center justify-between">
                                    <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-50 text-[#14213D] ring-1 ring-slate-200 group-hover:bg-blue-50 group-hover:text-[#3478F6] transition-colors">
                                        <Icon className="h-6 w-6" />
                                    </span>
                                    <span
                                        className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${feat.statusColor}`}
                                    >
                                        {feat.status}
                                    </span>
                                </div>

                                <h3 className="mt-5 text-lg font-bold text-[#1E293B] group-hover:text-[#3478F6] transition-colors">
                                    {feat.title}
                                </h3>

                                <p className="mt-2 text-sm leading-relaxed text-[#64748B] font-normal">
                                    {feat.desc}
                                </p>
                            </article>
                        );
                    })}
                </div>
            </section>

            {/* 5-STEP PIPELINE: HOW IT WORKS */}
            <section id="workflow" className="border-y border-[#E2E8F0] bg-white py-24">
                <div className="mx-auto max-w-7xl px-5 sm:px-8">
                    <div className="mx-auto max-w-2xl text-center space-y-3">
                        <p className="text-xs font-extrabold uppercase tracking-widest text-[#0F9D8A]">
                            The Verification Pipeline
                        </p>
                        <h2 className="text-3xl font-extrabold tracking-tight text-[#1E293B] sm:text-4xl">
                            How DocuVerify AI Works
                        </h2>
                        <p className="text-base text-[#64748B]">
                            Every expense claim flows through five verified stages ensuring complete financial accuracy and compliance.
                        </p>
                    </div>

                    <div className="relative mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:gap-3">
                        {pipelineSteps.map(({ number, title, desc, icon: Icon, tone }, idx) => (
                            <div
                                key={number}
                                className="relative flex flex-col justify-between rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 transition-all hover:border-[#3478F6]/40 hover:bg-white hover:shadow-md"
                            >
                                <div>
                                    <div className="flex items-center justify-between">
                                        <span className="font-mono text-xs font-black tracking-wider text-[#64748B]">
                                            STEP {number}
                                        </span>
                                        <span className={`flex h-10 w-10 items-center justify-center rounded-xl border ${tone} shadow-2xs`}>
                                            <Icon className="h-5 w-5" />
                                        </span>
                                    </div>

                                    <h3 className="mt-5 text-base font-bold text-[#1E293B]">{title}</h3>
                                    <p className="mt-2 text-xs leading-relaxed text-[#64748B] font-normal">{desc}</p>
                                </div>

                                {idx < pipelineSteps.length - 1 && (
                                    <span
                                        aria-hidden="true"
                                        className="pointer-events-none absolute -right-3 top-9 z-10 hidden h-6 w-6 items-center justify-center rounded-full border border-[#E2E8F0] bg-white text-slate-400 lg:flex shadow-xs"
                                    >
                                        <ChevronRight className="h-3.5 w-3.5" />
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* 3 DISTINCT ROLE WORKSPACES */}
            <section id="roles" className="mx-auto max-w-7xl px-5 py-24 sm:px-8">
                <div className="mx-auto max-w-2xl text-center space-y-3">
                    <p className="text-xs font-extrabold uppercase tracking-widest text-[#7656D6]">
                        Role-Governed Experiences
                    </p>
                    <h2 className="text-3xl font-extrabold tracking-tight text-[#1E293B] sm:text-4xl">
                        Three Dedicated Workspaces
                    </h2>
                    <p className="text-base text-[#64748B]">
                        Each role performs a distinct job with tailored views, information density, and specialized actions.
                    </p>
                </div>

                <div className="mt-16 grid gap-8 lg:grid-cols-3">
                    {roleWorkspaces.map((rw) => {
                        const Icon = rw.icon;
                        return (
                            <div
                                key={rw.role}
                                className={`flex flex-col justify-between rounded-3xl border bg-white p-7 shadow-sm transition-all duration-200 hover:-translate-y-1.5 hover:shadow-lg ${rw.borderColor}`}
                            >
                                <div className="space-y-5">
                                    <div className="flex items-center justify-between">
                                        <span
                                            className="flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-md"
                                            style={{ backgroundColor: rw.accentColor }}
                                        >
                                            <Icon className="h-6 w-6" />
                                        </span>
                                        <span
                                            className="rounded-full px-3 py-1 text-xs font-bold tracking-wide"
                                            style={{
                                                backgroundColor: `${rw.accentColor}15`,
                                                color: rw.accentColor,
                                            }}
                                        >
                                            {rw.badge}
                                        </span>
                                    </div>

                                    <div>
                                        <h3 className="text-xl font-extrabold text-[#1E293B]">{rw.title}</h3>
                                        <p className="mt-2 text-sm leading-relaxed text-[#64748B] font-normal">
                                            {rw.description}
                                        </p>
                                    </div>

                                    <div className="space-y-2.5 border-t border-slate-100 pt-4">
                                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                            Key Capabilities
                                        </span>
                                        <ul className="space-y-2 text-xs text-[#1E293B]">
                                            {rw.keyPoints.map((point) => (
                                                <li key={point} className="flex items-start gap-2">
                                                    <Check
                                                        className="h-4 w-4 shrink-0 mt-0.5"
                                                        style={{ color: rw.accentColor }}
                                                    />
                                                    <span className="font-medium">{point}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>

                                <div className="mt-8 pt-4 border-t border-slate-100">
                                    <Link
                                        to={`/login?role=${rw.loginRole}`}
                                        className={`w-full py-3 text-xs font-bold flex items-center justify-center gap-2 ${rw.buttonClass}`}
                                    >
                                        <span>Sign in as {rw.role}</span>
                                        <ArrowRight className="h-4 w-4" />
                                    </Link>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* SECURITY & ARCHITECTURE CALLOUT */}
            <section id="security" className="border-t border-[#E2E8F0] bg-[#14213D] py-20 text-white">
                <div className="mx-auto max-w-7xl px-5 sm:px-8">
                    <div className="flex flex-col items-start justify-between gap-8 rounded-3xl bg-gradient-to-r from-white/5 to-white/10 p-8 sm:p-12 lg:flex-row lg:items-center">
                        <div className="space-y-3 max-w-2xl">
                            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#0F9D8A]">
                                <ShieldCheck className="h-4 w-4" />
                                Fintech-Grade Compliance Architecture
                            </span>
                            <h2 className="text-2xl font-black text-white sm:text-3xl">
                                Built for Transparency. Designed for Zero Hallucinations.
                            </h2>
                            <p className="text-sm leading-relaxed text-slate-300 font-normal">
                                DocuVerify AI never allows autonomous models to approve or reject reimbursements. All OCR tokens, reviewer corrections, and approver verdicts are logged immutably with full provenance.
                            </p>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
                            <Link
                                to="/login"
                                className="btn-primary px-6 py-3.5 text-xs font-bold flex items-center justify-center gap-2"
                            >
                                <span>Launch Workspace</span>
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* FOOTER */}
            <footer className="border-t border-[#E2E8F0] bg-white py-8">
                <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-5 text-xs text-[#64748B] sm:flex-row sm:px-8">
                    <div className="flex items-center gap-3">
                        <span className="font-extrabold text-[#1E293B]">DocuVerify AI</span>
                        <span>·</span>
                        <span>Enterprise Document Verification &amp; Expense Auditing</span>
                    </div>
                    <div className="flex items-center gap-4 text-[11px]">
                        <span>Human-in-the-loop AI</span>
                        <span>·</span>
                        <span>Role-Based Access Control</span>
                        <span>·</span>
                        <span>Deterministic Evidence</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}