import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    FileText,
    PlusCircle,
    ClipboardList,
    History,
    MessageSquare,
    Settings,
    LogOut,
    ShieldCheck,
    Menu,
    X,
    ChevronRight,
    ClipboardCheck,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import type { UserRole } from '../types';

interface NavItem {
    to: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    roles?: UserRole[];
    badge?: string;
    section: 'operations' | 'intelligence' | 'system';
}

export default function AppLayout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [menuOpen, setMenuOpen] = useState(false);

    const userRole = user?.role ?? 'submitter';

    // Role-specific navigation items and nomenclature
    const navItems: NavItem[] = [
        { to: '/dashboard', label: 'Overview', icon: LayoutDashboard, section: 'operations' },
        { to: '/requests', label: 'My Expenses', icon: FileText, roles: ['submitter', 'admin'], section: 'operations' },
        { to: '/new-request', label: 'New Expense Claim', icon: PlusCircle, roles: ['submitter', 'admin'], section: 'operations' },
        {
            to: '/review-queue',
            label: userRole === 'approver' ? 'Decision Center' : 'Verification Center',
            icon: userRole === 'approver' ? ShieldCheck : ClipboardList,
            roles: ['reviewer', 'approver', 'admin'],
            section: 'operations',
        },
        { to: '/history', label: 'Document History', icon: History, section: 'intelligence' },
        { to: '/audit', label: 'Audit Trail', icon: ClipboardCheck, roles: ['approver', 'admin'], section: 'intelligence' },
        { to: '/assistant', label: 'AI Assistant', icon: MessageSquare, badge: 'AI', section: 'intelligence' },
        {
            to: '/settings',
            label: userRole === 'admin' ? 'Account & Users' : 'Account & Profile',
            icon: Settings,
            section: 'system',
        },
    ];

    const visibleItems = navItems.filter(
        (item) => !item.roles || (user && item.roles.includes(user.role))
    );

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    // Role styling accents
    const roleThemes = {
        submitter: {
            title: 'My Expenses',
            pill: 'bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30',
            activeNav: 'text-teal-300',
            activeBar: 'bg-[#0F9D8A]',
            logoBg: 'bg-[#0F9D8A]',
            avatarBg: 'bg-teal-500/20 text-teal-200 ring-teal-400/30',
        },
        reviewer: {
            title: 'Verification Center',
            pill: 'bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30',
            activeNav: 'text-blue-300',
            activeBar: 'bg-[#3478F6]',
            logoBg: 'bg-[#3478F6]',
            avatarBg: 'bg-blue-500/20 text-blue-200 ring-blue-400/30',
        },
        approver: {
            title: 'Decision Center',
            pill: 'bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/30',
            activeNav: 'text-violet-300',
            activeBar: 'bg-[#7656D6]',
            logoBg: 'bg-[#7656D6]',
            avatarBg: 'bg-violet-500/20 text-violet-200 ring-violet-400/30',
        },
        admin: {
            title: 'Admin Console',
            pill: 'bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30',
            activeNav: 'text-blue-300',
            activeBar: 'bg-[#3478F6]',
            logoBg: 'bg-[#14213D]',
            avatarBg: 'bg-slate-500/20 text-slate-200 ring-slate-400/30',
        },
    };

    const theme = roleThemes[userRole] ?? roleThemes.submitter;

    const renderNavSection = (section: 'operations' | 'intelligence' | 'system', title: string) => {
        const items = visibleItems.filter((i) => i.section === section);
        if (items.length === 0) return null;
        return (
            <div key={section} className="mb-4">
                <div className="px-3 pb-1 text-[9px] font-bold uppercase tracking-[.18em] text-slate-400">
                    {title}
                </div>
                <div className="space-y-0.5">
                    {items.map(({ to, label, icon: Icon, badge: itemBadge }) => (
                        <NavLink
                            key={to}
                            to={to}
                            onClick={() => setMenuOpen(false)}
                            className={({ isActive }) =>
                                `group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-all duration-150 ${
                                    isActive
                                        ? 'bg-white/10 text-white font-semibold'
                                        : 'text-slate-300 hover:bg-white/[0.06] hover:text-white'
                                }`
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    {isActive && (
                                        <span
                                            className={`absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full ${theme.activeBar}`}
                                        />
                                    )}
                                    <Icon
                                        className={`h-4 w-4 shrink-0 transition-colors ${
                                            isActive ? theme.activeNav : 'text-slate-300 group-hover:text-white'
                                        }`}
                                    />
                                    <span className="flex-1 truncate">{label}</span>
                                    {itemBadge && (
                                        <span className="rounded bg-[#8B5CF6]/30 px-1.5 py-0.5 text-[9px] font-bold text-[#DDD6FE]">
                                            {itemBadge}
                                        </span>
                                    )}
                                    {isActive && <ChevronRight className="h-3 w-3 text-slate-400 shrink-0" />}
                                </>
                            )}
                        </NavLink>
                    ))}
                </div>
            </div>
        );
    };

    const sidebar = (
        <div className="flex h-full flex-col justify-between bg-[#14213D] text-slate-200">
            <div>
                {/* Brand Header */}
                <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
                    <span
                        className={`flex h-8 w-8 items-center justify-center rounded-lg text-white shadow-sm ${theme.logoBg}`}
                    >
                        <ShieldCheck className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                            <span className="block text-sm font-bold leading-tight tracking-tight text-white">
                                DocuVerify
                            </span>
                            <span className="rounded bg-[#8B5CF6] px-1 py-0.2 text-[8px] font-bold uppercase tracking-wider text-white">
                                AI
                            </span>
                        </div>
                        <span className="block truncate text-[10px] font-medium text-slate-300">
                            {theme.title}
                        </span>
                    </div>
                </div>

                {/* Nav Links Grouped */}
                <nav className="flex-1 px-2.5 pt-4" aria-label="Main navigation">
                    {renderNavSection('operations', 'Operations')}
                    {renderNavSection('intelligence', 'Verification & Intelligence')}
                    {renderNavSection('system', 'System')}
                </nav>
            </div>

            {/* Bottom Status & Profile */}
            <div className="space-y-2 p-2.5 border-t border-white/10">
                {/* Engine Health Indicator */}
                <div className="flex items-center justify-between px-2 py-0.5 text-[10px] text-slate-300">
                    <span className="flex items-center gap-1.5 font-medium">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#0F9D8A] animate-pulse" />
                        AI Engine Active
                    </span>
                    <span className="font-mono text-[9px] text-slate-400">OCR &amp; Verification</span>
                </div>

                {/* User Profile Footer */}
                {user && (
                    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-2">
                        <div className="flex items-center gap-2.5">
                            <div
                                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-bold uppercase ring-1 ring-inset ${theme.avatarBg}`}
                            >
                                {user.display_name.charAt(0)}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="truncate text-xs font-semibold text-white leading-tight">{user.display_name}</p>
                                <span
                                    className={`inline-block rounded px-1.5 py-0.2 text-[8px] font-bold uppercase tracking-wider ${theme.pill}`}
                                >
                                    {user.role}
                                </span>
                            </div>
                            <button
                                onClick={handleLogout}
                                title="Log out"
                                aria-label="Log out"
                                className="rounded p-1 text-slate-300 transition hover:bg-white/10 hover:text-white"
                            >
                                <LogOut className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <div className="flex min-h-screen bg-[#F5F7FB] text-[#20263A]">
            {/* Desktop Sidebar */}
            <aside className="hidden w-[240px] shrink-0 flex-col bg-[#172554] border-r border-white/10 shadow-sm lg:flex">
                {sidebar}
            </aside>

            {/* Mobile Navigation Drawer */}
            {menuOpen && (
                <div className="fixed inset-0 z-40 lg:hidden">
                    <button
                        aria-label="Close navigation"
                        className="absolute inset-0 bg-[#0F172A]/70 backdrop-blur-xs"
                        onClick={() => setMenuOpen(false)}
                    />
                    <aside className="relative flex h-full w-[260px] flex-col bg-[#172554] shadow-xl">
                        {sidebar}
                    </aside>
                </div>
            )}

            {/* Main Application Area */}
            <div className="flex min-h-screen min-w-0 flex-1 flex-col">
                <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-[#E3E8F0] bg-white/95 px-4 backdrop-blur-md sm:px-6">
                    <div className="flex items-center gap-3">
                        <button
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
                            onClick={() => setMenuOpen(true)}
                            aria-label="Open navigation"
                        >
                            <Menu className="h-5 w-5" />
                        </button>
                        <span className="text-xs font-bold text-[#20263A] lg:hidden">DocuVerify AI</span>

                        {/* Breadcrumb Context Indicator */}
                        <div className="hidden items-center gap-2 text-xs sm:flex">
                            <span className="font-medium text-[#697386]">DocuVerify</span>
                            <span className="text-[#E3E8F0]">/</span>
                            <span className="font-semibold text-[#20263A]">{theme.title}</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="hidden items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-2.5 py-0.5 text-[10px] font-semibold text-[#0F9D8A] sm:flex">
                            <span className="h-1.5 w-1.5 rounded-full bg-[#0F9D8A] animate-pulse" />
                            Live Verification
                        </div>
                        <div className="hidden h-3.5 w-px bg-[#E3E8F0] sm:block" />
                        <span className="hidden text-xs font-semibold text-[#20263A] sm:block">
                            {user?.display_name}
                        </span>
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-[#20263A] shadow-xs ring-1 ring-[#E3E8F0]">
                            <ShieldCheck className="h-3.5 w-3.5 text-[#4F46E5]" />
                        </div>
                    </div>
                </header>

                <main className="min-w-0 flex-1">
                    <Outlet />
                </main>
            </div>

            {menuOpen && (
                <button
                    className="fixed right-4 top-4 z-50 rounded-lg bg-white p-2 text-slate-700 shadow-lg lg:hidden"
                    onClick={() => setMenuOpen(false)}
                    aria-label="Close navigation"
                >
                    <X className="h-5 w-5" />
                </button>
            )}
        </div>
    );
}
