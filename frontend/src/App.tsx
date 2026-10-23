import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import AppLayout from './layouts/AppLayout';
import DashboardPage from './pages/DashboardPage';
import MyRequestsPage from './pages/MyRequestsPage';
import NewRequestPage from './pages/NewRequestPage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import DocumentHistoryPage from './pages/DocumentHistoryPage';
import AIAssistantPage from './pages/AIAssistantPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './pages/LoginPage';
import RequestDetailPage from './pages/RequestDetailPage';
import LandingPage from './pages/LandingPage';
import AuditTrailPage from './pages/AuditTrailPage';
import { FileQuestion } from 'lucide-react';
import type { UserRole } from './types';

/** Redirect unauthenticated users to /login */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-400 text-sm">
        Loading…
      </div>
    );
  }
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

/** Enforce role-based access for specific routes */
function RoleRoute({ children, allowed }: { children: React.ReactNode; allowed: UserRole[] }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-400 text-sm">
        Loading…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (!allowed.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function NotFoundPage() {
  const { user } = useAuth();
  return (
    <main className="grid min-h-screen place-items-center bg-[#f5f7fb] p-5">
      <section className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
          <FileQuestion className="h-6 w-6" />
        </span>
        <p className="mt-5 text-[10px] font-bold uppercase tracking-[.15em] text-indigo-600">
          Page not found · 404
        </p>
        <h1 className="mt-2 text-xl">This page isn’t here</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          The link may be outdated, or the address may have been typed incorrectly.
        </p>
        <Link className="btn-primary mt-5" to={user ? '/dashboard' : '/'}>
          Return to {user ? 'workspace' : 'home'}
        </Link>
      </section>
    </main>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<DashboardPage />} />
            <Route
              path="requests"
              element={
                <RoleRoute allowed={['submitter', 'admin']}>
                  <MyRequestsPage />
                </RoleRoute>
              }
            />
            <Route path="requests/:id" element={<RequestDetailPage />} />
            <Route
              path="new-request"
              element={
                <RoleRoute allowed={['submitter', 'admin']}>
                  <NewRequestPage />
                </RoleRoute>
              }
            />
            <Route
              path="review-queue"
              element={
                <RoleRoute allowed={['reviewer', 'approver', 'admin']}>
                  <ReviewQueuePage />
                </RoleRoute>
              }
            />
            <Route
              path="audit"
              element={
                <RoleRoute allowed={['approver', 'admin']}>
                  <AuditTrailPage />
                </RoleRoute>
              }
            />
            <Route path="history" element={<DocumentHistoryPage />} />
            <Route path="assistant" element={<AIAssistantPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
