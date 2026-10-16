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
import { TakeAssessmentModal } from '../components/dashboard/TakeAssessmentModal';
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
  const [isAssessmentModalOpen, setIsAssessmentModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

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

  // Live Tasks and Activities
  const [tasks, setTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);
  const [recentActivities, setRecentActivities] = useState([]);
  const [isLoadingActivities, setIsLoadingActivities] = useState(true);
  const [dashboardError, setDashboardError] = useState(null);

  // Load live dashboard state from authoritative backend
  const fetchDashboardData = async () => {
    setIsCheckingStatus(true);
    setIsLoadingTasks(true);
    setIsLoadingActivities(true);
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
            : (directCompetency && directCompetency !== 'Not Yet Assessed' ? directCompetency : 'Competent');

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

    // 3. Fetch Recent Activities from genuine audit logs
    try {
      const actRes = await competencyService.getAgentActivities();
      if (actRes?.success && Array.isArray(actRes.activities)) {
        setRecentActivities(actRes.activities);
      } else {
        setRecentActivities([]);
      }
    } catch (err) {
      console.error('Error loading activities:', err);
      setRecentActivities([]);
    } finally {
      setIsLoadingActivities(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [user]);

  // Handle Assessment Completion
  const handleAssessmentComplete = async (newPrediction, newForm) => {
    const newTier = newPrediction.predicted_competency || newPrediction.prediction || 'Competent';
    const newDecision = newPrediction.evaluation_decision || 'Eligible';
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
      const [taskRes, actRes] = await Promise.all([
        competencyService.getAgentTasks(),
        competencyService.getAgentActivities()
      ]);
      if (taskRes?.success && Array.isArray(taskRes.tasks)) setTasks(taskRes.tasks);
      if (actRes?.success && Array.isArray(actRes.activities)) setRecentActivities(actRes.activities);
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
  const underReviewCount = tasks.filter(t => ['Application Submitted', 'Under Review'].includes(t.application_status) || t.state === 'Under Review').length;
  const acceptedCount = tasks.filter(t => ['Assigned', 'Accepted'].includes(t.application_status) || t.state === 'Assigned').length;
  const hasPendingCert = tasks.some(t => t.state === 'Verification Pending');

  // Work Readiness state
  const getReadinessState = () => {
    if (!hasCompletedAssessment) {
      return {
        badge: 'Action Required',
        badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
        title: 'Assessment Needed',
        subtitle: 'Complete evaluation to unlock tasks',
        actionLabel: 'Take Assessment',
        onAction: () => setIsAssessmentModalOpen(true),
        icon: AlertCircle
      };
    }
    if (evaluationDecision === 'Send to Review') {
      return {
        badge: 'Under Review',
        badgeColor: 'bg-blue-50 text-[#3B50BA] border-blue-200',
        title: 'Awaiting Sign-off',
        subtitle: 'Assessment pending admin review',
        actionLabel: 'View Details',
        onAction: () => setIsDetailsModalOpen(true),
        icon: Clock
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
      badge: 'Verified',
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      title: currentCompetency || 'Verified Agent',
      subtitle: 'Profile ready for opportunities',
      actionLabel: 'View Profile',
      onAction: () => navigate('/profile'),
      icon: ShieldCheck
    };
  };

  const readiness = getReadinessState();

  // Contextual Next Action
  const getNextAction = () => {
    if (!hasCompletedAssessment) {
      return {
        type: 'action',
        title: 'Competency Assessment Required',
        description: 'Complete your initial skill evaluation to verify your profile and unlock matching task opportunities.',
        ctaText: 'Take Assessment',
        onCta: () => setIsAssessmentModalOpen(true),
        badge: 'Required Action',
        icon: Sparkles
      };
    }
    if (evaluationDecision === 'Send to Review') {
      return {
        type: 'info',
        title: 'Assessment Under Administrative Review',
        description: 'Your evaluation results are pending administrative review. You will be cleared once an admin signs off.',
        ctaText: 'View Evaluation',
        onCta: () => setIsDetailsModalOpen(true),
        badge: 'In Review',
        icon: Clock
      };
    }
    if (underReviewCount > 0) {
      return {
        type: 'info',
        title: 'Applications Pending Review',
        description: `You have ${underReviewCount} task application${underReviewCount > 1 ? 's' : ''} currently submitted and under review by task managers.`,
        ctaText: 'View Applications',
        onCta: () => {
          const el = document.getElementById('tasks-section');
          if (el) el.scrollIntoView({ behavior: 'smooth' });
        },
        badge: 'In Pipeline',
        icon: Clock
      };
    }
    if (availableCount > 0) {
      return {
        type: 'opportunity',
        title: 'Active Opportunities Ready for You',
        description: `You have ${availableCount} verified task opportunit${availableCount > 1 ? 'ies' : 'y'} matching your credentials ready for immediate application.`,
        ctaText: 'Explore Opportunities',
        onCta: () => {
          const el = document.getElementById('tasks-section');
          if (el) el.scrollIntoView({ behavior: 'smooth' });
        },
        badge: 'Ready to Apply',
        icon: Briefcase
      };
    }
    return {
      type: 'neutral',
      title: 'Profile Up to Date',
      description: 'Your verified agent profile is in good standing. New matching tasks will automatically appear in your catalog.',
      ctaText: 'Browse Catalog',
      onCta: () => {
        const el = document.getElementById('tasks-section');
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      },
      badge: 'Active & Verified',
      icon: CheckCircle2
    };
  };

  const nextAction = getNextAction();

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
                    setIsAssessmentModalOpen(true);
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

          {/* Quick Skill Evaluation Sidebar Widget */}
          <div className="my-6 p-4 rounded-2xl bg-gradient-to-br from-blue-50/80 to-indigo-50/40 border border-blue-100 hidden md:block">
            <div className="flex items-center gap-2 text-xs font-bold text-[#3B50BA]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{hasCompletedAssessment ? 'Assess Competency' : 'Get Assessed'}</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
              {hasCompletedAssessment 
                ? 'Update your battery scores to unlock higher-tier roles.'
                : 'Take your initial assessment to calculate your AI competency and unlock matching tasks.'}
            </p>
            <button
              type="button"
              onClick={() => setIsAssessmentModalOpen(true)}
              className="w-full mt-3 py-2 px-3 bg-[#3B50BA] hover:bg-[#31429e] text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
            >
              {hasCompletedAssessment ? 'Retake Assessment' : 'Take Assessment'} &rarr;
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
                        {availableCount}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        eligible now
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Ready to apply</span>
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

            {/* Contextual Next Action Banner */}
            <div className={`rounded-2xl border p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all ${
              nextAction.type === 'action'
                ? 'bg-gradient-to-r from-amber-50/90 to-orange-50/50 border-amber-200/80 text-amber-950'
                : nextAction.type === 'opportunity'
                ? 'bg-gradient-to-r from-blue-50/90 to-indigo-50/50 border-blue-200/80 text-slate-900'
                : nextAction.type === 'info'
                ? 'bg-gradient-to-r from-sky-50/90 to-blue-50/50 border-sky-200/80 text-sky-950'
                : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="flex items-start gap-3.5">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5 shadow-2xs ${
                  nextAction.type === 'action'
                    ? 'bg-amber-100 text-amber-700'
                    : nextAction.type === 'opportunity'
                    ? 'bg-[#EEF2FF] text-[#3B50BA]'
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {React.createElement(nextAction.icon, { className: 'w-4 h-4' })}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold tracking-tight">
                      {nextAction.title}
                    </h4>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/80 border border-current/20">
                      {nextAction.badge}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
                    {nextAction.description}
                  </p>
                </div>
              </div>

              <div className="shrink-0 sm:self-center">
                <button
                  type="button"
                  onClick={nextAction.onCta}
                  className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-98 ${
                    nextAction.type === 'action'
                      ? 'bg-amber-600 hover:bg-amber-700 text-white'
                      : nextAction.type === 'opportunity'
                      ? 'bg-[#3B50BA] hover:bg-[#31429e] text-white'
                      : 'bg-slate-900 hover:bg-slate-800 text-white'
                  }`}
                >
                  <span>{nextAction.ctaText}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
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

            {/* Informative banner for unassessed agent */}
            {!hasCompletedAssessment && !isCheckingStatus && (
              <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs sm:text-sm text-amber-900">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    Competency assessment required. Complete your evaluation to verify your profile and unlock task application readiness.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAssessmentModalOpen(true)}
                  className="font-bold text-[#3B50BA] hover:underline whitespace-nowrap shrink-0 self-start sm:self-auto cursor-pointer"
                >
                  Take Assessment &rarr;
                </button>
              </div>
            )}

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
            ) : tasks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {tasks.map((task) => (
                  <div 
                    key={task.task_id || task.id} 
                    className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                          {task.title}
                        </h3>
                        {getTaskStateBadge(task)}
                      </div>
                      <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                        {task.description}
                      </p>

                      <div className="grid grid-cols-2 gap-4 mt-6 pt-2">
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Required competency</span>
                          <p className="text-sm font-bold text-slate-900 mt-1">
                            {task.requiredCompetency || task.required_competency || 'Competent'}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Certification</span>
                          <p className="text-sm font-bold text-slate-900 mt-1 leading-snug">
                            {task.required_certifications && task.required_certifications.length > 0 
                              ? task.required_certifications.join(', ') 
                              : 'Not required'}
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

                    <div className="pt-5 flex items-center justify-between border-t border-slate-100 mt-4">
                      <span className="text-xs font-semibold text-slate-600">
                        {task.payout || '$30 - $40 / hr'}
                      </span>
                      <button
                        type="button"
                        onClick={() => openTaskModal(task)}
                        className={`text-sm font-semibold inline-flex items-center gap-1 cursor-pointer transition-colors ${
                          task.state === 'Ready to Apply' || task.can_apply
                            ? 'text-[#3B50BA] hover:text-[#31429e] hover:underline'
                            : task.state === 'Assigned'
                            ? 'text-emerald-700 hover:text-emerald-800'
                            : 'text-slate-600 hover:text-slate-900 hover:underline'
                        }`}
                      >
                        {getTaskActionText(task)}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-dashed border-slate-250 p-8 sm:p-12 text-center shadow-xs flex flex-col items-center justify-center">
                <div className="w-14 h-14 rounded-2xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center mb-4 border border-blue-100/80 shadow-xs">
                  <Briefcase className="w-7 h-7" />
                </div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 mb-1.5">
                  No opportunities currently available
                </h3>
                <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
                  Check back soon for new task postings matching your domain profile.
                </p>
              </div>
            )}
          </section>

          {/* Section: Recent Activity (Backed by actual audit logs) */}
          <section className="space-y-3 pt-2">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Recent Activity
            </h2>
            <div className="bg-white rounded-2xl border border-slate-200/80 divide-y divide-slate-100 overflow-hidden shadow-xs">
              {isLoadingActivities ? (
                <div className="p-4 animate-pulse space-y-2">
                  <div className="h-4 bg-slate-100 rounded-sm w-3/4" />
                  <div className="h-4 bg-slate-100 rounded-sm w-1/2" />
                </div>
              ) : recentActivities.length > 0 ? (
                recentActivities.map((activity) => (
                  <div 
                    key={activity.id}
                    className="p-4 sm:px-6 flex items-center justify-between hover:bg-slate-50/50 transition-colors"
                  >
                    <div className="flex items-center gap-3.5">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                        activity.isPending 
                          ? 'bg-slate-100 text-slate-400' 
                          : 'bg-[#ECFDF5] text-[#059669]'
                      }`}>
                        {activity.isPending ? (
                          <Clock className="w-3.5 h-3.5" />
                        ) : (
                          <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                        )}
                      </div>
                      <span className="text-sm font-medium text-slate-800">
                        {activity.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {activity.isNew && (
                        <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-[#3B50BA] px-2 py-0.5 rounded-full border border-blue-200">
                          New
                        </span>
                      )}
                      <span className="text-xs sm:text-sm text-slate-400">
                        {activity.time}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-sm text-slate-400">
                  No recent activity logged yet.
                </div>
              )}
            </div>
          </section>
        </main>
      </div>

      {/* Modals */}
      <TakeAssessmentModal
        isOpen={isAssessmentModalOpen}
        onClose={() => setIsAssessmentModalOpen(false)}
        onAssessmentComplete={handleAssessmentComplete}
        currentData={formData}
        userId={user?.id}
      />

      <CompetencyDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
        prediction={predictionData}
        formData={formData}
        onOpenAssessment={() => setIsAssessmentModalOpen(true)}
      />

      <TaskModal
        isOpen={isTaskModalOpen}
        onClose={() => setIsTaskModalOpen(false)}
        task={selectedTask}
        userCompetency={currentCompetency || 'Not Yet Assessed'}
        onOpenAssessment={() => setIsAssessmentModalOpen(true)}
        onApplySuccess={handleApplySuccess}
      />


      <HelpModal
        isOpen={isHelpModalOpen}
        onClose={() => setIsHelpModalOpen(false)}
      />
    </div>
  );
};
