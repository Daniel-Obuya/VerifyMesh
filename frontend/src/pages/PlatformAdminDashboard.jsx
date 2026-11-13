import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { platformAdminService } from '../services/platformAdminService';
import { ThemeToggle } from '../components/common/ThemeToggle';
import {
  Shield,
  Users,
  Activity,
  Database,
  Cpu,
  RotateCcw,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Lock,
  UserCheck,
  Server,
  Key,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  LogOut,
  Sliders,
  LayoutGrid,
  FileText,
  Bell,
  ArrowRight,
  X
} from 'lucide-react';

export const PlatformAdminDashboard = () => {
  const { user, logout } = useAuth();
  const { isDark } = useTheme();

  // Navigation & Shell states
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'users' | 'roles' | 'audit' | 'assessments' | 'health' | 'ml'
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [moduleSearch, setModuleSearch] = useState('');
  const [timeframeDays, setTimeframeDays] = useState('30');
  const [showAlertsPopover, setShowAlertsPopover] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Data states
  const [overviewData, setOverviewData] = useState(null);
  const [usersData, setUsersData] = useState([]);
  const [userPagination, setUserPagination] = useState({ page: 1, total: 0, total_pages: 1 });
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('');
  const [userStatusFilter, setUserStatusFilter] = useState('');

  const [auditLogs, setAuditLogs] = useState([]);
  const [auditPagination, setAuditPagination] = useState({ page: 1, total: 0, total_pages: 1 });
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditSearch, setAuditSearch] = useState('');
  const [availableActions, setAvailableActions] = useState([]);

  // Assessments tab state
  const [assessmentsList, setAssessmentsList] = useState([]);
  const [assessmentSearch, setAssessmentSearch] = useState('');
  const [assessmentResultFilter, setAssessmentResultFilter] = useState('ALL');
  const [assessmentCompFilter, setAssessmentCompFilter] = useState('ALL');
  const [selectedAssessment, setSelectedAssessment] = useState(null);
  const [isAssessmentModalOpen, setIsAssessmentModalOpen] = useState(false);

  const [systemHealth, setSystemHealth] = useState(null);
  const [mlGovernance, setMlGovernance] = useState(null);

  const [isLoading, setIsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [feedback, setFeedback] = useState(null);

  // Navigation structure matching reference sidebar groups
  const navGroups = [
    {
      title: 'PLATFORM',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutGrid },
        { id: 'users', label: 'User Management', icon: Users },
        { id: 'roles', label: 'Roles & Permissions', icon: Key },
      ]
    },
    {
      title: 'GOVERNANCE',
      items: [
        { id: 'audit', label: 'Audit Logs', icon: FileText },
        { id: 'assessments', label: 'Assessments Audit', icon: CheckCircle2 },
      ]
    },
    {
      title: 'OPERATIONS',
      items: [
        { id: 'health', label: 'System Monitoring', icon: Activity },
        { id: 'ml', label: 'ML Model Governance', icon: Cpu },
      ]
    }
  ];

  const allNavItems = useMemo(() => navGroups.flatMap((g) => g.items), []);
  const activeTabMeta = allNavItems.find((i) => i.id === activeTab) || allNavItems[0];

  const filteredModules = useMemo(() => {
    const q = moduleSearch.trim().toLowerCase();
    if (!q) return [];
    return allNavItems.filter((item) => item.label.toLowerCase().includes(q));
  }, [moduleSearch, allNavItems]);

  // Unified VerifyMesh surface classes (Dark & Light mode)
  const shellBg = isDark ? 'bg-[#050814] text-slate-100' : 'bg-slate-50 text-slate-900';
  const sidebarBg = isDark ? 'bg-[#070b18] border-[#1b2542]' : 'bg-white border-slate-200';
  const headerBg = isDark ? 'bg-[#0b1020]/90 border-[#1b2542]' : 'bg-white/90 border-slate-200';
  const cardCls = isDark
    ? 'bg-[#0b1020] border border-[#1b2542] shadow-lg'
    : 'bg-white border border-slate-200 shadow-sm';
  const innerCardCls = isDark
    ? 'bg-[#0d1428] border border-[#1b2542]'
    : 'bg-slate-50 border border-slate-200';
  const inputCls = isDark
    ? 'bg-[#070b18] border border-[#1b2542] text-slate-100 placeholder-slate-500 focus:border-indigo-500'
    : 'bg-white border border-slate-300 text-slate-900 placeholder-slate-400 focus:border-indigo-600';
  const tableHeadCls = isDark
    ? 'bg-[#070b18] border-b border-[#1b2542] text-slate-400'
    : 'bg-slate-50 border-b border-slate-200 text-slate-500';
  const tableRowHover = isDark ? 'hover:bg-[#121a30]/60' : 'hover:bg-slate-50';
  const dividerCls = isDark ? 'divide-[#1b2542]' : 'divide-slate-200';
  const mutedText = isDark ? 'text-slate-400' : 'text-slate-500';
  const headingText = isDark ? 'text-white' : 'text-slate-900';

  const getCompetencyBadgeStyle = (competency) => {
    switch (competency) {
      case 'ELIGIBLE':
      case 'Eligible':
        return isDark
          ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40'
          : 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'NOT_ELIGIBLE':
      case 'Not Eligible':
        return isDark
          ? 'bg-rose-950/80 text-rose-300 border-rose-500/40'
          : 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return isDark
          ? 'bg-slate-800 text-slate-300 border-slate-700'
          : 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [userDetailLoading, setUserDetailLoading] = useState(false);

  // Load Overview Data
  const loadOverview = async (days = timeframeDays) => {
    try {
      const res = await platformAdminService.getOverview({ days });
      if (res?.success && res?.data) {
        setOverviewData(res.data);
      }
    } catch (err) {
      console.error('Failed to load overview:', err);
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load platform overview' });
    }
  };

  // Load Users
  const loadUsers = async (page = 1) => {
    try {
      const res = await platformAdminService.getUsers({
        page,
        limit: 15,
        search: userSearch,
        role: userRoleFilter,
        status: userStatusFilter
      });
      if (res?.success) {
        setUsersData(res.data || []);
        if (res.pagination) setUserPagination(res.pagination);
      }
    } catch (err) {
      console.error('Failed to load users:', err);
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load user directory' });
    }
  };

  // Open User Profile Modal
  const openUserProfile = async (userId) => {
    setIsUserModalOpen(true);
    setUserDetailLoading(true);
    setSelectedUserDetail(null);
    try {
      const res = await platformAdminService.getUserProfile(userId);
      if (res?.success && res?.data) {
        setSelectedUserDetail(res.data);
      }
    } catch (err) {
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load user profile' });
      setIsUserModalOpen(false);
    } finally {
      setUserDetailLoading(false);
    }
  };

  // Load Audit Logs
  const loadAuditLogs = async (page = 1) => {
    try {
      const res = await platformAdminService.getAuditLogs({
        page,
        limit: 20,
        search: auditSearch,
        action: auditActionFilter
      });
      if (res?.success) {
        setAuditLogs(res.data || []);
        if (res.pagination) setAuditPagination(res.pagination);
        if (res.available_actions) setAvailableActions(res.available_actions);
      }
    } catch (err) {
      console.error('Failed to load audit logs:', err);
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load audit logs' });
    }
  };

  // Load Assessments
  const loadAssessments = async () => {
    try {
      const res = await platformAdminService.getAssessments();
      if (res?.success && Array.isArray(res?.data)) {
        setAssessmentsList(res.data);
      } else if (Array.isArray(res?.data)) {
        setAssessmentsList(res.data);
      }
    } catch (err) {
      console.error('Failed to load assessments:', err);
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load assessments audit' });
    }
  };

  const filteredAssessments = useMemo(() => {
    return assessmentsList.filter((item) => {
      const q = assessmentSearch.toLowerCase().trim();
      const matchSearch = !q || (
        (item.agent_name && item.agent_name.toLowerCase().includes(q)) ||
        (item.agent_email && item.agent_email.toLowerCase().includes(q)) ||
        (item.exam_name && item.exam_name.toLowerCase().includes(q)) ||
        (item.category_name && item.category_name.toLowerCase().includes(q))
      );

      const isPassed = item.passed === 1 || item.passed === true || (item.assessment_score >= (item.passing_score || 70));
      const matchResult = assessmentResultFilter === 'ALL' ||
        (assessmentResultFilter === 'PASSED' && isPassed) ||
        (assessmentResultFilter === 'FAILED' && !isPassed);

      const matchComp = assessmentCompFilter === 'ALL' ||
        item.predicted_competency === assessmentCompFilter;

      return matchSearch && matchResult && matchComp;
    });
  }, [assessmentsList, assessmentSearch, assessmentResultFilter, assessmentCompFilter]);

  // Load Health & ML
  const loadHealth = async () => {
    try {
      const res = await platformAdminService.getSystemHealth();
      if (res && (res.success || res.status)) {
        setSystemHealth(res);
      }
    } catch (err) {
      console.error('Failed to load system health:', err);
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load system health telemetry' });
    }
  };

  const loadMlGovernance = async () => {
    try {
      const res = await platformAdminService.getMlModelGovernance();
      if (res?.success && res?.data) {
        setMlGovernance(res.data);
      }
    } catch (err) {
      console.error('Failed to load ML governance:', err);
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to load ML governance metadata' });
    }
  };

  const refreshCurrentTab = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      if (activeTab === 'overview') await loadOverview(timeframeDays);
      else if (activeTab === 'users' || activeTab === 'roles') await loadUsers(userPagination.page);
      else if (activeTab === 'audit') await loadAuditLogs(auditPagination.page);
      else if (activeTab === 'assessments') await loadAssessments();
      else if (activeTab === 'health') await loadHealth();
      else if (activeTab === 'ml') await loadMlGovernance();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshCurrentTab();
  }, [activeTab]);

  useEffect(() => {
    loadOverview(timeframeDays);
  }, [timeframeDays]);

  // Update user role handler
  const handleRoleChange = async (targetUserId, newRole) => {
    if (!window.confirm(`Are you sure you want to change this user's role to ${newRole}?`)) return;
    setActionLoading(targetUserId);
    setFeedback(null);
    try {
      const res = await platformAdminService.updateUserRole(targetUserId, newRole);
      if (res?.success) {
        setFeedback({ type: 'success', message: res.message });
        loadUsers(userPagination.page);
        loadOverview(timeframeDays);
      }
    } catch (err) {
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to update role' });
    } finally {
      setActionLoading(null);
    }
  };

  // Toggle user status handler
  const handleStatusToggle = async (targetUserId, currentStatus) => {
    const action = currentStatus ? 'suspend' : 'activate';
    if (!window.confirm(`Are you sure you want to ${action} this user's account?`)) return;
    setActionLoading(targetUserId);
    setFeedback(null);
    try {
      const res = await platformAdminService.updateUserStatus(targetUserId, !currentStatus);
      if (res?.success) {
        setFeedback({ type: 'success', message: res.message });
        loadUsers(userPagination.page);
        loadOverview(timeframeDays);
      }
    } catch (err) {
      setFeedback({ type: 'error', message: err?.data?.error || err?.message || 'Failed to update status' });
    } finally {
      setActionLoading(null);
    }
  };

  // User display helpers
  const fullName = user?.fullName || 'John Nyabuto';
  const firstName = fullName.split(' ')[0] || 'John';
  const initials = fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join('') || 'JN';

  // Derived real metrics for Overview charts
  const totalUsers = Number(overviewData?.users?.total_users || 0);
  const activeUsers = Number(overviewData?.users?.active_users || 0);
  const suspendedUsers = Number(overviewData?.users?.suspended_users || 0);
  const pendingVerification = Number(overviewData?.users?.pending_verification || 0);
  const unverifiedEmail = Number(overviewData?.users?.unverified_email_users || 0);
  const totalAgents = Number(overviewData?.users?.total_agents || 0);
  const totalOfficers = Number(overviewData?.users?.total_officers || 0);
  const totalAdmins = Number(overviewData?.users?.total_admins || 0);
  const activePct = totalUsers > 0 ? Math.round((activeUsers / totalUsers) * 100) : 0;

  const regTrend = overviewData?.registration_trend || [];
  const activityByDay = overviewData?.activity_by_day || [];
  const mlTrend = overviewData?.ml_inference_trend || [];
  const attentionItems = overviewData?.attention_items || [];
  const dbLatency = overviewData?.system_status?.db_latency_ms ?? null;
  const mlOperational = overviewData?.active_model?.status === 'HEALTHY';

  const totalAuditInWindow = activityByDay.reduce((sum, d) => sum + Number(d.total_events || 0), 0);
  const normalAuditInWindow = activityByDay.reduce((sum, d) => sum + Number(d.normal_events || 0), 0);
  const flaggedAuditInWindow = activityByDay.reduce((sum, d) => sum + Number(d.flagged_events || 0), 0);

  // SVG polyline helper for real trend data
  const buildSparkline = (values, width = 520, height = 140, pad = 12) => {
    if (!values || values.length === 0) {
      return { line: `0,${height - pad} ${width},${height - pad}`, area: `0,${height - pad} ${width},${height - pad} ${width},${height} 0,${height}` };
    }
    const pts = values.length === 1 ? [values[0], values[0]] : values;
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min || 1;
    const stepX = (width - pad * 2) / (pts.length - 1);
    const coords = pts.map((v, i) => {
      const x = pad + i * stepX;
      const y = height - pad - ((v - min) / range) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const line = coords.join(' ');
    const area = `${pad},${height} ${line} ${(width - pad).toFixed(1)},${height}`;
    return { line, area };
  };

  const regChart = buildSparkline(regTrend.map((r) => Number(r.cumulative_users || 0)), 600, 170, 14);
  const mlChart = buildSparkline(mlTrend.map((m) => Number(m.count || 0)), 340, 120, 10);
  const latencyChart = buildSparkline(
    activityByDay.length > 0 ? activityByDay.map((d) => Number(d.total_events || 0)) : [0, 0],
    340,
    110,
    10
  );

  // Donut stroke math for User Distribution
  const distTotal = totalAgents + totalOfficers + totalAdmins || 1;
  const agentDash = (totalAgents / distTotal) * 251.2;
  const officerDash = (totalOfficers / distTotal) * 251.2;
  const adminDash = (totalAdmins / distTotal) * 251.2;

  return (
    <div className={`min-h-screen flex flex-col font-sans transition-colors duration-200 ${shellBg}`}>
      {/* ========================================================= */}
      {/* FULL-WIDTH TOP HEADER BAR (Matching VerifyMesh Dashboards) */}
      {/* ========================================================= */}
      <header className={`sticky top-0 z-40 px-5 sm:px-8 py-3.5 border-b backdrop-blur-md flex items-center justify-between gap-4 ${headerBg}`}>
        {/* Brand Logo & Portal Badge */}
        <div className="flex items-center gap-3 select-none">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#4b5bd8] to-[#6f7dff] flex items-center justify-center p-2 shadow-lg shadow-indigo-500/25 shrink-0 text-white">
            <svg viewBox="0 0 28 28" fill="none" className="w-full h-full text-white">
              <path d="M6 8V18C6 20.2091 7.79086 22 10 22H20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
              <path d="M10 17L15 13L21 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="10" cy="17" r="2.2" fill="currentColor" />
              <circle cx="15" cy="13" r="2.2" fill="currentColor" />
              <circle cx="21" cy="16" r="2.2" fill="currentColor" />
            </svg>
          </div>
          <div className="flex items-center gap-2.5">
            <span className={`font-sora text-lg sm:text-xl font-bold tracking-tight leading-none ${headingText}`}>
              VerifyMesh
            </span>
            <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
              isDark
                ? 'bg-indigo-950/80 text-indigo-300 border-indigo-500/30'
                : 'bg-indigo-50 text-indigo-700 border-indigo-200'
            }`}>
              Platform Admin
            </span>
          </div>
        </div>

        {/* Right Controls: Search Modules, Workforce Portal Link, Refresh, Theme, Alerts, Profile Dropdown */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Search modules input */}
          <div className="relative hidden lg:block w-56">
            <Search className={`w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 ${mutedText}`} />
            <input
              type="text"
              value={moduleSearch}
              onChange={(e) => setModuleSearch(e.target.value)}
              placeholder="Search modules..."
              className={`w-full pl-8 pr-3 py-1.5 rounded-xl text-xs focus:outline-none ${inputCls}`}
            />
            {filteredModules.length > 0 && (
              <div className={`absolute left-0 right-0 mt-1.5 rounded-xl border shadow-xl overflow-hidden z-50 ${cardCls}`}>
                {filteredModules.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setActiveTab(m.id);
                      setModuleSearch('');
                    }}
                    className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2 cursor-pointer ${tableRowHover} ${headingText}`}
                  >
                    <m.icon className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{m.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={refreshCurrentTab}
            disabled={isLoading}
            className={`p-2 rounded-xl transition-colors cursor-pointer ${
              isDark
                ? 'text-slate-400 hover:text-white hover:bg-[#151f38]'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
            title="Refresh Portal Data"
          >
            <RotateCcw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>

          <ThemeToggle />

          {/* Notification / Attention Bell */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowAlertsPopover((prev) => !prev)}
              className={`flex items-center gap-1.5 p-2 rounded-xl transition-colors cursor-pointer ${
                isDark
                  ? 'text-slate-400 hover:text-white hover:bg-[#151f38]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title="Platform Alerts"
            >
              <Bell className="w-4 h-4" />
              {attentionItems.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-rose-500 text-white text-[10px] font-bold">
                  {attentionItems.length}
                </span>
              )}
            </button>

            {showAlertsPopover && (
              <div className={`absolute right-0 mt-2 w-80 rounded-2xl p-4 z-50 shadow-2xl ${cardCls}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-bold ${headingText}`}>Platform Alerts</span>
                  <button
                    type="button"
                    onClick={() => setShowAlertsPopover(false)}
                    className={`text-xs ${mutedText} hover:text-indigo-400`}
                  >
                    Close
                  </button>
                </div>
                {attentionItems.length > 0 ? (
                  <div className="space-y-2">
                    {attentionItems.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setActiveTab(item.target_tab);
                          setShowAlertsPopover(false);
                        }}
                        className={`w-full text-left p-2.5 rounded-xl text-xs flex items-center justify-between gap-2 cursor-pointer ${innerCardCls} ${tableRowHover}`}
                      >
                        <span className={headingText}>{item.title}</span>
                        <ChevronRight className="w-3.5 h-3.5 shrink-0 text-indigo-400" />
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className={`text-xs py-3 ${mutedText}`}>No active platform alerts.</p>
                )}
              </div>
            )}
          </div>

          {/* User Profile Pill & Dropdown (Matching AdminDashboard) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className={`flex items-center gap-2.5 p-1 sm:px-2 rounded-xl transition-colors cursor-pointer select-none ${
                isDark ? 'hover:bg-[#151f38]' : 'hover:bg-slate-100'
              }`}
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
                {initials}
              </div>
              <div className="text-left hidden sm:block">
                <p className={`text-xs font-semibold leading-tight ${headingText}`}>
                  {fullName}
                </p>
                <p className={`text-[10px] leading-tight ${mutedText}`}>
                  Platform Administrator
                </p>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 ${mutedText}`} />
            </button>

            {isUserMenuOpen && (
              <div className={`absolute right-0 mt-2 w-56 rounded-xl shadow-2xl border py-1.5 z-50 text-xs ${cardCls}`}>
                <div className={`px-3.5 py-2 border-b ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
                  <p className={`text-xs font-semibold ${headingText}`}>{fullName}</p>
                  <p className={`text-[10px] ${mutedText}`}>{user?.email || 'john.nyabuto@verifymesh.io'}</p>
                  <span className={`inline-block mt-1 text-[9px] font-semibold px-1.5 py-0.5 rounded border ${
                    isDark ? 'bg-indigo-950 text-indigo-300 border-indigo-500/20' : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                  }`}>
                    Platform Governance Console
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    refreshCurrentTab();
                  }}
                  className={`w-full text-left px-3.5 py-2 font-medium flex items-center gap-2 cursor-pointer ${tableRowHover} ${headingText}`}
                >
                  <RotateCcw className="w-3.5 h-3.5 text-indigo-400" />
                  Refresh Data
                </button>
                <div className={`border-t my-1 ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`} />
                <button
                  type="button"
                  onClick={logout}
                  className="w-full text-left px-3.5 py-2 font-medium text-rose-400 hover:bg-rose-950/30 flex items-center gap-2 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Container with Collapsible Sidebar + Content */}
      <div className="flex-1 flex max-w-[1600px] w-full mx-auto relative">
        {/* Left Collapsible Sidebar */}
        <aside
          className={`border-r flex flex-col justify-between p-3.5 shrink-0 transition-all duration-300 ease-in-out relative ${sidebarBg} ${
            isSidebarCollapsed ? 'w-20' : 'w-56 lg:w-60'
          }`}
        >
          <div className="space-y-4">
            {/* Collapse / Expand Toggle Button matching AdminDashboard */}
            <div className={`flex items-center pb-1 ${isSidebarCollapsed ? 'justify-center' : 'justify-end'}`}>
              <button
                type="button"
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className={`w-6 h-6 rounded-full border flex items-center justify-center transition-all shadow-md hover:scale-105 cursor-pointer ${
                  isDark
                    ? 'bg-[#12192e] border-[#2b3a67] text-slate-300 hover:text-white'
                    : 'bg-white border-slate-300 text-slate-600 hover:text-slate-900'
                }`}
                title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {isSidebarCollapsed ? (
                  <ChevronRight className="w-3.5 h-3.5" />
                ) : (
                  <ChevronLeft className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            {/* Grouped Navigation */}
            <nav className="space-y-4">
              {navGroups.map((group) => (
                <div key={group.title}>
                  {!isSidebarCollapsed && (
                    <p className={`px-3 mb-1.5 text-[10px] font-bold tracking-wider uppercase ${mutedText}`}>
                      {group.title}
                    </p>
                  )}
                  <div className="space-y-1">
                    {group.items.map((item) => {
                      const Icon = item.icon;
                      const isActive = activeTab === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => setActiveTab(item.id)}
                          title={isSidebarCollapsed ? item.label : undefined}
                          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                            isSidebarCollapsed ? 'justify-center' : ''
                          } ${
                            isActive
                              ? isDark
                                ? 'bg-[#1a244d] text-white border border-indigo-500/30 shadow-sm'
                                : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                              : isDark
                                ? 'text-slate-400 hover:text-white hover:bg-[#111830]'
                                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                          }`}
                        >
                          <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-indigo-400' : ''}`} />
                          {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </nav>
          </div>

          {/* Sidebar Footer */}
          <div className={`space-y-2 pt-4 border-t ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
            {!isSidebarCollapsed && (
              <div className={`px-2.5 py-2 rounded-lg text-[10px] ${innerCardCls} ${mutedText}`}>
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse" />
                  <span>Governance Gateway</span>
                </div>
                <p className="text-[9px] mt-0.5">Live telemetry active</p>
              </div>
            )}
            <button
              type="button"
              onClick={refreshCurrentTab}
              title={isSidebarCollapsed ? 'Refresh Data' : undefined}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              } ${
                isDark
                  ? 'text-slate-400 hover:text-white hover:bg-[#121a30]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              {!isSidebarCollapsed && <span>Refresh Data</span>}
            </button>
            <button
              type="button"
              onClick={logout}
              title={isSidebarCollapsed ? 'Sign Out' : undefined}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              } ${
                isDark
                  ? 'text-slate-400 hover:text-rose-400 hover:bg-rose-950/20'
                  : 'text-slate-600 hover:text-rose-600 hover:bg-rose-50'
              }`}
            >
              <LogOut className="w-3.5 h-3.5" />
              {!isSidebarCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">

        {/* Global Feedback Banner */}
        {feedback && (
          <div
            className={`mx-4 sm:mx-6 mt-4 p-3 rounded-xl border flex items-center justify-between text-xs font-semibold ${
              feedback.type === 'success'
                ? isDark
                  ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : isDark
                  ? 'bg-rose-950/80 border-rose-500/50 text-rose-300'
                  : 'bg-rose-50 border-rose-200 text-rose-700'
            }`}
          >
            <div className="flex items-center gap-2">
              {feedback.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              <span>{feedback.message}</span>
            </div>
            <button onClick={() => setFeedback(null)} className="opacity-70 hover:opacity-100">
              &times;
            </button>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto space-y-6">
          {/* ========================================================= */}
          {/* TAB 1: PLATFORM OVERVIEW (Reference Screenshots Layout)   */}
          {/* ========================================================= */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Hero Greeting Banner */}
              <div
                className={`rounded-2xl p-6 border shadow-xl relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isDark
                    ? 'bg-gradient-to-r from-[#111c44] via-[#0e2a4a] to-[#0a3c48] border-[#1e355e]'
                    : 'bg-gradient-to-r from-indigo-600 via-indigo-700 to-teal-700 border-indigo-500 text-white'
                }`}
              >
                <div className="relative z-10">
                  <h1 className="text-xl sm:text-2xl font-bold font-sora text-white tracking-tight">
                    Welcome back, {firstName}
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-200/90 mt-1 max-w-2xl leading-relaxed">
                    {attentionItems.length > 0
                      ? `You have ${attentionItems.length} active platform alert${attentionItems.length > 1 ? 's' : ''} and ${overviewData?.operations?.audit_events_24h ?? 0} audit events in the last 24 hours.`
                      : `All platform services are operational. ${overviewData?.operations?.audit_events_24h ?? 0} audit events recorded in the last 24 hours.`}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5 relative z-10 shrink-0">
                  <select
                    value={timeframeDays}
                    onChange={(e) => setTimeframeDays(e.target.value)}
                    className="px-3 py-2 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/15 text-white border border-white/20 backdrop-blur-sm focus:outline-none cursor-pointer"
                  >
                    <option value="7" className="text-slate-900">Last 7 days</option>
                    <option value="30" className="text-slate-900">Last 30 days</option>
                    <option value="90" className="text-slate-900">Last 90 days</option>
                    <option value="all" className="text-slate-900">All time</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => setActiveTab('audit')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-white/15 hover:bg-white/25 text-white border border-white/25 transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <span>View audit logs</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Row 1: Registered Users Trend (2/3) + Active Accounts Ring (1/3) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Registered Users Chart */}
                <div className={`lg:col-span-2 rounded-2xl p-5 flex flex-col justify-between ${cardCls}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className={`text-xs font-medium ${mutedText}`}>Registered users</span>
                      <div className={`text-3xl font-bold font-sora mt-1 ${headingText}`}>
                        {totalUsers}
                      </div>
                      <p className="text-xs text-emerald-400 font-medium mt-1">
                        {regTrend.reduce((s, r) => s + Number(r.new_users || 0), 0)} registered in selected period
                      </p>
                    </div>
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                      isDark ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                    }`}>
                      <Users className="w-4 h-4" />
                    </div>
                  </div>

                  <div className="mt-4 h-44 w-full">
                    <svg viewBox="0 0 600 170" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="regGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity="0.30" />
                          <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {[40, 85, 130].map((y) => (
                        <line
                          key={y}
                          x1="0"
                          y1={y}
                          x2="600"
                          y2={y}
                          stroke={isDark ? '#1b2542' : '#e2e8f0'}
                          strokeWidth="1"
                        />
                      ))}
                      <polygon points={regChart.area} fill="url(#regGrad)" />
                      <polyline
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={regChart.line}
                      />
                    </svg>
                  </div>
                </div>

                {/* Active Accounts Gauge */}
                <div className={`rounded-2xl p-6 flex flex-col items-center justify-center text-center ${cardCls}`}>
                  <div className="relative w-32 h-32 flex items-center justify-center">
                    <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke={isDark ? '#141d38' : '#e2e8f0'}
                        strokeWidth="10"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="10"
                        strokeLinecap="round"
                        strokeDasharray={`${(activePct / 100) * 251.2} 251.2`}
                      />
                    </svg>
                    <span className={`absolute text-2xl font-bold font-sora ${headingText}`}>
                      {activePct}%
                    </span>
                  </div>
                  <h3 className={`text-sm font-bold font-sora mt-4 ${headingText}`}>Active accounts</h3>
                  <p className={`text-xs mt-1 ${mutedText}`}>
                    {activeUsers} of {totalUsers} registered
                  </p>
                </div>
              </div>

              {/* Row 2: 3-Column Analytics Cards (Audit Activity, DB Performance, Account Status) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Platform Audit Activity (7-day breakdown) */}
                <div className={`rounded-2xl p-5 flex flex-col justify-between ${cardCls}`}>
                  <div>
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-semibold ${headingText}`}>Platform activity</span>
                      <span className="text-[11px] font-semibold text-emerald-400">
                        {overviewData?.operations?.audit_events_24h ?? 0} today
                      </span>
                    </div>
                    <div className={`text-2xl font-bold font-sora mt-1 ${headingText}`}>
                      {totalAuditInWindow.toLocaleString()}
                    </div>
                    <p className={`text-[11px] mt-0.5 ${mutedText}`}>
                      Audit events · selected period
                    </p>
                    <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px]">
                      <span className={`flex items-center gap-1.5 ${mutedText}`}>
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        Operational {normalAuditInWindow.toLocaleString()}
                      </span>
                      <span className={`flex items-center gap-1.5 ${mutedText}`}>
                        <span className="w-2 h-2 rounded-full bg-amber-400" />
                        Flagged {flaggedAuditInWindow.toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Bar Chart from real activityByDay */}
                  <div className="mt-5 flex items-end justify-between gap-2 h-28 pt-2">
                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => {
                      const match = activityByDay.find((d) => d.day_label === day);
                      const count = Number(match?.total_events || 0);
                      const maxCount = Math.max(...activityByDay.map((d) => Number(d.total_events || 0)), 1);
                      const heightPct = Math.max(8, Math.round((count / maxCount) * 100));
                      return (
                        <div key={day} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                          <div
                            title={`${day}: ${count} events`}
                            style={{ height: `${heightPct}%` }}
                            className="w-full rounded-t-md bg-indigo-500/90 hover:bg-indigo-400 transition-all"
                          />
                          <span className={`text-[10px] ${mutedText}`}>{day}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Database & API Performance */}
                <div className={`rounded-2xl p-5 flex flex-col justify-between ${cardCls}`}>
                  <div>
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-semibold ${headingText}`}>Database performance</span>
                      <span className="text-[11px] font-semibold text-emerald-400">
                        {overviewData?.system_status?.database || 'ONLINE'}
                      </span>
                    </div>
                    <div className={`text-2xl font-bold font-sora mt-1 ${headingText}`}>
                      {dbLatency !== null ? `${dbLatency} ms` : '—'}
                    </div>
                    <p className={`text-[11px] mt-0.5 ${mutedText}`}>Live MySQL query round-trip</p>
                    <div className="flex flex-wrap items-center gap-2 mt-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded-md font-medium ${innerCardCls} ${headingText}`}>
                        API v{overviewData?.system_status?.api_version || '2.0.0'}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-md font-medium ${innerCardCls} ${headingText}`}>
                        {overviewData?.operations?.total_audit_logs ?? 0} total logs
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 h-28 w-full">
                    <svg viewBox="0 0 340 110" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.28" />
                          <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {[30, 65, 95].map((y) => (
                        <line key={y} x1="0" y1={y} x2="340" y2={y} stroke={isDark ? '#1b2542' : '#e2e8f0'} strokeWidth="1" />
                      ))}
                      <polygon points={latencyChart.area} fill="url(#perfGrad)" />
                      <polyline
                        fill="none"
                        stroke="#6366f1"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={latencyChart.line}
                      />
                    </svg>
                  </div>
                </div>

                {/* Account Status Breakdown */}
                <div className={`rounded-2xl p-5 flex flex-col justify-between ${cardCls}`}>
                  <div>
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-semibold ${headingText}`}>Account status</span>
                      <span className={`text-[11px] ${mutedText}`}>Live directory</span>
                    </div>
                    <div className={`text-2xl font-bold font-sora mt-1 ${headingText}`}>
                      {activeUsers}
                    </div>
                    <p className={`text-[11px] mt-0.5 ${mutedText}`}>Active accounts</p>
                  </div>

                  <div className="space-y-3 mt-4 text-xs">
                    {[
                      { label: 'Active', val: activeUsers, color: 'bg-emerald-400' },
                      { label: 'Pending verification', val: pendingVerification, color: 'bg-amber-400' },
                      { label: 'Unverified email', val: unverifiedEmail, color: 'bg-indigo-400' },
                      { label: 'Suspended', val: suspendedUsers, color: 'bg-rose-400' },
                    ].map((row) => {
                      const pct = totalUsers > 0 ? Math.round((row.val / totalUsers) * 100) : 0;
                      return (
                        <div key={row.label} className="space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className={headingText}>{row.label}</span>
                            <span className={`font-semibold ${headingText}`}>{row.val}</span>
                          </div>
                          <div className={`w-full h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-[#141d38]' : 'bg-slate-100'}`}>
                            <div
                              style={{ width: `${Math.max(row.val > 0 ? 6 : 0, pct)}%` }}
                              className={`h-full rounded-full ${row.color}`}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Row 3: 4 Compact KPI Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className={`rounded-2xl p-4 flex items-center gap-3.5 ${cardCls}`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                    isDark ? 'bg-indigo-950/70 text-indigo-400 border border-indigo-500/30' : 'bg-indigo-50 text-indigo-600'
                  }`}>
                    <Users className="w-4 h-4" />
                  </div>
                  <div>
                    <span className={`text-[11px] block ${mutedText}`}>Suspended accounts</span>
                    <div className={`text-xl font-bold font-sora ${headingText}`}>{suspendedUsers}</div>
                    <span className={`text-[10px] ${mutedText}`}>Locked from sign-in</span>
                  </div>
                </div>

                <div className={`rounded-2xl p-4 flex items-center gap-3.5 ${cardCls}`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                    isDark ? 'bg-indigo-950/70 text-indigo-400 border border-indigo-500/30' : 'bg-indigo-50 text-indigo-600'
                  }`}>
                    <Shield className="w-4 h-4" />
                  </div>
                  <div>
                    <span className={`text-[11px] block ${mutedText}`}>Administrators</span>
                    <div className={`text-xl font-bold font-sora ${headingText}`}>{totalAdmins + totalOfficers}</div>
                    <span className={`text-[10px] ${mutedText}`}>
                      {totalAdmins} Platform Admin · {totalOfficers} Workforce Officer{totalOfficers !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>

                <div className={`rounded-2xl p-4 flex items-center gap-3.5 ${cardCls}`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                    isDark ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-50 text-emerald-600'
                  }`}>
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <span className={`text-[11px] block ${mutedText}`}>Assessments logged</span>
                    <div className={`text-xl font-bold font-sora ${headingText}`}>
                      {overviewData?.operations?.total_assessments ?? 0}
                    </div>
                    <span className={`text-[10px] ${mutedText}`}>
                      {overviewData?.operations?.total_tasks ?? 0} tasks configured
                    </span>
                  </div>
                </div>

                <div className={`rounded-2xl p-4 flex items-center gap-3.5 ${cardCls}`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                    mlOperational
                      ? isDark ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-50 text-emerald-600'
                      : isDark ? 'bg-amber-950/70 text-amber-400 border border-amber-500/30' : 'bg-amber-50 text-amber-600'
                  }`}>
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <span className={`text-[11px] block ${mutedText}`}>ML service status</span>
                    <div className={`text-lg font-bold font-sora ${mlOperational ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {mlOperational ? 'Operational' : 'Degraded'}
                    </div>
                    <span className={`text-[10px] ${mutedText}`}>
                      Model v{overviewData?.active_model?.model_version || '3.0.0'} · 5 features
                    </span>
                  </div>
                </div>
              </div>

              {/* Row 4: User Distribution Donut + ML Inference Trend + System Health List */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* User Distribution */}
                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <h3 className={`text-xs font-bold font-sora mb-4 ${headingText}`}>User distribution</h3>
                  <div className="flex items-center gap-6">
                    <svg viewBox="0 0 100 100" className="w-24 h-24 shrink-0 -rotate-90">
                      <circle cx="50" cy="50" r="40" fill="none" stroke={isDark ? '#141d38' : '#e2e8f0'} strokeWidth="14" />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#6366f1"
                        strokeWidth="14"
                        strokeDasharray={`${agentDash} 251.2`}
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="14"
                        strokeDasharray={`${officerDash} 251.2`}
                        strokeDashoffset={-agentDash}
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="14"
                        strokeDasharray={`${adminDash} 251.2`}
                        strokeDashoffset={-(agentDash + officerDash)}
                      />
                    </svg>
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-indigo-500" />
                        <span className={mutedText}>Agents</span>
                        <strong className={headingText}>{totalAgents}</strong>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className={mutedText}>Workforce Officers</span>
                        <strong className={headingText}>{totalOfficers}</strong>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-amber-500" />
                        <span className={mutedText}>Platform Admins</span>
                        <strong className={headingText}>{totalAdmins}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* ML Suitability Evaluations Trend */}
                <div className={`rounded-2xl p-5 flex flex-col justify-between ${cardCls}`}>
                  <div className="flex items-center justify-between">
                    <h3 className={`text-xs font-bold font-sora ${headingText}`}>
                      ML suitability evaluations
                    </h3>
                    <span className={`text-[11px] font-semibold ${mutedText}`}>
                      {overviewData?.operations?.total_evaluations ?? 0} total
                    </span>
                  </div>
                  <div className="mt-4 h-28 w-full">
                    <svg viewBox="0 0 340 120" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="mlGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#14b8a6" stopOpacity="0.30" />
                          <stop offset="100%" stopColor="#14b8a6" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {[30, 65, 100].map((y) => (
                        <line key={y} x1="0" y1={y} x2="340" y2={y} stroke={isDark ? '#1b2542' : '#e2e8f0'} strokeWidth="1" />
                      ))}
                      <polygon points={mlChart.area} fill="url(#mlGrad)" />
                      <polyline
                        fill="none"
                        stroke="#14b8a6"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={mlChart.line}
                      />
                    </svg>
                  </div>
                </div>

                {/* System Health Services List */}
                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <h3 className={`text-xs font-bold font-sora mb-3 ${headingText}`}>System health</h3>
                  <div className={`divide-y text-xs ${dividerCls}`}>
                    {[
                      { name: 'Backend API', status: 'Operational', meta: 'v2.0.0', ok: true },
                      { name: 'MySQL database', status: 'Operational', meta: dbLatency !== null ? `${dbLatency} ms` : 'Online', ok: true },
                      { name: 'Authentication service', status: 'Operational', meta: 'HMAC-SHA256', ok: true },
                      { name: 'ML inference service', status: mlOperational ? 'Operational' : 'Degraded', meta: 'Model v3', ok: mlOperational },
                    ].map((svc) => (
                      <div key={svc.name} className="py-2.5 flex items-center justify-between gap-2">
                        <span className={headingText}>{svc.name}</span>
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                              svc.ok
                                ? isDark
                                  ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                                  : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : isDark
                                  ? 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                                  : 'bg-amber-50 text-amber-700 border-amber-200'
                            }`}
                          >
                            {svc.status}
                          </span>
                          <span className={`text-[10px] font-mono ${mutedText}`}>{svc.meta}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Row 5: Attention Required + Recent Administrative Activity */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Attention Required */}
                <div className={`lg:col-span-5 rounded-2xl p-5 ${cardCls}`}>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className={`text-xs font-bold font-sora ${headingText}`}>Attention required</h3>
                      <p className={`text-[11px] ${mutedText}`}>Live checks from database</p>
                    </div>
                  </div>

                  {attentionItems.length > 0 ? (
                    <div className={`divide-y ${dividerCls}`}>
                      {attentionItems.map((item) => (
                        <div key={item.id} className="py-3 flex items-center justify-between gap-3">
                          <span className={`text-xs ${headingText}`}>{item.title}</span>
                          <button
                            type="button"
                            onClick={() => setActiveTab(item.target_tab)}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold border transition-colors shrink-0 cursor-pointer ${
                              isDark
                                ? 'bg-[#0d1428] border-[#1b2542] text-slate-200 hover:border-indigo-500'
                                : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                            }`}
                          >
                            Open
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-8 text-center">
                      <CheckCircle2 className="w-7 h-7 text-emerald-400 mx-auto mb-2" />
                      <p className={`text-xs font-semibold ${headingText}`}>All systems nominal</p>
                      <p className={`text-[11px] mt-0.5 ${mutedText}`}>No suspended accounts or critical alerts detected.</p>
                    </div>
                  )}
                </div>

                {/* Recent Administrative Activity */}
                <div className={`lg:col-span-7 rounded-2xl p-5 ${cardCls}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className={`text-xs font-bold font-sora ${headingText}`}>Recent administrative activity</h3>
                    <button
                      type="button"
                      onClick={() => setActiveTab('audit')}
                      className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 cursor-pointer"
                    >
                      View all &rarr;
                    </button>
                  </div>

                  {overviewData?.recent_audit_events?.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className={`text-[10px] font-bold uppercase tracking-wider border-b ${isDark ? 'border-[#1b2542] text-slate-400' : 'border-slate-200 text-slate-500'}`}>
                            <th className="py-2 pr-3">Actor</th>
                            <th className="py-2 px-3">Action</th>
                            <th className="py-2 px-3">Target</th>
                            <th className="py-2 px-3">Time</th>
                            <th className="py-2 pl-3 text-right">Result</th>
                          </tr>
                        </thead>
                        <tbody className={`divide-y ${dividerCls}`}>
                          {overviewData.recent_audit_events.slice(0, 6).map((ev) => {
                            const isWarning = /REJECT|ABANDON|CANCEL|SUSPEND/i.test(ev.action || '');
                            return (
                              <tr key={ev.log_id} className={tableRowHover}>
                                <td className={`py-2.5 pr-3 font-medium whitespace-nowrap ${headingText}`}>
                                  {ev.actor_name || 'System'}
                                </td>
                                <td className={`py-2.5 px-3 font-mono text-[11px] ${mutedText}`}>
                                  {ev.action}
                                </td>
                                <td className={`py-2.5 px-3 whitespace-nowrap ${mutedText}`}>
                                  {ev.entity_type ? `${ev.entity_type} #${ev.entity_id}` : '—'}
                                </td>
                                <td className={`py-2.5 px-3 whitespace-nowrap text-[11px] ${mutedText}`}>
                                  {ev.created_at ? new Date(ev.created_at).toLocaleString() : '—'}
                                </td>
                                <td className="py-2.5 pl-3 text-right whitespace-nowrap">
                                  <span
                                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                                      isWarning
                                        ? isDark
                                          ? 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                                          : 'bg-amber-50 text-amber-700 border-amber-200'
                                        : isDark
                                          ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                                          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    }`}
                                  >
                                    {isWarning ? 'Flagged' : 'Success'}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className={`text-xs py-8 text-center ${mutedText}`}>No audit records recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 2: USER & ACCESS GOVERNANCE                           */}
          {/* ========================================================= */}
          {activeTab === 'users' && (
            <div className="space-y-4">
              <div className={`rounded-2xl p-4 flex flex-col md:flex-row gap-3 items-center justify-between ${cardCls}`}>
                <div className="relative w-full md:w-80">
                  <Search className={`w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 ${mutedText}`} />
                  <input
                    type="text"
                    placeholder="Search user name or email..."
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && loadUsers(1)}
                    className={`w-full pl-9 pr-3 py-2 rounded-xl text-xs focus:outline-none ${inputCls}`}
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
                  <select
                    value={userRoleFilter}
                    onChange={(e) => setUserRoleFilter(e.target.value)}
                    className={`px-3 py-2 rounded-xl text-xs focus:outline-none ${inputCls}`}
                  >
                    <option value="">All Roles</option>
                    <option value="AGENT">Agent</option>
                    <option value="WORKFORCE_OFFICER">Workforce Officer</option>
                    <option value="PLATFORM_ADMIN">Platform Admin</option>
                    <option value="ADMIN">Administrator (Legacy)</option>
                  </select>

                  <select
                    value={userStatusFilter}
                    onChange={(e) => setUserStatusFilter(e.target.value)}
                    className={`px-3 py-2 rounded-xl text-xs focus:outline-none ${inputCls}`}
                  >
                    <option value="">All Statuses</option>
                    <option value="active">Active Only</option>
                    <option value="inactive">Suspended Only</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => loadUsers(1)}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <Filter className="w-3.5 h-3.5" />
                    <span>Filter</span>
                  </button>
                </div>
              </div>

              <div className={`rounded-2xl overflow-hidden ${cardCls}`}>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className={`text-[11px] font-semibold uppercase tracking-wider ${tableHeadCls}`}>
                        <th className="py-3 px-4">User</th>
                        <th className="py-3 px-4">Role</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Registered</th>
                        <th className="py-3 px-4">Last Login</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y ${dividerCls}`}>
                      {usersData.length === 0 ? (
                        <tr>
                          <td colSpan={6} className={`py-10 text-center text-xs ${mutedText}`}>
                            No user accounts match your current search or filter criteria.
                          </td>
                        </tr>
                      ) : usersData.map((u) => (
                        <tr key={u.user_id} className={`transition-colors ${tableRowHover}`}>
                          <td className="py-3.5 px-4">
                            <div className={`font-semibold ${headingText}`}>{u.full_name}</div>
                            <div className={`text-[11px] ${mutedText}`}>{u.email}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <select
                              value={u.role}
                              disabled={actionLoading === u.user_id || u.user_id === user?.id}
                              onChange={(e) => handleRoleChange(u.user_id, e.target.value)}
                              className={`rounded-lg px-2.5 py-1 text-xs focus:outline-none font-medium ${inputCls}`}
                            >
                              <option value="AGENT">Agent</option>
                              <option value="WORKFORCE_OFFICER">Workforce Officer</option>
                              <option value="PLATFORM_ADMIN">Platform Admin</option>
                              {u.role === 'ADMIN' && <option value="ADMIN">ADMIN (Legacy)</option>}
                            </select>
                          </td>
                          <td className="py-3.5 px-4">
                            {u.is_active ? (
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                                isDark ? 'bg-emerald-950 text-emerald-300 border-emerald-500/40' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              }`}>
                                Active
                              </span>
                            ) : (
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                                isDark ? 'bg-rose-950 text-rose-300 border-rose-500/40' : 'bg-rose-50 text-rose-700 border-rose-200'
                              }`}>
                                Suspended
                              </span>
                            )}
                          </td>
                          <td className={`py-3.5 px-4 text-[11px] ${mutedText}`}>
                            {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                          </td>
                          <td className={`py-3.5 px-4 text-[11px] ${mutedText}`}>
                            {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Not recorded'}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="inline-flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => openUserProfile(u.user_id)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
                                  isDark
                                    ? 'bg-[#0d1428] text-indigo-300 border-[#1b2542] hover:border-indigo-500'
                                    : 'bg-slate-50 text-indigo-600 border-slate-200 hover:bg-slate-100'
                                }`}
                              >
                                Profile
                              </button>
                              <button
                                type="button"
                                disabled={actionLoading === u.user_id || u.user_id === user?.id}
                                onClick={() => handleStatusToggle(u.user_id, u.is_active)}
                                className={`px-3 py-1 rounded-lg text-xs font-semibold border transition-colors cursor-pointer disabled:opacity-40 ${
                                  u.is_active
                                    ? isDark
                                      ? 'bg-rose-950/40 text-rose-300 border-rose-700/50 hover:bg-rose-900/60'
                                      : 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100'
                                    : isDark
                                      ? 'bg-emerald-950/40 text-emerald-300 border-emerald-700/50 hover:bg-emerald-900/60'
                                      : 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                                }`}
                              >
                                {u.is_active ? 'Suspend' : 'Activate'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className={`p-3 border-t flex items-center justify-between text-xs ${isDark ? 'bg-[#070b18] border-[#1b2542]' : 'bg-slate-50 border-slate-200'} ${mutedText}`}>
                  <span>Total Users: {userPagination.total}</span>
                  <div className="flex items-center gap-2">
                    <button
                      disabled={userPagination.page <= 1}
                      onClick={() => loadUsers(userPagination.page - 1)}
                      className={`px-3 py-1 rounded-lg border disabled:opacity-50 ${inputCls}`}
                    >
                      Previous
                    </button>
                    <span>
                      Page {userPagination.page} of {userPagination.total_pages}
                    </span>
                    <button
                      disabled={userPagination.page >= userPagination.total_pages}
                      onClick={() => loadUsers(userPagination.page + 1)}
                      className={`px-3 py-1 rounded-lg border disabled:opacity-50 ${inputCls}`}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 3: ROLES & PERMISSIONS MATRIX                         */}
          {/* ========================================================= */}
          {activeTab === 'roles' && (
            <div className="space-y-6">
              <div className={`rounded-2xl p-6 ${cardCls}`}>
                <h2 className={`text-lg font-bold font-sora ${headingText}`}>
                  Role-Based Access Control (RBAC) Matrix
                </h2>
                <p className={`text-xs mt-1 ${mutedText}`}>
                  Strict separation of duties enforced across VerifyMesh backend blueprints and frontend routes.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
                  {[
                    {
                      role: 'PLATFORM_ADMIN',
                      title: 'Platform Administrator',
                      count: totalAdmins,
                      desc: 'System governance, user role management, audit log streaming, database telemetry, and ML v3 oversight.',
                      perms: ['/api/platform-admin/*', 'Role & Status Governance', 'Audit Log Stream', 'ML Model Governance'],
                    },
                    {
                      role: 'WORKFORCE_OFFICER',
                      title: 'Workforce Officer',
                      count: totalOfficers,
                      desc: 'Candidate verification, credential & experience review, task management, and eligibility determinations.',
                      perms: ['/api/admin/*', 'Credential Verification', 'Task Creation & Allocation', 'Eligibility Reviews'],
                    },
                    {
                      role: 'AGENT',
                      title: 'Agent (Candidate)',
                      count: totalAgents,
                      desc: 'Profile management, certification & work history submission, competency assessments, and task applications.',
                      perms: ['/api/competency/*', '/api/tasks/apply', 'Self-Service Profile', 'Zero-Trust Assessments'],
                    },
                  ].map((r) => (
                    <div key={r.role} className={`rounded-2xl p-5 flex flex-col justify-between ${innerCardCls}`}>
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                            {r.role}
                          </span>
                          <span className={`text-xs font-bold ${headingText}`}>{r.count} users</span>
                        </div>
                        <h3 className={`text-sm font-bold font-sora mt-3 ${headingText}`}>{r.title}</h3>
                        <p className={`text-xs mt-1 leading-relaxed ${mutedText}`}>{r.desc}</p>
                        <ul className="mt-3 space-y-1.5 text-[11px]">
                          {r.perms.map((p) => (
                            <li key={p} className={`flex items-center gap-1.5 ${headingText}`}>
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              <span>{p}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setUserRoleFilter(r.role);
                          setActiveTab('users');
                        }}
                        className="mt-4 w-full py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
                      >
                        View {r.title}s
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 4: LIVE AUDIT LOG STREAM                              */}
          {/* ========================================================= */}
          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className={`rounded-2xl p-4 flex flex-col md:flex-row gap-3 items-center justify-between ${cardCls}`}>
                <div className="relative w-full md:w-80">
                  <Search className={`w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 ${mutedText}`} />
                  <input
                    type="text"
                    placeholder="Search action, actor, or payload..."
                    value={auditSearch}
                    onChange={(e) => setAuditSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && loadAuditLogs(1)}
                    className={`w-full pl-9 pr-3 py-2 rounded-xl text-xs focus:outline-none ${inputCls}`}
                  />
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto">
                  <select
                    value={auditActionFilter}
                    onChange={(e) => setAuditActionFilter(e.target.value)}
                    className={`px-3 py-2 rounded-xl text-xs focus:outline-none max-w-xs ${inputCls}`}
                  >
                    <option value="">All Action Types</option>
                    {availableActions.map((act) => (
                      <option key={act} value={act}>
                        {act}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => loadAuditLogs(1)}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <Filter className="w-3.5 h-3.5" />
                    <span>Filter</span>
                  </button>
                </div>
              </div>

              <div className={`rounded-2xl overflow-hidden ${cardCls}`}>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className={`text-[11px] font-semibold uppercase tracking-wider ${tableHeadCls}`}>
                        <th className="py-3 px-4">Log ID</th>
                        <th className="py-3 px-4">Action</th>
                        <th className="py-3 px-4">Actor</th>
                        <th className="py-3 px-4">Target Entity</th>
                        <th className="py-3 px-4">Payload Details</th>
                        <th className="py-3 px-4 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y font-mono text-[11px] ${dividerCls}`}>
                      {auditLogs.map((log) => (
                        <tr key={log.log_id} className={`transition-colors ${tableRowHover}`}>
                          <td className={`py-3 px-4 ${mutedText}`}>#{log.log_id}</td>
                          <td className="py-3 px-4">
                            <span className={`font-bold px-2.5 py-0.5 rounded border ${
                              isDark ? 'text-indigo-300 bg-indigo-950/80 border-indigo-500/30' : 'text-indigo-700 bg-indigo-50 border-indigo-200'
                            }`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-sans text-xs">
                            <div className={`font-semibold ${headingText}`}>{log.actor_name || 'System'}</div>
                            <div className={`text-[11px] ${mutedText}`}>{log.actor_email}</div>
                          </td>
                          <td className={`py-3 px-4 ${headingText}`}>
                            {log.entity_type ? `${log.entity_type} (#${log.entity_id})` : '—'}
                          </td>
                          <td className={`py-3 px-4 font-mono text-[10px] max-w-xs truncate ${mutedText}`} title={log.description}>
                            {log.description || '—'}
                          </td>
                          <td className={`py-3 px-4 text-right whitespace-nowrap ${mutedText}`}>
                            {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className={`p-3 border-t flex items-center justify-between text-xs ${isDark ? 'bg-[#070b18] border-[#1b2542]' : 'bg-slate-50 border-slate-200'} ${mutedText}`}>
                  <span>Total Events: {auditPagination.total}</span>
                  <div className="flex items-center gap-2">
                    <button
                      disabled={auditPagination.page <= 1}
                      onClick={() => loadAuditLogs(auditPagination.page - 1)}
                      className={`px-3 py-1 rounded-lg border disabled:opacity-50 ${inputCls}`}
                    >
                      Previous
                    </button>
                    <span>
                      Page {auditPagination.page} of {auditPagination.total_pages}
                    </span>
                    <button
                      disabled={auditPagination.page >= auditPagination.total_pages}
                      onClick={() => loadAuditLogs(auditPagination.page + 1)}
                      className={`px-3 py-1 rounded-lg border disabled:opacity-50 ${inputCls}`}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 5: ASSESSMENTS AUDIT & HISTORY                        */}
          {/* ========================================================= */}
          {activeTab === 'assessments' && (
            <div className="space-y-6">
              <div className={`rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${cardCls}`}>
                <div>
                  <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase block">
                    AUDIT TRAIL &amp; INFERENCE LOGS
                  </span>
                  <h1 className={`text-xl sm:text-2xl font-bold font-sora mt-1 tracking-tight ${headingText}`}>
                    Assessment History &amp; Test Records
                  </h1>
                  <p className={`text-xs mt-1 ${mutedText}`}>
                    Historical log of candidate competency evaluations, battery subscores, passing threshold (&ge;70%), and ML suitability outputs.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
                  <span className={`text-xs px-3 py-1.5 rounded-xl border ${innerCardCls} ${headingText}`}>
                    Total: <strong className="font-mono">{assessmentsList.length}</strong>
                  </span>
                  <span className={`text-xs px-3 py-1.5 rounded-xl border ${
                    isDark ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40' : 'text-emerald-700 bg-emerald-50 border-emerald-200'
                  }`}>
                    Passed: <strong className="font-mono">{assessmentsList.filter(a => a.passed === 1 || a.passed === true).length}</strong>
                  </span>
                  <span className={`text-xs px-3 py-1.5 rounded-xl border ${
                    isDark ? 'text-indigo-300 bg-indigo-950/60 border-indigo-500/40' : 'text-indigo-700 bg-indigo-50 border-indigo-200'
                  }`}>
                    Pass Rate: <strong className="font-mono">{assessmentsList.length > 0 ? Math.round((assessmentsList.filter(a => a.passed === 1 || a.passed === true).length / assessmentsList.length) * 100) : 0}%</strong>
                  </span>
                </div>
              </div>

              <div className={`rounded-2xl p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between ${cardCls}`}>
                <div className="flex-1 relative">
                  <Search className={`w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 ${mutedText}`} />
                  <input
                    type="text"
                    placeholder="Search assessments by candidate name, email, or battery..."
                    value={assessmentSearch}
                    onChange={(e) => setAssessmentSearch(e.target.value)}
                    className={`w-full pl-9 pr-9 py-2 rounded-xl text-xs focus:outline-none ${inputCls}`}
                  />
                  {assessmentSearch && (
                    <button
                      type="button"
                      onClick={() => setAssessmentSearch('')}
                      className={`absolute right-3 top-1/2 -translate-y-1/2 ${mutedText} hover:text-indigo-400`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={assessmentResultFilter}
                    onChange={(e) => setAssessmentResultFilter(e.target.value)}
                    className={`px-3 py-2 rounded-xl text-xs font-medium focus:outline-none cursor-pointer ${inputCls}`}
                  >
                    <option value="ALL">All Outcomes</option>
                    <option value="PASSED">Passed Only (&ge;70%)</option>
                    <option value="FAILED">Failed Only (&lt;70%)</option>
                  </select>

                  <select
                    value={assessmentCompFilter}
                    onChange={(e) => setAssessmentCompFilter(e.target.value)}
                    className={`px-3 py-2 rounded-xl text-xs font-medium focus:outline-none cursor-pointer ${inputCls}`}
                  >
                    <option value="ALL">All Predicted Classes</option>
                    <option value="ELIGIBLE">Eligible</option>
                    <option value="NOT_ELIGIBLE">Not Eligible</option>
                  </select>

                  {(assessmentSearch || assessmentResultFilter !== 'ALL' || assessmentCompFilter !== 'ALL') && (
                    <button
                      type="button"
                      onClick={() => {
                        setAssessmentSearch('');
                        setAssessmentResultFilter('ALL');
                        setAssessmentCompFilter('ALL');
                      }}
                      className={`px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer ${inputCls}`}
                    >
                      Reset Filters
                    </button>
                  )}
                </div>
              </div>

              <div className={`rounded-2xl overflow-hidden ${cardCls}`}>
                {filteredAssessments.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className={`text-[11px] font-semibold uppercase tracking-wider ${tableHeadCls}`}>
                          <th className="py-3.5 px-4 font-semibold">ID</th>
                          <th className="py-3.5 px-4 font-semibold">Candidate</th>
                          <th className="py-3.5 px-4 font-semibold">Assessment Battery</th>
                          <th className="py-3.5 px-4 font-semibold">Score &amp; Status</th>
                          <th className="py-3.5 px-4 font-semibold">Attempt</th>
                          <th className="py-3.5 px-4 font-semibold">AI Decision</th>
                          <th className="py-3.5 px-4 font-semibold">Date Completed</th>
                          <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className={`divide-y ${dividerCls}`}>
                        {filteredAssessments.slice(0, 50).map((item) => {
                          const isPassed = item.passed === 1 || item.passed === true || (item.assessment_score >= (item.passing_score || 70));
                          return (
                            <tr key={item.exam_result_id} className={`transition-colors ${tableRowHover}`}>
                              <td className={`py-3.5 px-4 font-mono ${mutedText}`}>#{item.exam_result_id}</td>
                              <td className="py-3.5 px-4">
                                <div className={`font-semibold ${headingText}`}>{item.agent_name}</div>
                                <div className={`text-[11px] ${mutedText}`}>{item.agent_email}</div>
                              </td>
                              <td className="py-3.5 px-4">
                                <span className={`font-medium block ${headingText}`}>{item.exam_name || 'Standard Battery'}</span>
                                <span className={`text-[10px] ${mutedText}`}>{item.category_name || 'General Domain'}</span>
                              </td>
                              <td className="py-3.5 px-4">
                                <div className="flex items-center gap-2">
                                  <span className={`font-bold font-mono ${headingText}`}>{item.assessment_score}%</span>
                                  {isPassed ? (
                                    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                      isDark ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40' : 'text-emerald-700 bg-emerald-50 border-emerald-200'
                                    }`}>
                                      <CheckCircle2 className="w-3 h-3" />
                                      Passed
                                    </span>
                                  ) : (
                                    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                      isDark ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' : 'text-rose-700 bg-rose-50 border-rose-200'
                                    }`}>
                                      <XCircle className="w-3 h-3" />
                                      Failed
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className={`py-3.5 px-4 ${mutedText}`}>Attempt #{item.attempt_number}</td>
                              <td className="py-3.5 px-4">
                                <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getCompetencyBadgeStyle(item.predicted_competency)}`}>
                                  {item.predicted_competency || 'In Review'}
                                </span>
                              </td>
                              <td className={`py-3.5 px-4 text-[11px] ${mutedText}`}>
                                {item.completed_at ? new Date(item.completed_at).toLocaleString() : '—'}
                              </td>
                              <td className="py-3.5 px-4 text-right">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedAssessment(item);
                                    setIsAssessmentModalOpen(true);
                                  }}
                                  className={`px-3 py-1 rounded-lg border text-xs font-semibold cursor-pointer transition-colors ${
                                    isDark
                                      ? 'bg-[#0d1428] hover:bg-[#141f3d] text-indigo-300 border-[#1b2542]'
                                      : 'bg-slate-50 hover:bg-slate-100 text-indigo-600 border-slate-200'
                                  }`}
                                >
                                  Inspect
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-12 text-center">
                    <CheckCircle2 className={`w-8 h-8 mx-auto mb-2 ${mutedText}`} />
                    <p className={`text-sm font-semibold ${headingText}`}>No assessment records found</p>
                    <p className={`text-xs mt-1 ${mutedText}`}>No evaluations match the current filter criteria.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 6: SYSTEM & DATABASE TELEMETRY                        */}
          {/* ========================================================= */}
          {activeTab === 'health' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <div className={`flex items-center gap-2 text-xs font-semibold ${mutedText}`}>
                    <Database className="w-4 h-4 text-indigo-400" />
                    <span>Database Engine</span>
                  </div>
                  <div className={`text-xl font-bold font-sora mt-2 ${headingText}`}>
                    {systemHealth?.database?.engine || '—'}
                  </div>
                  <p className={`text-xs mt-1 ${mutedText}`}>
                    Version: {systemHealth?.database?.version || '—'} &bull; Latency: {systemHealth?.database?.latency_ms != null ? `${systemHealth.database.latency_ms} ms` : '—'}
                  </p>
                  <div className={`mt-3 flex items-center gap-1.5 text-xs ${systemHealth?.database?.connected ? 'text-emerald-400' : 'text-rose-400'}`}>
                    <span className={`w-2 h-2 rounded-full ${systemHealth?.database?.connected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                    <span>{systemHealth?.database?.connected ? 'Connected & Ready' : 'Disconnected'}</span>
                  </div>
                </div>

                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <div className={`flex items-center gap-2 text-xs font-semibold ${mutedText}`}>
                    <Server className="w-4 h-4 text-emerald-400" />
                    <span>Backend API &amp; Uptime</span>
                  </div>
                  <div className={`text-xl font-bold font-sora mt-2 ${headingText}`}>
                    {systemHealth?.server?.uptime_seconds != null
                      ? `${Math.floor(systemHealth.server.uptime_seconds / 3600)}h ${Math.floor((systemHealth.server.uptime_seconds % 3600) / 60)}m ${systemHealth.server.uptime_seconds % 60}s`
                      : '—'}
                  </div>
                  <p className={`text-xs mt-1 ${mutedText}`}>API v{systemHealth?.server?.api_version || '2.0.0'}</p>
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{systemHealth?.status || 'Checking...'}</span>
                  </div>
                </div>

                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <div className={`flex items-center gap-2 text-xs font-semibold ${mutedText}`}>
                    <Lock className="w-4 h-4 text-purple-400" />
                    <span>Security &amp; Tokens</span>
                  </div>
                  <div className={`text-xl font-bold font-sora mt-2 ${headingText}`}>
                    {systemHealth?.security?.token_algorithm || '—'}
                  </div>
                  <p className={`text-xs mt-1 ${mutedText}`}>
                    Session TTL: {systemHealth?.security?.session_timeout_seconds ? `${Math.round(systemHealth.security.session_timeout_seconds / 3600)}h` : '—'}
                  </p>
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-indigo-400">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>RBAC: {systemHealth?.security?.rbac_status || 'ENFORCED'}</span>
                  </div>
                </div>

                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <div className={`flex items-center gap-2 text-xs font-semibold ${mutedText}`}>
                    <Cpu className="w-4 h-4 text-cyan-400" />
                    <span>ML Pipeline Artifact</span>
                  </div>
                  <div className={`text-xl font-bold font-sora mt-2 ${headingText}`}>
                    {systemHealth?.ml_pipeline?.model_loaded ? 'Loaded & Ready' : 'Unavailable'}
                  </div>
                  <p className={`text-xs mt-1 truncate ${mutedText}`}>
                    SHA-256: {systemHealth?.ml_pipeline?.sha256 ? `${systemHealth.ml_pipeline.sha256.substring(0, 12)}...` : '—'}
                  </p>
                  <div className={`mt-3 flex items-center gap-1.5 text-xs ${systemHealth?.ml_pipeline?.artifact_exists_on_disk ? 'text-emerald-400' : 'text-amber-400'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{systemHealth?.ml_pipeline?.artifact_exists_on_disk ? 'Verified on Disk' : 'Missing on Disk'}</span>
                  </div>
                </div>
              </div>

              <div className={`rounded-2xl p-5 ${cardCls}`}>
                <h3 className={`text-sm font-bold font-sora mb-4 flex items-center gap-2 ${headingText}`}>
                  <Database className="w-4 h-4 text-indigo-400" />
                  <span>Live Database Table Volumes</span>
                </h3>

                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 text-xs">
                  {systemHealth?.database?.tables &&
                    Object.entries(systemHealth.database.tables).map(([tbl, count]) => (
                      <div key={tbl} className={`p-3 rounded-xl flex justify-between items-center ${innerCardCls}`}>
                        <span className={`font-mono text-[11px] truncate ${mutedText}`}>{tbl}</span>
                        <span className={`font-bold px-2 py-0.5 rounded ${headingText}`}>{count}</span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Flagged / Error Audit Events */}
              <div className={`rounded-2xl p-5 ${cardCls}`}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className={`text-sm font-bold font-sora flex items-center gap-2 ${headingText}`}>
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>Recent Flagged &amp; Rejected Operational Events</span>
                  </h3>
                  <span className={`text-xs font-semibold ${mutedText}`}>
                    {systemHealth?.server?.flagged_events_24h ?? 0} in last 24h
                  </span>
                </div>
                {systemHealth?.server?.recent_flagged_events?.length > 0 ? (
                  <div className={`divide-y text-xs ${dividerCls}`}>
                    {systemHealth.server.recent_flagged_events.map((ev) => (
                      <div key={ev.log_id} className="py-2.5 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 shrink-0">
                            {ev.action}
                          </span>
                          <span className={`truncate ${headingText}`}>{ev.actor_name || 'System'}</span>
                          <span className={`text-[11px] truncate ${mutedText}`}>
                            {ev.entity_type ? `${ev.entity_type} #${ev.entity_id}` : ''}
                          </span>
                        </div>
                        <span className={`text-[11px] whitespace-nowrap ${mutedText}`}>
                          {ev.created_at ? new Date(ev.created_at).toLocaleString() : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={`text-xs py-6 text-center ${mutedText}`}>No flagged or rejected events recorded.</p>
                )}
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 7: ML MODEL TECHNICAL GOVERNANCE (MODEL V3)           */}
          {/* ========================================================= */}
          {activeTab === 'ml' && (
            <div className="space-y-6">
              {/* Deployment & Availability Header */}
              <div className={`rounded-2xl p-6 relative overflow-hidden ${cardCls}`}>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className={`text-base font-bold font-sora ${headingText}`}>
                        {mlGovernance?.model_metadata?.model_name || 'Loading model metadata...'}
                      </h2>
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                        mlGovernance?.model_metadata?.model_loaded
                          ? isDark ? 'bg-emerald-950 text-emerald-300 border-emerald-500/40' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : isDark ? 'bg-rose-950 text-rose-300 border-rose-500/40' : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {mlGovernance?.model_metadata?.model_loaded ? 'Loaded in Memory' : 'Not Loaded'}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                        mlGovernance?.model_metadata?.available_for_predictions
                          ? isDark ? 'bg-indigo-950 text-indigo-300 border-indigo-500/40' : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                          : isDark ? 'bg-amber-950 text-amber-300 border-amber-500/40' : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}>
                        {mlGovernance?.model_metadata?.available_for_predictions ? 'Available for Predictions' : 'Predictions Unavailable'}
                      </span>
                    </div>
                    <p className={`text-xs mt-1.5 ${mutedText}`}>
                      Algorithm: <span className={headingText}>{mlGovernance?.model_metadata?.algorithm || '—'}</span>
                    </p>
                    <p className={`text-[11px] mt-0.5 ${mutedText}`}>
                      Trained UTC: <span className={headingText}>{mlGovernance?.model_metadata?.created_at_utc ? new Date(mlGovernance.model_metadata.created_at_utc).toLocaleString() : 'Not recorded'}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                      <span className={`text-[10px] uppercase tracking-wider block font-semibold ${mutedText}`}>Decision Threshold</span>
                      <span className="text-lg font-bold font-sora text-indigo-400">
                        {mlGovernance?.model_metadata?.decision_threshold != null ? mlGovernance.model_metadata.decision_threshold : '—'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className={`mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-3 gap-3 text-xs ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
                  <div>
                    <span className={`text-[11px] block ${mutedText}`}>Artifact Location (Relative):</span>
                    <span className={`font-mono text-[11px] ${headingText}`}>
                      {mlGovernance?.model_metadata?.artifact_location || '—'}
                    </span>
                  </div>
                  <div className="md:col-span-2">
                    <span className={`text-[11px] block ${mutedText}`}>Artifact SHA-256 Digest:</span>
                    <span className={`font-mono text-[11px] truncate block ${headingText}`} title={mlGovernance?.model_metadata?.model_sha256}>
                      {mlGovernance?.model_metadata?.model_sha256 || '—'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Production Usage vs Offline Evaluation */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Live Production Prediction Activity */}
                <div className={`rounded-2xl p-5 ${cardCls}`}>
                  <h3 className={`text-sm font-bold font-sora mb-1 ${headingText}`}>
                    Production Prediction Activity
                  </h3>
                  <p className={`text-[11px] mb-4 ${mutedText}`}>
                    Live records persisted in MySQL (<code className="font-mono">ml_predictions</code> &amp; <code className="font-mono">eligibility_evaluations</code>).
                  </p>
                  <div className="space-y-2.5 text-xs">
                    <div className={`p-3 rounded-xl flex items-center justify-between ${innerCardCls}`}>
                      <span className={mutedText}>Total ML Predictions</span>
                      <strong className={`font-mono text-sm ${headingText}`}>
                        {mlGovernance?.production_usage?.total_ml_predictions ?? '—'}
                      </strong>
                    </div>
                    <div className={`p-3 rounded-xl flex items-center justify-between ${innerCardCls}`}>
                      <span className={mutedText}>Eligibility Evaluations</span>
                      <strong className={`font-mono text-sm ${headingText}`}>
                        {mlGovernance?.production_usage?.total_eligibility_evaluations ?? '—'}
                      </strong>
                    </div>
                    <div className={`p-3 rounded-xl flex items-center justify-between ${innerCardCls}`}>
                      <span className={mutedText}>Eligible / Ineligible</span>
                      <strong className={`font-mono ${headingText}`}>
                        <span className="text-emerald-400">{mlGovernance?.production_usage?.eligible_decisions ?? 0}</span>
                        {' / '}
                        <span className="text-rose-400">{mlGovernance?.production_usage?.ineligible_decisions ?? 0}</span>
                      </strong>
                    </div>
                    <div className={`p-3 rounded-xl flex items-center justify-between ${innerCardCls}`}>
                      <span className={mutedText}>Last Recorded Prediction</span>
                      <span className={`text-[11px] ${headingText}`}>
                        {mlGovernance?.production_usage?.last_prediction_at
                          ? new Date(mlGovernance.production_usage.last_prediction_at).toLocaleString()
                          : 'Not recorded'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Offline Grouped-CV Evaluation Metrics */}
                <div className={`lg:col-span-2 rounded-2xl p-5 ${cardCls}`}>
                  <h3 className={`text-sm font-bold font-sora mb-1 ${headingText}`}>
                    Offline Cross-Validation Evaluation (&tau; = 0.60)
                  </h3>
                  <p className={`text-[11px] mb-4 ${mutedText}`}>
                    From <code className="font-mono">verifymesh_stage2_metadata_v3.json</code> ({mlGovernance?.training_and_evaluation?.training_scenario || 'Scenario B'}).
                    {' '}Training dataset: <strong className={headingText}>{mlGovernance?.training_and_evaluation?.eligible_training_records?.toLocaleString() ?? '—'}</strong> eligible records
                    from <strong className={headingText}>{mlGovernance?.training_and_evaluation?.total_applicant_task_pairs?.toLocaleString() ?? '—'}</strong> pairs.
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
                    {[
                      { label: 'Accuracy', val: mlGovernance?.training_and_evaluation?.test_metrics?.accuracy, cls: headingText },
                      { label: 'Precision', val: mlGovernance?.training_and_evaluation?.test_metrics?.precision, cls: headingText },
                      { label: 'Recall', val: mlGovernance?.training_and_evaluation?.test_metrics?.recall, cls: 'text-emerald-400' },
                      { label: 'Macro F1', val: mlGovernance?.training_and_evaluation?.test_metrics?.macro_f1, cls: headingText },
                      { label: 'ROC-AUC', val: mlGovernance?.training_and_evaluation?.test_metrics?.roc_auc, cls: 'text-indigo-400' },
                      { label: 'PR-AUC', val: mlGovernance?.training_and_evaluation?.test_metrics?.pr_auc, cls: 'text-cyan-400' },
                    ].map((m) => (
                      <div key={m.label} className={`p-3 rounded-xl ${innerCardCls}`}>
                        <span className={`text-[10px] uppercase font-semibold ${mutedText}`}>{m.label}</span>
                        <div className={`text-base font-bold font-sora mt-1 ${m.cls}`}>
                          {m.val != null ? `${(Number(m.val) * 100).toFixed(1)}%` : '—'}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* OOF Confusion Matrix */}
                  {mlGovernance?.training_and_evaluation?.confusion_matrix_oof_tau060 && (
                    <div className="mt-4 pt-4 border-t border-[#1b2542]/40">
                      <span className={`text-[11px] font-semibold uppercase tracking-wider block mb-2 ${mutedText}`}>
                        Out-of-Fold Confusion Matrix (&tau; = 0.60)
                      </span>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-center">
                        <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                          <span className={`text-[10px] block ${mutedText}`}>True Positive (TP)</span>
                          <strong className="font-mono text-emerald-400">{mlGovernance.training_and_evaluation.confusion_matrix_oof_tau060.tp}</strong>
                        </div>
                        <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                          <span className={`text-[10px] block ${mutedText}`}>True Negative (TN)</span>
                          <strong className={`font-mono ${headingText}`}>{mlGovernance.training_and_evaluation.confusion_matrix_oof_tau060.tn}</strong>
                        </div>
                        <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                          <span className={`text-[10px] block ${mutedText}`}>False Positive (FP)</span>
                          <strong className="font-mono text-amber-400">{mlGovernance.training_and_evaluation.confusion_matrix_oof_tau060.fp}</strong>
                        </div>
                        <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                          <span className={`text-[10px] block ${mutedText}`}>False Negative (FN)</span>
                          <strong className="font-mono text-rose-400">{mlGovernance.training_and_evaluation.confusion_matrix_oof_tau060.fn}</strong>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 5-Feature Engineering Schema */}
              <div className={`rounded-2xl p-5 ${cardCls}`}>
                <h3 className={`text-sm font-bold font-sora mb-2 flex items-center gap-2 ${headingText}`}>
                  <Sliders className="w-4 h-4 text-indigo-400" />
                  <span>Engineered 5-Feature Input Schema (Non-Redundant)</span>
                </h3>
                <p className={`text-xs mb-4 ${mutedText}`}>
                  Engineered features computed at candidate inference time with standardized Logistic Regression coefficients from model metadata.
                </p>

                <div className="space-y-2 text-xs">
                  {mlGovernance?.model_metadata?.features?.map((f) => (
                    <div key={f.name} className={`p-3 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${innerCardCls}`}>
                      <div>
                        <span className="font-mono font-bold text-indigo-400 text-xs">{f.name}</span>
                        <p className={`text-[11px] mt-0.5 ${mutedText}`}>{f.description}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {f.standardized_coefficient != null && (
                          <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${cardCls} ${headingText}`}>
                            coef: {f.standardized_coefficient > 0 ? `+${f.standardized_coefficient}` : f.standardized_coefficient}
                          </span>
                        )}
                        <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${mutedText}`}>
                          {f.data_type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </main>
        </div>
      </div>

      {/* Assessment Inspection Dossier Modal */}
      {isAssessmentModalOpen && selectedAssessment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className={`w-full max-w-xl rounded-2xl p-6 shadow-2xl relative space-y-5 max-h-[90vh] overflow-y-auto ${cardCls}`}>
            <div className={`flex items-start justify-between pb-3 border-b ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                    EVALUATION DOSSIER #{selectedAssessment.exam_result_id}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getCompetencyBadgeStyle(selectedAssessment.predicted_competency)}`}>
                    {selectedAssessment.predicted_competency}
                  </span>
                </div>
                <h3 className={`text-base font-bold font-sora mt-1 ${headingText}`}>
                  {selectedAssessment.agent_name}
                </h3>
                <p className={`text-xs ${mutedText}`}>
                  Attempt #{selectedAssessment.attempt_number} &bull; {selectedAssessment.completed_at ? new Date(selectedAssessment.completed_at).toLocaleString() : 'Date pending'}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsAssessmentModalOpen(false)}
                className={`${mutedText} hover:text-indigo-400 p-1 rounded-lg cursor-pointer`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className={`p-4 rounded-xl space-y-2 ${innerCardCls}`}>
              <span className={`text-[10px] font-bold uppercase tracking-wider block ${mutedText}`}>
                {selectedAssessment.category_name || 'General Domain'}
              </span>
              <div className="flex items-center justify-between">
                <h4 className={`text-sm font-bold ${headingText}`}>
                  {selectedAssessment.exam_name || 'Standard Competency Assessment Battery'}
                </h4>
                <div className="flex items-center gap-2">
                  <span className={`text-lg font-bold font-mono ${headingText}`}>
                    {selectedAssessment.assessment_score}%
                  </span>
                  {(selectedAssessment.passed === 1 || selectedAssessment.passed === true || (selectedAssessment.assessment_score >= (selectedAssessment.passing_score || 70))) ? (
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      isDark ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40' : 'text-emerald-700 bg-emerald-50 border-emerald-200'
                    }`}>
                      Passed
                    </span>
                  ) : (
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      isDark ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' : 'text-rose-700 bg-rose-50 border-rose-200'
                    }`}>
                      Failed
                    </span>
                  )}
                </div>
              </div>
            </div>

            {selectedAssessment.features && (
              <div>
                <h5 className={`text-[11px] font-bold uppercase tracking-wider mb-2.5 ${mutedText}`}>
                  Inference Features
                </h5>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  {Object.entries(selectedAssessment.features).map(([k, v]) => (
                    <div key={k} className={`p-2.5 rounded-xl ${innerCardCls}`}>
                      <span className={`text-[10px] block truncate ${mutedText}`}>{k}</span>
                      <span className={`font-bold font-mono mt-0.5 block ${headingText}`}>{String(v ?? '—')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className={`pt-2 flex justify-end border-t ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
              <button
                type="button"
                onClick={() => setIsAssessmentModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* User Profile & Verification Inspection Modal */}
      {isUserModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className={`w-full max-w-xl rounded-2xl p-6 shadow-2xl relative space-y-5 max-h-[90vh] overflow-y-auto ${cardCls}`}>
            <div className={`flex items-start justify-between pb-3 border-b ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
              <div>
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                  USER ACCOUNT &amp; VERIFICATION DOSSIER
                </span>
                <h3 className={`text-base font-bold font-sora mt-1 ${headingText}`}>
                  {selectedUserDetail?.profile?.full_name || 'Loading user profile...'}
                </h3>
                <p className={`text-xs ${mutedText}`}>
                  {selectedUserDetail?.profile?.email || ''}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsUserModalOpen(false)}
                className={`${mutedText} hover:text-indigo-400 p-1 rounded-lg cursor-pointer`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {userDetailLoading ? (
              <div className="py-8 text-center">
                <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className={`text-xs ${mutedText}`}>Loading account details from MySQL...</p>
              </div>
            ) : selectedUserDetail?.profile ? (
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className={`p-3 rounded-xl ${innerCardCls}`}>
                    <span className={`text-[10px] block ${mutedText}`}>User ID</span>
                    <strong className={`font-mono ${headingText}`}>#{selectedUserDetail.profile.user_id}</strong>
                  </div>
                  <div className={`p-3 rounded-xl ${innerCardCls}`}>
                    <span className={`text-[10px] block ${mutedText}`}>Assigned Role</span>
                    <strong className={headingText}>{selectedUserDetail.profile.canonical_role}</strong>
                  </div>
                  <div className={`p-3 rounded-xl ${innerCardCls}`}>
                    <span className={`text-[10px] block ${mutedText}`}>Account Status</span>
                    <strong className={selectedUserDetail.profile.is_active ? 'text-emerald-400' : 'text-rose-400'}>
                      {selectedUserDetail.profile.is_active ? 'Active' : 'Suspended'}
                    </strong>
                  </div>
                  <div className={`p-3 rounded-xl ${innerCardCls}`}>
                    <span className={`text-[10px] block ${mutedText}`}>Email Verification</span>
                    <strong className={selectedUserDetail.profile.email_verified ? 'text-emerald-400' : 'text-amber-400'}>
                      {selectedUserDetail.profile.email_verified ? 'Verified' : 'Unverified'}
                    </strong>
                  </div>
                  <div className={`p-3 rounded-xl ${innerCardCls}`}>
                    <span className={`text-[10px] block ${mutedText}`}>Registered</span>
                    <strong className={headingText}>
                      {selectedUserDetail.profile.created_at ? new Date(selectedUserDetail.profile.created_at).toLocaleDateString() : '—'}
                    </strong>
                  </div>
                  <div className={`p-3 rounded-xl ${innerCardCls}`}>
                    <span className={`text-[10px] block ${mutedText}`}>Last Login</span>
                    <strong className={headingText}>
                      {selectedUserDetail.profile.last_login_at ? new Date(selectedUserDetail.profile.last_login_at).toLocaleString() : 'Not recorded'}
                    </strong>
                  </div>
                </div>

                {selectedUserDetail.verification_summary && (
                  <div>
                    <h4 className={`text-[11px] font-bold uppercase tracking-wider mb-2 ${mutedText}`}>
                      Agent Verification Profile (#{selectedUserDetail.profile.agent_id})
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                        <span className={`text-[10px] block ${mutedText}`}>Certifications</span>
                        <strong className={headingText}>
                          {selectedUserDetail.verification_summary.verified_certifications} / {selectedUserDetail.verification_summary.total_certifications} verified
                        </strong>
                      </div>
                      <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                        <span className={`text-[10px] block ${mutedText}`}>Work Experience</span>
                        <strong className={headingText}>
                          {selectedUserDetail.verification_summary.verified_experiences} / {selectedUserDetail.verification_summary.total_experiences} verified
                        </strong>
                      </div>
                      <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                        <span className={`text-[10px] block ${mutedText}`}>Assessments</span>
                        <strong className={headingText}>
                          {selectedUserDetail.verification_summary.total_assessments} completed
                        </strong>
                      </div>
                      <div className={`p-2.5 rounded-xl ${innerCardCls}`}>
                        <span className={`text-[10px] block ${mutedText}`}>Applications</span>
                        <strong className={headingText}>
                          {selectedUserDetail.verification_summary.total_applications} submitted
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <h4 className={`text-[11px] font-bold uppercase tracking-wider mb-2 ${mutedText}`}>
                    Recent User Activity ({selectedUserDetail.recent_actions?.length || 0})
                  </h4>
                  {selectedUserDetail.recent_actions?.length > 0 ? (
                    <div className={`divide-y rounded-xl border p-2 ${dividerCls} ${innerCardCls}`}>
                      {selectedUserDetail.recent_actions.map((act) => (
                        <div key={act.log_id} className="py-1.5 px-2 flex items-center justify-between gap-2">
                          <span className="font-mono text-[10px] text-indigo-400">{act.action}</span>
                          <span className={`text-[10px] ${mutedText}`}>
                            {act.created_at ? new Date(act.created_at).toLocaleString() : '—'}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className={`text-xs ${mutedText}`}>No audit events recorded for this user.</p>
                  )}
                </div>
              </div>
            ) : null}

            <div className={`pt-2 flex justify-end border-t ${isDark ? 'border-[#1b2542]' : 'border-slate-200'}`}>
              <button
                type="button"
                onClick={() => setIsUserModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
