import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { AgentDashboard } from './pages/AgentDashboard';
import { ProfilePage } from './pages/ProfilePage';
import { AdminDashboard } from './pages/AdminDashboard';
import { CreateTaskPage } from './pages/CreateTaskPage';

// Protected Route wrapper that redirects unauthenticated users
const ProtectedRoute = ({ children, allowedRole }) => {
  const { isAuthenticated, role, isInitializing } = useAuth();

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRole && role !== allowedRole) {
    // If user's role doesn't match this route, redirect to their assigned dashboard
    return <Navigate to={role === 'Administrator' || role === 'ADMIN' ? '/admin/dashboard' : '/dashboard'} replace />;
  }

  return children;
};

// Public Route wrapper that redirects already-authenticated users to their dashboard
const PublicOnlyRoute = ({ children }) => {
  const { isAuthenticated, role, isInitializing } = useAuth();

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to={role === 'Administrator' || role === 'ADMIN' ? '/admin/dashboard' : '/dashboard'} replace />;
  }

  return children;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Default and Login */}
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicOnlyRoute>
                <RegisterPage />
              </PublicOnlyRoute>
            }
          />

          {/* Role-Specific Dashboards & Agent Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AgentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute allowedRole="Agent">
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AgentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/dashboard"
            element={
              <ProtectedRoute allowedRole="Agent">
                <Navigate to="/dashboard" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute allowedRole="Administrator">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/tasks/create"
            element={
              <ProtectedRoute allowedRole="Administrator">
                <CreateTaskPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/tasks/:taskId/edit"
            element={
              <ProtectedRoute allowedRole="Administrator">
                <CreateTaskPage />
              </ProtectedRoute>
            }
          />

          {/* Catch-all redirect to /login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
