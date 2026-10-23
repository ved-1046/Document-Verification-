import { useState, type FormEvent } from 'react';
import axios from 'axios';
import { Eye, EyeOff, Lock, Mail, ShieldCheck, FileText, ClipboardCheck, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';
import type { AuthToken, User } from '../types';

type PresetRole = 'submitter' | 'reviewer' | 'approver';

interface RolePreset {
    id: PresetRole;
    label: string;
    sublabel: string;
    email: string;
    icon: React.ComponentType<{ className?: string }>;
    accentColor: string;
    activeTabClass: string;
    pillClass: string;
}

const PRESETS: RolePreset[] = [
    {
        id: 'submitter',
        label: 'Submitter',
        sublabel: 'My Expenses',
        email: 'submitter@example.com',
        icon: FileText,
        accentColor: '#0F9D8A',
        activeTabClass: 'border-[#0F9D8A] bg-[#0F9D8A]/10 text-[#0F9D8A] ring-1 ring-[#0F9D8A]/30',
        pillClass: 'bg-teal-50 text-[#0F9D8A] border-teal-200',
    },
    {
        id: 'reviewer',
        label: 'Reviewer',
        sublabel: 'Verification Center',
        email: 'reviewer@example.com',
        icon: ClipboardCheck,
        accentColor: '#3478F6',
        activeTabClass: 'border-[#3478F6] bg-[#3478F6]/10 text-[#3478F6] ring-1 ring-[#3478F6]/30',
        pillClass: 'bg-blue-50 text-[#3478F6] border-blue-200',
    },
    {
        id: 'approver',
        label: 'Approver',
        sublabel: 'Decision Center',
        email: 'approver@example.com',
        icon: ShieldCheck,
        accentColor: '#7656D6',
        activeTabClass: 'border-[#7656D6] bg-[#7656D6]/10 text-[#7656D6] ring-1 ring-[#7656D6]/30',
        pillClass: 'bg-violet-50 text-[#7656D6] border-violet-200',
    },
];

function loginErrorMessage(err: unknown): string {
    if (axios.isAxiosError(err)) {
        if (!err.response) {
            return 'Cannot reach the API. Please ensure the backend server is running on port 8080.';
        }
        const detail = err.response.data?.detail;
        if (typeof detail === 'string') {
            return detail;
        }
        if (Array.isArray(detail) && detail[0]?.msg) {
            return String(detail[0].msg);
        }
    }
    return 'Invalid email or password. Please verify your credentials and try again.';
}

export default function LoginPage() {
    const { login } = useAuth();
    const navigate = useNavigate();

    const [selectedRole, setSelectedRole] = useState<PresetRole>('submitter');
    const [email, setEmail] = useState('submitter@example.com');
    const [password, setPassword] = useState('password123');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    function handleSelectPreset(role: PresetRole) {
        setSelectedRole(role);
        setError(null);
        if (role === 'submitter') {
            setEmail('submitter@example.com');
        } else if (role === 'reviewer') {
            setEmail('reviewer@example.com');
        } else if (role === 'approver') {
            setEmail('approver@example.com');
        }
        setPassword('password123');
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setError(null);

        const cleanEmail = email.trim();
        if (!cleanEmail) {
            setError('Please enter your email address.');
            return;
        }
        if (!password) {
            setError('Please enter your password.');
            return;
        }

        setLoading(true);
        try {
            // 1. Authenticate with backend API
            const tokenRes = await api.post<AuthToken>('/auth/login', {
                email: cleanEmail,
                password,
            });
            const token = tokenRes.data.access_token;

            // 2. Fetch authenticated user profile to verify actual role from database
            const meRes = await api.get<User>('/auth/me', {
                headers: { Authorization: `Bearer ${token}` },
            });
            const authenticatedUser = meRes.data;

            // 3. Save authenticated session and navigate to dashboard
            login(token, authenticatedUser);
            navigate('/dashboard');
        } catch (err) {
            setError(loginErrorMessage(err));
        } finally {
            setLoading(false);
        }
    }

    const activePreset = PRESETS.find((p) => p.id === selectedRole) ?? PRESETS[0];

    return (
        <div className="flex min-h-screen w-full bg-[#F5F7FB]">
            {/* LEFT PANEL: Deep Navy Branding (#14213D) */}
            <div className="hidden lg:flex lg:w-[48%] xl:w-[45%] flex-col justify-between bg-[#14213D] p-12 xl:p-16 text-white relative overflow-hidden select-none">
                {/* Brand Header */}
                <div className="relative z-10 flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
                        <ShieldCheck className="h-5 w-5 text-teal-400" />
                    </span>
                    <div className="flex items-center gap-2">
                        <span className="text-lg font-bold tracking-tight text-white">DocuVerify</span>
                        <span className="rounded bg-[#3478F6] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white">
                            AI
                        </span>
                    </div>
                </div>

                {/* Center Content: Exact Required Heading, Subtitle & Abstract Verification Visual */}
                <div className="relative z-10 my-auto py-10 space-y-8 max-w-lg">
                    <div className="space-y-3">
                        <h1 className="text-3xl xl:text-4xl font-extrabold tracking-tight text-white leading-tight">
                            Documents you can trust.
                        </h1>
                        <p className="text-sm xl:text-base text-slate-300 leading-relaxed font-normal">
                            Verify expenses. Find mismatches. Make informed decisions.
                        </p>
                    </div>

                    {/* Subtle, Elegant Abstract Verification Graphic */}
                    <div className="relative w-full max-w-sm pt-4">
                        {/* Soft Ambient Radial Glow */}
                        <div className="absolute inset-0 bg-radial from-teal-500/10 via-[#3478F6]/10 to-transparent rounded-3xl blur-2xl pointer-events-none" />

                        {/* Layered Document Visual */}
                        <div className="relative rounded-2xl border border-white/15 bg-white/[0.06] backdrop-blur-md p-6 shadow-2xl space-y-5 transition-transform duration-300 hover:-translate-y-0.5">
                            <div className="flex items-center justify-between border-b border-white/10 pb-4">
                                <div className="flex items-center gap-2.5">
                                    <div className="h-3 w-24 bg-white/40 rounded-full" />
                                    <div className="h-2 w-12 bg-white/20 rounded-full" />
                                </div>
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-500/20 border border-teal-400/30 px-2.5 py-0.5 text-[11px] font-semibold text-teal-300">
                                    <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-pulse" />
                                    OCR Extracted
                                </span>
                            </div>

                            {/* Minimal Field Verification Rows */}
                            <div className="space-y-2.5 text-xs">
                                <div className="flex items-center justify-between py-1 border-b border-white/5">
                                    <span className="text-slate-400">Total Claimed</span>
                                    <span className="font-mono font-bold text-white">₹2,450.00</span>
                                </div>
                                <div className="flex items-center justify-between py-1 border-b border-white/5">
                                    <span className="text-slate-400">Receipt Extracted</span>
                                    <span className="font-mono font-bold text-teal-300">₹2,450.00</span>
                                </div>
                                <div className="flex items-center justify-between py-1">
                                    <span className="text-slate-400">Verification Result</span>
                                    <span className="font-semibold text-teal-300 flex items-center gap-1">
                                        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 stroke-current fill-none stroke-[3]" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M5 13l4 4L19 7" />
                                        </svg>
                                        Exact Match
                                    </span>
                                </div>
                            </div>

                            {/* Verification Seal Badge */}
                            <div className="rounded-xl border border-teal-400/20 bg-teal-500/10 p-3 text-center">
                                <p className="text-[11px] font-semibold text-teal-200">
                                    Automated Cross-Document Verification Active
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Left Panel Footer */}
                <div className="relative z-10 text-xs text-slate-400 font-medium">
                    Enterprise Financial Integrity Platform
                </div>
            </div>

            {/* RIGHT PANEL: Clean White Background & Attractive Login Form */}
            <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-10 lg:p-14">
                <div className="w-full max-w-[420px] space-y-6">
                    {/* Header */}
                    <div className="space-y-2 text-center sm:text-left">
                        {/* Mobile Brand Bar */}
                        <div className="inline-flex items-center gap-2 rounded-lg bg-[#14213D] px-3 py-1.5 text-xs font-bold text-white mb-2 lg:hidden shadow-xs">
                            <ShieldCheck className="h-4 w-4 text-teal-400" />
                            <span>DocuVerify AI</span>
                        </div>
                        <h2 className="text-2xl font-bold tracking-tight text-[#1E293B] sm:text-3xl">
                            Sign in to your account
                        </h2>
                        <p className="text-xs sm:text-sm text-[#64748B]">
                            Select a role or enter your credentials to access your workspace.
                        </p>
                    </div>

                    {/* Role Presets Selector Tabs (For seamless role evaluation) */}
                    <div className="space-y-1.5">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                            Workspace Profile
                        </p>
                        <div className="grid grid-cols-3 gap-2">
                            {PRESETS.map((preset) => {
                                const Icon = preset.icon;
                                const isSelected = selectedRole === preset.id;
                                return (
                                    <button
                                        key={preset.id}
                                        type="button"
                                        onClick={() => handleSelectPreset(preset.id)}
                                        className={`flex flex-col items-center gap-1.5 rounded-xl border p-2.5 text-center transition-all ${
                                            isSelected
                                                ? preset.activeTabClass
                                                : 'border-[#E2E8F0] bg-white text-[#64748B] hover:border-slate-300 hover:bg-slate-50/70'
                                        }`}
                                    >
                                        <Icon className="h-4 w-4 shrink-0" />
                                        <div className="min-w-0">
                                            <p className="text-xs font-bold text-[#1E293B] leading-tight">
                                                {preset.label}
                                            </p>
                                            <p className="text-[10px] text-[#64748B] truncate mt-0.5">
                                                {preset.sublabel}
                                            </p>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Login Card */}
                    <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 sm:p-7 shadow-card space-y-5">
                        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
                            {/* Email */}
                            <div>
                                <label className="form-label text-xs font-semibold text-[#1E293B]" htmlFor="email">
                                    Email address
                                </label>
                                <div className="relative">
                                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B]">
                                        <Mail className="h-4 w-4" />
                                    </span>
                                    <input
                                        id="email"
                                        type="email"
                                        className="form-input pl-9 text-xs"
                                        placeholder="name@example.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>

                            {/* Password */}
                            <div>
                                <label className="form-label text-xs font-semibold text-[#1E293B]" htmlFor="password">
                                    Password
                                </label>
                                <div className="relative">
                                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B]">
                                        <Lock className="h-4 w-4" />
                                    </span>
                                    <input
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        className="form-input pl-9 pr-9 text-xs"
                                        placeholder="••••••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                    />
                                    <button
                                        type="button"
                                        className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-[#64748B] transition hover:text-[#1E293B]"
                                        onClick={() => setShowPassword(!showPassword)}
                                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>

                            {/* Error Alert */}
                            {error && (
                                <div
                                    role="alert"
                                    className="rounded-xl border border-red-200 bg-[#FEF2F2] p-3 text-xs text-[#DC2626] leading-relaxed font-medium"
                                >
                                    {error}
                                </div>
                            )}

                            {/* Submit Button */}
                            <button
                                type="submit"
                                disabled={loading}
                                className={`w-full py-2.5 rounded-lg text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-2 text-white ${
                                    selectedRole === 'submitter'
                                        ? 'bg-[#0F9D8A] hover:bg-[#0D8675]'
                                        : selectedRole === 'reviewer'
                                        ? 'bg-[#3478F6] hover:bg-[#2563EB]'
                                        : 'bg-[#7656D6] hover:bg-[#6845C9]'
                                }`}
                            >
                                {loading ? (
                                    <span className="inline-flex items-center gap-2">
                                        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                        Authenticating…
                                    </span>
                                ) : (
                                    <>
                                        <span>Sign in to {activePreset.sublabel}</span>
                                        <ArrowRight className="h-3.5 w-3.5" />
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    {/* Bottom Helper Note */}
                    <div className="text-center text-xs text-[#64748B]">
                        Authorized access for registered organizational users.
                    </div>
                </div>
            </div>
        </div>
    );
}
