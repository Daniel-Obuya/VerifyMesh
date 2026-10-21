import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  LayoutGrid, 
  User, 
  ListChecks, 
  ShieldCheck, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  LogOut, 
  Bell, 
  ChevronDown, 
  Check, 
  ArrowRight, 
  Sparkles, 
  RotateCcw, 
  Briefcase, 
  Award,
  ExternalLink,
  X,
  HelpCircle,
  Trash2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BrandLogo } from '../components/auth/BrandLogo';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Alert } from '../components/ui/Alert';
import { adminService } from '../services/adminService';

export const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Navigation tab
  const [activeTab, setActiveTab] = useState('overview');
  const [toastMessage, setToastMessage] = useState(null);

  // Loading & error states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Data states
  const [overviewData, setOverviewData] = useState(null);
  const [agentsList, setAgentsList] = useState([]);
  const [tasksList, setTasksList] = useState([]);
  const [taskMetadata, setTaskMetadata] = useState({ categories: [], certifications: [], skills: [] });
  const [assessmentsList, setAssessmentsList] = useState([]);
  const [reviewsList, setReviewsList] = useState([]);
  const [verificationsData, setVerificationsData] = useState({ certifications: [], experiences: [] });
  const [isReviewingAction, setIsReviewingAction] = useState(false);
  const [rejectionModal, setRejectionModal] = useState({
    isOpen: false,
    type: null, // 'certification' | 'experience'
    id: null,
    title: '',
    reason: ''
  });

  // Filter & Search states
  const [agentSearch, setAgentSearch] = useState('');
  const [agentStatusFilter, setAgentStatusFilter] = useState('ALL');
  const [agentCompFilter, setAgentCompFilter] = useState('ALL');

  const [taskSearch, setTaskSearch] = useState('');
  const [taskCategoryFilter, setTaskCategoryFilter] = useState('ALL');
  const [taskStatusFilter, setTaskStatusFilter] = useState('ACTIVE');

  const [assessmentSearch, setAssessmentSearch] = useState('');
  const [assessmentCompFilter, setAssessmentCompFilter] = useState('ALL');

  const [reviewStatusFilter, setReviewStatusFilter] = useState('ALL');
  const [reviewEligibilityFilter, setReviewEligibilityFilter] = useState('ALL');

  // Modal states
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isAgentModalOpen, setIsAgentModalOpen] = useState(false);

  const [selectedAssessment, setSelectedAssessment] = useState(null);
  const [isAssessmentModalOpen, setIsAssessmentModalOpen] = useState(false);

  const [selectedReview, setSelectedReview] = useState(null);
  const [reviewDetail, setReviewDetail] = useState(null);
  const [isLoadingReviewDetail, setIsLoadingReviewDetail] = useState(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  // Delete Task Modal State
  const [taskToDelete, setTaskToDelete] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeletingTask, setIsDeletingTask] = useState(false);

  // Fetch all initial data
  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [overviewRes, agentsRes, tasksRes, metaRes, assessmentsRes, reviewsRes, verifsRes] = await Promise.all([
        adminService.getOverview().catch(() => null),
        adminService.getAgents().catch(() => null),
        adminService.getTasks().catch(() => null),
        adminService.getTaskMetadata().catch(() => null),
        adminService.getAssessments().catch(() => null),
        adminService.getReviews().catch(() => null),
        adminService.getPendingVerifications().catch(() => null)
      ]);

      if (overviewRes?.data) setOverviewData(overviewRes.data);
      if (agentsRes?.data) setAgentsList(agentsRes.data);
      if (tasksRes?.data) setTasksList(tasksRes.data);
      if (metaRes?.data) setTaskMetadata(metaRes.data);
      if (assessmentsRes?.data) setAssessmentsList(assessmentsRes.data);
      if (reviewsRes?.data) setReviewsList(reviewsRes.data);
      if (verifsRes?.data) setVerificationsData(verifsRes.data);
    } catch (err) {
      setError('Failed to load dashboard data. Please check connection and server status.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Verification Review Action Handlers
  const handleApproveCertification = async (certId) => {
    setIsReviewingAction(true);
    try {
      const res = await adminService.reviewCertification(certId, 'VERIFIED');
      showToast(res?.message || 'Certification verified successfully.');
      await fetchData();
    } catch (err) {
      showToast(err?.response?.data?.error || 'Failed to approve certification.');
    } finally {
      setIsReviewingAction(false);
    }
  };

  const handleApproveExperience = async (expId) => {
    setIsReviewingAction(true);
    try {
      const res = await adminService.reviewExperience(expId, 'VERIFIED');
      showToast(res?.message || 'Work experience verified successfully.');
      await fetchData();
    } catch (err) {
      showToast(err?.response?.data?.error || 'Failed to approve work experience.');
    } finally {
      setIsReviewingAction(false);
    }
  };

  const handleOpenRejectModal = (type, id, title) => {
    setRejectionModal({
      isOpen: true,
      type,
      id,
      title,
      reason: ''
    });
  };

  const handleSubmitRejection = async () => {
    if (!rejectionModal.reason.trim()) {
      showToast('Please provide a reason for rejection.');
      return;
    }
    setIsReviewingAction(true);
    try {
      if (rejectionModal.type === 'certification') {
        const res = await adminService.reviewCertification(rejectionModal.id, 'REJECTED', rejectionModal.reason);
        showToast(res?.message || 'Certification marked as rejected.');
      } else {
        const res = await adminService.reviewExperience(rejectionModal.id, 'REJECTED', rejectionModal.reason);
        showToast(res?.message || 'Work experience marked as rejected.');
      }
      setRejectionModal({ isOpen: false, type: null, id: null, title: '', reason: '' });
      await fetchData();
    } catch (err) {
      showToast(err?.response?.data?.error || 'Failed to submit rejection.');
    } finally {
      setIsReviewingAction(false);
    }
  };

  const pendingVerificationsCount = (verificationsData.certifications?.length || 0) + (verificationsData.experiences?.length || 0);

  // Helper for Competency Badge Styling
  const getCompetencyBadgeStyle = (competency) => {
    switch (competency) {
      case 'ELIGIBLE':
      case 'Eligible':
      case 'COMPETENT':
      case 'ADVANCED':
      case 'Competent':
      case 'Advanced':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'NOT_ELIGIBLE':
      case 'Not Eligible':
      case 'NEEDS_IMPROVEMENT':
      case 'Needs Improvement':
      case 'Ineligible':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'BASIC':
      case 'Basic':
      case 'Send to Review':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  // Helper for Task Status Badge
  const getTaskStatusBadgeStyle = (status) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'DRAFT':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'INACTIVE':
        return 'bg-slate-100 text-slate-600 border-slate-200';
      case 'COMPLETED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  // Helper for Eligibility Review Status Badge
  const getReviewStatusBadgeStyle = (status) => {
    switch (status) {
      case 'APPROVED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'PENDING':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'REJECTED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  // =====================================================================
  // TASK MANAGEMENT HANDLERS
  // =====================================================================
  const openCreateTaskModal = () => {
    navigate('/admin/tasks/create');
  };

  const openEditTaskModal = (task) => {
    navigate(`/admin/tasks/${task.task_id}/edit`);
  };

  const handleToggleTaskStatus = async (task) => {
    const newStatus = task.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await adminService.setTaskStatus(task.task_id, newStatus);
      showToast(
        newStatus === 'INACTIVE'
          ? `Task "${task.task_name}" deactivated and removed from active view.`
          : `Task "${task.task_name}" activated.`
      );
      const tasksRes = await adminService.getTasks();
      if (tasksRes?.data) setTasksList(tasksRes.data);
    } catch (err) {
      showToast(`Error changing task status: ${err.message}`);
    }
  };

  const openDeleteTaskModal = (task) => {
    setTaskToDelete(task);
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDeleteTask = async () => {
    if (!taskToDelete) return;
    setIsDeletingTask(true);
    try {
      await adminService.deleteTask(taskToDelete.task_id);
      showToast(`Task "${taskToDelete.task_name}" permanently deleted.`);
      setIsDeleteModalOpen(false);
      setTaskToDelete(null);
      const tasksRes = await adminService.getTasks();
      if (tasksRes?.data) setTasksList(tasksRes.data);
    } catch (err) {
      showToast(err?.response?.data?.error || err.message || 'Failed to delete task.');
    } finally {
      setIsDeletingTask(false);
    }
  };

  // Review Detail Modal Handler
  const openReviewDetailModal = async (review) => {
    setSelectedReview(review);
    setIsReviewModalOpen(true);
    setIsLoadingReviewDetail(true);
    try {
      const res = await adminService.getReviewDetail(review.evaluation_id);
      if (res?.data) setReviewDetail(res.data);
    } catch {
      setReviewDetail(review);
    } finally {
      setIsLoadingReviewDetail(false);
    }
  };

  // =====================================================================
  // FILTERED DATA
  // =====================================================================
  const filteredAgents = useMemo(() => {
    return agentsList.filter(agent => {
      const matchesSearch = 
        !agentSearch ||
        agent.full_name?.toLowerCase().includes(agentSearch.toLowerCase()) ||
        agent.email?.toLowerCase().includes(agentSearch.toLowerCase()) ||
        agent.phone?.includes(agentSearch);

      const matchesStatus = 
        agentStatusFilter === 'ALL' || agent.status === agentStatusFilter;

      const matchesComp = 
        agentCompFilter === 'ALL' || 
        (agentCompFilter === 'UNASSESSED' ? !agent.predicted_competency :
         agentCompFilter === 'ELIGIBLE' ? ['ELIGIBLE', 'COMPETENT', 'ADVANCED', 'Eligible', 'Competent', 'Advanced'].includes(agent.predicted_competency) :
         agentCompFilter === 'NOT_ELIGIBLE' ? ['NOT_ELIGIBLE', 'NEEDS_IMPROVEMENT', 'BASIC', 'Not Eligible', 'Needs Improvement', 'Ineligible'].includes(agent.predicted_competency) :
         agent.predicted_competency === agentCompFilter);

      return matchesSearch && matchesStatus && matchesComp;
    });
  }, [agentsList, agentSearch, agentStatusFilter, agentCompFilter]);

  const filteredTasks = useMemo(() => {
    return tasksList.filter(task => {
      const matchesSearch = 
        !taskSearch ||
        task.task_name?.toLowerCase().includes(taskSearch.toLowerCase()) ||
        task.description?.toLowerCase().includes(taskSearch.toLowerCase());

      const matchesCat = 
        taskCategoryFilter === 'ALL' || String(task.category_id) === String(taskCategoryFilter);

      const matchesStatus = 
        taskStatusFilter === 'ALL' || task.status === taskStatusFilter;

      return matchesSearch && matchesCat && matchesStatus;
    });
  }, [tasksList, taskSearch, taskCategoryFilter, taskStatusFilter]);

  const filteredAssessments = useMemo(() => {
    return assessmentsList.filter(item => {
      const matchesSearch = 
        !assessmentSearch ||
        item.agent_name?.toLowerCase().includes(assessmentSearch.toLowerCase()) ||
        item.agent_email?.toLowerCase().includes(assessmentSearch.toLowerCase());

      const matchesComp = 
        assessmentCompFilter === 'ALL' ||
        (assessmentCompFilter === 'ELIGIBLE' ? ['ELIGIBLE', 'COMPETENT', 'ADVANCED', 'Eligible', 'Competent', 'Advanced'].includes(item.predicted_competency) :
         assessmentCompFilter === 'NOT_ELIGIBLE' ? ['NOT_ELIGIBLE', 'NEEDS_IMPROVEMENT', 'BASIC', 'Not Eligible', 'Needs Improvement', 'Ineligible'].includes(item.predicted_competency) :
         item.predicted_competency === assessmentCompFilter);

      return matchesSearch && matchesComp;
    });
  }, [assessmentsList, assessmentSearch, assessmentCompFilter]);

  const filteredReviews = useMemo(() => {
    return reviewsList.filter(rev => {
      const matchesRevStatus = 
        reviewStatusFilter === 'ALL' || rev.review_status === reviewStatusFilter;

      const matchesEligStatus = 
        reviewEligibilityFilter === 'ALL' || rev.eligibility_status === reviewEligibilityFilter;

      return matchesRevStatus && matchesEligStatus;
    });
  }, [reviewsList, reviewStatusFilter, reviewEligibilityFilter]);

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

      {/* Top Navbar */}
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
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-slate-900 tracking-tight">VerifyMesh</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
              Admin Portal
            </span>
          </div>
        </div>

        {/* User Info & Actions */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-semibold text-slate-900 leading-tight">
              {user?.fullName || 'System Administrator'}
            </p>
            <p className="text-xs text-slate-400 leading-tight">
              {user?.email || 'admin@verifymesh.io'}
            </p>
          </div>

          <div className="w-9 h-9 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-xs flex items-center justify-center">
            {user?.fullName ? user.fullName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'AD'}
          </div>

          <Button variant="secondary" size="sm" onClick={handleLogout} className="text-xs">
            <LogOut className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
            Sign Out
          </Button>
        </div>
      </header>

      {/* Main Container with Sidebar + Content */}
      <div className="flex-1 flex flex-col md:flex-row max-w-[1440px] w-full mx-auto">
        {/* Left Sidebar */}
        <aside className="w-full md:w-56 lg:w-60 bg-white border-r border-slate-200/80 flex flex-col justify-between p-4 shrink-0">
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeTab === 'overview'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <LayoutGrid className="w-4 h-4 text-[#3B50BA]" />
              <span>Overview</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('agents')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeTab === 'agents'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <User className="w-4 h-4 text-slate-500" />
              <span>Agents</span>
              {agentsList.length > 0 && (
                <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {agentsList.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('tasks')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeTab === 'tasks'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <ListChecks className="w-4 h-4 text-slate-500" />
              <span>Tasks</span>
              {tasksList.length > 0 && (
                <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {tasksList.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('assessments')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeTab === 'assessments'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 text-slate-500" />
              <span>Assessments</span>
              {assessmentsList.length > 0 && (
                <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {assessmentsList.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('reviews')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeTab === 'reviews'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <ShieldCheck className="w-4 h-4 text-slate-500" />
              <span>Eligibility Reviews</span>
              {overviewData?.pending_reviews > 0 && (
                <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                  {overviewData.pending_reviews}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('verifications')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                activeTab === 'verifications'
                  ? 'bg-[#EEF2FF] text-[#3B50BA]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Award className="w-4 h-4 text-slate-500" />
              <span>Verifications</span>
              {pendingVerificationsCount > 0 && (
                <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                  {pendingVerificationsCount}
                </span>
              )}
            </button>
          </div>

          {/* Quick Model Info Widget */}
          <div className="my-6 p-4 rounded-2xl bg-gradient-to-br from-blue-50/80 to-indigo-50/40 border border-blue-100 hidden md:block">
            <div className="flex items-center gap-2 text-xs font-bold text-[#3B50BA]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Model Runtime</span>
            </div>
            <p className="text-[11px] text-slate-600 mt-1.5 font-medium leading-relaxed">
              Random Forest Inference:
            </p>
            <p className="text-[11px] text-emerald-700 font-semibold mt-0.5 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
              Active in Flask Memory
            </p>
            <p className="text-[10px] text-slate-400 mt-1">
              3-way decision &bull; 11 features
            </p>
          </div>

          {/* Bottom Sidebar Items */}
          <div className="space-y-1 pt-4 border-t border-slate-150">
            <button
              type="button"
              onClick={() => fetchData()}
              className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              <span>Refresh Data</span>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50/60 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5 text-slate-500 hover:text-rose-600" />
              <span>Sign Out</span>
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 sm:p-8 lg:p-10 space-y-6 overflow-y-auto max-w-7xl">
          {error && (
            <Alert type="error" message={error} onClose={() => setError(null)} />
          )}

          {isLoading ? (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-xs">
              <div className="w-8 h-8 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm font-semibold text-slate-700">Loading VerifyMesh Admin Portal...</p>
              <p className="text-xs text-slate-400 mt-1">Querying active database records and inference runtime status</p>
            </div>
          ) : (
            <>
              {/* ========================================================= */}
              {/* TAB 1: OVERVIEW */}
              {/* ========================================================= */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Header Title */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                        ADMINISTRATION CONSOLE
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1 tracking-tight">
                        System Overview &amp; Health
                      </h1>
                      <p className="text-sm text-slate-500 mt-1">
                        Live monitoring of agent registrations, active tasks, assessment throughput, and AI model health.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="secondary" size="sm" onClick={fetchData}>
                        <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                        Refresh
                      </Button>
                      <Button size="sm" onClick={openCreateTaskModal}>
                        + Create Task
                      </Button>
                    </div>
                  </div>

                  {/* 4 KPI Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
                    {/* Card 1: Agents */}
                    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Agents</span>
                        <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#3B50BA] flex items-center justify-center">
                          <User className="w-4 h-4" />
                        </div>
                      </div>
                      <p className="text-3xl font-bold text-slate-900 mt-2">{overviewData?.total_agents ?? 0}</p>
                      <p className="text-xs text-emerald-600 font-medium mt-1">
                        {overviewData?.active_agents ?? 0} active in pool
                      </p>
                    </div>

                    {/* Card 2: Tasks */}
                    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tasks</span>
                        <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                          <ListChecks className="w-4 h-4" />
                        </div>
                      </div>
                      <p className="text-3xl font-bold text-slate-900 mt-2">{overviewData?.total_tasks ?? 0}</p>
                      <p className="text-xs text-blue-600 font-medium mt-1">
                        {overviewData?.active_tasks ?? 0} active for allocation
                      </p>
                    </div>

                    {/* Card 3: Assessments */}
                    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Assessments</span>
                        <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                          <CheckCircle2 className="w-4 h-4" />
                        </div>
                      </div>
                      <p className="text-3xl font-bold text-slate-900 mt-2">{overviewData?.total_assessments ?? 0}</p>
                      <p className="text-xs text-emerald-600 font-medium mt-1">
                        {overviewData?.total_assessments > 0
                          ? `${Math.round((overviewData.passed_assessments / overviewData.total_assessments) * 100)}% passing rate`
                          : 'No attempts yet'}
                      </p>
                    </div>

                    {/* Card 4: Pending Reviews */}
                    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending Reviews</span>
                        <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                          <ShieldCheck className="w-4 h-4" />
                        </div>
                      </div>
                      <p className="text-3xl font-bold text-slate-900 mt-2">{overviewData?.pending_reviews ?? 0}</p>
                      <p className="text-xs text-amber-600 font-medium mt-1">
                        {overviewData?.pending_reviews > 0 ? 'Awaiting administrator action' : 'All reviews up to date'}
                      </p>
                    </div>
                  </div>

                  {/* Architecture & Model Runtime Card */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs">
                    <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                      <div>
                        <h2 className="text-lg font-bold text-slate-900">Decoupled ML Runtime Status</h2>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Tuned externally in Google Colab &bull; Served in real-time via VerifyMesh Flask Inference Engine
                        </p>
                      </div>
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        Model Preloaded &amp; Healthy
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-5">
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Model Algorithm</span>
                        <p className="text-sm font-bold text-slate-900 mt-1">
                          {overviewData?.active_model?.algorithm || 'RandomForestClassifier'}
                        </p>
                        <p className="text-[11px] text-slate-500 mt-0.5">Scikit-learn Ensemble</p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Feature Set</span>
                        <p className="text-sm font-bold text-slate-900 mt-1">
                          {overviewData?.active_model?.feature_set_version || '11-features-leverage'}
                        </p>
                        <p className="text-[11px] text-slate-500 mt-0.5">Certified leverage feature enabled</p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Active Artifact</span>
                        <p className="text-sm font-bold text-slate-900 mt-1 truncate" title={overviewData?.runtime_model?.model_file}>
                          {overviewData?.runtime_model?.model_file || 'threeway_decision_model.joblib'}
                        </p>
                        <p className="text-[11px] text-slate-500 mt-0.5">Preloaded on backend boot</p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Decision Classes</span>
                        <p className="text-sm font-bold text-slate-900 mt-1">3-Way Decision</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">Ineligible (0) | Review (1) | Eligible (2)</p>
                      </div>
                    </div>
                  </div>

                  {/* Recent Assessments Card */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs">
                    <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                      <div>
                        <h2 className="text-lg font-bold text-slate-900">Recent Assessment Submissions</h2>
                        <p className="text-xs text-slate-500 mt-0.5">Latest evaluations processed through the inference pipeline</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab('assessments')}
                        className="text-xs font-semibold text-[#3B50BA] hover:underline flex items-center gap-1"
                      >
                        View all assessments &rarr;
                      </button>
                    </div>

                    {overviewData?.recent_assessments?.length > 0 ? (
                      <div className="overflow-x-auto mt-4">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="border-b border-slate-100 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              <th className="pb-3 font-semibold">Agent</th>
                              <th className="pb-3 font-semibold">Score</th>
                              <th className="pb-3 font-semibold">Attempt</th>
                              <th className="pb-3 font-semibold">Predicted Competency</th>
                              <th className="pb-3 font-semibold">Confidence</th>
                              <th className="pb-3 font-semibold">Completed At</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700">
                            {overviewData.recent_assessments.map((a) => (
                              <tr key={a.exam_result_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-3 font-semibold text-slate-900">
                                  {a.agent_name}
                                  <span className="block text-[11px] text-slate-400 font-normal">{a.agent_email}</span>
                                </td>
                                <td className="py-3">
                                  <span className="font-semibold text-slate-900">{a.assessment_score}%</span>
                                  {a.passed ? (
                                    <span className="ml-1.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">Passed</span>
                                  ) : (
                                    <span className="ml-1.5 text-[10px] font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded">Failed</span>
                                  )}
                                </td>
                                <td className="py-3 text-slate-600">Attempt #{a.attempt_number}</td>
                                <td className="py-3">
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(a.predicted_competency)}`}>
                                    {a.predicted_competency || 'In Review'}
                                  </span>
                                </td>
                                <td className="py-3 text-slate-700 font-mono">
                                  {a.confidence ? `${Math.round(a.confidence > 1 ? a.confidence : a.confidence * 100)}%` : '—'}
                                </td>
                                <td className="py-3 text-slate-500 text-xs">
                                  {a.completed_at ? new Date(a.completed_at).toLocaleString() : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="py-8 text-center">
                        <CheckCircle2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-700">No assessments recorded yet</p>
                        <p className="text-xs text-slate-400 mt-1">Assessment results will populate here as agents complete their evaluations.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB 2: AGENTS DIRECTORY */}
              {/* ========================================================= */}
              {activeTab === 'agents' && (
                <div className="space-y-6">
                  {/* Header Title & Actions */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                        TALENT POOL
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1 tracking-tight">
                        Agent Directory
                      </h1>
                      <p className="text-sm text-slate-500 mt-1">
                        Inspect registered agents, education backgrounds, total assessment attempts, and AI competency classifications.
                      </p>
                    </div>
                    <div className="text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200/80 self-start sm:self-auto">
                      Showing <strong>{filteredAgents.length}</strong> of <strong>{agentsList.length}</strong> agents
                    </div>
                  </div>

                  {/* Search and Filters */}
                  <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="Search by agent name, email, or phone..."
                        value={agentSearch}
                        onChange={(e) => setAgentSearch(e.target.value)}
                        className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                      />
                      <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>

                    <div className="flex items-center gap-2">
                      <select
                        value={agentCompFilter}
                        onChange={(e) => setAgentCompFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                      >
                        <option value="ALL">All Competencies</option>
                        <option value="ELIGIBLE">Eligible</option>
                        <option value="NOT_ELIGIBLE">Not Eligible</option>
                        <option value="UNASSESSED">Unassessed</option>
                      </select>

                      <select
                        value={agentStatusFilter}
                        onChange={(e) => setAgentStatusFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                      >
                        <option value="ALL">All Statuses</option>
                        <option value="ACTIVE">Active</option>
                        <option value="INACTIVE">Inactive</option>
                        <option value="SUSPENDED">Suspended</option>
                      </select>
                    </div>
                  </div>

                  {/* Agents Table */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
                    {filteredAgents.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Agent Name</th>
                              <th className="py-3.5 px-4 font-semibold">Contact / Education</th>
                              <th className="py-3.5 px-4 font-semibold">Experience</th>
                              <th className="py-3.5 px-4 font-semibold">Availability</th>
                              <th className="py-3.5 px-4 font-semibold">Latest Assessment</th>
                              <th className="py-3.5 px-4 font-semibold">AI Predicted Competency</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700">
                            {filteredAgents.map((ag) => (
                              <tr key={ag.agent_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-3.5 px-4 font-semibold text-slate-900">
                                  <div className="flex items-center gap-2.5">
                                    <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-600 font-bold text-xs flex items-center justify-center shrink-0">
                                      {ag.full_name ? ag.full_name[0].toUpperCase() : 'A'}
                                    </div>
                                    <div>
                                      <p className="font-semibold text-slate-900 leading-tight">{ag.full_name}</p>
                                      <p className="text-xs text-slate-400 font-normal">{ag.email}</p>
                                    </div>
                                  </div>
                                </td>
                                <td className="py-3.5 px-4">
                                  <p className="text-xs text-slate-700">{ag.phone || 'No phone recorded'}</p>
                                  <p className="text-[11px] text-slate-400 truncate max-w-[200px]" title={ag.education}>
                                    {ag.education || 'Self-declared experience'}
                                  </p>
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className="font-semibold text-slate-900">{ag.experience_months || 0}</span>
                                  <span className="text-xs text-slate-500 ml-1">months</span>
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                    ag.availability_status === 'AVAILABLE' 
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                                      : 'bg-slate-100 text-slate-600 border border-slate-200'
                                  }`}>
                                    {ag.availability_status || 'AVAILABLE'}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4">
                                  {ag.assessment_score != null ? (
                                    <div>
                                      <span className="font-semibold text-slate-900">{ag.assessment_score}%</span>
                                      <span className="text-[11px] text-slate-400 block">
                                        Attempt #{ag.attempt_number} ({ag.total_attempts} total)
                                      </span>
                                    </div>
                                  ) : (
                                    <span className="text-xs text-slate-400 italic">Unassessed</span>
                                  )}
                                </td>
                                <td className="py-3.5 px-4">
                                  {ag.predicted_competency ? (
                                    <div className="space-y-0.5">
                                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(ag.predicted_competency)}`}>
                                        {ag.predicted_competency}
                                      </span>
                                      {ag.confidence_percent && (
                                        <p className="text-[10px] text-slate-400 font-mono">
                                          Confidence: {ag.confidence_percent}%
                                        </p>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200">
                                      Pending Assessment
                                    </span>
                                  )}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <Button 
                                    variant="secondary" 
                                    size="sm" 
                                    className="text-xs"
                                    onClick={() => {
                                      setSelectedAgent(ag);
                                      setIsAgentModalOpen(true);
                                    }}
                                  >
                                    View Profile
                                  </Button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="p-12 text-center">
                        <User className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-700">No agents found</p>
                        <p className="text-xs text-slate-400 mt-1">
                          {agentSearch || agentStatusFilter !== 'ALL' || agentCompFilter !== 'ALL'
                            ? 'No agents match your active search and filter criteria.'
                            : 'No agents are currently registered in the database.'}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB 3: TASKS */}
              {/* ========================================================= */}
              {activeTab === 'tasks' && (
                <div className="space-y-6">
                  {/* Header Title & Actions */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                        TASK CONFIGURATION &amp; REQUIREMENTS
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1 tracking-tight">
                        Task Allocation Catalog
                      </h1>
                      <p className="text-sm text-slate-500 mt-1">
                        Configure allocation roles, assign minimum competency tiers, and define automated qualification rules.
                      </p>
                    </div>
                    <Button onClick={openCreateTaskModal} className="self-start sm:self-auto">
                      + Create Task
                    </Button>
                  </div>

                  {/* Search and Filters */}
                  <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="Search tasks by name or description..."
                        value={taskSearch}
                        onChange={(e) => setTaskSearch(e.target.value)}
                        className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                      />
                      <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>

                    <div className="flex items-center gap-2">
                      <select
                        value={taskCategoryFilter}
                        onChange={(e) => setTaskCategoryFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                      >
                        <option value="ALL">All Categories</option>
                        {taskMetadata.categories.map((c) => (
                          <option key={c.category_id} value={c.category_id}>
                            {c.category_name}
                          </option>
                        ))}
                      </select>

                      <select
                        value={taskStatusFilter}
                        onChange={(e) => setTaskStatusFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                      >
                        <option value="ACTIVE">Active Tasks (Default)</option>
                        <option value="INACTIVE">Inactive Tasks</option>
                        <option value="ALL">All Statuses</option>
                        <option value="DRAFT">Draft</option>
                        <option value="COMPLETED">Completed</option>
                      </select>
                    </div>
                  </div>

                  {/* Tasks List */}
                  {filteredTasks.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      {filteredTasks.map((t) => (
                        <div key={t.task_id} className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
                          <div>
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <span className="inline-block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                                  {t.category_name || 'General Category'}
                                </span>
                                <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                                  {t.task_name}
                                </h3>
                              </div>
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getTaskStatusBadgeStyle(t.status)}`}>
                                {t.status}
                              </span>
                            </div>

                            <p className="text-xs sm:text-sm text-slate-600 mt-2 line-clamp-2 leading-relaxed">
                              {t.description || 'No detailed description provided for this task.'}
                            </p>

                            {/* Compensation and arrangement tags */}
                            <div className="flex flex-wrap items-center gap-1.5 mt-3">
                              <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 text-[11px] font-semibold border border-emerald-100 flex items-center gap-1">
                                {t.payment_type === 'Hourly' ? (
                                  t.hourly_rate_min != null
                                    ? `${t.currency || 'KES'} ${Number(t.hourly_rate_min).toLocaleString()}${t.hourly_rate_max ? ` - ${Number(t.hourly_rate_max).toLocaleString()}` : ''} / hr`
                                    : 'Hourly'
                                ) : (
                                  t.fixed_budget != null
                                    ? `${t.currency || 'KES'} ${Number(t.fixed_budget).toLocaleString()} (Fixed)`
                                    : 'Fixed Budget'
                                )}
                              </span>

                              <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px] font-medium">
                                {t.work_arrangement || 'Remote'}
                              </span>

                              {t.positions_count > 1 && (
                                <span className="px-2 py-0.5 rounded-md bg-blue-50 text-[#3B50BA] text-[11px] font-medium border border-blue-100">
                                  {t.positions_count} Openings
                                </span>
                              )}

                              <span className="px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 text-[11px] font-medium border border-purple-100">
                                {t.application_count || 0} applicants
                              </span>
                            </div>

                            {/* Requirements breakdown */}
                            <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
                              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                                Eligibility Requirements
                              </p>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                                  <span className="text-[10px] text-slate-400 block font-medium">Min. Competency</span>
                                  <span className={`inline-block mt-0.5 px-2 py-0.2 rounded text-[11px] font-semibold border ${getCompetencyBadgeStyle(t.minimum_competency)}`}>
                                    {t.minimum_competency || 'BASIC'}
                                  </span>
                                </div>

                                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                                  <span className="text-[10px] text-slate-400 block font-medium">Min. Experience</span>
                                  <span className="font-semibold text-slate-900 mt-0.5 block">
                                    {t.minimum_experience_months ? `${t.minimum_experience_months} months` : 'None required'}
                                  </span>
                                </div>

                                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                                  <span className="text-[10px] text-slate-400 block font-medium">Certification</span>
                                  <span className="font-semibold text-slate-900 mt-0.5 block truncate" title={t.certification_name}>
                                    {t.certification_name || 'Not required'}
                                  </span>
                                </div>

                                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                                  <span className="text-[10px] text-slate-400 block font-medium">Exam Verification</span>
                                  <span className="font-semibold text-slate-900 mt-0.5 block">
                                    {t.exam_required ? 'Required' : 'Optional'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Footer Actions */}
                          <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
                            <span className="text-xs text-slate-400">
                              {t.evaluation_count || 0} evaluations linked
                            </span>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => handleToggleTaskStatus(t)}
                                className="text-xs"
                              >
                                {t.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                              </Button>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => openEditTaskModal(t)}
                                className="text-xs"
                              >
                                Edit Task
                              </Button>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => openDeleteTaskModal(t)}
                                className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200"
                              >
                                <Trash2 className="w-3.5 h-3.5 mr-1" />
                                Delete
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-xs">
                      <ListChecks className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                      <p className="text-base font-bold text-slate-800">No tasks configured</p>
                      <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-md mx-auto">
                        There are currently no tasks configured in the database. Create your first task to define competency requirements and unlock allocation rules.
                      </p>
                      <Button onClick={openCreateTaskModal} className="mt-4">
                        + Create First Task
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB 4: ASSESSMENTS AUDIT */}
              {/* ========================================================= */}
              {activeTab === 'assessments' && (
                <div className="space-y-6">
                  {/* Header Title */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                        AUDIT TRAIL &amp; INFERENCE LOGS
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1 tracking-tight">
                        Assessment History
                      </h1>
                      <p className="text-sm text-slate-500 mt-1">
                        Historical log of competency assessments, exam battery scores, and Random Forest 3-way classification outputs.
                      </p>
                    </div>
                    <div className="text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200/80 self-start sm:self-auto">
                      Total Assessments: <strong>{assessmentsList.length}</strong>
                    </div>
                  </div>

                  {/* Search and Filters */}
                  <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="Search assessments by agent name or email..."
                        value={assessmentSearch}
                        onChange={(e) => setAssessmentSearch(e.target.value)}
                        className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                      />
                      <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>

                    <select
                      value={assessmentCompFilter}
                      onChange={(e) => setAssessmentCompFilter(e.target.value)}
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                    >
                      <option value="ALL">All Predicted Classes</option>
                      <option value="ELIGIBLE">Eligible</option>
                      <option value="NOT_ELIGIBLE">Not Eligible</option>
                    </select>
                  </div>

                  {/* Assessments Table */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
                    {filteredAssessments.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">ID</th>
                              <th className="py-3.5 px-4 font-semibold">Agent</th>
                              <th className="py-3.5 px-4 font-semibold">Attempt</th>
                              <th className="py-3.5 px-4 font-semibold">Score</th>
                              <th className="py-3.5 px-4 font-semibold">AI Predicted Competency</th>
                              <th className="py-3.5 px-4 font-semibold">Confidence</th>
                              <th className="py-3.5 px-4 font-semibold">Completed Date</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Details</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700">
                            {filteredAssessments.map((item) => (
                              <tr key={item.exam_result_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                                  #{item.exam_result_id}
                                </td>
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold text-slate-900 leading-tight">{item.agent_name}</p>
                                  <p className="text-xs text-slate-400 font-normal">{item.agent_email}</p>
                                </td>
                                <td className="py-3.5 px-4 font-medium text-slate-700">
                                  Attempt #{item.attempt_number}
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className="font-semibold text-slate-900">{item.assessment_score}%</span>
                                  {item.passed ? (
                                    <span className="ml-1.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">Passed</span>
                                  ) : (
                                    <span className="ml-1.5 text-[10px] font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded">Failed</span>
                                  )}
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(item.predicted_competency)}`}>
                                    {item.predicted_competency || 'In Review'}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4 font-mono text-slate-700">
                                  {item.confidence_percent ? `${item.confidence_percent}%` : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-500">
                                  {item.completed_at ? new Date(item.completed_at).toLocaleString() : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    className="text-xs"
                                    onClick={() => {
                                      setSelectedAssessment(item);
                                      setIsAssessmentModalOpen(true);
                                    }}
                                  >
                                    Inspect Features
                                  </Button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="p-12 text-center">
                        <CheckCircle2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-700">No assessment records found</p>
                        <p className="text-xs text-slate-400 mt-1">No evaluations match the search or filter criteria.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB 5: ELIGIBILITY REVIEWS */}
              {/* ========================================================= */}
              {activeTab === 'reviews' && (
                <div className="space-y-6">
                  {/* Header Title */}
                  <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block">
                        HUMAN-IN-THE-LOOP ALLOCATION
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1 tracking-tight">
                        Eligibility Reviews
                      </h1>
                      <p className="text-sm text-slate-500 mt-1">
                        Oversee binary gatekeeper predictions (Eligible / Not Eligible) and multi-criteria rule compliance for task eligibility.
                      </p>
                    </div>
                    <div className="text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200/80 self-start sm:self-auto">
                      Showing <strong>{filteredReviews.length}</strong> review records
                    </div>
                  </div>

                  {/* Conceptual Distinction Banner */}
                  <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 text-xs sm:text-sm text-amber-900 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-amber-900">
                        Operational Rule: AI Competency Prediction &ne; Final Task Eligibility
                      </p>
                      <p className="text-xs text-amber-800/90 mt-1 leading-relaxed">
                        The <strong>AI Predicted Competency</strong> reflects general test and experience performance. 
                        <strong> Task Eligibility</strong> evaluates compliance with mandatory criteria for a specific role (such as minimum required months or required certifications). 
                        An agent can be Competent in general, yet require Review for roles requiring higher experience.
                      </p>
                    </div>
                  </div>

                  {/* Filters */}
                  <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-xs flex flex-wrap gap-3 items-center justify-between">
                    <div className="flex items-center gap-3">
                      <label className="text-xs font-semibold text-slate-500">Review Status:</label>
                      <select
                        value={reviewStatusFilter}
                        onChange={(e) => setReviewStatusFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                      >
                        <option value="ALL">All Review Statuses</option>
                        <option value="PENDING">Pending Action</option>
                        <option value="APPROVED">Approved</option>
                        <option value="REJECTED">Rejected</option>
                        <option value="NOT_REQUIRED">Not Required</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-3">
                      <label className="text-xs font-semibold text-slate-500">Eligibility Status:</label>
                      <select
                        value={reviewEligibilityFilter}
                        onChange={(e) => setReviewEligibilityFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-[#3B50BA]"
                      >
                        <option value="ALL">All Eligibility Outcomes</option>
                        <option value="ELIGIBLE">Eligible</option>
                        <option value="PENDING_REVIEW">Pending Review</option>
                        <option value="NOT_ELIGIBLE">Not Eligible</option>
                      </select>
                    </div>
                  </div>

                  {/* Reviews Table / Honest Empty State */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
                    {filteredReviews.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Evaluation ID</th>
                              <th className="py-3.5 px-4 font-semibold">Agent</th>
                              <th className="py-3.5 px-4 font-semibold">Task</th>
                              <th className="py-3.5 px-4 font-semibold">AI Prediction</th>
                              <th className="py-3.5 px-4 font-semibold">Eligibility Status</th>
                              <th className="py-3.5 px-4 font-semibold">Review Status</th>
                              <th className="py-3.5 px-4 font-semibold">Evaluated At</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700">
                            {filteredReviews.map((rev) => (
                              <tr key={rev.evaluation_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                                  #{rev.evaluation_id}
                                </td>
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold text-slate-900 leading-tight">{rev.agent_name}</p>
                                  <p className="text-xs text-slate-400 font-normal">{rev.agent_email}</p>
                                </td>
                                <td className="py-3.5 px-4 font-semibold text-slate-800">
                                  {rev.task_name}
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(rev.predicted_competency)}`}>
                                    {rev.predicted_competency || '—'}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${
                                    rev.eligibility_status === 'ELIGIBLE' 
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : rev.eligibility_status === 'PENDING_REVIEW'
                                      ? 'bg-amber-50 text-amber-700 border-amber-200'
                                      : 'bg-rose-50 text-rose-700 border-rose-200'
                                  }`}>
                                    {rev.eligibility_status}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getReviewStatusBadgeStyle(rev.review_status)}`}>
                                    {rev.review_status}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-500">
                                  {rev.evaluated_at ? new Date(rev.evaluated_at).toLocaleString() : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    className="text-xs"
                                    onClick={() => openReviewDetailModal(rev)}
                                  >
                                    Inspect Review
                                  </Button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="p-12 text-center">
                        <ShieldCheck className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-base font-bold text-slate-800">No eligibility reviews recorded</p>
                        <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-md mx-auto">
                          There are currently no eligibility review records in the database. 
                          Reviews are generated when agents submit assessments against tasks where rules require human verification.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB: VERIFICATIONS */}
              {/* ========================================================= */}
              {activeTab === 'verifications' && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-xl font-bold text-slate-900 tracking-tight">Profile Verifications</h2>
                      <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                        Audit and approve agent submitted certifications and work history entries. Verified entries directly populate the 11-feature vector for the Random Forest model.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                        {pendingVerificationsCount} Total Pending
                      </span>
                      <Button variant="secondary" size="sm" onClick={() => fetchData()}>
                        <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                        Refresh Queue
                      </Button>
                    </div>
                  </div>

                  {/* Section 1: Pending Certifications */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Award className="w-4 h-4 text-[#3B50BA]" />
                        <h3 className="text-sm font-bold text-slate-900">
                          Pending Professional Certifications
                        </h3>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          {verificationsData.certifications?.length || 0}
                        </span>
                      </div>
                    </div>

                    {verificationsData.certifications && verificationsData.certifications.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Agent</th>
                              <th className="py-3.5 px-4 font-semibold">Certification Name</th>
                              <th className="py-3.5 px-4 font-semibold">Issuing Org</th>
                              <th className="py-3.5 px-4 font-semibold">Credential ID / URL</th>
                              <th className="py-3.5 px-4 font-semibold">Issue / Expiry Date</th>
                              <th className="py-3.5 px-4 font-semibold">Submitted</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700">
                            {verificationsData.certifications.map((c) => (
                              <tr key={c.agent_cert_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold text-slate-900 leading-tight">{c.agent_name}</p>
                                  <p className="text-xs text-slate-400 font-normal">{c.agent_email}</p>
                                </td>
                                <td className="py-3.5 px-4 font-semibold text-slate-800">
                                  {c.certification_name}
                                </td>
                                <td className="py-3.5 px-4 text-slate-600">
                                  {c.issuing_organization || '—'}
                                </td>
                                <td className="py-3.5 px-4">
                                  {c.certificate_number && (
                                    <p className="font-mono text-xs text-slate-700">{c.certificate_number}</p>
                                  )}
                                  {c.credential_url ? (
                                    <a
                                      href={c.credential_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 text-xs text-[#3B50BA] hover:underline mt-0.5"
                                    >
                                      <span>Verify Link</span>
                                      <ExternalLink className="w-3 h-3" />
                                    </a>
                                  ) : (
                                    <span className="text-xs text-slate-400">No link provided</span>
                                  )}
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-600">
                                  <span>{c.issue_date}</span>
                                  {c.expiry_date ? <span> &rarr; {c.expiry_date}</span> : <span className="text-slate-400"> (No Expiry)</span>}
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-500">
                                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <Button
                                      size="sm"
                                      className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                                      disabled={isReviewingAction}
                                      onClick={() => handleApproveCertification(c.agent_cert_id)}
                                    >
                                      Approve
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-xs text-rose-600 hover:bg-rose-50"
                                      disabled={isReviewingAction}
                                      onClick={() => handleOpenRejectModal('certification', c.agent_cert_id, c.certification_name)}
                                    >
                                      Reject
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="p-8 text-center text-slate-500">
                        <Award className="w-6 h-6 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-700">No pending certifications</p>
                        <p className="text-xs text-slate-400 mt-0.5">All agent submitted credentials have been audited.</p>
                      </div>
                    )}
                  </div>

                  {/* Section 2: Pending Work Experience */}
                  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-[#3B50BA]" />
                        <h3 className="text-sm font-bold text-slate-900">
                          Pending Work Experience Tenures
                        </h3>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          {verificationsData.experiences?.length || 0}
                        </span>
                      </div>
                    </div>

                    {verificationsData.experiences && verificationsData.experiences.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Agent</th>
                              <th className="py-3.5 px-4 font-semibold">Role &amp; Company</th>
                              <th className="py-3.5 px-4 font-semibold">Category</th>
                              <th className="py-3.5 px-4 font-semibold">Tenure Period</th>
                              <th className="py-3.5 px-4 font-semibold">Description</th>
                              <th className="py-3.5 px-4 font-semibold">Submitted</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700">
                            {verificationsData.experiences.map((exp) => (
                              <tr key={exp.experience_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold text-slate-900 leading-tight">{exp.agent_name}</p>
                                  <p className="text-xs text-slate-400 font-normal">{exp.agent_email}</p>
                                </td>
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold text-slate-900 leading-tight">{exp.job_title}</p>
                                  <p className="text-xs text-slate-500 font-normal">{exp.company}</p>
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                                    {exp.work_category}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-600">
                                  <span>{exp.start_date} &rarr; {exp.is_current ? 'Present' : (exp.end_date || 'Ongoing')}</span>
                                </td>
                                <td className="py-3.5 px-4 max-w-xs">
                                  <p className="text-xs text-slate-600 line-clamp-2">
                                    {exp.description || '—'}
                                  </p>
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-500">
                                  {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <Button
                                      size="sm"
                                      className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                                      disabled={isReviewingAction}
                                      onClick={() => handleApproveExperience(exp.experience_id)}
                                    >
                                      Approve
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-xs text-rose-600 hover:bg-rose-50"
                                      disabled={isReviewingAction}
                                      onClick={() => handleOpenRejectModal('experience', exp.experience_id, `${exp.job_title} at ${exp.company}`)}
                                    >
                                      Reject
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="p-8 text-center text-slate-500">
                        <Briefcase className="w-6 h-6 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-700">No pending work experience entries</p>
                        <p className="text-xs text-slate-400 mt-0.5">All agent submitted work history has been reviewed.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>


      {/* ================================================================= */}
      {/* MODAL: INSPECT AGENT PROFILE */}
      {/* ================================================================= */}
      <Modal
        isOpen={isAgentModalOpen}
        onClose={() => setIsAgentModalOpen(false)}
        title="Agent Details &amp; History"
      >
        {selectedAgent && (
          <div className="space-y-4 text-xs sm:text-sm text-slate-700">
            <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
              <div className="w-10 h-10 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-sm flex items-center justify-center shrink-0">
                {selectedAgent.full_name ? selectedAgent.full_name[0].toUpperCase() : 'A'}
              </div>
              <div>
                <h4 className="text-base font-bold text-slate-900">{selectedAgent.full_name}</h4>
                <p className="text-xs text-slate-400">{selectedAgent.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Status</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{selectedAgent.status}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Availability</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{selectedAgent.availability_status}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Phone Number</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{selectedAgent.phone || 'None recorded'}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Total Attempts</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{selectedAgent.total_attempts || 0} attempts</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] text-slate-400 block uppercase font-bold">Education &amp; Background</span>
              <p className="text-xs text-slate-800 font-medium mt-0.5">
                {selectedAgent.education || 'Self-declared background'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-indigo-50/60 border border-indigo-100">
              <span className="text-[10px] text-indigo-700 block uppercase font-bold">Latest ML Competency Assessment</span>
              <div className="flex items-center justify-between mt-1">
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(selectedAgent.predicted_competency)}`}>
                  {selectedAgent.predicted_competency || 'Not Assessed'}
                </span>
                <span className="text-xs font-mono text-slate-600">
                  Score: {selectedAgent.assessment_score != null ? `${selectedAgent.assessment_score}%` : 'N/A'}
                </span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setIsAgentModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ================================================================= */}
      {/* MODAL: INSPECT ASSESSMENT FEATURES */}
      {/* ================================================================= */}
      <Modal
        isOpen={isAssessmentModalOpen}
        onClose={() => setIsAssessmentModalOpen(false)}
        title="Assessment Features &amp; Inference Audit"
      >
        {selectedAssessment && (
          <div className="space-y-4 text-xs sm:text-sm text-slate-700">
            <div className="pb-3 border-b border-slate-100">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">{selectedAssessment.agent_name}</h4>
                  <p className="text-xs text-slate-400">Attempt #{selectedAssessment.attempt_number} &bull; {selectedAssessment.completed_at ? new Date(selectedAssessment.completed_at).toLocaleString() : ''}</p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(selectedAssessment.predicted_competency)}`}>
                  {selectedAssessment.predicted_competency}
                </span>
              </div>
            </div>

            <div>
              <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                10-Feature Battery Scores (Inference Inputs)
              </h5>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Assessment Score</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.assessment_score ?? selectedAssessment.assessment_score}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Communication Score</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.communication_score ?? '—'}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Product Knowledge</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.product_knowledge_score ?? '—'}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Sales Skill Score</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.sales_skill_score ?? '—'}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Customer Service Score</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.customer_service_score ?? '—'}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Previous Experience</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.previous_experience_months ?? '—'} months</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Sales Experience</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.sales_experience_months ?? '—'} months</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block">Certification Count</span>
                  <span className="font-bold text-slate-900">{selectedAssessment.features?.certification_count ?? '—'}</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600">Model Prediction Confidence</span>
              <span className="text-xs font-mono font-bold text-slate-900">
                {selectedAssessment.confidence_percent ? `${selectedAssessment.confidence_percent}%` : '—'}
              </span>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setIsAssessmentModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ================================================================= */}
      {/* MODAL: INSPECT ELIGIBILITY REVIEW */}
      {/* ================================================================= */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        title="Eligibility Evaluation Details"
      >
        {selectedReview && (
          <div className="space-y-4 text-xs sm:text-sm text-slate-700">
            {isLoadingReviewDetail ? (
              <div className="py-6 text-center">
                <div className="w-6 h-6 border-2 border-[#3B50BA] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-500">Loading evaluation checks...</p>
              </div>
            ) : (
              <>
                <div className="pb-3 border-b border-slate-100">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">{selectedReview.agent_name}</h4>
                      <p className="text-xs text-slate-500 font-medium mt-0.5">Role evaluated: {selectedReview.task_name}</p>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getReviewStatusBadgeStyle(selectedReview.review_status)}`}>
                      {selectedReview.review_status}
                    </span>
                  </div>
                </div>

                {/* Explanation text */}
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] text-slate-400 block uppercase font-bold">System Evaluation Summary</span>
                  <p className="text-xs text-slate-800 mt-1 leading-relaxed">
                    {selectedReview.explanation || 'Automated rule-based verification check completed.'}
                  </p>
                </div>

                {/* Checks breakdown if available */}
                {reviewDetail?.checks?.length > 0 && (
                  <div>
                    <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                      Individual Requirement Checks
                    </h5>
                    <div className="space-y-2">
                      {reviewDetail.checks.map((chk) => (
                        <div key={chk.check_id} className="p-2.5 rounded-lg border border-slate-100 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-semibold text-slate-800">{chk.requirement_type}</span>
                            <span className="text-slate-400 block text-[11px]">
                              Expected: {chk.expected_value} &bull; Actual: {chk.actual_value || 'None'}
                            </span>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${chk.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                            {chk.passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900">
                  <p className="font-semibold">Review Action Policy</p>
                  <p className="text-[11px] mt-0.5 text-amber-800 leading-relaxed">
                    Administrator decision overrides (Approve/Reject) are restricted to authorized compliance workflows once task allocation agreements are countersigned.
                  </p>
                </div>

                <div className="pt-2 flex justify-end">
                  <Button variant="secondary" size="sm" onClick={() => setIsReviewModalOpen(false)}>
                    Close
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* ================================================================= */}
      {/* MODAL: REJECT VERIFICATION SUBMISSION */}
      {/* ================================================================= */}
      <Modal
        isOpen={rejectionModal.isOpen}
        onClose={() => setRejectionModal({ isOpen: false, type: null, id: null, title: '', reason: '' })}
        title="Reject Verification Request"
      >
        <div className="space-y-4 text-xs sm:text-sm text-slate-700">
          <p className="text-xs text-slate-600">
            You are rejecting verification for: <strong className="text-slate-900">{rejectionModal.title}</strong>.
          </p>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Rejection Reason <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              value={rejectionModal.reason}
              onChange={(e) => setRejectionModal({ ...rejectionModal, reason: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:outline-none focus:border-[#3B50BA]"
              placeholder="Explain why this credential or experience claim was rejected (e.g. invalid credential ID, unverified employer, expired certificate)..."
              required
            />
          </div>
          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRejectionModal({ isOpen: false, type: null, id: null, title: '', reason: '' })}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-rose-600 hover:bg-rose-700 text-white"
              disabled={isReviewingAction}
              onClick={handleSubmitRejection}
            >
              {isReviewingAction ? 'Submitting...' : 'Confirm Rejection'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ========================================================= */}
      {/* MODAL: DELETE TASK CONFIRMATION */}
      {/* ========================================================= */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          if (!isDeletingTask) {
            setIsDeleteModalOpen(false);
            setTaskToDelete(null);
          }
        }}
        title="Delete Task"
      >
        <div className="space-y-4 text-xs sm:text-sm text-slate-700">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center shrink-0 border border-rose-100">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-slate-900 text-sm">
                Are you sure you want to delete &ldquo;{taskToDelete?.task_name}&rdquo;?
              </p>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                This action is permanent and cannot be undone. The task, its requirements, topic links, and evaluation associations will be permanently removed from both the admin portal and agent dashboards.
              </p>
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setIsDeleteModalOpen(false);
                setTaskToDelete(null);
              }}
              disabled={isDeletingTask}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleConfirmDeleteTask}
              isLoading={isDeletingTask}
              className="bg-rose-600 hover:bg-rose-700 text-white font-medium"
            >
              Delete Permanently
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
