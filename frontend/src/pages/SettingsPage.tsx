import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { KeyRound, Plus, ShieldCheck, Users, Search } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { ManagedUser, UserRole } from '../types';

const roles: UserRole[] = ['submitter', 'reviewer', 'approver', 'admin'];

export default function SettingsPage() {
    const { user } = useAuth();
    const isAdmin = user?.role === 'admin';
    const [users, setUsers] = useState<ManagedUser[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');
    const [created, setCreated] = useState<ManagedUser | null>(null);
    const [editing, setEditing] = useState<ManagedUser | null>(null);
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [role, setRole] = useState<UserRole>('submitter');
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('all');
    const [statusFilter, setStatusFilter] = useState('all');
    const [editName, setEditName] = useState('');
    const [editEmail, setEditEmail] = useState('');

    const loadUsers = useCallback(async () => {
        if (!isAdmin) return;
        setLoading(true);
        try {
            setUsers((await api.get<ManagedUser[]>('/admin/users')).data);
        } catch {
            setError('Could not load the user directory.');
        } finally {
            setLoading(false);
        }
    }, [isAdmin]);

    useEffect(() => {
        void loadUsers();
    }, [loadUsers]);

    async function createUser(event: FormEvent) {
        event.preventDefault();
        setError('');
        setNotice('');
        try {
            const response = await api.post<ManagedUser>('/admin/users', { display_name: name, email, role, is_active: true });
            setCreated(response.data);
            setName('');
            setEmail('');
            setRole('submitter');
            await loadUsers();
        } catch (err) {
            setError((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Could not create this account.');
        }
    }

    async function updateUser(person: ManagedUser, changes: Partial<ManagedUser>) {
        setError('');
        setNotice('');
        const sensitive = changes.is_active === false || (changes.role && changes.role !== person.role);
        if (sensitive && !window.confirm(`Apply this account change for ${person.display_name}? Role and activation changes affect access immediately.`)) return;
        try {
            await api.patch(`/admin/users/${person.id}`, changes);
            setNotice(`${person.display_name}'s account was updated.`);
            await loadUsers();
        } catch (err) {
            setError((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Could not update this account.');
        }
    }

    const visibleUsers = useMemo(() => users.filter(person => {
        const matchesText = `${person.display_name} ${person.email}`.toLowerCase().includes(search.toLowerCase());
        return matchesText && (roleFilter === 'all' || person.role === roleFilter) && (statusFilter === 'all' || String(person.is_active) === statusFilter);
    }), [users, search, roleFilter, statusFilter]);

    async function changePassword(event: FormEvent) {
        event.preventDefault();
        setError('');
        setNotice('');
        if (newPassword !== confirmPassword) {
            setError('The new passwords do not match.');
            return;
        }
        try {
            await api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword });
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
            setNotice('Password changed successfully.');
        } catch (err) {
            setError((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Could not change the password.');
        }
    }

    async function saveProfile(event: FormEvent) {
        event.preventDefault();
        if (!editing) return;
        try {
            await api.patch(`/admin/users/${editing.id}`, { display_name: editName, email: editEmail });
            setEditing(null);
            setNotice('Profile details updated.');
            await loadUsers();
        } catch (err) {
            setError((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Could not update profile details.');
        }
    }

    return (
        <div className="page-wrap mx-auto max-w-5xl space-y-7">
            <header>
                <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.15em] text-indigo-700 shadow-xs">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Workspace Controls &amp; Security
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-main sm:text-3xl">Account &amp; Security</h1>
                <p className="mt-1 text-sm text-muted">
                    Manage your sign-in credentials and, for administrators, platform user identities and permissions.
                </p>
            </header>

            {(error || notice) && (
                <div role={error ? 'alert' : 'status'} className={`rounded-xl border p-4 text-xs font-semibold ${error ? 'border-red-200 bg-red-50 text-red-700' : 'border-teal-200 bg-teal-50 text-teal-800'}`}>
                    {error || notice}
                </div>
            )}

            {/* Change Password */}
            <section className="card overflow-hidden">
                <div className="flex items-center gap-3 border-b border-surface-border bg-slate-50/70 px-6 py-4">
                    <span className="rounded-xl bg-indigo-50 p-2 text-indigo-700 ring-1 ring-indigo-200/50">
                        <KeyRound className="h-4 w-4" />
                    </span>
                    <div>
                        <h2 className="text-sm font-bold text-main">Change Password</h2>
                        <p className="mt-0.5 text-xs text-muted">Use a strong password with at least 10 characters.</p>
                    </div>
                </div>
                <form onSubmit={changePassword} className="p-6 grid gap-4 sm:grid-cols-3">
                    <div>
                        <label className="form-label" htmlFor="current-password">Current password</label>
                        <input id="current-password" className="form-input" type="password" autoComplete="current-password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required />
                    </div>
                    <div>
                        <label className="form-label" htmlFor="new-password">New password</label>
                        <input id="new-password" className="form-input" type="password" autoComplete="new-password" minLength={10} value={newPassword} onChange={e => setNewPassword(e.target.value)} required />
                    </div>
                    <div>
                        <label className="form-label" htmlFor="confirm-password">Confirm new password</label>
                        <input id="confirm-password" className="form-input" type="password" autoComplete="new-password" minLength={10} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required />
                    </div>
                    <div className="sm:col-span-3 pt-2">
                        <button className="btn-primary" type="submit">Update password</button>
                    </div>
                </form>
            </section>

            {!isAdmin ? (
                <section className="card p-6">
                    <div className="flex items-start gap-3">
                        <ShieldCheck className="mt-0.5 h-5 w-5 text-indigo-600" />
                        <div>
                            <h2 className="text-sm font-bold text-main">Identity &amp; Permissions</h2>
                            <p className="mt-1 text-xs text-muted font-medium">
                                Signed in as <strong className="text-main">{user?.display_name}</strong> ({user?.email}) · <span className="capitalize">{user?.role}</span>.
                            </p>
                            <p className="mt-2 text-xs text-muted">Contact an administrator to update your role or account details.</p>
                        </div>
                    </div>
                </section>
            ) : (
                <>
                    {/* Admin User Directory */}
                    <section className="card overflow-hidden">
                        <div className="flex items-center gap-3 border-b border-surface-border bg-slate-50/70 px-6 py-4">
                            <span className="rounded-xl bg-indigo-50 p-2 text-indigo-700 ring-1 ring-indigo-200/50">
                                <Users className="h-4 w-4" />
                            </span>
                            <div>
                                <h2 className="text-sm font-bold text-main">User Directory &amp; Roles</h2>
                                <p className="mt-0.5 text-xs text-muted">Role changes take effect immediately across all workspaces.</p>
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-2 border-b border-surface-border p-4 bg-white">
                            <div className="relative flex-1 min-w-[200px]">
                                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                                <input className="form-input py-2 pl-9 text-xs" type="search" aria-label="Search users" placeholder="Search name or email" value={search} onChange={e => setSearch(e.target.value)} />
                            </div>
                            <select className="form-input w-auto py-2 text-xs font-medium" aria-label="Filter by role" value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
                                <option value="all">All roles</option>
                                {roles.map(item => <option key={item} value={item}>{item}</option>)}
                            </select>
                            <select className="form-input w-auto py-2 text-xs font-medium" aria-label="Filter by account status" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                                <option value="all">All statuses</option>
                                <option value="true">Active</option>
                                <option value="false">Inactive</option>
                            </select>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[760px] text-left text-xs">
                                <thead className="bg-slate-50/70 text-[10px] font-bold uppercase tracking-wider text-muted">
                                    <tr>
                                        <th className="px-6 py-3.5">Person</th>
                                        <th className="px-4 py-3.5">Role</th>
                                        <th className="px-4 py-3.5">Status</th>
                                        <th className="px-4 py-3.5">Created</th>
                                        <th className="px-6 py-3.5 text-right">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-surface-border">
                                    {visibleUsers.map(person => (
                                        <tr key={person.id} className="hover:bg-slate-50/80 transition-colors">
                                            <td className="px-6 py-4">
                                                <p className="font-bold text-main">{person.display_name}</p>
                                                <p className="mt-0.5 text-muted">{person.email}</p>
                                            </td>
                                            <td className="px-4 py-4">
                                                <select
                                                    aria-label={`Role for ${person.display_name}`}
                                                    className="form-input py-1.5 text-xs font-semibold"
                                                    value={person.role}
                                                    onChange={e => void updateUser(person, { role: e.target.value as UserRole })}
                                                >
                                                    <option value="submitter">Submitter</option>
                                                    <option value="reviewer">Reviewer</option>
                                                    <option value="approver">Approver</option>
                                                    <option value="admin">Administrator</option>
                                                </select>
                                            </td>
                                            <td className="px-4 py-4">
                                                <button
                                                    type="button"
                                                    className={`rounded-full px-3 py-1 text-[10px] font-bold ${person.is_active ? 'bg-teal-50 text-teal-700 ring-1 ring-teal-200' : 'bg-slate-100 text-slate-500'}`}
                                                    onClick={() => void updateUser(person, { is_active: !person.is_active })}
                                                >
                                                    {person.is_active ? 'Active' : 'Inactive'}
                                                </button>
                                            </td>
                                            <td className="px-4 py-4 text-muted font-medium">
                                                {new Date(person.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button
                                                    type="button"
                                                    className="font-bold text-indigo-700 hover:text-indigo-900 transition-colors"
                                                    onClick={() => { setEditName(person.display_name); setEditEmail(person.email); setEditing(person); }}
                                                >
                                                    Edit
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {loading && <p className="p-4 text-xs text-muted">Loading directory…</p>}
                            {!loading && visibleUsers.length === 0 && <p className="p-8 text-center text-xs text-muted">No accounts match these filters.</p>}
                        </div>
                    </section>

                    {/* Add User */}
                    <section className="card overflow-hidden">
                        <div className="flex items-center gap-3 border-b border-surface-border bg-slate-50/70 px-6 py-4">
                            <span className="rounded-xl bg-teal-50 p-2 text-teal-700 ring-1 ring-teal-200/50">
                                <Plus className="h-4 w-4" />
                            </span>
                            <div>
                                <h2 className="text-sm font-bold text-main">Provision New Account</h2>
                                <p className="mt-0.5 text-xs text-muted">A secure one-time password will be generated for the new user.</p>
                            </div>
                        </div>
                        <form onSubmit={createUser} className="p-6 grid gap-4 sm:grid-cols-3">
                            <div>
                                <label className="form-label" htmlFor="person-name">Full name</label>
                                <input id="person-name" className="form-input" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required maxLength={100} />
                            </div>
                            <div>
                                <label className="form-label" htmlFor="person-email">Work email</label>
                                <input id="person-email" className="form-input" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required />
                            </div>
                            <div>
                                <label className="form-label" htmlFor="person-role">Role</label>
                                <select id="person-role" className="form-input font-medium" value={role} onChange={e => setRole(e.target.value as UserRole)}>
                                    {roles.map(item => <option key={item} value={item}>{item === 'admin' ? 'Administrator' : item[0].toUpperCase() + item.slice(1)}</option>)}
                                </select>
                            </div>
                            <div className="sm:col-span-3 pt-2">
                                <button className="btn-primary" type="submit">Create account</button>
                            </div>
                        </form>
                    </section>
                </>
            )}

            {created?.temporary_password && (
                <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/60 backdrop-blur-xs p-4" role="presentation">
                    <section role="dialog" aria-modal="true" aria-labelledby="temp-password-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">Account Provisioned</p>
                        <h2 id="temp-password-title" className="text-base font-bold text-main">Share Temporary Credentials</h2>
                        <p className="text-xs leading-relaxed text-muted font-medium">
                            Give this one-time password to {created.display_name} through your approved secure channel.
                        </p>
                        <code className="block break-all rounded-xl border border-surface-border bg-slate-50 p-4 font-mono text-sm font-bold text-main">
                            {created.temporary_password}
                        </code>
                        <button className="btn-primary w-full" onClick={() => setCreated(null)}>
                            Done
                        </button>
                    </section>
                </div>
            )}

            {editing && (
                <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/60 backdrop-blur-xs p-4">
                    <form onSubmit={saveProfile} role="dialog" aria-modal="true" aria-labelledby="edit-user-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">User Profile</p>
                        <h2 id="edit-user-title" className="text-base font-bold text-main">Edit {editing.display_name}</h2>
                        <div>
                            <label className="form-label" htmlFor="edit-user-name">Full name</label>
                            <input id="edit-user-name" className="form-input" value={editName} onChange={e => setEditName(e.target.value)} required maxLength={100}/>
                        </div>
                        <div>
                            <label className="form-label" htmlFor="edit-user-email">Email address</label>
                            <input id="edit-user-email" type="email" className="form-input" value={editEmail} onChange={e => setEditEmail(e.target.value)} required/>
                        </div>
                        <div className="flex justify-end gap-2 pt-2">
                            <button type="button" className="btn-secondary text-xs" onClick={() => setEditing(null)}>Cancel</button>
                            <button type="submit" className="btn-primary text-xs">Save profile</button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
}
