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
  RefreshCw
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

  // Active user menu
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Modals state
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [agentProfile, setAgentProfile] = useState(null);
  const [taskFilter, setTaskFilter] = useState('all'); // 'all', 'eligible', 'assessment_needed'

  const openAssessmentForTask = (task = null) => {
    if (task && (task.task_id || task.id)) {
      navigate(`/agent/assessment/${task.task_id || task.id}`);
    } else {
      const taskNeedingExam = tasks.find(t => t.state === 'Assessment Needed' || !t.prerequisites?.assessment_met);
      if (taskNeedingExam) {
        navigate(`/agent/assessment/${taskNeedingExam.task_id || taskNeedingExam.id}`);
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
              description: 'AI-assisted prediction based on your verified competency profile.',
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
      }
    } catch (err) {
      console.error('Error loading agent profile:', err);
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

    // Cache locally for fallback persistence
    if (user?.id) {
      const localKey = `verifymesh_agent_assessment_${user.id}`;
      localStorage.setItem(localKey, JSON.stringify({
        ...newPrediction,
        assessment: newForm,
        competency_level: newTier,
        evaluation_decision: newDecision,
        confidence: newConf,
      }));
    }

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
      if (user?.id) {
        localStorage.removeItem(`verifymesh_agent_assessment_${user.id}`);
      }
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
      const [taskRes, actRes] = await Promise.all([
        competencyService.getAgentTasks(),
        competencyService.getAgentActivities()
      ]);
      if (taskRes?.success && Array.isArray(taskRes.tasks)) setTasks(taskRes.tasks);
      if (actRes?.success && Array.isArray(actRes.activities)) setRecentActivities(actRes.activities);
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

  // Helper for task state badge styling following 8-step precedence
  const getTaskStateBadge = (task) => {
    const state = task.state || 'Requirements Pending';

    // 1. Assigned
    if (state === 'Assigned' || task.application_status === 'Assigned') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Assigned
        </span>
      );
    }

    // 2. Application Submitted
    if (state === 'Application Submitted' || task.application_status === 'Application Submitted') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-[#3B50BA] border border-blue-200 shrink-0">
          <Clock className="w-3.5 h-3.5" />
          Application Submitted
        </span>
      );
    }

    // 3. Under Review
    if (state === 'Under Review' || task.application_status === 'Under Review') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
          <Clock className="w-3.5 h-3.5" />
          Under Review
        </span>
      );
    }

    // 4. Shortlisted
    if (state === 'Shortlisted' || task.application_status === 'Shortlisted') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 shrink-0">
          <Sparkles className="w-3.5 h-3.5" />
          Shortlisted
        </span>
      );
    }

    // 5. Ready to Apply
    if (state === 'Ready to Apply' || task.can_apply) {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
          <Check className="w-3.5 h-3.5" />
          Ready to Apply
        </span>
      );
    }

    // 6. Certification Required
    if (state === 'Certification Required') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 shrink-0" title={task.blocking_reason}>
          <AlertCircle className="w-3.5 h-3.5" />
          Certification Required
        </span>
      );
    }

    // 7. Verification Pending
    if (state === 'Verification Pending') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
          <Clock className="w-3.5 h-3.5" />
          Verification Pending
        </span>
      );
    }

    // 8. Assessment Needed
    if (state === 'Assessment Needed') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
          <AlertCircle className="w-3.5 h-3.5" />
          Assessment Needed
        </span>
      );
    }

    // Other specific blocking reasons (e.g. Experience Required, Competency Below Standard, etc.)
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
        {state}
      </span>
    );
  };

  // Helper for task card CTA label
  const getTaskActionText = (task) => {
    if (task.state === 'Assigned' || task.application_status === 'Assigned') {
      return 'View assignment →';
    }
    if (task.application_status && task.application_status !== 'Not Applied') {
      return 'View application →';
    }
    if (task.state === 'Ready to Apply' || task.can_apply) {
      return 'Apply now →';
    }
    return 'View requirements →';
  };

  // Work Overview metrics computed strictly from authoritative backend tasks and agent status
  const firstName = user?.fullName ? user.fullName.trim().split(' ')[0] : (user?.username || 'Agent');
  const availableCount = tasks.filter(t => t.can_apply === true || t.state === 'Ready to Apply').length;
  const assessmentNeededCount = tasks.filter(t => t.state === 'Assessment Needed' || !t.prerequisites?.assessment_met).length;
  const underReviewCount = tasks.filter(t => ['Application Submitted', 'Under Review'].includes(t.application_status) || t.state === 'Under Review').length;
  const acceptedCount = tasks.filter(t => ['Assigned', 'Accepted'].includes(t.application_status) || t.state === 'Assigned').length;
  const hasPendingCert = tasks.some(t => t.state === 'Verification Pending');

  // Filter tasks based on selected tab
  const filteredTasks = tasks.filter(t => {
    if (taskFilter === 'eligible') return t.can_apply === true || t.state === 'Ready to Apply';
    if (taskFilter === 'assessment_needed') return t.state === 'Assessment Needed' || !t.prerequisites?.assessment_met;
    return true;
  });

  // Work Readiness state
  const getReadinessState = () => {
    if (currentCompetency) {
      const isEligible = currentCompetency === 'Eligible' || evaluationDecision === 'Eligible';
      return {
        badge: isEligible ? 'Verified' : 'Not Eligible',
        badgeColor: isEligible
          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
          : 'bg-rose-50 text-rose-700 border-rose-200',
        title: isEligible ? 'Eligible' : 'Not Eligible',
        subtitle: isEligible ? 'Verified competency gatekeeper status' : 'Competency threshold not met',
        actionLabel: 'View Profile',
        onAction: () => navigate('/profile'),
        icon: isEligible ? ShieldCheck : AlertCircle
      };
    }
    if (hasPendingCert) {
      return {
        badge: 'Pending',
        badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
        title: 'Cert Pending',
        subtitle: 'Credentials in verification',
        actionLabel: 'View Profile',
        onAction: () => navigate('/profile'),
        icon: Clock
      };
    }
    return {
      badge: 'Active',
      badgeColor: 'bg-blue-50 text-[#3B50BA] border-blue-200',
      title: 'Active Agent',
      subtitle: 'Select a task to qualify',
      actionLabel: 'Browse Tasks',
      onAction: () => {
        const el = document.getElementById('tasks-section');
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      },
      icon: Briefcase
    };
  };

  const readiness = getReadinessState();

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans text-slate-800">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-xl flex items-center gap-3 text-xs sm:text-sm animate-in slide-in-from-top-4 duration-300">
          <Sparkles className="w-4 h-4 text-[#818CF8]" />
          <span>{toastMessage}</span>
          <button 
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-slate-400 hover:text-white ml-2"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Top Navbar matching screenshot */}
      <header className="bg-white border-b border-slate-200/80 px-6 sm:px-8 h-16 flex items-center justify-between sticky top-0 z-30">
        {/* Brand Logo */}
        <div className="flex items-center gap-2.5 select-none">
          <div className="w-8 h-8 rounded-lg bg-[#3B50BA] flex items-center justify-center p-1.5 shadow-xs shrink-0">
            <svg 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2.2" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              className="w-full h-full text-white"
            >
              <path d="M3 16l6-6 4 4 8-8" />
              <path d="M14 6h7v7" />
            </svg>
          </div>
          <span className="text-lg font-bold text-slate-900 tracking-tight">
            VerifyMesh
          </span>
        </div>

        {/* User Info & Actions */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Notification Bell */}
          <button 
            type="button"
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-full transition-colors relative"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5" />
            {hasCompletedAssessment && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#3B50BA] rounded-full" />
            )}
          </button>

          {/* User Profile Pill & Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2.5 p-1 sm:px-2 rounded-xl hover:bg-slate-50 transition-colors cursor-pointer select-none"
            >
              <div className="w-9 h-9 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-xs sm:text-sm flex items-center justify-center">
                {user?.fullName ? user.fullName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'DO'}
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-sm font-semibold text-slate-900 leading-tight">
                  {user?.fullName || 'Daniel Obuya'}
                </p>
                <p className="text-xs text-slate-400 leading-tight">
                  {user?.role || 'Agent'}
                </p>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {/* Profile Dropdown */}
            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg border border-slate-150 py-1.5 z-40 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3 py-2 border-b border-slate-100 sm:hidden">
                  <p className="text-xs font-semibold text-slate-900">{user?.fullName || 'Daniel Obuya'}</p>
                  <p className="text-[11px] text-slate-400">Agent</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/profile');
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2 cursor-pointer"
                >
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  My Profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    openAssessmentForTask();
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-semibold text-[#3B50BA] hover:bg-blue-50/60 flex items-center gap-2"
                >
                  <Sparkles className="w-3.5 h-3.5 text-[#3B50BA]" />
                  {hasCompletedAssessment ? 'Retake Assessment' : 'Complete Assessment'}
                </button>

                {/* Reset Toggle for Demo & Verification */}
                <button
                  type="button"
                  onClick={handleResetAssessment}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-amber-700 hover:bg-amber-50/60 flex items-center gap-2"
                  title="Toggle back to unassessed first-time view"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-amber-600" />
                  Reset to Unassessed (Demo)
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    setIsHelpModalOpen(true);
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                  Help &amp; Documentation
                </button>
                <div className="border-t border-slate-100 my-1" />
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 flex items-center gap-2"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Container with Sidebar + Content */}
      <div className="flex-1 flex flex-col md:flex-row max-w-[1440px] w-full mx-auto">
        {/* Left Sidebar matching screenshot */}
        <aside className="w-full md:w-56 lg:w-60 bg-white border-r border-slate-200/80 flex flex-col justify-between p-4 shrink-0">
          <div className="space-y-1">
            {/* Dashboard Nav */}
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors cursor-pointer ${
                currentPath === '/dashboard' || currentPath === '/agent/dashboard'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <LayoutGrid className="w-4 h-4 text-[#3B50BA]" />
              <span>Dashboard</span>
            </button>

            {/* My Profile */}
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors cursor-pointer ${
                currentPath === '/profile'
                  ? 'bg-[#EEF2FF] text-[#3B50BA] font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <User className={`w-4 h-4 ${currentPath === '/profile' ? 'text-[#3B50BA]' : 'text-slate-500'}`} />
              <span>My Profile</span>
            </button>

            {/* Tasks */}
            <button
              type="button"
              onClick={() => navigate('/tasks')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors cursor-pointer ${
                currentPath === '/tasks'
                  ? 'bg-[#EEF2FF] text-[#3B50BA] font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <ListChecks className={`w-4 h-4 ${currentPath === '/tasks' ? 'text-[#3B50BA]' : 'text-slate-500'}`} />
              <span>Tasks</span>
            </button>
          </div>

          {/* Task-Driven Skill Evaluation Sidebar Widget */}
          <div className="my-6 p-4 rounded-2xl bg-gradient-to-br from-blue-50/80 to-indigo-50/40 border border-blue-100 hidden md:block">
            <div className="flex items-center gap-2 text-xs font-bold text-[#3B50BA]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Task-Driven Qualification</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
              Each task opportunity defines its required scenario assessment topic. Complete missing evaluations to qualify for matching roles.
            </p>
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById('tasks-section');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              className="w-full mt-3 py-2 px-3 bg-[#3B50BA] hover:bg-[#31429e] text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <span>Explore Opportunities</span> &darr;
            </button>
          </div>

          {/* Bottom Sidebar Items */}
          <div className="space-y-1 pt-4 border-t border-slate-150">
            <button
              type="button"
              onClick={() => setIsHelpModalOpen(true)}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <HelpCircle className="w-4 h-4 text-slate-500" />
              <span>Help</span>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50/60 transition-colors"
            >
              <LogOut className="w-4 h-4 text-slate-500 hover:text-rose-600" />
              <span>Logout</span>
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 sm:p-8 lg:p-10 space-y-8 overflow-y-auto max-w-6xl">
          {/* ============================================================
             YOUR WORK OVERVIEW: PROFESSIONAL WORKPLACE HERO
             ============================================================ */}
          <section className="space-y-6">
            {/* Top Welcome Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-bold text-[#3B50BA] tracking-wider uppercase block">
                  Your Work Overview
                </span>
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mt-1">
                  Welcome back, {firstName}
                </h1>
                <p className="text-sm text-slate-500 mt-1">
                  Here is your real-time work activity and verified task opportunities.
                </p>
              </div>

              {/* Primary & Secondary Action Buttons */}
              <div className="flex items-center gap-3 shrink-0">
                <button
                  type="button"
                  onClick={() => navigate('/profile')}
                  className="px-4 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
                >
                  <User className="w-4 h-4 text-slate-500" />
                  <span>My Profile</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const el = document.getElementById('tasks-section');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="px-4 sm:px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-xs sm:text-sm shadow-xs hover:shadow-sm transition-all flex items-center gap-2 cursor-pointer active:scale-98"
                >
                  <Briefcase className="w-4 h-4" />
                  <span>Explore Opportunities</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Profile Completion / Readiness Summary */}
            {agentProfile && agentProfile.readiness_score !== undefined && (
              <div className="p-3.5 px-4 rounded-2xl bg-white border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-blue-50 text-[#3B50BA] flex items-center justify-center font-bold text-xs shrink-0">
                    {agentProfile.readiness_score}%
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900">Profile Readiness</span>
                      <span className={`px-2 py-0.2 rounded-full font-semibold text-[10px] ${
                        agentProfile.readiness_score >= 75 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {agentProfile.readiness_score === 100 ? 'Fully Verified' : 'Profile Active'}
                      </span>
                    </div>
                    <p className="text-slate-500 mt-0.5 text-[11px]">
                      Verified agent profile. Browse available tasks below to qualify and apply.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center">
                  {agentProfile.readiness_checks && (
                    <div className="flex items-center gap-1.5">
                      {!agentProfile.readiness_checks.certification && (
                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                          Add Certification
                        </span>
                      )}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => navigate('/profile')}
                    className="font-bold text-[#3B50BA] hover:underline text-xs whitespace-nowrap cursor-pointer ml-1"
                  >
                    View Profile &rarr;
                  </button>
                </div>
              </div>
            )}

            {/* Error Banner with Retry (Distinguishes actual errors from empty 0s) */}
            {dashboardError && !isLoadingTasks && (
              <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-between gap-3 text-sm text-rose-800">
                <div className="flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{dashboardError}</span>
                </div>
                <button
                  type="button"
                  onClick={fetchDashboardData}
                  className="px-3 py-1.5 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-800 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry</span>
                </button>
              </div>
            )}

            {/* 4 Compact Work Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
              {/* Card 1: Available Opportunities */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Available Tasks
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-blue-50 text-[#3B50BA] flex items-center justify-center shrink-0">
                    <Briefcase className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-4">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-slate-100 rounded-md w-14 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-slate-900 tracking-tight">
                        {tasks.length}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        opportunities
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500">{availableCount} ready to apply</span>
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById('tasks-section');
                      if (el) el.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="font-semibold text-[#3B50BA] hover:underline cursor-pointer"
                  >
                    View &rarr;
                  </button>
                </div>
              </div>

              {/* Card 2: Applications Under Review */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Under Review
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
                    <Clock className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-4">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-slate-100 rounded-md w-14 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-slate-900 tracking-tight">
                        {underReviewCount}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        in pipeline
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Awaiting decision</span>
                  {underReviewCount > 0 ? (
                    <span className="font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 text-[10px]">
                      Pending
                    </span>
                  ) : (
                    <span className="text-slate-400 text-[11px]">None active</span>
                  )}
                </div>
              </div>

              {/* Card 3: Accepted Work */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Assigned Work
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-4">
                  {isLoadingTasks ? (
                    <div className="h-8 bg-slate-100 rounded-md w-14 animate-pulse" />
                  ) : (
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-slate-900 tracking-tight">
                        {acceptedCount}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        contracts
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Accepted assignments</span>
                  {acceptedCount > 0 ? (
                    <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 text-[10px]">
                      Active
                    </span>
                  ) : (
                    <span className="text-slate-400 text-[11px]">0 active</span>
                  )}
                </div>
              </div>

              {/* Card 4: Work Readiness */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Work Readiness
                  </span>
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                    !hasCompletedAssessment ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'
                  }`}>
                    {React.createElement(readiness.icon, { className: 'w-4 h-4' })}
                  </div>
                </div>
                <div className="mt-4">
                  {isCheckingStatus ? (
                    <div className="h-8 bg-slate-100 rounded-md w-24 animate-pulse" />
                  ) : (
                    <div>
                      <span className="text-lg font-bold text-slate-900 tracking-tight block truncate" title={readiness.title}>
                        {readiness.title}
                      </span>
                      <span className="text-xs text-slate-400 font-medium block truncate">
                        {readiness.subtitle}
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className={`px-2 py-0.5 rounded-full font-semibold text-[10px] border ${readiness.badgeColor}`}>
                    {readiness.badge}
                  </span>
                  <button
                    type="button"
                    onClick={readiness.onAction}
                    className="font-semibold text-[#3B50BA] hover:underline cursor-pointer"
                  >
                    {readiness.actionLabel} &rarr;
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* Section: Tasks for You */}
          <section id="tasks-section" className="space-y-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Tasks for You
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Opportunities evaluated against your competency level and verified certifications.
              </p>
            </div>

            {/* Task Filter Tabs */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                <button
                  type="button"
                  onClick={() => setTaskFilter('all')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                    taskFilter === 'all'
                      ? 'bg-[#3B50BA] text-white shadow-xs'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  All Opportunities ({tasks.length})
                </button>
                <button
                  type="button"
                  onClick={() => setTaskFilter('eligible')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                    taskFilter === 'eligible'
                      ? 'bg-[#3B50BA] text-white shadow-xs'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Ready to Apply ({availableCount})
                </button>
                <button
                  type="button"
                  onClick={() => setTaskFilter('assessment_needed')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                    taskFilter === 'assessment_needed'
                      ? 'bg-[#3B50BA] text-white shadow-xs'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Assessments Needed ({assessmentNeededCount})
                </button>
              </div>
            </div>

            {/* Tasks Grid */}
            {isLoadingTasks ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs animate-pulse space-y-4">
                    <div className="h-5 bg-slate-200 rounded-md w-3/4" />
                    <div className="h-4 bg-slate-100 rounded-sm w-full" />
                    <div className="h-4 bg-slate-100 rounded-sm w-2/3" />
                    <div className="h-8 bg-slate-100 rounded-md w-full mt-4" />
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
                      className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                              {task.title}
                            </h3>
                            {task.category && (
                              <span className="text-xs text-slate-400 font-medium">{task.category}</span>
                            )}
                          </div>
                          {getTaskStateBadge(task)}
                        </div>

                        <p className="text-sm text-slate-500 mt-2 leading-relaxed line-clamp-2">
                          {task.description}
                        </p>

                        {/* Task-Driven Assessment Topic Box */}
                        <div className={`mt-4 p-3 rounded-xl border text-xs ${
                          isAssessmentPassed 
                            ? 'bg-emerald-50/50 border-emerald-200/80' 
                            : 'bg-blue-50/40 border-blue-100'
                        }`}>
                          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500 mb-1.5">
                            <span className="uppercase tracking-wider text-[#3B50BA]">
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
                                  <span className="font-semibold text-slate-900 truncate text-[11px]" title={rt.name}>
                                    {rt.name}
                                  </span>
                                  <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border shrink-0 ${
                                    rt.status === 'Passed'
                                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                                      : rt.status === 'Failed'
                                      ? 'bg-rose-100 text-rose-800 border-rose-300'
                                      : 'bg-amber-100 text-amber-800 border-amber-300'
                                  }`}>
                                    {rt.status === 'Passed'
                                      ? `✓ Passed (${rt.latest_score}%)`
                                      : rt.status === 'Failed'
                                      ? `✗ Failed (${rt.latest_score}%)`
                                      : `Needed (≥${rt.passing_threshold}%)`}
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-bold text-slate-900 truncate" title={examName}>
                                {examName}
                              </span>
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${
                                isAssessmentPassed
                                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                                  : task.exam_status === 'Failed'
                                  ? 'bg-rose-100 text-rose-800 border-rose-300'
                                  : 'bg-amber-100 text-amber-800 border-amber-300'
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
                        <div className="grid grid-cols-2 gap-3 mt-3.5 pt-2 border-t border-slate-100">
                          <div>
                            <span className="text-[11px] text-slate-400 font-medium block">Required competency</span>
                            <p className="text-xs font-bold text-slate-900 mt-0.5">
                              {task.requiredCompetency || task.required_competency || 'Eligible'}
                            </p>
                          </div>
                          <div>
                            <span className="text-[11px] text-slate-400 font-medium block">Certification</span>
                            <p className="text-xs font-bold text-slate-900 mt-0.5 truncate" title={task.required_certification}>
                              {task.required_certification || 'None required'}
                            </p>
                          </div>
                        </div>

                        {task.blocking_reason && !task.can_apply && (!task.application_status || task.application_status === 'Not Applied') && (
                          <div className="mt-3.5 p-2 rounded-lg bg-amber-50/70 border border-amber-100 text-[11px] text-amber-800 leading-snug flex items-start gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                            <span>{task.blocking_reason}</span>
                          </div>
                        )}
                      </div>

                      <div className="pt-4 flex items-center justify-between border-t border-slate-100 mt-4">
                        <div>
                          <span className="text-xs font-semibold text-slate-600 block">
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
                              className="px-3 py-1.5 bg-[#3B50BA] hover:bg-[#31429e] text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center gap-1 cursor-pointer"
                            >
                              <span>Take Assessment</span>
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          ) : task.state === 'Ready to Apply' || task.can_apply ? (
                            <button
                              type="button"
                              onClick={() => openTaskModal(task)}
                              className="px-3 py-1.5 bg-[#3B50BA] hover:bg-[#31429e] text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center gap-1 cursor-pointer"
                            >
                              <span>Apply Now</span>
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => openTaskModal(task)}
                              className="text-xs font-semibold text-[#3B50BA] hover:underline cursor-pointer"
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
              <div className="bg-white rounded-2xl border border-dashed border-slate-250 p-8 sm:p-12 text-center shadow-xs flex flex-col items-center justify-center">
                <div className="w-14 h-14 rounded-2xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center mb-4 border border-blue-100/80 shadow-xs">
                  <Briefcase className="w-7 h-7" />
                </div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 mb-1.5">
                  No opportunities match your filter
                </h3>
                <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
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
