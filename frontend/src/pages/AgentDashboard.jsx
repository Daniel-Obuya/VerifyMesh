import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { competencyService } from '../services/competencyService';
import { TakeAssessmentModal } from '../components/dashboard/TakeAssessmentModal';
import { CompetencyDetailsModal } from '../components/dashboard/CompetencyDetailsModal';
import { TaskModal } from '../components/dashboard/TaskModal';
import { AllTasksModal } from '../components/dashboard/AllTasksModal';
import { ProfileModal } from '../components/dashboard/ProfileModal';
import { HelpModal } from '../components/dashboard/HelpModal';

export const AgentDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Active navigation tab & user menu
  const [activeNav, setActiveNav] = useState('dashboard');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Modals state
  const [isAssessmentModalOpen, setIsAssessmentModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isAllTasksModalOpen, setIsAllTasksModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Dynamic Assessment State
  const [isCheckingStatus, setIsCheckingStatus] = useState(true);
  const [hasCompletedAssessment, setHasCompletedAssessment] = useState(false);
  const [currentCompetency, setCurrentCompetency] = useState(null);
  const [currentConfidence, setCurrentConfidence] = useState(null);
  
  const [formData, setFormData] = useState({
    previous_experience_months: 24,
    sales_experience_months: 18,
    customer_service_experience_months: 12,
    certification_count: 2,
    relevant_certification: 1,
    assessment_score: 78.5,
    communication_score: 82.0,
    product_knowledge_score: 79.0,
    sales_skill_score: 80.0,
    customer_service_score: 85.0,
  });

  const [predictionData, setPredictionData] = useState(null);
  const [recentActivities, setRecentActivities] = useState([]);

  // Check agent's assessment state from backend on mount or user change
  useEffect(() => {
    let isMounted = true;

    const checkAgentAssessment = async () => {
      setIsCheckingStatus(true);
      try {
        // 1. Check if user profile already has assessment info
        const directCompetency = user?.competency_level || user?.competencyLevel;
        const directAssessment = user?.assessment;

        // 2. Fetch fresh agent status from backend
        let backendStatus = null;
        try {
          const res = await competencyService.getAgentStatus(user?.id);
          if (res?.success) {
            backendStatus = res;
          }
        } catch {
          // Fallback to local storage cache if network glitch
        }

        // 3. Fallback to cached local storage if available for this specific user
        const localKey = `verifymesh_agent_assessment_${user?.id || 'default'}`;
        let localCached = null;
        try {
          const raw = localStorage.getItem(localKey);
          if (raw) localCached = JSON.parse(raw);
        } catch {
          localCached = null;
        }

        if (!isMounted) return;

        // Determine if agent has completed assessment
        const hasAssessed = Boolean(
          (backendStatus && backendStatus.has_assessed && backendStatus.competency_level) ||
          directCompetency ||
          (localCached && (localCached.predicted_competency || localCached.competency_level))
        );

        if (hasAssessed) {
          const resolvedCompetency = 
            backendStatus?.competency_level || 
            directCompetency || 
            localCached?.predicted_competency || 
            localCached?.competency_level || 
            'Competent';

          const resolvedConfidence = 
            backendStatus?.confidence ?? 
            localCached?.confidence ?? 
            user?.confidence ?? 
            78;

          const resolvedPrediction = 
            backendStatus?.prediction_data || 
            localCached?.prediction_data || 
            localCached || 
            {
              predicted_competency: resolvedCompetency,
              confidence: resolvedConfidence,
              level_tier: resolvedCompetency === 'Advanced' || resolvedCompetency === 'Exceeds Standard' ? 4 : 3,
              probabilities: {
                [resolvedCompetency]: resolvedConfidence,
                ...(resolvedCompetency === 'Competent' 
                  ? { Advanced: 14, Basic: 6, 'Needs Improvement': 2 } 
                  : { Competent: 10, Basic: 4, 'Needs Improvement': 1 })
              },
              tier_info: {
                title: resolvedCompetency,
                description: 'AI-assisted prediction based on your current competency data.',
              }
            };

          setHasCompletedAssessment(true);
          setCurrentCompetency(resolvedCompetency);
          setCurrentConfidence(resolvedConfidence);
          setPredictionData(resolvedPrediction);

          if (backendStatus?.assessment) {
            setFormData(backendStatus.assessment);
          } else if (localCached?.assessment) {
            setFormData(localCached.assessment);
          }

          setRecentActivities([
            { id: 1, title: 'Technical assessment completed', time: '2 days ago' },
            { id: 2, title: 'Certification verified', time: '5 days ago' },
            { id: 3, title: 'Competency profile updated', time: '1 week ago' },
          ]);
        } else {
          // Agent is unassessed / first-time user
          setHasCompletedAssessment(false);
          setCurrentCompetency(null);
          setCurrentConfidence(null);
          setPredictionData(null);
          setRecentActivities([
            { 
              id: 'init-1', 
              title: 'Agent profile initialized • Awaiting competency evaluation', 
              time: 'Pending', 
              isPending: true 
            }
          ]);
        }
      } catch (err) {
        if (isMounted) {
          setHasCompletedAssessment(false);
          setCurrentCompetency(null);
          setCurrentConfidence(null);
        }
      } finally {
        if (isMounted) {
          setIsCheckingStatus(false);
        }
      }
    };

    checkAgentAssessment();

    return () => {
      isMounted = false;
    };
  }, [user]);

  // Handle Assessment Completion
  const handleAssessmentComplete = (newPrediction, newForm) => {
    const newTier = newPrediction.predicted_competency || newPrediction.prediction || 'Competent';
    const newConf = newPrediction.confidence || 78;

    // Cache locally for persistence
    if (user?.id) {
      const localKey = `verifymesh_agent_assessment_${user.id}`;
      localStorage.setItem(localKey, JSON.stringify({
        ...newPrediction,
        assessment: newForm,
        competency_level: newTier,
        confidence: newConf,
      }));
    }

    setHasCompletedAssessment(true);
    setCurrentCompetency(newTier);
    setCurrentConfidence(newConf);
    setPredictionData(newPrediction);
    if (newForm) setFormData(newForm);

    // Prepend new activity
    setRecentActivities(prev => [
      {
        id: Date.now(),
        title: 'Technical assessment completed',
        time: 'Just now',
        isNew: true,
      },
      ...prev.filter(item => item.id !== 'init-1' && item.id !== 1),
    ]);

    setToastMessage(`Assessment evaluated! Current competency: ${newTier} (${newConf}% confidence).`);
    setTimeout(() => setToastMessage(null), 6000);
  };

  // Reset to Unassessed (Demo & Testing Feature)
  const handleResetAssessment = async () => {
    try {
      if (user?.id) {
        await competencyService.resetAssessment(user.id);
        localStorage.removeItem(`verifymesh_agent_assessment_${user.id}`);
      }
      setHasCompletedAssessment(false);
      setCurrentCompetency(null);
      setCurrentConfidence(null);
      setPredictionData(null);
      setRecentActivities([
        { 
          id: 'init-1', 
          title: 'Agent profile initialized • Awaiting competency evaluation', 
          time: 'Pending', 
          isPending: true 
        }
      ]);
      setIsUserMenuOpen(false);
      setToastMessage('Agent reset to unassessed state. You are now previewing the first-time agent view.');
      setTimeout(() => setToastMessage(null), 5000);
    } catch {
      // Fallback
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

  // Helper to determine eligibility for assessed agents based on 4-class or binary labels
  const isHighTier = 
    currentCompetency === 'Advanced' || 
    currentCompetency === 'Exceeds Standard';

  const isStandardTier = 
    isHighTier || 
    currentCompetency === 'Competent' || 
    currentCompetency === 'Meets Standard' || 
    currentCompetency === 'Meets/Exceeds Standard';

  // Available tasks mapping
  const tasksList = [
    {
      id: 'task-1',
      title: 'Customer Support Specialist',
      description: 'Support customers and resolve product-related enquiries.',
      requiredCompetency: 'Competent',
      certification: 'Customer Service Certification',
      payout: '$28 - $34 / hr',
      isEligible: isStandardTier,
    },
    {
      id: 'task-2',
      title: 'Technical Support Agent',
      description: 'Troubleshoot technical issues and guide customers to a fix.',
      requiredCompetency: 'Competent',
      certification: 'Not required',
      payout: '$32 - $38 / hr',
      isEligible: isStandardTier,
    },
    {
      id: 'task-3',
      title: 'Product Consultant',
      description: 'Advise customers on product fit and help them choose the right plan.',
      requiredCompetency: 'Advanced',
      certification: 'Sales & Product Certification',
      payout: '$40 - $48 / hr',
      isEligible: isHighTier,
    },
    {
      id: 'task-4',
      title: 'Enterprise Escalation Lead',
      description: 'Manage complex multi-tier stakeholder communications and resolution paths.',
      requiredCompetency: 'Advanced',
      certification: 'Leadership Verification',
      payout: '$45 - $55 / hr',
      isEligible: isHighTier,
    },
  ];

  // Helper for competency badge styling
  const getBadgeStyle = (competency) => {
    switch (competency) {
      case 'Advanced':
      case 'Exceeds Standard':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'Competent':
      case 'Meets Standard':
      case 'Meets/Exceeds Standard':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'Basic':
      case 'Needs Refresher':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Needs Improvement':
      case 'Below Standard':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

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
                DO
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
                    setIsProfileModalOpen(true);
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
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
            {/* Dashboard Nav (Active) */}
            <button
              type="button"
              onClick={() => setActiveNav('dashboard')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeNav === 'dashboard'
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
              onClick={() => setIsProfileModalOpen(true)}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <User className="w-4 h-4 text-slate-500" />
              <span>My Profile</span>
            </button>

            {/* Tasks */}
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById('tasks-section');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <ListChecks className="w-4 h-4 text-slate-500" />
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
          {/* Card: YOUR COMPETENCY */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs relative">
            {isCheckingStatus ? (
              /* Loading Skeleton */
              <div className="animate-pulse space-y-4">
                <div className="h-3 bg-slate-200 rounded-sm w-32" />
                <div className="h-8 bg-slate-200 rounded-md w-48" />
                <div className="h-2 bg-slate-100 rounded-full w-56" />
                <div className="h-4 bg-slate-100 rounded-sm w-72 mt-4" />
              </div>
            ) : hasCompletedAssessment ? (
              /* ============================================================
                 ASSESSED AGENT VIEW (Existing UI maintained with dynamic data)
                 ============================================================ */
              <>
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                      YOUR COMPETENCY
                    </span>
                    <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mt-1.5 tracking-tight">
                      {currentCompetency}
                    </h1>

                    {/* Confidence Bar Row */}
                    <div className="flex items-center gap-3.5 mt-3.5">
                      <div className="w-36 sm:w-44 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className="bg-[#3B50BA] h-full rounded-full transition-all duration-700 ease-out"
                          style={{ width: `${Math.min(currentConfidence || 78, 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-slate-700">
                        {currentConfidence}% confidence
                      </span>
                    </div>
                  </div>

                  {/* Primary CTA Button */}
                  <div className="flex items-center gap-2.5 shrink-0 sm:pt-1">
                    <button
                      type="button"
                      onClick={() => setIsAssessmentModalOpen(true)}
                      className="px-4 sm:px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-sm shadow-xs hover:shadow-sm transition-all flex items-center gap-2 cursor-pointer active:scale-98"
                    >
                      <Sparkles className="w-4 h-4" />
                      Take Assessment
                    </button>
                  </div>
                </div>

                {/* Bottom Row: AI explanation & View details link */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-6 pt-4 border-t border-slate-100">
                  <p className="text-sm text-slate-500">
                    AI-assisted prediction based on your current competency data.
                  </p>
                  <div className="flex items-center gap-4">
                    <button
                      type="button"
                      onClick={() => setIsDetailsModalOpen(true)}
                      className="text-sm font-medium text-[#3B50BA] hover:text-[#31429e] hover:underline inline-flex items-center gap-1 cursor-pointer"
                    >
                      View competency details &rarr;
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* ============================================================
                 UNASSESSED / FIRST-TIME AGENT VIEW (Requirement 2)
                 ============================================================ */
              <>
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                      YOUR COMPETENCY
                    </span>
                    <h1 className="text-2xl sm:text-3xl font-bold text-slate-700 mt-1.5 tracking-tight flex items-center gap-2.5">
                      <span>Pending Competency Profile</span>
                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                        Not Assessed
                      </span>
                    </h1>

                    {/* Pending Confidence Row */}
                    <div className="flex items-center gap-3.5 mt-3.5">
                      <div className="w-36 sm:w-44 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="bg-slate-300 h-full rounded-full w-0" />
                      </div>
                      <span className="text-sm font-medium text-slate-400">
                        Pending &bull; 0% evaluation
                      </span>
                    </div>
                  </div>

                  {/* Primary CTA Button for Unassessed Agent */}
                  <div className="flex items-center gap-2.5 shrink-0 sm:pt-1">
                    <button
                      type="button"
                      onClick={() => setIsAssessmentModalOpen(true)}
                      className="px-4 sm:px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-sm shadow-xs hover:shadow-sm transition-all flex items-center gap-2 cursor-pointer active:scale-98"
                    >
                      <Sparkles className="w-4 h-4" />
                      Complete Profile &amp; Assess Competency
                    </button>
                  </div>
                </div>

                {/* Bottom Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-6 pt-4 border-t border-slate-100">
                  <p className="text-sm text-slate-500">
                    You have not submitted your profile features or taken a competency assessment yet.
                  </p>
                  <div>
                    <button
                      type="button"
                      onClick={() => setIsAssessmentModalOpen(true)}
                      className="text-sm font-semibold text-[#3B50BA] hover:text-[#31429e] hover:underline inline-flex items-center gap-1 cursor-pointer"
                    >
                      Take assessment to unlock details &rarr;
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Section: Tasks for You */}
          <section id="tasks-section" className="space-y-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Tasks for You
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Opportunities that match your current competency and verified requirements.
              </p>
            </div>

            {hasCompletedAssessment ? (
              /* ============================================================
                 ASSESSED AGENT VIEW: Task Cards Grid
                 ============================================================ */
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {/* Task 1: Customer Support Specialist */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                          Customer Support Specialist
                        </h3>
                        {tasksList[0].isEligible ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] shrink-0">
                            ✓ Eligible
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#FFF7ED] text-[#D97706] border border-[#FED7AA] shrink-0">
                            Not currently eligible
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                        Support customers and resolve product-related enquiries.
                      </p>

                      <div className="grid grid-cols-2 gap-4 mt-6 pt-2">
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Required competency</span>
                          <p className="text-sm font-bold text-slate-900 mt-1">Competent</p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Certification</span>
                          <p className="text-sm font-bold text-slate-900 mt-1 leading-snug">
                            Customer Service Certification
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="pt-6">
                      <button
                        type="button"
                        onClick={() => openTaskModal(tasksList[0])}
                        className="text-sm font-semibold text-[#3B50BA] hover:text-[#31429e] hover:underline inline-flex items-center gap-1 cursor-pointer"
                      >
                        {tasksList[0].isEligible ? 'View task →' : 'View requirements →'}
                      </button>
                    </div>
                  </div>

                  {/* Task 2: Technical Support Agent */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                          Technical Support Agent
                        </h3>
                        {tasksList[1].isEligible ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] shrink-0">
                            ✓ Eligible
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#FFF7ED] text-[#D97706] border border-[#FED7AA] shrink-0">
                            Not currently eligible
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                        Troubleshoot technical issues and guide customers to a fix.
                      </p>

                      <div className="grid grid-cols-2 gap-4 mt-6 pt-2">
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Required competency</span>
                          <p className="text-sm font-bold text-slate-900 mt-1">Competent</p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Certification</span>
                          <p className="text-sm font-bold text-slate-900 mt-1">Not required</p>
                        </div>
                      </div>
                    </div>

                    <div className="pt-6">
                      <button
                        type="button"
                        onClick={() => openTaskModal(tasksList[1])}
                        className="text-sm font-semibold text-[#3B50BA] hover:text-[#31429e] hover:underline inline-flex items-center gap-1 cursor-pointer"
                      >
                        {tasksList[1].isEligible ? 'View task →' : 'View requirements →'}
                      </button>
                    </div>
                  </div>

                  {/* Task 3: Product Consultant */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                          Product Consultant
                        </h3>
                        {tasksList[2].isEligible ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] shrink-0">
                            ✓ Eligible
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#FFF7ED] text-[#D97706] border border-[#FED7AA] shrink-0">
                            Not currently eligible
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                        Advise customers on product fit and help them choose the right plan.
                      </p>

                      <div className="grid grid-cols-2 gap-4 mt-6 pt-2">
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Required competency</span>
                          <p className="text-sm font-bold text-slate-900 mt-1">Advanced</p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400 font-medium block">Your competency</span>
                          <p className="text-sm font-bold text-slate-900 mt-1">{currentCompetency}</p>
                        </div>
                      </div>
                    </div>

                    <div className="pt-6">
                      <button
                        type="button"
                        onClick={() => openTaskModal(tasksList[2])}
                        className="text-sm font-semibold text-[#3B50BA] hover:text-[#31429e] hover:underline inline-flex items-center gap-1 cursor-pointer"
                      >
                        {tasksList[2].isEligible ? 'View task →' : 'View requirements →'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* View all tasks link */}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={() => setIsAllTasksModalOpen(true)}
                    className="text-sm font-semibold text-[#3B50BA] hover:text-[#31429e] hover:underline inline-flex items-center gap-1 cursor-pointer"
                  >
                    View all tasks &rarr;
                  </button>
                </div>
              </>
            ) : (
              /* ============================================================
                 UNASSESSED / FIRST-TIME AGENT VIEW: Empty State Prompt (Requirement 2)
                 ============================================================ */
              <div className="bg-white rounded-2xl border border-dashed border-slate-250 p-8 sm:p-12 text-center shadow-xs flex flex-col items-center justify-center">
                <div className="w-14 h-14 rounded-2xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center mb-4 border border-blue-100/80 shadow-xs">
                  <Briefcase className="w-7 h-7" />
                </div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 mb-1.5">
                  No eligible tasks to display yet
                </h3>
                <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed mb-6">
                  No eligible tasks to display yet. Complete your profile assessment to calculate your AI competency score and view matching tasks.
                </p>
                <button
                  type="button"
                  onClick={() => setIsAssessmentModalOpen(true)}
                  className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-sm shadow-xs hover:shadow-sm transition-all inline-flex items-center gap-2 cursor-pointer active:scale-98"
                >
                  <Sparkles className="w-4 h-4" />
                  Complete Assessment
                </button>
              </div>
            )}
          </section>

          {/* Section: Recent Activity */}
          <section className="space-y-3 pt-2">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Recent Activity
            </h2>
            <div className="bg-white rounded-2xl border border-slate-200/80 divide-y divide-slate-100 overflow-hidden shadow-xs">
              {recentActivities.map((activity) => (
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
              ))}
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
        userCompetency={currentCompetency || 'Unassessed'}
        onOpenAssessment={() => setIsAssessmentModalOpen(true)}
      />

      <AllTasksModal
        isOpen={isAllTasksModalOpen}
        onClose={() => setIsAllTasksModalOpen(false)}
        tasks={tasksList}
        onSelectTask={openTaskModal}
      />

      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        user={user}
        competency={currentCompetency || 'Pending Assessment'}
        confidence={currentConfidence || 0}
      />

      <HelpModal
        isOpen={isHelpModalOpen}
        onClose={() => setIsHelpModalOpen(false)}
      />
    </div>
  );
};
