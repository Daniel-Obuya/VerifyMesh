import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutGrid, 
  User, 
  ListChecks, 
  HelpCircle, 
  LogOut, 
  Bell, 
  ChevronDown, 
  ChevronLeft,
  ChevronRight,
  Check, 
  ArrowRight, 
  Sparkles, 
  ShieldCheck, 
  CheckCircle2, 
  Briefcase, 
  Clock, 
  RotateCcw, 
  AlertCircle, 
  X,
  RefreshCw,
  Star,
  XCircle,
  Send
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { competencyService } from '../services/competencyService';
import { CompetencyDetailsModal } from '../components/dashboard/CompetencyDetailsModal';
import { TaskModal } from '../components/dashboard/TaskModal';
import { HelpModal } from '../components/dashboard/HelpModal';

export const AgentDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;

  // Sidebar collapsible state matching ProfilePage
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Active user menu dropdown
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Modals state
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [agentProfile, setAgentProfile] = useState(null);
  const [taskFilter, setTaskFilter] = useState('all'); // 'all', 'eligible', 'assessment_needed', 'applications'

  // User Avatar synced with ProfilePage
  const avatarStorageKey = user?.id ? `verifymesh_agent_avatar_${user.id}` : 'verifymesh_agent_avatar';
  const [avatarUrl, setAvatarUrl] = useState(() => {
    try {
      return localStorage.getItem(avatarStorageKey) || null;
    } catch {
      return null;
    }
  });

  const openAssessmentForTask = (task = null) => {
    if (task && (task.task_id || task.id)) {
      const tId = task.task_id || task.id;
      const unpassed = task.required_topics?.find(rt => rt.status !== 'Passed');
      const targetTopic = unpassed || task.required_topics?.[0];
      const queryStr = targetTopic ? `?topicId=${targetTopic.topic_id}` : '';
      navigate(`/agent/assessment/${tId}${queryStr}`);
    } else {
      const taskNeedingExam = tasks.find(t => t.state === 'Assessment Needed' || !t.prerequisites?.assessment_met);
      if (taskNeedingExam) {
        const tId = taskNeedingExam.task_id || taskNeedingExam.id;
        const unpassed = taskNeedingExam.required_topics?.find(rt => rt.status !== 'Passed');
        const targetTopic = unpassed || taskNeedingExam.required_topics?.[0];
        const queryStr = targetTopic ? `?topicId=${targetTopic.topic_id}` : '';
        navigate(`/agent/assessment/${tId}${queryStr}`);
      } else {
        navigate('/agent/assessment/general');
      }
    }
  };

  const handleProceedToApply = (taskId) => {
    const targetTask = tasks.find(t => (t.task_id || t.id) === taskId);
    if (targetTask) {
      setSelectedTask(targetTask);
      setIsTaskModalOpen(true);
    }
  };

  // Auto-scroll to tasks section if navigating to /tasks
  useEffect(() => {
    if (location.pathname === '/tasks') {
      const el = document.getElementById('tasks-section');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  }, [location.pathname]);

  // Dynamic Assessment State
  const [isCheckingStatus, setIsCheckingStatus] = useState(true);
  const [hasCompletedAssessment, setHasCompletedAssessment] = useState(false);
  const [currentCompetency, setCurrentCompetency] = useState(null);
  const [evaluationDecision, setEvaluationDecision] = useState(null);
  const [currentConfidence, setCurrentConfidence] = useState(null);
  const [formData, setFormData] = useState(null);
  const [predictionData, setPredictionData] = useState(null);

  // Live Tasks
  const [tasks, setTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);
  const [myApplications, setMyApplications] = useState([]);
  const [dashboardError, setDashboardError] = useState(null);

  // Load live dashboard state from authoritative backend
  const fetchDashboardData = async () => {
    setIsCheckingStatus(true);
    setIsLoadingTasks(true);
    setDashboardError(null);

    try {
      // 1. Check assessment status
      let backendStatus = null;
      let backendReachable = false;
      try {
        const res = await competencyService.getAgentStatus();
        if (res?.success !== undefined) {
          backendReachable = true;
          if (res.success) backendStatus = res;
        }
      } catch (err) {
        console.error('Error fetching agent status:', err);
      }

      const directCompetency = user?.competency_level || user?.competencyLevel;
      const hasAssessed = Boolean(
        backendReachable
          ? (backendStatus?.has_assessed && backendStatus?.competency_level && backendStatus?.competency_level !== 'Not Yet Assessed')
          : (directCompetency && directCompetency !== 'Not Yet Assessed')
      );

      if (hasAssessed) {
        const resolvedCompetency =
          (backendStatus?.competency_level && backendStatus.competency_level !== 'Not Yet Assessed')
            ? backendStatus.competency_level
            : (directCompetency && directCompetency !== 'Not Yet Assessed' ? directCompetency : 'Eligible');

        const resolvedDecision =
          (backendStatus?.evaluation_decision && backendStatus.evaluation_decision !== 'Not Yet Evaluated')
            ? backendStatus.evaluation_decision
            : 'Eligible';

        const resolvedConfidence = backendStatus?.confidence ?? 78;

        const resolvedPrediction =
          backendStatus?.prediction_data ||
          {
            predicted_competency: resolvedCompetency,
            evaluation_decision: resolvedDecision,
            confidence: resolvedConfidence,
            tier_info: {
              title: resolvedCompetency,
              description: 'AI-assisted prediction based on your verified competency profile.'
            }
          };

        setHasCompletedAssessment(true);
        setCurrentCompetency(resolvedCompetency);
        setEvaluationDecision(resolvedDecision);
        setCurrentConfidence(resolvedConfidence);
        setPredictionData(resolvedPrediction);
        if (backendStatus?.assessment) {
          setFormData(backendStatus.assessment);
        }
      } else {
        setHasCompletedAssessment(false);
        setCurrentCompetency(null);
        setEvaluationDecision(null);
        setCurrentConfidence(null);
        setPredictionData(null);
        setFormData(null);
      }
    } catch (err) {
      console.error('Assessment status error:', err);
      setHasCompletedAssessment(false);
      setCurrentCompetency(null);
      setEvaluationDecision(null);
      setCurrentConfidence(null);
    } finally {
      setIsCheckingStatus(false);
    }

    // 2. Fetch Tasks with Eligibility
    try {
      const taskRes = await competencyService.getAgentTasks();
      if (taskRes?.success && Array.isArray(taskRes.tasks)) {
        setTasks(taskRes.tasks);
      } else {
        setTasks([]);
        if (taskRes?.error) {
          setDashboardError(taskRes.error);
        }
      }
    } catch (err) {
      console.error('Error loading tasks:', err);
      setTasks([]);
      setDashboardError('Unable to load your work opportunities. Please verify your connection.');
    } finally {
      setIsLoadingTasks(false);
    }

    // 3. Fetch authenticated agent profile for verified readiness & missing requirements
    try {
      const profRes = await competencyService.getProfile();
      if (profRes?.success && profRes.data) {
        setAgentProfile(profRes.data);
        if (profRes.data.avatar_url) {
          setAvatarUrl(profRes.data.avatar_url);
        }
      }
    } catch (err) {
      console.error('Error loading agent profile:', err);
    }

    // 4. Fetch authenticated agent applications & assignments
    try {
      const appsRes = await competencyService.getAgentApplications();
      if (appsRes?.success && Array.isArray(appsRes.data)) {
        setMyApplications(appsRes.data);
      }
    } catch (err) {
      console.error('Error loading agent applications:', err);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [user]);

  // Handle Assessment Completion
  const handleAssessmentComplete = async (newPrediction, newForm) => {
    const newTier = newPrediction.predicted_competency || newPrediction.prediction || 'Eligible';
    const newDecision = newPrediction.evaluation_decision || (newTier === 'Eligible' ? 'Eligible' : 'Not Eligible');
    const newConf = newPrediction.confidence || 78;

    setHasCompletedAssessment(true);
    setCurrentCompetency(newTier);
    setEvaluationDecision(newDecision);
    setCurrentConfidence(newConf);
    setPredictionData(newPrediction);
    if (newForm) setFormData(newForm);

    setToastMessage(`Assessment evaluated! Competency: ${newTier} • Evaluation: ${newDecision} (${newConf}% confidence).`);
    setTimeout(() => setToastMessage(null), 6000);

    // Refresh tasks and audit activities from backend
    try {
      await fetchDashboardData();
    } catch (err) {
      console.error('Error refreshing post-assessment:', err);
    }
  };

  // Reset to Unassessed (Demo & Testing Feature)
  const handleResetAssessment = async () => {
    try {
      await competencyService.resetAssessment();
      setIsUserMenuOpen(false);
      setToastMessage('Agent reset to unassessed state. Tasks now reflect prerequisite requirements.');
      setTimeout(() => setToastMessage(null), 5000);
      await fetchDashboardData();
    } catch (err) {
      console.error('Error resetting assessment:', err);
    }
  };

  // Callback on successful task application submission
  const handleApplySuccess = async (taskId, newStatus) => {
    setToastMessage(`Application successfully submitted! Status: ${newStatus}`);
    setTimeout(() => setToastMessage(null), 5000);
    try {
      const [taskRes, appRes] = await Promise.all([
        competencyService.getAgentTasks(),
        competencyService.getAgentApplications()
      ]);
      if (taskRes?.success && Array.isArray(taskRes.tasks)) setTasks(taskRes.tasks);
      if (appRes?.success && Array.isArray(appRes.data)) setMyApplications(appRes.data);
    } catch (err) {
      console.error('Error refreshing post-apply:', err);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const openTaskModal = (task) => {
    setSelectedTask(task);
    setIsTaskModalOpen(true);
  };

  // Helper for task state badge styling following 8-step precedence in Dark SaaS Theme
  const getTaskStateBadge = (task) => {
    const state = task.state || 'Requirements Pending';

    // 1. Assigned
    if (state === 'Assigned' || task.application_status === 'Assigned') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          Assigned
        </span>
      );
    }

    // 2. Application Submitted
    if (state === 'Application Submitted' || task.application_status === 'Application Submitted') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/60 text-blue-300 border border-blue-500/40">
          <Clock className="w-3 h-3 text-blue-400" />
          Application Submitted
        </span>
      );
    }

    // 3. Under Review
    if (state === 'Under Review' || task.application_status === 'Under Review') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-300 border border-amber-500/40">
          <Clock className="w-3 h-3 text-amber-400" />
          Under Review
        </span>
      );
    }

    // 4. Shortlisted
    if (state === 'Shortlisted' || task.application_status === 'Shortlisted') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-500/40">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          Shortlisted
        </span>
      );
    }

    // 5. Ready to Apply
    if (state === 'Ready to Apply' || task.can_apply) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
          <Check className="w-3 h-3 text-emerald-400" />
          Ready to Apply
        </span>
      );
    }

    // 6. Certification Required
    if (state === 'Certification Required') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-500/40" title={task.blocking_reason}>
          <AlertCircle className="w-3 h-3 text-rose-400" />
          Certification Required
        </span>
      );
    }

    // 7. Verification Pending
    if (state === 'Verification Pending') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-300 border border-amber-500/40">
          <Clock className="w-3 h-3 text-amber-400" />
          Verification Pending
        </span>
      );
    }

    // 8. Assessment Needed
    if (state === 'Assessment Needed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950/60 text-purple-300 border border-purple-500/40">
          <AlertCircle className="w-3 h-3 text-purple-400" />
          Assessment Needed
        </span>
      );
    }

    // Other specific blocking reasons
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-900/60 text-slate-400 border border-slate-700/60">
        {state}
      </span>
    );
  };

  // Authoritative clean name & initials
  const rawName = agentProfile?.full_name || user?.fullName || user?.username || 'Agent';
  const cleanName = rawName.replace(/\s*\(Verified\)/gi, '').trim();
  const firstName = cleanName.split(' ')[0] || 'Agent';

  const userInitials = cleanName
    ? cleanName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'AG';

  // Work Overview metrics computed strictly from authoritative backend tasks
  const availableCount = tasks.filter(t => t.can_apply === true || t.state === 'Ready to Apply').length;
  const assessmentNeededCount = tasks.filter(t => t.state === 'Assessment Needed' || !t.prerequisites?.assessment_met).length;
  const underReviewCount = tasks.filter(t => ['Application Submitted', 'Under Review'].includes(t.application_status) || t.state === 'Under Review').length;
  const acceptedCount = tasks.filter(t => ['Assigned', 'Accepted'].includes(t.application_status) || t.state === 'Assigned').length;
  const qualifiedCount = tasks.filter(t => 
    t.can_apply === true || 
    t.state === 'Ready to Apply' || 
    t.is_eligible === true || 
    (t.prerequisites?.certification_met && t.prerequisites?.assessment_met && t.prerequisites?.experience_met)
  ).length;

  // Filter tasks based on selected tab
  const filteredTasks = tasks.filter(t => {
    if (taskFilter === 'eligible') return t.can_apply === true || t.state === 'Ready to Apply';
    if (taskFilter === 'assessment_needed') return t.state === 'Assessment Needed' || !t.prerequisites?.assessment_met;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex flex-col font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
      {/* Ambient background glows */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed bottom-10 right-10 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-[#0d1428] text-white px-4 py-3 rounded-xl shadow-2xl border border-[#2b3a67] flex items-center gap-3 text-xs sm:text-sm animate-in slide-in-from-top-4 duration-300">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span>{toastMessage}</span>
          <button 
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-slate-400 hover:text-white ml-2 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ================================================================= */}
      {/* TOP NAVBAR (Exact design language from Profile & Auth) */}
      {/* ================================================================= */}
      <header className="bg-[#080d1a]/95 border-b border-[#1b2542] px-4 sm:px-8 h-16 flex items-center justify-between sticky top-0 z-40 backdrop-blur-md">
        {/* Left: Brand */}
        <div 
          className="flex items-center gap-3 select-none cursor-pointer" 
          onClick={() => navigate('/dashboard')}
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#4b5bd8] to-[#6f7dff] flex items-center justify-center p-2 shadow-lg shadow-indigo-500/25 shrink-0">
            <svg viewBox="0 0 28 28" fill="none" className="w-full h-full text-white">
              <path d="M6 8V18C6 20.2091 7.79086 22 10 22H20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
              <path d="M10 17L15 13L21 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="10" cy="17" r="2.2" fill="currentColor" />
              <circle cx="15" cy="13" r="2.2" fill="currentColor" />
              <circle cx="21" cy="16" r="2.2" fill="currentColor" />
            </svg>
          </div>
          <span className="font-sora text-lg sm:text-xl font-bold text-white tracking-tight leading-none">
            VerifyMesh
          </span>
        </div>

        {/* Right: Notifications & User Profile */}
        <div className="flex items-center gap-3 sm:gap-4">
          <button 
            type="button"
            className="p-2 text-slate-400 hover:text-white hover:bg-[#151f38] rounded-xl transition-colors relative cursor-pointer"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            {hasCompletedAssessment && (
              <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-[#5a69f0] rounded-full shadow-[0_0_8px_#5a69f0]" />
            )}
          </button>

          {/* User Profile Pill & Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2.5 p-1 sm:px-2 rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer select-none"
            >
              {avatarUrl ? (
                <img 
                  src={avatarUrl} 
                  alt={cleanName} 
                  className="w-8 h-8 rounded-full object-cover border border-[#2b3a67] shadow-xs" 
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
                  {userInitials}
                </div>
              )}
              <div className="text-left hidden sm:block">
                <p className="text-xs font-semibold text-white leading-tight">
                  {cleanName}
                </p>
                <p className="text-[10px] text-slate-400 leading-tight">
                  {user?.role || 'Agent'}
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-[#0d1428] rounded-xl shadow-2xl border border-[#2b3a67] py-1.5 z-50 animate-in fade-in zoom-in-95 duration-150 text-xs">
                <div className="px-3.5 py-2 border-b border-[#1e2a4a] sm:hidden">
                  <p className="text-xs font-semibold text-white">{cleanName}</p>
                  <p className="text-[10px] text-slate-400">Agent</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/dashboard');
                  }}
                  className="w-full text-left px-3.5 py-2.5 font-semibold text-white bg-[#1a2850] flex items-center gap-2 cursor-pointer"
                >
                  <LayoutGrid className="w-3.5 h-3.5 text-indigo-400" />
                  Dashboard
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/profile');
                  }}
                  className="w-full text-left px-3.5 py-2.5 font-medium text-slate-300 hover:bg-[#15203d] hover:text-white flex items-center gap-2 cursor-pointer"
                >
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  My Profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    openAssessmentForTask();
                  }}
                  className="w-full text-left px-3.5 py-2.5 font-semibold text-indigo-400 hover:bg-indigo-950/40 flex items-center gap-2 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  {hasCompletedAssessment ? 'Retake Assessment' : 'Complete Assessment'}
                </button>

                {/* Reset Toggle for Demo & Verification */}
                <button
                  type="button"
                  onClick={handleResetAssessment}
                  className="w-full text-left px-3.5 py-2.5 font-medium text-amber-400 hover:bg-amber-950/40 flex items-center gap-2 cursor-pointer"
                  title="Toggle back to unassessed view"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
                  Reset to Unassessed (Demo)
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    setIsHelpModalOpen(true);
                  }}
                  className="w-full text-left px-3.5 py-2.5 font-medium text-slate-300 hover:bg-[#15203d] hover:text-white flex items-center gap-2 cursor-pointer"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                  Help &amp; Documentation
                </button>
                <div className="border-t border-[#1e2a4a] my-1" />
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3.5 py-2.5 font-medium text-rose-400 hover:bg-rose-950/40 flex items-center gap-2 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ================================================================= */}
      {/* MAIN CONTAINER: SIDEBAR + CONTENT */}
      {/* ================================================================= */}
      <div className="flex-1 flex max-w-[1600px] w-full mx-auto relative">
        {/* Left Collapsible Sidebar */}
        <aside 
          className={`bg-[#080d1a] border-r border-[#1b2542] flex flex-col justify-between p-3.5 shrink-0 transition-all duration-300 ease-in-out relative ${
            isSidebarCollapsed ? 'w-20' : 'w-56 lg:w-60'
          }`}
        >
          {/* Top Navigation Links */}
          <div className="space-y-1.5">
            {/* Collapse / Expand Toggle Button */}
            <div className="flex items-center justify-end pb-2">
              <button
                type="button"
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className="w-6 h-6 rounded-full bg-[#12192e] border border-[#2b3a67] text-slate-300 hover:text-white flex items-center justify-center transition-all shadow-md hover:scale-105 cursor-pointer"
                title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {isSidebarCollapsed ? (
                  <ChevronRight className="w-3.5 h-3.5" />
                ) : (
                  <ChevronLeft className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            {/* Dashboard Link (Active on AgentDashboard) */}
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all cursor-pointer bg-gradient-to-r from-[#2942d9] via-[#465deb] to-[#6074f7] shadow-[0_0_20px_rgba(70,93,235,0.45)] text-white ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
            >
              <LayoutGrid className="w-4 h-4 shrink-0 text-white" />
              {!isSidebarCollapsed && <span>Dashboard</span>}
            </button>

            {/* My Profile Link */}
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-[#121a30] transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
            >
              <User className="w-4 h-4 shrink-0 text-slate-400" />
              {!isSidebarCollapsed && <span>My Profile</span>}
            </button>

            {/* Tasks Link */}
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById('tasks-section');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-[#121a30] transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
            >
              <ListChecks className="w-4 h-4 shrink-0 text-slate-400" />
              {!isSidebarCollapsed && <span>Tasks</span>}
            </button>
          </div>

          {/* Task-Driven Skill Evaluation Sidebar Widget (Hidden when collapsed) */}
          {!isSidebarCollapsed && (
            <div className="my-4 p-3.5 rounded-2xl bg-[#0b1020] border border-[#24335c]/80 shadow-[0_0_15px_rgba(15,23,42,0.6)]">
              <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-400">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>Task Qualification</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                Complete missing scenario topic assessments to qualify for matching opportunities.
              </p>
              <button
                type="button"
                onClick={() => {
                  const el = document.getElementById('tasks-section');
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
                className="w-full mt-3 py-2 px-3 text-xs font-semibold rounded-xl bg-[#141d36] hover:bg-[#1c294d] border border-[#2b3c6e] text-indigo-300 hover:text-white transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <span>Explore Tasks</span> &darr;
              </button>
            </div>
          )}

          {/* Bottom Sidebar Items */}
          <div className="space-y-1.5 pt-3 border-t border-[#1b2542]">
            <button
              type="button"
              onClick={() => setIsHelpModalOpen(true)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-[#121a30] transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
              title="Help & Guide"
            >
              <HelpCircle className="w-4 h-4 shrink-0 text-slate-400" />
              {!isSidebarCollapsed && <span>Help &amp; Guide</span>}
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
              title="Sign Out"
            >
              <LogOut className="w-4 h-4 shrink-0 text-slate-400" />
              {!isSidebarCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        </aside>

        {/* ================================================================= */}
        {/* MAIN CONTENT AREA */}
        {/* ================================================================= */}
        <main className="flex-1 p-5 sm:p-7 lg:p-8 space-y-7 overflow-y-auto max-w-6xl mx-auto">
          {/* ============================================================
             YOUR WORK OVERVIEW: PROFESSIONAL ENTERPRISE WORKPLACE HERO
             ============================================================ */}
          <section className="space-y-5">
            {/* Top Welcome Header Container */}
            <div className="p-6 sm:p-7 rounded-2xl bg-[#0b1020]/90 border border-[#24335c]/80 shadow-[0_0_30px_rgba(15,23,42,0.8)] backdrop-blur-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-indigo-500/10 via-transparent to-transparent pointer-events-none" />

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
                <div>
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase font-sora">
                      Your Work Overview
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified Active Agent
                    </span>
                  </div>
                  <h1 className="text-xl sm:text-2xl font-bold font-sora text-white tracking-tight mt-1.5">
                    Welcome back, {firstName}
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-400 mt-1">
                    Here is your real-time work activity and verified task opportunities.
                  </p>
                </div>

                {/* Primary & Secondary Action Buttons */}
                <div className="flex items-center gap-2.5 shrink-0">
                  <button
                    type="button"
                    onClick={() => navigate('/profile')}
                    className="px-3.5 py-2 rounded-xl bg-[#141d36] hover:bg-[#1c294d] border border-[#2b3c6e] text-slate-200 hover:text-white text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer"
                  >
                    <User className="w-3.5 h-3.5 text-indigo-400" />
                    <span>My Profile</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById('tasks-section');
                      if (el) el.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#2942d9] to-[#5a6ef0] hover:brightness-110 text-white text-xs font-semibold shadow-[0_0_15px_rgba(70,93,235,0.4)] transition-all flex items-center gap-2 cursor-pointer"
                  >
                    <Briefcase className="w-3.5 h-3.5" />
                    <span>Explore Opportunities</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                  </button>
                </div>
              </div>

              {/* Profile Completion / Readiness Summary */}
              {agentProfile && agentProfile.readiness_score !== undefined && (
                <div className="mt-5 p-4 rounded-xl bg-[#0e162d] border border-[#232f52] flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
                  <div className="flex items-center gap-3.5 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center justify-center font-bold text-sm shrink-0">
                      {agentProfile.readiness_score}%
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-semibold text-white">Profile Readiness</span>
                        <span className={`px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                          agentProfile.readiness_score >= 75 
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/40' 
                            : 'bg-amber-950/60 text-amber-300 border border-amber-500/40'
                        }`}>
                          {agentProfile.readiness_score === 100 ? 'Fully Verified' : `${agentProfile.readiness_score}% Complete`}
                        </span>
                      </div>
                      {/* Animated gradient progress bar */}
                      <div className="w-full bg-[#141c33] rounded-full h-1.5 mt-2 overflow-hidden border border-[#1b2542]">
                        <div 
                          className="bg-gradient-to-r from-[#2942d9] via-[#465deb] to-[#38bdf8] h-full rounded-full transition-all duration-500 shadow-[0_0_10px_rgba(56,189,248,0.5)]"
                          style={{ width: `${Math.min(100, Math.max(5, agentProfile.readiness_score))}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                    {agentProfile.readiness_checks && (
                      <div className="hidden md:flex items-center gap-2 text-[11px]">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border ${
                          agentProfile.readiness_checks.personal_info
                            ? 'bg-[#09152a] text-emerald-400 border-emerald-500/30'
                            : 'bg-[#151c2e] text-slate-400 border-[#232f52]'
                        }`}>
                          {agentProfile.readiness_checks.personal_info ? <Check className="w-3 h-3 text-emerald-400" /> : '•'} 1. Contact
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border ${
                          agentProfile.readiness_checks.experience
                            ? 'bg-[#09152a] text-emerald-400 border-emerald-500/30'
                            : 'bg-[#151c2e] text-slate-400 border-[#232f52]'
                        }`}>
                          {agentProfile.readiness_checks.experience ? <Check className="w-3 h-3 text-emerald-400" /> : '•'} 2. Experience
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border ${
                          agentProfile.readiness_checks.certification
                            ? 'bg-[#09152a] text-emerald-400 border-emerald-500/30'
                            : 'bg-[#151c2e] text-slate-400 border-[#232f52]'
                        }`}>
                          {agentProfile.readiness_checks.certification ? <Check className="w-3 h-3 text-emerald-400" /> : '•'} 3. Certifications
                        </span>
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => navigate('/profile')}
                      className="font-semibold text-indigo-400 hover:text-indigo-300 text-xs whitespace-nowrap cursor-pointer transition-colors"
                    >
                      View Profile &rarr;
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Error Banner with Retry */}
            {dashboardError && !isLoadingTasks && (
              <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/40 flex items-center justify-between gap-3 text-xs sm:text-sm text-rose-300">
                <div className="flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{dashboardError}</span>
                </div>
                <button
                  type="button"
                  onClick={fetchDashboardData}
                  className="px-2.5 py-1 rounded-md bg-rose-900/60 hover:bg-rose-800/80 text-rose-200 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer border border-rose-700/50"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry</span>
                </button>
              </div>
            )}

            {/* 4 Compact Work Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Card 1: Available Opportunities */}
              <div className="bg-[#0b1020]/90 rounded-2xl border border-[#24335c]/80 p-5 shadow-[0_0_20px_rgba(15,23,42,0.6)] flex flex-col justify-between hover:border-[#3d528b] transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Available Tasks
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
                    <Briefcase className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3.5">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-[#141d36] rounded-md w-16 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-sora text-white tracking-tight">
                        {tasks.length}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        opportunities
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-[#1b2542] flex items-center justify-between text-xs">
                  <span className="text-slate-400 text-[11px]">{availableCount} ready to apply</span>
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById('tasks-section');
                      if (el) el.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="font-semibold text-indigo-400 hover:text-indigo-300 cursor-pointer text-xs transition-colors"
                  >
                    View &rarr;
                  </button>
                </div>
              </div>

              {/* Card 2: Applications Under Review */}
              <div className="bg-[#0b1020]/90 rounded-2xl border border-[#24335c]/80 p-5 shadow-[0_0_20px_rgba(15,23,42,0.6)] flex flex-col justify-between hover:border-[#3d528b] transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Under Review
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0">
                    <Clock className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3.5">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-[#141d36] rounded-md w-16 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-sora text-white tracking-tight">
                        {underReviewCount}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        in pipeline
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-[#1b2542] flex items-center justify-between text-xs">
                  <span className="text-slate-400 text-[11px]">Awaiting decision</span>
                  {underReviewCount > 0 ? (
                    <span className="font-semibold text-amber-300 bg-amber-950/60 px-2.5 py-0.5 rounded-full border border-amber-500/40 text-[10px]">
                      Pending
                    </span>
                  ) : (
                    <span className="text-slate-500 text-[11px]">None active</span>
                  )}
                </div>
              </div>

              {/* Card 3: Accepted Work */}
              <div className="bg-[#0b1020]/90 rounded-2xl border border-[#24335c]/80 p-5 shadow-[0_0_20px_rgba(15,23,42,0.6)] flex flex-col justify-between hover:border-[#3d528b] transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Assigned Work
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3.5">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-[#141d36] rounded-md w-16 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-sora text-white tracking-tight">
                        {acceptedCount}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        contracts
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-[#1b2542] flex items-center justify-between text-xs">
                  <span className="text-slate-400 text-[11px]">Accepted assignments</span>
                  {acceptedCount > 0 ? (
                    <span className="font-semibold text-emerald-400 bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-500/40 text-[10px]">
                      Active
                    </span>
                  ) : (
                    <span className="text-slate-500 text-[11px]">0 active</span>
                  )}
                </div>
              </div>

              {/* Card 4: Task Qualification (Matching exact user mockup & specification) */}
              <div className="bg-[#0b1020]/90 rounded-2xl border border-[#24335c]/80 p-5 shadow-[0_0_20px_rgba(15,23,42,0.6)] flex flex-col justify-between hover:border-[#3d528b] transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Task Qualification
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3.5">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-[#141d36] rounded-md w-16 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-sora text-white tracking-tight">
                        {qualifiedCount}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        / {tasks.length} tasks qualified for
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-[#1b2542] flex items-center justify-between text-xs">
                  <span className="font-semibold text-emerald-400 bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-500/40 text-[10px]">
                    Verified
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setTaskFilter('eligible');
                      const el = document.getElementById('tasks-section');
                      if (el) el.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="font-semibold text-indigo-400 hover:text-indigo-300 cursor-pointer text-xs transition-colors"
                  >
                    View Tasks &rarr;
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* ============================================================
             SECTION: TASKS FOR YOU
             ============================================================ */}
          <section id="tasks-section" className="space-y-4">
            <div>
              <h2 className="text-lg sm:text-xl font-bold font-sora text-white tracking-tight">
                Tasks for You
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Opportunities evaluated against your competency level and verified certifications.
              </p>
            </div>

            {/* Task Filter Tabs */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                <button
                  type="button"
                  onClick={() => setTaskFilter('all')}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    taskFilter === 'all'
                      ? 'bg-gradient-to-r from-[#2942d9] to-[#4e64eb] text-white shadow-[0_0_15px_rgba(70,93,235,0.4)]'
                      : 'bg-[#0e162d] border border-[#232f52] text-slate-400 hover:text-white hover:border-[#34487c]'
                  }`}
                >
                  All Opportunities ({tasks.length})
                </button>
                <button
                  type="button"
                  onClick={() => setTaskFilter('eligible')}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    taskFilter === 'eligible'
                      ? 'bg-gradient-to-r from-[#2942d9] to-[#4e64eb] text-white shadow-[0_0_15px_rgba(70,93,235,0.4)]'
                      : 'bg-[#0e162d] border border-[#232f52] text-slate-400 hover:text-white hover:border-[#34487c]'
                  }`}
                >
                  Ready to Apply ({availableCount})
                </button>
                <button
                  type="button"
                  onClick={() => setTaskFilter('assessment_needed')}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    taskFilter === 'assessment_needed'
                      ? 'bg-gradient-to-r from-[#2942d9] to-[#4e64eb] text-white shadow-[0_0_15px_rgba(70,93,235,0.4)]'
                      : 'bg-[#0e162d] border border-[#232f52] text-slate-400 hover:text-white hover:border-[#34487c]'
                  }`}
                >
                  Assessments Needed ({assessmentNeededCount})
                </button>
                <button
                  type="button"
                  onClick={() => setTaskFilter('applications')}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    taskFilter === 'applications'
                      ? 'bg-gradient-to-r from-[#2942d9] to-[#4e64eb] text-white shadow-[0_0_15px_rgba(70,93,235,0.4)]'
                      : 'bg-[#0e162d] border border-[#232f52] text-slate-400 hover:text-white hover:border-[#34487c]'
                  }`}
                >
                  My Applications ({myApplications.length})
                </button>
              </div>
            </div>

            {/* Content: Applications vs Available Tasks */}
            {taskFilter === 'applications' ? (
              myApplications.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {myApplications.map((app) => {
                    const isAssigned = app.status === 'Assigned';
                    const isShortlisted = app.status === 'Shortlisted';
                    const isRejected = app.status === 'Rejected';
                    const isUnderReview = app.status === 'Under Review';

                    return (
                      <div
                        key={app.application_id}
                        className={`bg-[#0b1020]/90 rounded-2xl border p-5 sm:p-6 shadow-[0_0_25px_rgba(15,23,42,0.7)] flex flex-col justify-between transition-all ${
                          isAssigned
                            ? 'border-emerald-500/50 bg-gradient-to-br from-[#0b1020] to-emerald-950/20'
                            : isShortlisted
                            ? 'border-indigo-500/50 bg-gradient-to-br from-[#0b1020] to-indigo-950/20'
                            : isRejected
                            ? 'border-rose-500/50 bg-gradient-to-br from-[#0b1020] to-rose-950/20'
                            : 'border-[#24335c]/80 hover:border-[#3d528b]'
                        }`}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h3 className="text-base font-bold font-sora text-white leading-snug line-clamp-1">
                                {app.task_name}
                              </h3>
                              <span className="text-xs text-indigo-400/90 font-medium">
                                {app.category_name} &bull; {app.work_arrangement || 'Remote'}
                              </span>
                            </div>
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1 shrink-0 ${
                                isAssigned
                                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                                  : isShortlisted
                                  ? 'bg-indigo-950/60 text-indigo-300 border-indigo-500/40'
                                  : isRejected
                                  ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                                  : isUnderReview
                                  ? 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                                  : 'bg-slate-900/60 text-slate-400 border-slate-700/60'
                              }`}
                            >
                              {isAssigned && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                              {isRejected && <XCircle className="w-3 h-3 text-rose-400" />}
                              {app.status}
                            </span>
                          </div>

                          <div className="mt-4 p-3 rounded-xl bg-[#0e162d] border border-[#232f52] space-y-1.5 text-xs text-slate-300">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 font-medium text-[11px]">Compensation:</span>
                              <span className="font-semibold text-white text-xs">{app.payout}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 font-medium text-[11px]">Applied:</span>
                              <span className="text-slate-300 font-medium text-xs">
                                {new Date(app.applied_at).toLocaleDateString()}
                              </span>
                            </div>
                            {app.notes && (
                              <div className="pt-2 border-t border-[#1e2a4a] mt-1.5">
                                <span className="text-slate-400 font-medium text-[11px] block">Your Note:</span>
                                <span className="text-slate-300 italic block mt-0.5 text-xs">&ldquo;{app.notes}&rdquo;</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-[#1b2542] text-xs">
                          {isAssigned ? (
                            <div className="p-2.5 rounded-xl bg-emerald-950/40 text-emerald-300 font-medium flex items-center gap-2 border border-emerald-500/30 text-xs">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              <span>You are assigned to this task! Deliverables coordination active.</span>
                            </div>
                          ) : isShortlisted ? (
                            <div className="p-2.5 rounded-xl bg-indigo-950/40 text-indigo-300 font-medium flex items-center gap-2 border border-indigo-500/30 text-xs">
                              <Star className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                              <span>Shortlisted by admin! Final review in progress.</span>
                            </div>
                          ) : isRejected ? (
                            <div className="p-2.5 rounded-xl bg-rose-950/40 text-rose-300 font-medium flex items-center gap-2 border border-rose-500/30 text-xs">
                              <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                              <span>Application was not selected for this opening.</span>
                            </div>
                          ) : (
                            <div className="p-2.5 rounded-xl bg-[#0e162d] text-slate-300 font-medium flex items-center gap-2 border border-[#232f52] text-xs">
                              <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              <span>Application under review by client and administration.</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="bg-[#0b1020]/50 rounded-2xl border border-dashed border-[#24335c] p-10 sm:p-12 text-center shadow-[0_0_20px_rgba(15,23,42,0.4)] flex flex-col items-center justify-center">
                  <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-3 border border-indigo-500/20 shadow-xs">
                    <Briefcase className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold font-sora text-white mb-1">
                    No submitted applications yet
                  </h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                    Browse available opportunities under &lsquo;All Opportunities&rsquo; and click &lsquo;Apply Now&rsquo; once your prerequisites are met.
                  </p>
                </div>
              )
            ) : isLoadingTasks ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-[#0b1020]/90 rounded-2xl border border-[#24335c]/80 p-5 sm:p-6 shadow-xs animate-pulse space-y-3.5">
                    <div className="h-5 bg-[#141d36] rounded-md w-3/4" />
                    <div className="h-3.5 bg-[#141d36] rounded-sm w-full" />
                    <div className="h-3.5 bg-[#141d36] rounded-sm w-2/3" />
                    <div className="h-9 bg-[#141d36] rounded-xl w-full mt-4" />
                  </div>
                ))}
              </div>
            ) : filteredTasks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredTasks.map((task) => {
                  const isAssessmentPassed = task.exam_status === 'Passed' || task.prerequisites?.assessment_met;
                  const examName = task.exam_name || (task.exam_id === 3 ? 'Customer Support Diagnostic Assessment' : 'VerifyMesh Competency Assessment');
                  const examPassingScore = task.exam_passing_score ?? 70;

                  return (
                    <div 
                      key={task.task_id || task.id} 
                      className="bg-[#0b1020]/90 rounded-2xl border border-[#24335c]/80 p-5 sm:p-6 shadow-[0_0_25px_rgba(15,23,42,0.7)] flex flex-col justify-between hover:border-indigo-500/50 hover:shadow-[0_0_35px_rgba(70,93,235,0.2)] transition-all"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="text-base font-bold font-sora text-white leading-snug line-clamp-1">
                              {task.title}
                            </h3>
                            {task.category && (
                              <span className="text-xs text-indigo-400/90 font-medium">{task.category}</span>
                            )}
                          </div>
                          {getTaskStateBadge(task)}
                        </div>

                        <p className="text-xs text-slate-300 mt-2.5 leading-relaxed line-clamp-2">
                          {task.description}
                        </p>

                        {/* Task-Driven Assessment Topic Box */}
                        <div className={`mt-4 p-3 rounded-xl border text-xs ${
                          isAssessmentPassed 
                            ? 'bg-emerald-950/20 border-emerald-500/30' 
                            : 'bg-[#0e162d] border-[#232f52]'
                        }`}>
                          <div className="flex items-center justify-between text-[10px] font-semibold text-slate-400 mb-2">
                            <span className="uppercase tracking-wider text-indigo-400 font-bold">
                              Required Qualification {task.required_topics?.length > 1 ? `(${task.required_topics.length} Topics)` : 'Assessment'}
                            </span>
                            <span className="text-slate-400">
                              {task.topics_total ? `${task.topics_passed_count || 0}/${task.topics_total} Passed` : '5 Questions'}
                            </span>
                          </div>

                          {task.required_topics && task.required_topics.length > 0 ? (
                            <div className="space-y-1.5">
                              {task.required_topics.map(rt => (
                                <div key={rt.topic_id} className="flex items-center justify-between gap-2">
                                  <span className="font-medium text-slate-200 truncate text-[11px]" title={rt.name || rt.topic_name}>
                                    {rt.name || rt.topic_name}
                                  </span>
                                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${
                                    rt.status === 'Passed'
                                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                                      : rt.status === 'Failed'
                                      ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                                      : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                                  }`}>
                                    {rt.status === 'Passed'
                                      ? `✓ Passed (${rt.latest_score ?? rt.score ?? 0}%)`
                                      : rt.status === 'Failed'
                                      ? `✗ Failed (${rt.latest_score ?? rt.score ?? 0}%)`
                                      : `Needed (≥${rt.passing_threshold ?? rt.passing_score ?? 70}%)`}
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-slate-200 truncate text-xs" title={examName}>
                                {examName}
                              </span>
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${
                                isAssessmentPassed
                                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                                  : task.exam_status === 'Failed'
                                  ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                                  : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                              }`}>
                                {isAssessmentPassed 
                                  ? (task.exam_score !== null && task.exam_score !== undefined ? `✓ Passed (${task.exam_score}%)` : '✓ Passed') 
                                  : task.exam_status === 'Failed'
                                  ? `✗ Failed (${task.exam_score}%)`
                                  : `Needed (≥${examPassingScore}%)`}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Requirements Grid */}
                        <div className="grid grid-cols-2 gap-2.5 mt-3.5 pt-3 border-t border-[#1b2542]">
                          <div>
                            <span className="text-[10px] text-slate-400 font-medium block uppercase tracking-wider">Required competency</span>
                            <p className="text-xs font-semibold text-white mt-0.5">
                              {task.requiredCompetency || task.required_competency || 'Eligible'}
                            </p>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 font-medium block uppercase tracking-wider">Certification</span>
                            <p className="text-xs font-semibold text-white mt-0.5 truncate" title={task.required_certification}>
                              {task.required_certification || 'None required'}
                            </p>
                          </div>
                        </div>

                        {task.blocking_reason && !task.can_apply && (!task.application_status || task.application_status === 'Not Applied') && (
                          <div className="mt-3 p-2.5 rounded-xl bg-amber-950/40 border border-amber-500/30 text-[11px] text-amber-300 leading-snug flex items-start gap-2">
                            <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                            <span>{task.blocking_reason}</span>
                          </div>
                        )}
                      </div>

                      <div className="pt-3.5 flex items-center justify-between border-t border-[#1b2542] mt-4">
                        <div>
                          <span className="text-sm font-bold text-white block">
                            {task.payout || '$30 - $40 / hr'}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {task.work_arrangement || 'Remote'}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {task.state === 'Assessment Needed' ? (
                            <button
                              type="button"
                              onClick={() => openAssessmentForTask(task)}
                              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-[#2942d9] to-[#5a6ef0] hover:brightness-110 text-white font-semibold text-xs shadow-[0_0_15px_rgba(70,93,235,0.4)] flex items-center gap-1 cursor-pointer transition-all"
                            >
                              <span>Take Assessment</span>
                              <ArrowRight className="w-3 h-3 ml-0.5" />
                            </button>
                          ) : task.state === 'Ready to Apply' || task.can_apply ? (
                            <button
                              type="button"
                              onClick={() => openTaskModal(task)}
                              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:brightness-110 text-white font-semibold text-xs shadow-[0_0_15px_rgba(16,185,129,0.35)] flex items-center gap-1 cursor-pointer transition-all"
                            >
                              <span>Apply Now</span>
                              <ArrowRight className="w-3 h-3 ml-0.5" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => openTaskModal(task)}
                              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 hover:underline cursor-pointer transition-colors"
                            >
                              View details &rarr;
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-[#0b1020]/50 rounded-2xl border border-dashed border-[#24335c] p-10 sm:p-12 text-center shadow-[0_0_20px_rgba(15,23,42,0.4)] flex flex-col items-center justify-center">
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-3 border border-indigo-500/20 shadow-xs">
                  <Briefcase className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold font-sora text-white mb-1">
                  No opportunities match your filter
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                  Try switching back to 'All Opportunities' to view all available tasks.
                </p>
              </div>
            )}
          </section>
        </main>
      </div>

      {/* Modals */}
      <CompetencyDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
        prediction={predictionData}
        formData={formData}
        onOpenAssessment={() => openAssessmentForTask()}
      />

      <TaskModal
        isOpen={isTaskModalOpen}
        onClose={() => setIsTaskModalOpen(false)}
        task={selectedTask}
        userCompetency={currentCompetency || 'Not Yet Assessed'}
        onOpenAssessment={(t) => openAssessmentForTask(t || selectedTask)}
        onApplySuccess={handleApplySuccess}
      />

      <HelpModal
        isOpen={isHelpModalOpen}
        onClose={() => setIsHelpModalOpen(false)}
      />
    </div>
  );
};
