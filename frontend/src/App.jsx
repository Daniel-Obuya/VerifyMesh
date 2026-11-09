import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { AgentDashboard } from './pages/AgentDashboard';
import { ProfilePage } from './pages/ProfilePage';
import { AdminDashboard } from './pages/AdminDashboard';
import { CreateTaskPage } from './pages/CreateTaskPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { AssessmentResultsPage } from './pages/AssessmentResultsPage';
import { SupervisorVerifyPage } from './pages/SupervisorVerifyPage';

// Helper to check whether user has a workforce officer / operational admin role
const isWorkforceRole = (userRole) => 
  ['Workforce Officer', 'WORKFORCE_OFFICER', 'Administrator', 'ADMIN'].includes(userRole);

const getRoleDashboard = (userRole) =>
  isWorkforceRole(userRole) ? '/workforce/dashboard' : '/dashboard';

// Protected Route wrapper that redirects unauthenticated users
const ProtectedRoute = ({ children, allowedRole, allowedRoles }) => {
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

  const authorized = allowedRoles 
    ? allowedRoles.includes(role) || (allowedRoles.includes('Workforce Officer') && isWorkforceRole(role))
    : allowedRole
    ? role === allowedRole || (allowedRole === 'Workforce Officer' && isWorkforceRole(role)) || (allowedRole === 'Administrator' && isWorkforceRole(role))
    : true;

  if (!authorized) {
    return <Navigate to={getRoleDashboard(role)} replace />;
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
    return <Navigate to={getRoleDashboard(role)} replace />;
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

          {/* Public Supervisor Employment Verification Portal */}
          <Route path="/verify-experience" element={<SupervisorVerifyPage />} />

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
            path="/agent/assessment/:taskId"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AssessmentPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/assessment"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AssessmentPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/assessments/:taskId"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AssessmentPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/assessment/results/:attemptId"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AssessmentResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/assessments/results/:attemptId"
            element={
              <ProtectedRoute allowedRole="Agent">
                <AssessmentResultsPage />
              </ProtectedRoute>
            }
          />
          {/* Workforce Officer Portal Routes */}
          <Route
            path="/workforce/dashboard"
            element={
              <ProtectedRoute allowedRole="Workforce Officer">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workforce/tasks/create"
            element={
              <ProtectedRoute allowedRole="Workforce Officer">
                <CreateTaskPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workforce/tasks/:taskId/edit"
            element={
              <ProtectedRoute allowedRole="Workforce Officer">
                <CreateTaskPage />
              </ProtectedRoute>
            }
          />

          {/* Backward-Compatible Admin Redirects */}
          <Route
            path="/admin/dashboard"
            element={<Navigate to="/workforce/dashboard" replace />}
          />
          <Route
            path="/admin/tasks/create"
            element={<Navigate to="/workforce/tasks/create" replace />}
          />
          <Route
            path="/admin/tasks/:taskId/edit"
            element={<Navigate to="/workforce/tasks/:taskId/edit" replace />}
          />
          <Route
            path="/admin"
            element={<Navigate to="/workforce/dashboard" replace />}
          />

          {/* Catch-all redirect to /login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
