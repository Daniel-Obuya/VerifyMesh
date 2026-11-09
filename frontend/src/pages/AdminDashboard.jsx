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
  AlertTriangle,
  LogOut, 
  Bell, 
  ChevronDown, 
  ChevronLeft,
  ChevronRight,
  Check, 
  ArrowRight, 
  Sparkles, 
  RotateCcw, 
  Briefcase, 
  Award,
  ExternalLink,
  X,
  HelpCircle,
  Trash2,
  UserCheck,
  Mail,
  Phone,
  Users,
  XCircle,
  BrainCircuit
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

  // Sidebar collapsible state matching AgentDashboard and ProfilePage
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

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
  const [assessmentResultFilter, setAssessmentResultFilter] = useState('ALL');
  const [assessmentCompFilter, setAssessmentCompFilter] = useState('ALL');

  const [reviewStatusFilter, setReviewStatusFilter] = useState('ALL');
  const [reviewEligibilityFilter, setReviewEligibilityFilter] = useState('ALL');

  // Modal states
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [selectedAgentProfile, setSelectedAgentProfile] = useState(null);
  const [isLoadingAgentProfile, setIsLoadingAgentProfile] = useState(false);
  const [agentModalTab, setAgentModalTab] = useState('overview'); // 'overview' | 'experience' | 'certifications' | 'assessments'
  const [isAgentModalOpen, setIsAgentModalOpen] = useState(false);

  const openAgentModal = async (agent) => {
    setSelectedAgent(agent);
    setSelectedAgentProfile(null);
    setAgentModalTab('overview');
    setIsAgentModalOpen(true);
    setIsLoadingAgentProfile(true);
    try {
      const res = await adminService.getAgentProfile(agent.agent_id);
      if (res?.data) {
        setSelectedAgentProfile(res.data);
      }
    } catch (err) {
      console.warn('Could not load detailed agent profile:', err);
    } finally {
      setIsLoadingAgentProfile(false);
    }
  };

  const [selectedAssessment, setSelectedAssessment] = useState(null);
  const [isAssessmentModalOpen, setIsAssessmentModalOpen] = useState(false);

  const [selectedReview, setSelectedReview] = useState(null);
  const [reviewDetail, setReviewDetail] = useState(null);
  const [isLoadingReviewDetail, setIsLoadingReviewDetail] = useState(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewActionComment, setReviewActionComment] = useState('');
  const [isSubmittingReviewDecision, setIsSubmittingReviewDecision] = useState(false);

  // Delete Task Modal State
  const [taskToDelete, setTaskToDelete] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeletingTask, setIsDeletingTask] = useState(false);

  // Task Applicants Modal State
  const [isApplicantsModalOpen, setIsApplicantsModalOpen] = useState(false);
  const [selectedTaskForApplicants, setSelectedTaskForApplicants] = useState(null);
  const [taskApplicants, setTaskApplicants] = useState([]);
  const [isLoadingApplicants, setIsLoadingApplicants] = useState(false);
  const [isActionProcessing, setIsActionProcessing] = useState(false);

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

  // Authoritative clean officer identity
  const rawOfficerName = user?.fullName || user?.username || 'Workforce Officer';
  const officerFullName = rawOfficerName.replace(/\s*\(Verified\)/gi, '').trim();
  const officerFirstName = officerFullName.split(' ')[0] || 'Officer';
  const officerInitials = officerFullName
    ? officerFullName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'WO';

  // Operational KPI calculations
  const totalAgents = overviewData?.total_agents ?? agentsList.length;
  const activeAgents = overviewData?.active_agents ?? agentsList.filter(a => a.status === 'ACTIVE').length;
  const agentUtilizationRate = totalAgents > 0 ? Math.round((activeAgents / totalAgents) * 100) : 0;

  const totalTasks = overviewData?.total_tasks ?? tasksList.length;
  const activeTasks = overviewData?.active_tasks ?? tasksList.filter(t => t.status === 'ACTIVE').length;

  const pendingCertsCount = verificationsData.certifications?.length ?? overviewData?.pending_certifications ?? 0;
  const pendingExpsCount = verificationsData.experiences?.length ?? overviewData?.pending_experiences ?? 0;
  const pendingVerificationsCount = pendingCertsCount + pendingExpsCount;

  const pendingReviewsCount = overviewData?.pending_reviews ?? reviewsList.filter(r => r.review_status === 'PENDING').length;
  const totalAssessments = overviewData?.total_assessments ?? assessmentsList.length;
  const passedAssessments = overviewData?.passed_assessments ?? assessmentsList.filter(a => a.passed === 1 || a.passed === true).length;
  const passRate = totalAssessments > 0 ? Math.round((passedAssessments / totalAssessments) * 100) : 0;

  // Pipeline distribution metrics
  const appsUnderReview = overviewData?.applications_under_review ?? pendingReviewsCount;
  const appsShortlisted = overviewData?.applications_shortlisted ?? reviewsList.filter(r => r.review_status === 'APPROVED' || r.eligibility_status === 'ELIGIBLE').length;
  const appsAssigned = overviewData?.applications_assigned ?? 0;
  const appsRejected = overviewData?.applications_rejected ?? reviewsList.filter(r => r.review_status === 'REJECTED' || r.eligibility_status === 'NOT_ELIGIBLE').length;
  const totalPipelineApps = Math.max(appsUnderReview + appsShortlisted + appsAssigned + appsRejected, 1);

  // Helper for Competency Badge Styling (Obsidian Dark Theme)
  const getCompetencyBadgeStyle = (competency) => {
    switch (competency) {
      case 'ELIGIBLE':
      case 'Eligible':
      case 'COMPETENT':
      case 'ADVANCED':
      case 'Competent':
      case 'Advanced':
        return 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40';
      case 'NOT_ELIGIBLE':
      case 'Not Eligible':
      case 'NEEDS_IMPROVEMENT':
      case 'Needs Improvement':
      case 'Ineligible':
        return 'bg-rose-950/60 text-rose-300 border-rose-500/40';
      case 'BASIC':
      case 'Basic':
      case 'Send to Review':
        return 'bg-amber-950/60 text-amber-300 border-amber-500/40';
      default:
        return 'bg-slate-900/60 text-slate-300 border-slate-700/50';
    }
  };

  // Helper for Task Status Badge (Obsidian Dark Theme)
  const getTaskStatusBadgeStyle = (status) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40';
      case 'DRAFT':
        return 'bg-amber-950/60 text-amber-300 border-amber-500/40';
      case 'INACTIVE':
        return 'bg-slate-900/60 text-slate-400 border-slate-700/50';
      case 'COMPLETED':
        return 'bg-blue-950/60 text-blue-300 border-blue-500/40';
      default:
        return 'bg-slate-900/60 text-slate-300 border-slate-700/50';
    }
  };

  // Helper for Eligibility Review Status Badge (Obsidian Dark Theme)
  const getReviewStatusBadgeStyle = (status) => {
    switch (status) {
      case 'APPROVED':
        return 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40';
      case 'PENDING':
        return 'bg-amber-950/60 text-amber-300 border-amber-500/40';
      case 'REJECTED':
        return 'bg-rose-950/60 text-rose-300 border-rose-500/40';
      default:
        return 'bg-slate-900/60 text-slate-300 border-slate-700/50';
    }
  };

  // =====================================================================
  // TASK MANAGEMENT HANDLERS
  // =====================================================================
  const openCreateTaskModal = () => {
    navigate('/workforce/tasks/create');
  };

  const openEditTaskModal = (task) => {
    navigate(`/workforce/tasks/${task.task_id}/edit`);
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

  // Task Applicants Modal Handlers
  const openApplicantsModal = async (task) => {
    setSelectedTaskForApplicants(task);
    setIsApplicantsModalOpen(true);
    setIsLoadingApplicants(true);
    try {
      const res = await adminService.getTaskApplicants(task.task_id);
      if (res?.data) {
        setTaskApplicants(res.data);
      } else {
        setTaskApplicants([]);
      }
    } catch (err) {
      console.error('Error fetching applicants:', err);
      showToast('Failed to load applicants for this task.');
      setTaskApplicants([]);
    } finally {
      setIsLoadingApplicants(false);
    }
  };

  const handleAssignTask = async (applicationId) => {
    setIsActionProcessing(true);
    try {
      const res = await adminService.assignTaskApplication(applicationId);
      if (res?.success) {
        showToast('Task successfully assigned to applicant!');
        const appsRes = await adminService.getTaskApplicants(selectedTaskForApplicants.task_id);
        if (appsRes?.data) setTaskApplicants(appsRes.data);
        const tasksRes = await adminService.getTasks();
        if (tasksRes?.data) setTasksList(tasksRes.data);
      }
    } catch (err) {
      console.error('Error assigning task:', err);
      showToast(err?.response?.data?.error || err.message || 'Failed to assign task.');
    } finally {
      setIsActionProcessing(false);
    }
  };

  const handleUpdateApplicationStatus = async (applicationId, newStatus) => {
    setIsActionProcessing(true);
    try {
      const res = await adminService.updateApplicationStatus(applicationId, newStatus);
      if (res?.success) {
        showToast(`Application marked as ${newStatus}.`);
        const appsRes = await adminService.getTaskApplicants(selectedTaskForApplicants.task_id);
        if (appsRes?.data) setTaskApplicants(appsRes.data);
      }
    } catch (err) {
      console.error('Error updating status:', err);
      showToast(err?.response?.data?.error || err.message || 'Failed to update status.');
    } finally {
      setIsActionProcessing(false);
    }
  };

  // Review Detail Modal Handler
  const openReviewDetailModal = async (review) => {
    setSelectedReview(review);
    setReviewActionComment('');
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

  const handleReviewDecisionSubmit = async (decision) => {
    if (!selectedReview?.evaluation_id) return;
    setIsSubmittingReviewDecision(true);
    try {
      const res = await adminService.submitReviewAction(
        selectedReview.evaluation_id,
        decision,
        reviewActionComment
      );
      showToast(res?.message || `Review decision '${decision}' successfully recorded.`);
      setIsReviewModalOpen(false);
      setReviewActionComment('');
      // Refresh reviews list
      const revsRes = await adminService.getReviews();
      if (revsRes?.data) setReviewsList(revsRes.data);
    } catch (err) {
      showToast(err?.response?.data?.error || err.message || 'Failed to submit review decision.', 'error');
    } finally {
      setIsSubmittingReviewDecision(false);
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
        item.agent_email?.toLowerCase().includes(assessmentSearch.toLowerCase()) ||
        item.exam_name?.toLowerCase().includes(assessmentSearch.toLowerCase()) ||
        item.category_name?.toLowerCase().includes(assessmentSearch.toLowerCase());

      const matchesResult = 
        assessmentResultFilter === 'ALL' ||
        (assessmentResultFilter === 'PASSED' ? (item.passed === 1 || item.passed === true) : (!item.passed || item.passed === 0));

      const matchesComp = 
        assessmentCompFilter === 'ALL' ||
        (assessmentCompFilter === 'ELIGIBLE' ? ['ELIGIBLE', 'COMPETENT', 'ADVANCED', 'Eligible', 'Competent', 'Advanced'].includes(item.predicted_competency) :
         assessmentCompFilter === 'NOT_ELIGIBLE' ? ['NOT_ELIGIBLE', 'NEEDS_IMPROVEMENT', 'BASIC', 'Not Eligible', 'Needs Improvement', 'Ineligible'].includes(item.predicted_competency) :
         item.predicted_competency === assessmentCompFilter);

      return matchesSearch && matchesResult && matchesComp;
    });
  }, [assessmentsList, assessmentSearch, assessmentResultFilter, assessmentCompFilter]);

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
    <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex flex-col font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
      {/* Ambient background glows */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed bottom-10 right-10 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-[#0d1428] text-white px-4 py-3 rounded-xl shadow-2xl border border-[#2b3a67] flex items-center gap-3 text-xs sm:text-sm animate-in slide-in-from-top-4 duration-300">
          <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
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

      {/* Top Navbar */}
      <header className="bg-[#080d1a]/95 border-b border-[#1b2542] px-4 sm:px-8 h-16 flex items-center justify-between sticky top-0 z-40 backdrop-blur-md">
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
            <span className="font-sora text-lg sm:text-xl font-bold text-white tracking-tight leading-none">
              VerifyMesh
            </span>
            <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider">
              Workforce Portal
            </span>
          </div>
        </div>

        {/* User Info & Actions */}
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            type="button"
            onClick={fetchData}
            className={`p-2 text-slate-400 hover:text-white hover:bg-[#151f38] rounded-xl transition-colors cursor-pointer ${isLoading ? 'animate-spin text-indigo-400' : ''}`}
            title="Refresh Portal Data"
            aria-label="Refresh Data"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* User Profile Pill & Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2.5 p-1 sm:px-2 rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer select-none"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
                {officerInitials}
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-xs font-semibold text-white leading-tight">
                  {officerFullName}
                </p>
                <p className="text-[10px] text-slate-400 leading-tight">
                  Workforce Officer
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-[#0d1428] rounded-xl shadow-2xl border border-[#2b3a67] py-1.5 z-50 animate-in fade-in zoom-in-95 duration-150 text-xs">
                <div className="px-3.5 py-2 border-b border-[#1e2a4a]">
                  <p className="text-xs font-semibold text-white">{officerFullName}</p>
                  <p className="text-[10px] text-slate-400">{user?.email || 'officer@verifymesh.io'}</p>
                  <span className="inline-block mt-1 text-[9px] font-semibold px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-500/20">
                    Workforce Operations Console
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    fetchData();
                  }}
                  className="w-full text-left px-3.5 py-2 font-medium text-slate-300 hover:bg-[#15203d] hover:text-white flex items-center gap-2 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-indigo-400" />
                  Refresh Data
                </button>
                <div className="border-t border-[#1e2a4a] my-1" />
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3.5 py-2 font-medium text-rose-400 hover:bg-rose-950/40 flex items-center gap-2 cursor-pointer"
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
            <div className={`flex items-center pb-2 ${isSidebarCollapsed ? 'justify-center' : 'justify-end'}`}>
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

            {/* Navigation Tabs */}
            {[
              { id: 'overview', label: 'Overview', icon: LayoutGrid, count: null },
              { id: 'agents', label: 'Agents', icon: Users, count: agentsList.length },
              { id: 'tasks', label: 'Tasks', icon: Briefcase, count: tasksList.length },
              { id: 'assessments', label: 'Assessments', icon: CheckCircle2, count: assessmentsList.length },
              { id: 'reviews', label: 'Eligibility Reviews', icon: ShieldCheck, count: pendingReviewsCount, isAmber: true },
              { id: 'verifications', label: 'Verifications', icon: Award, count: pendingVerificationsCount, isAmber: true }
            ].map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  title={isSidebarCollapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-r from-[#2942d9] via-[#465deb] to-[#6074f7] shadow-[0_0_20px_rgba(70,93,235,0.45)] text-white'
                      : 'text-slate-400 hover:text-white hover:bg-[#121a30]'
                  } ${isSidebarCollapsed ? 'justify-center' : ''}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  {!isSidebarCollapsed && (
                    <>
                      <span className="truncate">{item.label}</span>
                      {item.count !== null && item.count !== undefined && item.count > 0 && (
                        <span className={`ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                          item.isAmber
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : isActive
                              ? 'bg-white/20 text-white'
                              : 'bg-[#151f38] text-slate-300 border border-[#2b3a67]'
                        }`}>
                          {item.count}
                        </span>
                      )}
                    </>
                  )}
                </button>
              );
            })}
          </div>

          {/* Bottom Sidebar Items */}
          <div className="space-y-2 pt-4 border-t border-[#1b2542]">
            {!isSidebarCollapsed && (
              <div className="px-2 py-1.5 rounded-lg bg-[#0d1428] border border-[#1b2542] text-[10px] text-slate-400">
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse" />
                  <span>Workforce Gateway</span>
                </div>
                <p className="text-[9px] text-slate-500 mt-0.5">Operational mode active</p>
              </div>
            )}
            <button
              type="button"
              onClick={() => fetchData()}
              title={isSidebarCollapsed ? 'Refresh Data' : undefined}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-[#121a30] transition-colors cursor-pointer ${isSidebarCollapsed ? 'justify-center' : ''}`}
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
              {!isSidebarCollapsed && <span>Refresh Data</span>}
            </button>
            <button
              type="button"
              onClick={handleLogout}
              title={isSidebarCollapsed ? 'Sign Out' : undefined}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 transition-colors cursor-pointer ${isSidebarCollapsed ? 'justify-center' : ''}`}
            >
              <LogOut className="w-3.5 h-3.5" />
              {!isSidebarCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-5 sm:p-6 lg:p-8 space-y-6 overflow-y-auto max-w-[1600px] w-full">
          {error && (
            <Alert type="error" message={error} onClose={() => setError(null)} />
          )}

          {isLoading ? (
            <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-12 text-center shadow-xl">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm font-semibold text-white">Loading Workforce Officer Console...</p>
              <p className="text-xs text-slate-400 mt-1">Synchronizing active agent records, verification pipelines, and candidate queues</p>
            </div>
          ) : (
            <>
              {/* ========================================================= */}
              {/* TAB 1: WORKFORCE OPERATIONS OVERVIEW */}
              {/* ========================================================= */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Welcome Operations Header Banner */}
                  <div className="bg-[#0b1020] rounded-2xl p-6 border border-[#1b2542] shadow-xl relative overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="absolute -right-10 -top-10 w-60 h-60 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />
                    <div className="relative z-10">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase font-sora">
                          Workforce Operations Console
                        </span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
                      </div>
                      <h1 className="text-xl sm:text-2xl font-bold font-sora text-white mt-1 tracking-tight">
                        Welcome back, {officerFirstName}
                      </h1>
                      <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
                        Operational management for agent credential verification, eligibility determinations, and task workforce allocation.
                      </p>
                    </div>
                    <div className="flex items-center gap-2.5 relative z-10 shrink-0">
                      <button 
                        type="button" 
                        onClick={fetchData} 
                        className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#12192e] border border-[#2b3a67] text-slate-300 hover:text-white hover:border-[#3b4e87] transition-all flex items-center gap-1.5 cursor-pointer"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        Refresh
                      </button>
                      <button 
                        type="button" 
                        onClick={openCreateTaskModal} 
                        className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-[#2942d9] to-[#5a69f0] hover:from-[#354ee0] hover:to-[#6b7aff] text-white shadow-lg shadow-indigo-500/25 transition-all flex items-center gap-1.5 cursor-pointer"
                      >
                        + Create Task
                      </button>
                    </div>
                  </div>

                  {/* 6 High-Contrast Operational KPI Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                    {/* KPI 1: Total Registered Agents */}
                    <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-lg hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Agents</span>
                        <div className="w-7 h-7 rounded-lg bg-indigo-950/70 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
                          <Users className="w-3.5 h-3.5" />
                        </div>
                      </div>
                      <div className="my-2">
                        <p className="text-2xl font-bold font-sora text-white">{totalAgents}</p>
                      </div>
                      <p className="text-[11px] text-emerald-400 font-medium">
                        {activeAgents} active ({agentUtilizationRate}% pool)
                      </p>
                    </div>

                    {/* KPI 2: Active Talent */}
                    <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-lg hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Active Talent</span>
                        <div className="w-7 h-7 rounded-lg bg-emerald-950/70 text-emerald-400 border border-emerald-500/30 flex items-center justify-center">
                          <UserCheck className="w-3.5 h-3.5" />
                        </div>
                      </div>
                      <div className="my-2">
                        <p className="text-2xl font-bold font-sora text-white">{activeAgents}</p>
                      </div>
                      <p className="text-[11px] text-slate-400 font-medium">
                        Ready for allocation
                      </p>
                    </div>

                    {/* KPI 3: Pending Verifications */}
                    <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-lg hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Verifications</span>
                        <div className="w-7 h-7 rounded-lg bg-amber-950/70 text-amber-400 border border-amber-500/30 flex items-center justify-center">
                          <Award className="w-3.5 h-3.5" />
                        </div>
                      </div>
                      <div className="my-2 flex items-baseline justify-between">
                        <p className="text-2xl font-bold font-sora text-white">{pendingVerificationsCount}</p>
                        {pendingVerificationsCount > 0 && (
                          <button
                            type="button"
                            onClick={() => setActiveTab('verifications')}
                            className="text-[10px] font-semibold text-amber-400 hover:text-amber-300 underline cursor-pointer"
                          >
                            Review &rarr;
                          </button>
                        )}
                      </div>
                      <p className="text-[11px] text-amber-400 font-medium truncate">
                        {pendingCertsCount} certs &bull; {pendingExpsCount} exp
                      </p>
                    </div>

                    {/* KPI 4: Active Tasks */}
                    <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-lg hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Active Tasks</span>
                        <div className="w-7 h-7 rounded-lg bg-indigo-950/70 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
                          <Briefcase className="w-3.5 h-3.5" />
                        </div>
                      </div>
                      <div className="my-2 flex items-baseline justify-between">
                        <p className="text-2xl font-bold font-sora text-white">{activeTasks}</p>
                        <button
                          type="button"
                          onClick={() => setActiveTab('tasks')}
                          className="text-[10px] font-semibold text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
                        >
                          Manage &rarr;
                        </button>
                      </div>
                      <p className="text-[11px] text-indigo-300 font-medium">
                        of {totalTasks} total tasks
                      </p>
                    </div>

                    {/* KPI 5: Applications Under Review */}
                    <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-lg hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Candidate Reviews</span>
                        <div className="w-7 h-7 rounded-lg bg-purple-950/70 text-purple-400 border border-purple-500/30 flex items-center justify-center">
                          <ShieldCheck className="w-3.5 h-3.5" />
                        </div>
                      </div>
                      <div className="my-2 flex items-baseline justify-between">
                        <p className="text-2xl font-bold font-sora text-white">{pendingReviewsCount}</p>
                        {pendingReviewsCount > 0 && (
                          <button
                            type="button"
                            onClick={() => setActiveTab('reviews')}
                            className="text-[10px] font-semibold text-purple-400 hover:text-purple-300 underline cursor-pointer"
                          >
                            Evaluate &rarr;
                          </button>
                        )}
                      </div>
                      <p className="text-[11px] text-purple-300 font-medium">
                        Stage 1 eligible
                      </p>
                    </div>

                    {/* KPI 6: Assessment Pass Rate */}
                    <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-lg hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Evaluation Pass</span>
                        <div className="w-7 h-7 rounded-lg bg-teal-950/70 text-teal-400 border border-teal-500/30 flex items-center justify-center">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </div>
                      </div>
                      <div className="my-2">
                        <p className="text-2xl font-bold font-sora text-white">{passRate}%</p>
                      </div>
                      <p className="text-[11px] text-teal-300 font-medium">
                        {passedAssessments} of {totalAssessments} passed
                      </p>
                    </div>
                  </div>

                  {/* Operations Attention Queue / Action Required Section */}
                  <div className="bg-[#0b1020] rounded-2xl p-6 border border-[#1b2542] shadow-xl">
                    <div className="flex items-center justify-between pb-4 border-b border-[#1b2542]">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-amber-950/70 text-amber-400 border border-amber-500/30 flex items-center justify-center">
                          <AlertCircle className="w-4 h-4" />
                        </div>
                        <div>
                          <h2 className="text-base font-bold font-sora text-white">Operational Attention Queue</h2>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Critical pending credential validations and candidate evaluations requiring workforce officer action
                          </p>
                        </div>
                      </div>
                      <span className="text-xs text-slate-400 bg-[#12192e] px-2.5 py-1 rounded-lg border border-[#2b3a67]">
                        {pendingVerificationsCount + pendingReviewsCount} Total Pending Items
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
                      {/* Queue Card 1: Pending Certifications */}
                      <div className="bg-[#0e162e] rounded-xl p-4 border border-[#202e52] flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-200">Certification Approvals</span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              pendingCertsCount > 0 
                                ? 'bg-amber-950/70 text-amber-300 border border-amber-500/40' 
                                : 'bg-emerald-950/70 text-emerald-300 border border-emerald-500/40'
                            }`}>
                              {pendingCertsCount > 0 ? `${pendingCertsCount} Pending` : 'All Verified'}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                            Agent-submitted professional credentials and licenses requiring official verification.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveTab('verifications')}
                          className="mt-4 w-full py-2 px-3 rounded-lg text-xs font-semibold bg-[#15203d] text-indigo-300 hover:text-white hover:bg-indigo-900/40 border border-[#2b3a67] transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                        >
                          <span>Open Certifications Queue</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Queue Card 2: Pending Work Experience */}
                      <div className="bg-[#0e162e] rounded-xl p-4 border border-[#202e52] flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-200">Work Experience Tenures</span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              pendingExpsCount > 0 
                                ? 'bg-amber-950/70 text-amber-300 border border-amber-500/40' 
                                : 'bg-emerald-950/70 text-emerald-300 border border-emerald-500/40'
                            }`}>
                              {pendingExpsCount > 0 ? `${pendingExpsCount} Pending` : 'All Verified'}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                            Employment records, supervisor responses, and tenure claims awaiting sign-off.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveTab('verifications')}
                          className="mt-4 w-full py-2 px-3 rounded-lg text-xs font-semibold bg-[#15203d] text-indigo-300 hover:text-white hover:bg-indigo-900/40 border border-[#2b3a67] transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                        >
                          <span>Open Experience Queue</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Queue Card 3: Candidate Applications */}
                      <div className="bg-[#0e162e] rounded-xl p-4 border border-[#202e52] flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-200">Candidate Reviews</span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              pendingReviewsCount > 0 
                                ? 'bg-purple-950/70 text-purple-300 border border-purple-500/40' 
                                : 'bg-emerald-950/70 text-emerald-300 border border-emerald-500/40'
                            }`}>
                              {pendingReviewsCount > 0 ? `${pendingReviewsCount} Under Review` : 'All Evaluated'}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                            Applicants satisfying Stage 1 mandatory criteria awaiting final assignment decisions.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveTab('reviews')}
                          className="mt-4 w-full py-2 px-3 rounded-lg text-xs font-semibold bg-[#15203d] text-indigo-300 hover:text-white hover:bg-indigo-900/40 border border-[#2b3a67] transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                        >
                          <span>Evaluate Candidate Pool</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Visual Operational Pipelines */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Pipeline Card 1: Application Lifecycle Posture */}
                    <div className="bg-[#0b1020] rounded-2xl p-5 border border-[#1b2542] shadow-xl">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Briefcase className="w-4 h-4 text-indigo-400" />
                          <h3 className="text-sm font-bold font-sora text-white">Application Pipeline Posture</h3>
                        </div>
                        <span className="text-[11px] text-slate-400 font-medium">
                          {totalPipelineApps} Total Applications
                        </span>
                      </div>

                      {/* Multi-segment Progress Bar */}
                      <div className="w-full h-3 rounded-full bg-[#12192e] overflow-hidden flex border border-[#1e2a4a]">
                        <div 
                          className="bg-indigo-500 transition-all duration-500" 
                          style={{ width: `${(appsUnderReview / totalPipelineApps) * 100}%` }}
                          title={`Under Review: ${appsUnderReview}`}
                        />
                        <div 
                          className="bg-cyan-500 transition-all duration-500" 
                          style={{ width: `${(appsShortlisted / totalPipelineApps) * 100}%` }}
                          title={`Shortlisted: ${appsShortlisted}`}
                        />
                        <div 
                          className="bg-emerald-500 transition-all duration-500" 
                          style={{ width: `${(appsAssigned / totalPipelineApps) * 100}%` }}
                          title={`Assigned: ${appsAssigned}`}
                        />
                        <div 
                          className="bg-rose-500 transition-all duration-500" 
                          style={{ width: `${(appsRejected / totalPipelineApps) * 100}%` }}
                          title={`Rejected: ${appsRejected}`}
                        />
                      </div>

                      {/* Legend */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3.5 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-indigo-500 shrink-0" />
                          <span className="text-slate-400">Under Review:</span>
                          <span className="font-bold text-white">{appsUnderReview}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-cyan-500 shrink-0" />
                          <span className="text-slate-400">Shortlisted:</span>
                          <span className="font-bold text-white">{appsShortlisted}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                          <span className="text-slate-400">Assigned:</span>
                          <span className="font-bold text-white">{appsAssigned}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                          <span className="text-slate-400">Rejected:</span>
                          <span className="font-bold text-white">{appsRejected}</span>
                        </div>
                      </div>
                    </div>

                    {/* Pipeline Card 2: Talent Readiness Posture */}
                    <div className="bg-[#0b1020] rounded-2xl p-5 border border-[#1b2542] shadow-xl">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-emerald-400" />
                          <h3 className="text-sm font-bold font-sora text-white">Talent Pool Readiness</h3>
                        </div>
                        <span className="text-[11px] text-slate-400 font-medium">
                          {totalAgents} Registered
                        </span>
                      </div>

                      {/* Multi-segment Progress Bar */}
                      <div className="w-full h-3 rounded-full bg-[#12192e] overflow-hidden flex border border-[#1e2a4a]">
                        <div 
                          className="bg-emerald-500 transition-all duration-500" 
                          style={{ width: `${totalAgents > 0 ? (activeAgents / totalAgents) * 100 : 0}%` }}
                          title={`Active Talent: ${activeAgents}`}
                        />
                        <div 
                          className="bg-amber-500 transition-all duration-500" 
                          style={{ width: `${totalAgents > 0 ? (Math.max(0, totalAgents - activeAgents) / totalAgents) * 100 : 0}%` }}
                          title={`In Review / Inactive: ${Math.max(0, totalAgents - activeAgents)}`}
                        />
                      </div>

                      {/* Legend */}
                      <div className="grid grid-cols-2 gap-2 mt-3.5 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                          <span className="text-slate-400">Active Talent:</span>
                          <span className="font-bold text-white">{activeAgents} ({agentUtilizationRate}%)</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                          <span className="text-slate-400">Onboarding / In Review:</span>
                          <span className="font-bold text-white">{Math.max(0, totalAgents - activeAgents)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recent Operational Activity Stream */}
                  <div className="bg-[#0b1020] rounded-2xl p-6 border border-[#1b2542] shadow-xl">
                    <div className="flex items-center justify-between pb-4 border-b border-[#1b2542]">
                      <div>
                        <h2 className="text-base font-bold font-sora text-white">Recent Operational Activity</h2>
                        <p className="text-xs text-slate-400 mt-0.5">Latest evaluations and assessments processed across the workforce pool</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab('assessments')}
                        className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        View all assessments &rarr;
                      </button>
                    </div>

                    {overviewData?.recent_assessments?.length > 0 ? (
                      <div className="overflow-x-auto mt-4">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-[#1b2542] text-[10px] font-semibold text-slate-400 uppercase tracking-wider bg-[#0d1428]">
                              <th className="py-3 px-3.5 font-semibold">Candidate Agent</th>
                              <th className="py-3 px-3.5 font-semibold">Evaluation Score</th>
                              <th className="py-3 px-3.5 font-semibold">Attempt</th>
                              <th className="py-3 px-3.5 font-semibold">Predicted Competency</th>
                              <th className="py-3 px-3.5 font-semibold">Confidence</th>
                              <th className="py-3 px-3.5 font-semibold">Completed Date</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1b2542] text-slate-300">
                            {overviewData.recent_assessments.map((a) => (
                              <tr key={a.exam_result_id} className="hover:bg-[#121a30] transition-colors">
                                <td className="py-3 px-3.5 font-semibold text-white">
                                  {a.agent_name}
                                  <span className="block text-[11px] text-slate-400 font-normal">{a.agent_email}</span>
                                </td>
                                <td className="py-3 px-3.5">
                                  <span className="font-semibold text-white">{a.assessment_score}%</span>
                                  {a.passed ? (
                                    <span className="ml-2 text-[10px] font-semibold text-emerald-400 bg-emerald-950/70 px-2 py-0.5 rounded-full border border-emerald-500/40">
                                      Passed
                                    </span>
                                  ) : (
                                    <span className="ml-2 text-[10px] font-semibold text-rose-400 bg-rose-950/70 px-2 py-0.5 rounded-full border border-rose-500/40">
                                      Failed
                                    </span>
                                  )}
                                </td>
                                <td className="py-3 px-3.5 text-slate-400">Attempt #{a.attempt_number}</td>
                                <td className="py-3 px-3.5">
                                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getCompetencyBadgeStyle(a.predicted_competency)}`}>
                                    {a.predicted_competency || 'In Review'}
                                  </span>
                                </td>
                                <td className="py-3 px-3.5 text-slate-300 font-mono text-[11px]">
                                  {a.confidence ? `${Math.round(a.confidence > 1 ? a.confidence : a.confidence * 100)}%` : '—'}
                                </td>
                                <td className="py-3 px-3.5 text-slate-400 text-[11px]">
                                  {a.completed_at ? new Date(a.completed_at).toLocaleString() : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="py-10 text-center">
                        <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-300">No assessments recorded yet</p>
                        <p className="text-xs text-slate-500 mt-0.5">Evaluation submissions will automatically stream into this operational feed.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB 2: AGENT TALENT DIRECTORY */}
              {/* ========================================================= */}
              {activeTab === 'agents' && (
                <div className="space-y-6">
                  {/* Header Title & Summary Banner */}
                  <div className="bg-[#0b1020] rounded-2xl p-6 border border-[#1b2542] shadow-xl relative overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="absolute -right-10 -top-10 w-60 h-60 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />
                    <div className="relative z-10">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase font-sora">
                          Workforce Talent Management
                        </span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
                      </div>
                      <h1 className="text-xl sm:text-2xl font-bold font-sora text-white mt-1 tracking-tight">
                        Agent Talent Directory
                      </h1>
                      <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
                        Inspect candidate profiles, verified work credentials, evaluation scores, and task readiness.
                      </p>
                    </div>
                    <div className="text-xs font-semibold text-slate-300 bg-[#12192e] px-3.5 py-2 rounded-xl border border-[#2b3a67] self-start sm:self-auto relative z-10">
                      Showing <strong className="text-indigo-400">{filteredAgents.length}</strong> of <strong className="text-white">{agentsList.length}</strong> agents
                    </div>
                  </div>

                  {/* Search and Filters Toolbar */}
                  <div className="bg-[#0b1020] rounded-2xl p-4 border border-[#1b2542] shadow-lg flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="Search agents by name, email, or phone..."
                        value={agentSearch}
                        onChange={(e) => setAgentSearch(e.target.value)}
                        className="w-full h-10 pl-9 pr-4 rounded-xl border border-[#1e2a4a] bg-[#0d1428] text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                      />
                      <svg className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      {agentSearch && (
                        <button
                          type="button"
                          onClick={() => setAgentSearch('')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2.5">
                      <select
                        value={agentCompFilter}
                        onChange={(e) => setAgentCompFilter(e.target.value)}
                        className="h-10 px-3 rounded-xl border border-[#1e2a4a] text-xs font-medium text-slate-300 bg-[#0d1428] focus:outline-none focus:border-indigo-500 cursor-pointer"
                      >
                        <option value="ALL">All Competencies</option>
                        <option value="ELIGIBLE">Eligible / Advanced</option>
                        <option value="NOT_ELIGIBLE">Not Eligible / Basic</option>
                        <option value="UNASSESSED">Unassessed</option>
                      </select>

                      <select
                        value={agentStatusFilter}
                        onChange={(e) => setAgentStatusFilter(e.target.value)}
                        className="h-10 px-3 rounded-xl border border-[#1e2a4a] text-xs font-medium text-slate-300 bg-[#0d1428] focus:outline-none focus:border-indigo-500 cursor-pointer"
                      >
                        <option value="ALL">All Statuses</option>
                        <option value="ACTIVE">Active</option>
                        <option value="INACTIVE">Inactive</option>
                        <option value="SUSPENDED">Suspended</option>
                      </select>

                      {(agentSearch || agentStatusFilter !== 'ALL' || agentCompFilter !== 'ALL') && (
                        <button
                          type="button"
                          onClick={() => {
                            setAgentSearch('');
                            setAgentStatusFilter('ALL');
                            setAgentCompFilter('ALL');
                          }}
                          className="h-10 px-3 rounded-xl border border-[#2b3a67] text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-[#12192e] hover:bg-[#1a2542] transition-colors flex items-center gap-1.5 cursor-pointer shrink-0"
                          title="Reset Filters"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Reset</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Agents Table */}
                  <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] shadow-xl overflow-hidden">
                    {filteredAgents.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="bg-[#0d1428] border-b border-[#1b2542] text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                              <th className="py-3 px-4 font-semibold">Candidate Agent</th>
                              <th className="py-3 px-4 font-semibold">Contact &amp; Education</th>
                              <th className="py-3 px-4 font-semibold">Verified Credentials</th>
                              <th className="py-3 px-4 font-semibold">Status &amp; Availability</th>
                              <th className="py-3 px-4 font-semibold">Latest Assessment</th>
                              <th className="py-3 px-4 font-semibold">Competency Fit</th>
                              <th className="py-3 px-4 font-semibold text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1b2542] text-slate-300">
                            {filteredAgents.map((ag) => {
                              const initials = ag.full_name
                                ? ag.full_name.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
                                : 'AG';
                              const verifiedCerts = ag.verified_certifications_count || 0;
                              const verifiedExps = ag.verified_experiences_count || 0;

                              return (
                                <tr key={ag.agent_id} className="hover:bg-[#121a30] transition-colors">
                                  {/* Candidate Agent */}
                                  <td className="py-3.5 px-4 font-semibold text-white">
                                    <div className="flex items-center gap-3">
                                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-xs">
                                        {initials}
                                      </div>
                                      <div>
                                        <p className="font-semibold text-white leading-tight">{ag.full_name}</p>
                                        <p className="text-[11px] text-slate-400 font-normal mt-0.5">{ag.email}</p>
                                      </div>
                                    </div>
                                  </td>

                                  {/* Contact & Education */}
                                  <td className="py-3.5 px-4">
                                    <p className="text-xs text-slate-200">{ag.phone || 'No phone recorded'}</p>
                                    <p className="text-[11px] text-slate-400 truncate max-w-[200px] mt-0.5" title={ag.education}>
                                      {ag.education || 'Self-declared background'}
                                    </p>
                                  </td>

                                  {/* Verified Credentials */}
                                  <td className="py-3.5 px-4">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-950/70 text-indigo-300 border border-indigo-500/30">
                                        {verifiedCerts} cert{verifiedCerts !== 1 ? 's' : ''}
                                      </span>
                                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950/70 text-emerald-300 border border-emerald-500/30">
                                        {verifiedExps} exp
                                      </span>
                                    </div>
                                    <p className="text-[10px] text-slate-400 mt-1">
                                      {ag.experience_months || 0} months tenure
                                    </p>
                                  </td>

                                  {/* Status & Availability */}
                                  <td className="py-3.5 px-4">
                                    <div className="space-y-1">
                                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                                        ag.status === 'ACTIVE'
                                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
                                          : 'bg-slate-900/60 text-slate-400 border-slate-700/50'
                                      }`}>
                                        {ag.status || 'ACTIVE'}
                                      </span>
                                      <span className="block text-[10px] text-slate-400">
                                        {ag.availability_status || 'AVAILABLE'}
                                      </span>
                                    </div>
                                  </td>

                                  {/* Latest Assessment */}
                                  <td className="py-3.5 px-4">
                                    {ag.assessment_score != null ? (
                                      <div>
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-semibold text-white">{ag.assessment_score}%</span>
                                          {ag.assessment_score >= 70 ? (
                                            <span className="text-[9px] font-semibold text-emerald-400 bg-emerald-950/70 px-1.5 py-0.2 rounded border border-emerald-500/30">
                                              Passed
                                            </span>
                                          ) : (
                                            <span className="text-[9px] font-semibold text-rose-400 bg-rose-950/70 px-1.5 py-0.2 rounded border border-rose-500/30">
                                              Failed
                                            </span>
                                          )}
                                        </div>
                                        <span className="text-[10px] text-slate-400 block mt-0.5">
                                          Attempt #{ag.attempt_number} ({ag.total_attempts} total)
                                        </span>
                                      </div>
                                    ) : (
                                      <span className="text-[11px] text-slate-500 italic">Unassessed</span>
                                    )}
                                  </td>

                                  {/* Competency Classification */}
                                  <td className="py-3.5 px-4">
                                    {ag.predicted_competency ? (
                                      <div className="space-y-0.5">
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getCompetencyBadgeStyle(ag.predicted_competency)}`}>
                                          {ag.predicted_competency}
                                        </span>
                                        {ag.confidence_percent && (
                                          <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                                            {ag.confidence_percent}% confidence
                                          </p>
                                        )}
                                      </div>
                                    ) : (
                                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-900/60 text-slate-400 border border-slate-700/50">
                                        Pending Assessment
                                      </span>
                                    )}
                                  </td>

                                  {/* Action */}
                                  <td className="py-3.5 px-4 text-right">
                                    <button 
                                      type="button"
                                      onClick={() => openAgentModal(ag)}
                                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#12192e] text-indigo-300 hover:text-white hover:bg-indigo-900/40 border border-[#2b3a67] transition-all cursor-pointer"
                                    >
                                      Inspect Profile &rarr;
                                    </button>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="py-12 text-center">
                        <Users className="w-9 h-9 text-slate-600 mx-auto mb-2.5" />
                        <p className="text-sm font-semibold text-slate-300">No agents found</p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {agentSearch || agentStatusFilter !== 'ALL' || agentCompFilter !== 'ALL'
                            ? 'No agents match your active search and filter criteria.'
                            : 'No agents are currently registered in the workforce database.'}
                        </p>
                        {(agentSearch || agentStatusFilter !== 'ALL' || agentCompFilter !== 'ALL') && (
                          <button
                            type="button"
                            onClick={() => {
                              setAgentSearch('');
                              setAgentStatusFilter('ALL');
                              setAgentCompFilter('ALL');
                            }}
                            className="mt-3.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#12192e] text-indigo-300 hover:text-white border border-[#2b3a67] inline-flex items-center gap-1.5 cursor-pointer"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Reset Filters</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* TAB 3: WORKFORCE TASK ALLOCATION CATALOG */}
              {/* ========================================================= */}
              {activeTab === 'tasks' && (
                <div className="space-y-6">
                  {/* Header Title & Actions Banner */}
                  <div className="bg-[#0b1020] rounded-2xl p-6 border border-[#1b2542] shadow-xl relative overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="absolute -right-10 -top-10 w-60 h-60 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />
                    <div className="relative z-10">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase font-sora">
                          Workforce Task Management
                        </span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
                      </div>
                      <h1 className="text-xl sm:text-2xl font-bold font-sora text-white mt-1 tracking-tight">
                        Task Allocation Catalog
                      </h1>
                      <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
                        Configure allocation roles, assign minimum competency tiers, define automated qualification rules, and review candidate applicants.
                      </p>
                    </div>
                    <button 
                      type="button" 
                      onClick={openCreateTaskModal} 
                      className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-[#2942d9] to-[#5a69f0] hover:from-[#354ee0] hover:to-[#6b7aff] text-white shadow-lg shadow-indigo-500/25 transition-all flex items-center gap-1.5 cursor-pointer self-start sm:self-auto shrink-0 relative z-10"
                    >
                      <span>+ Create Task</span>
                    </button>
                  </div>

                  {/* Search and Filters Toolbar */}
                  <div className="bg-[#0b1020] rounded-2xl p-4 border border-[#1b2542] shadow-lg flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="Search tasks by name or description..."
                        value={taskSearch}
                        onChange={(e) => setTaskSearch(e.target.value)}
                        className="w-full h-10 pl-9 pr-4 rounded-xl border border-[#1e2a4a] bg-[#0d1428] text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                      />
                      <svg className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      {taskSearch && (
                        <button
                          type="button"
                          onClick={() => setTaskSearch('')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2.5">
                      <select
                        value={taskCategoryFilter}
                        onChange={(e) => setTaskCategoryFilter(e.target.value)}
                        className="h-10 px-3 rounded-xl border border-[#1e2a4a] text-xs font-medium text-slate-300 bg-[#0d1428] focus:outline-none focus:border-indigo-500 cursor-pointer"
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
                        className="h-10 px-3 rounded-xl border border-[#1e2a4a] text-xs font-medium text-slate-300 bg-[#0d1428] focus:outline-none focus:border-indigo-500 cursor-pointer"
                      >
                        <option value="ACTIVE">Active Tasks (Default)</option>
                        <option value="INACTIVE">Inactive Tasks</option>
                        <option value="ALL">All Statuses</option>
                        <option value="DRAFT">Draft</option>
                        <option value="COMPLETED">Completed</option>
                      </select>

                      {(taskSearch || taskCategoryFilter !== 'ALL' || taskStatusFilter !== 'ACTIVE') && (
                        <button
                          type="button"
                          onClick={() => {
                            setTaskSearch('');
                            setTaskCategoryFilter('ALL');
                            setTaskStatusFilter('ACTIVE');
                          }}
                          className="h-10 px-3 rounded-xl border border-[#2b3a67] text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-[#12192e] hover:bg-[#1a2542] transition-colors flex items-center gap-1.5 cursor-pointer shrink-0"
                          title="Reset Filters"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Reset</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Tasks Grid */}
                  {filteredTasks.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {filteredTasks.map((t) => (
                        <div key={t.task_id} className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-5 shadow-xl hover:border-[#2b3a67] transition-all flex flex-col justify-between">
                          <div>
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <span className="inline-block text-[10px] font-semibold text-indigo-400 uppercase tracking-wider mb-1">
                                  {t.category_name || 'General Category'}
                                </span>
                                <h3 className="text-base font-bold font-sora text-white leading-snug">
                                  {t.task_name}
                                </h3>
                              </div>
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${getTaskStatusBadgeStyle(t.status)}`}>
                                {t.status}
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 mt-2 line-clamp-2 leading-relaxed">
                              {t.description || 'No detailed description provided for this task.'}
                            </p>

                            {/* Compensation & arrangement tags */}
                            <div className="flex flex-wrap items-center gap-2 mt-3">
                              <span className="px-2.5 py-1 rounded-lg bg-emerald-950/70 text-emerald-300 text-[11px] font-semibold border border-emerald-500/30">
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

                              <span className="px-2.5 py-1 rounded-lg bg-[#12192e] text-slate-300 text-[11px] font-medium border border-[#2b3a67]">
                                {t.work_arrangement || 'Remote'}
                              </span>

                              {t.positions_count > 1 && (
                                <span className="px-2.5 py-1 rounded-lg bg-indigo-950/70 text-indigo-300 text-[11px] font-medium border border-indigo-500/30">
                                  {t.positions_count} Openings
                                </span>
                              )}

                              <span className="px-2.5 py-1 rounded-lg bg-purple-950/70 text-purple-300 text-[11px] font-medium border border-purple-500/30">
                                {t.application_count || 0} applicant{t.application_count !== 1 ? 's' : ''}
                              </span>
                            </div>

                            {/* Eligibility Requirements breakdown */}
                            <div className="mt-4 pt-3 border-t border-[#1b2542] space-y-2">
                              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                Mandatory Prerequisites
                              </p>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                                  <span className="text-[10px] text-slate-400 block font-medium">Min. Competency</span>
                                  <span className={`inline-block mt-0.5 px-2 py-0.2 rounded-full text-[10px] font-semibold border ${getCompetencyBadgeStyle(t.minimum_competency)}`}>
                                    {t.minimum_competency || 'BASIC'}
                                  </span>
                                </div>

                                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                                  <span className="text-[10px] text-slate-400 block font-medium">Min. Experience</span>
                                  <span className="font-semibold text-white mt-0.5 block text-xs">
                                    {t.minimum_experience_months ? `${t.minimum_experience_months} months` : 'None required'}
                                  </span>
                                </div>

                                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                                  <span className="text-[10px] text-slate-400 block font-medium">Certification</span>
                                  <span className="font-semibold text-white mt-0.5 block truncate text-xs" title={t.certification_name}>
                                    {t.certification_name || 'Not required'}
                                  </span>
                                </div>

                                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                                  <span className="text-[10px] text-slate-400 block font-medium">Exam Gate</span>
                                  <span className="font-semibold text-white mt-0.5 block text-xs">
                                    {t.exam_required ? 'Required' : 'Optional'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Footer Actions */}
                          <div className="mt-5 pt-3 border-t border-[#1b2542] flex items-center justify-between flex-wrap gap-2">
                            <span className="text-[11px] text-slate-500">
                              Task ID: #{t.task_id}
                            </span>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => openApplicantsModal(t)}
                                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-[#2942d9] to-[#5a69f0] text-white hover:from-[#354ee0] hover:to-[#6b7aff] shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
                              >
                                <Users className="w-3.5 h-3.5" />
                                <span>Applicants ({t.application_count || 0})</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => handleToggleTaskStatus(t)}
                                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[#12192e] text-slate-300 hover:text-white border border-[#2b3a67] transition-all cursor-pointer"
                              >
                                {t.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                              </button>
                              <button
                                type="button"
                                onClick={() => openEditTaskModal(t)}
                                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[#12192e] text-indigo-300 hover:text-white border border-[#2b3a67] transition-all cursor-pointer"
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                onClick={() => openDeleteTaskModal(t)}
                                className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 border border-transparent hover:border-rose-900/40 transition-all cursor-pointer"
                                title="Delete Task"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-12 text-center shadow-xl">
                      <Briefcase className="w-9 h-9 text-slate-600 mx-auto mb-3" />
                      <p className="text-sm font-bold text-white">No tasks configured</p>
                      <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                        There are currently no tasks matching your filter criteria. Create your task to define competency requirements and unlock workforce allocation.
                      </p>
                      <button 
                        type="button" 
                        onClick={openCreateTaskModal} 
                        className="mt-4 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-[#2942d9] to-[#5a69f0] hover:from-[#354ee0] hover:to-[#6b7aff] text-white shadow-lg shadow-indigo-500/25 transition-all inline-flex items-center gap-1.5 cursor-pointer"
                      >
                        + Create Task
                      </button>
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
                  <div className="bg-[#0b1020] rounded-2xl p-6 sm:p-7 border border-[#1b2542] shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase block">
                        AUDIT TRAIL &amp; INFERENCE LOGS
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold font-sora text-white mt-1 tracking-tight">
                        Assessment History
                      </h1>
                      <p className="text-xs sm:text-sm text-slate-400 mt-1">
                        Historical log of competency assessments, exam battery scores, passing policy (&ge;70%), and ML binary classification outputs.
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
                      <span className="text-xs text-slate-300 bg-[#0d1428] px-3 py-1.5 rounded-xl border border-[#1e2a4a]">
                        Total: <strong className="text-white font-mono">{assessmentsList.length}</strong>
                      </span>
                      <span className="text-xs text-emerald-400 bg-emerald-950/40 px-3 py-1.5 rounded-xl border border-emerald-500/30">
                        Passed: <strong className="font-mono">{passedAssessments}</strong>
                      </span>
                      <span className="text-xs text-indigo-300 bg-indigo-950/40 px-3 py-1.5 rounded-xl border border-indigo-500/30">
                        Pass Rate: <strong className="font-mono">{assessmentsList.length > 0 ? Math.round((passedAssessments / assessmentsList.length) * 100) : 0}%</strong>
                      </span>
                    </div>
                  </div>

                  {/* Search and Filters Toolbar */}
                  <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-xl flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="Search assessments by agent name, email, exam, or category..."
                        value={assessmentSearch}
                        onChange={(e) => setAssessmentSearch(e.target.value)}
                        className="w-full pl-9 pr-9 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white placeholder:text-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition-all"
                      />
                      <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                      {assessmentSearch && (
                        <button
                          type="button"
                          onClick={() => setAssessmentSearch('')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                      <select
                        value={assessmentResultFilter}
                        onChange={(e) => setAssessmentResultFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-xs font-medium text-slate-300 focus:outline-none focus:border-indigo-500 transition-all cursor-pointer"
                      >
                        <option value="ALL">All Outcomes</option>
                        <option value="PASSED">Passed Only (&ge;70%)</option>
                        <option value="FAILED">Failed Only (&lt;70%)</option>
                      </select>

                      <select
                        value={assessmentCompFilter}
                        onChange={(e) => setAssessmentCompFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-xs font-medium text-slate-300 focus:outline-none focus:border-indigo-500 transition-all cursor-pointer"
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
                          className="px-3 py-2 rounded-xl bg-[#151f38] text-xs font-semibold text-slate-300 hover:text-white border border-[#2b3a67] transition-all cursor-pointer"
                        >
                          Reset Filters
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Assessments Table */}
                  <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] shadow-xl overflow-hidden">
                    {filteredAssessments.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-[#080d1a] border-b border-[#1b2542] text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">ID</th>
                              <th className="py-3.5 px-4 font-semibold">Candidate</th>
                              <th className="py-3.5 px-4 font-semibold">Assessment Battery</th>
                              <th className="py-3.5 px-4 font-semibold">Score &amp; Policy (&ge;70%)</th>
                              <th className="py-3.5 px-4 font-semibold">Attempt</th>
                              <th className="py-3.5 px-4 font-semibold">AI Predicted Competency</th>
                              <th className="py-3.5 px-4 font-semibold">Confidence</th>
                              <th className="py-3.5 px-4 font-semibold">Date Completed</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Details</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1b2542]/60 text-slate-300">
                            {filteredAssessments.map((item) => {
                              const isPassed = item.passed === 1 || item.passed === true || (item.assessment_score >= (item.passing_score || 70));
                              const candidateInitials = item.agent_name
                                ? item.agent_name.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
                                : 'AG';

                              return (
                                <tr key={item.exam_result_id} className="hover:bg-[#121a36]/40 transition-colors">
                                  <td className="py-3.5 px-4 font-mono text-xs text-slate-500">
                                    #{item.exam_result_id}
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <div className="flex items-center gap-2.5">
                                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-[10px] flex items-center justify-center shrink-0">
                                        {candidateInitials}
                                      </div>
                                      <div>
                                        <p className="font-semibold text-white leading-tight">{item.agent_name}</p>
                                        <p className="text-xs text-slate-400 font-normal">{item.agent_email}</p>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <p className="text-xs font-semibold text-indigo-300 leading-tight">
                                      {item.exam_name || 'Standard Competency Battery'}
                                    </p>
                                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-[#151f38] text-slate-400 border border-[#23315c] mt-1">
                                      {item.category_name || 'General Domain'}
                                    </span>
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <div className="flex items-center gap-2">
                                      <span className="font-bold text-white font-mono text-sm">
                                        {item.assessment_score}%
                                      </span>
                                      {isPassed ? (
                                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                          Passed
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-950/60 border border-rose-500/40 px-2 py-0.5 rounded-full">
                                          <XCircle className="w-3 h-3 text-rose-400" />
                                          Failed
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-[10px] text-slate-500 mt-0.5">
                                      Threshold: &ge;{item.passing_score || 70}%
                                    </p>
                                  </td>
                                  <td className="py-3.5 px-4 font-medium text-slate-400">
                                    Attempt #{item.attempt_number}
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(item.predicted_competency)}`}>
                                      {item.predicted_competency || 'In Review'}
                                    </span>
                                  </td>
                                  <td className="py-3.5 px-4 font-mono text-slate-300">
                                    {item.confidence_percent ? `${item.confidence_percent}%` : '—'}
                                  </td>
                                  <td className="py-3.5 px-4 text-xs text-slate-400">
                                    {item.completed_at ? new Date(item.completed_at).toLocaleString() : '—'}
                                  </td>
                                  <td className="py-3.5 px-4 text-right">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setSelectedAssessment(item);
                                        setIsAssessmentModalOpen(true);
                                      }}
                                      className="px-3 py-1.5 rounded-xl bg-[#151f38] hover:bg-[#1c294d] text-indigo-300 hover:text-white border border-[#23315c] text-xs font-semibold cursor-pointer transition-all"
                                    >
                                      Inspect Battery
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
                        <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-300">No assessment records found</p>
                        <p className="text-xs text-slate-500 mt-1">No evaluations match the search or filter criteria.</p>
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
                  <div className="bg-[#0b1020] rounded-2xl p-6 sm:p-7 border border-[#1b2542] shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase block">
                        HUMAN-IN-THE-LOOP ALLOCATION
                      </span>
                      <h1 className="text-2xl sm:text-3xl font-bold font-sora text-white mt-1 tracking-tight">
                        Eligibility Reviews
                      </h1>
                      <p className="text-xs sm:text-sm text-slate-400 mt-1">
                        Oversee binary gatekeeper predictions (Eligible / Not Eligible) and multi-criteria rule compliance for task eligibility.
                      </p>
                    </div>
                    <div className="text-xs text-slate-300 bg-[#0d1428] px-3.5 py-2 rounded-xl border border-[#1e2a4a] self-start sm:self-auto font-medium">
                      Showing <strong className="text-white font-mono">{filteredReviews.length}</strong> review records
                    </div>
                  </div>

                  {/* Conceptual Distinction Banner */}
                  <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/40 text-xs sm:text-sm text-amber-200 flex items-start gap-3 shadow-md">
                    <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-amber-300 font-sora">
                        Operational Rule: AI Competency Prediction &ne; Final Task Eligibility
                      </p>
                      <p className="text-xs text-amber-200/90 mt-1 leading-relaxed">
                        The <strong>AI Predicted Competency</strong> reflects general test and experience performance. 
                        <strong> Task Eligibility</strong> evaluates compliance with mandatory criteria for a specific role (such as minimum required months or required certifications). 
                        An agent can be Competent in general, yet require Review for roles requiring higher experience.
                      </p>
                    </div>
                  </div>

                  {/* Filters */}
                  <div className="bg-[#0b1020] rounded-2xl p-4 sm:p-5 border border-[#1b2542] shadow-xl flex flex-wrap gap-3 items-center justify-between">
                    <div className="flex items-center gap-3">
                      <label className="text-xs font-semibold text-slate-400">Review Status:</label>
                      <select
                        value={reviewStatusFilter}
                        onChange={(e) => setReviewStatusFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-xs font-medium text-slate-300 focus:outline-none focus:border-indigo-500 transition-all cursor-pointer"
                      >
                        <option value="ALL">All Review Statuses</option>
                        <option value="PENDING">Pending Action</option>
                        <option value="APPROVED">Approved</option>
                        <option value="REJECTED">Rejected</option>
                        <option value="NOT_REQUIRED">Not Required</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-3">
                      <label className="text-xs font-semibold text-slate-400">Eligibility Status:</label>
                      <select
                        value={reviewEligibilityFilter}
                        onChange={(e) => setReviewEligibilityFilter(e.target.value)}
                        className="px-3 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-xs font-medium text-slate-300 focus:outline-none focus:border-indigo-500 transition-all cursor-pointer"
                      >
                        <option value="ALL">All Eligibility Outcomes</option>
                        <option value="ELIGIBLE">Eligible</option>
                        <option value="PENDING_REVIEW">Pending Review</option>
                        <option value="NOT_ELIGIBLE">Not Eligible</option>
                      </select>
                    </div>
                  </div>

                  {/* Reviews Table / Honest Empty State */}
                  <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] shadow-xl overflow-hidden">
                    {filteredReviews.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-[#080d1a] border-b border-[#1b2542] text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Evaluation ID</th>
                              <th className="py-3.5 px-4 font-semibold">Candidate</th>
                              <th className="py-3.5 px-4 font-semibold">Target Task</th>
                              <th className="py-3.5 px-4 font-semibold">AI Prediction</th>
                              <th className="py-3.5 px-4 font-semibold">Eligibility Status</th>
                              <th className="py-3.5 px-4 font-semibold">Review Status</th>
                              <th className="py-3.5 px-4 font-semibold">Evaluated Date</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1b2542]/60 text-slate-300">
                            {filteredReviews.map((rev) => {
                              const candidateInitials = rev.agent_name
                                ? rev.agent_name.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
                                : 'AG';

                              return (
                                <tr key={rev.evaluation_id} className="hover:bg-[#121a36]/40 transition-colors">
                                  <td className="py-3.5 px-4 font-mono text-xs text-slate-500">
                                    #{rev.evaluation_id}
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <div className="flex items-center gap-2.5">
                                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-[10px] flex items-center justify-center shrink-0">
                                        {candidateInitials}
                                      </div>
                                      <div>
                                        <p className="font-semibold text-white leading-tight">{rev.agent_name}</p>
                                        <p className="text-xs text-slate-400 font-normal">{rev.agent_email}</p>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <p className="font-semibold text-white">{rev.task_name}</p>
                                    <span className="text-[10px] text-slate-500 font-mono">Task #{rev.task_id}</span>
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getCompetencyBadgeStyle(rev.predicted_competency)}`}>
                                      {rev.predicted_competency || '—'}
                                    </span>
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${
                                      rev.eligibility_status === 'ELIGIBLE' 
                                        ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                                        : rev.eligibility_status === 'PENDING_REVIEW'
                                        ? 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                                        : 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                                    }`}>
                                      {rev.eligibility_status}
                                    </span>
                                  </td>
                                  <td className="py-3.5 px-4">
                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getReviewStatusBadgeStyle(rev.review_status)}`}>
                                      {rev.review_status}
                                    </span>
                                  </td>
                                  <td className="py-3.5 px-4 text-xs text-slate-400">
                                    {rev.evaluated_at ? new Date(rev.evaluated_at).toLocaleString() : '—'}
                                  </td>
                                  <td className="py-3.5 px-4 text-right">
                                    <button
                                      type="button"
                                      onClick={() => openReviewDetailModal(rev)}
                                      className="px-3 py-1.5 rounded-xl bg-[#151f38] hover:bg-[#1c294d] text-indigo-300 hover:text-white border border-[#23315c] text-xs font-semibold cursor-pointer transition-all"
                                    >
                                      Inspect Review
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
                        <ShieldCheck className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                        <p className="text-base font-bold font-sora text-white">No eligibility reviews recorded</p>
                        <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-md mx-auto">
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
                      <h2 className="text-xl font-bold font-sora text-white tracking-tight">Profile Verifications</h2>
                      <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                        Audit and approve candidate submitted certifications and employment tenure records. Verified entries directly populate the feature vector for ML suitability inference.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30">
                        {pendingVerificationsCount} Total Pending
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchData()}
                        className="border-[#2b3a67] bg-[#0d1428] text-slate-200 hover:bg-[#151f38] hover:text-white"
                      >
                        <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                        Refresh Queue
                      </Button>
                    </div>
                  </div>

                  {/* Section 1: Pending Certifications */}
                  <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] shadow-xl overflow-hidden">
                    <div className="px-6 py-4 border-b border-[#1b2542] flex items-center justify-between bg-[#080d1a]">
                      <div className="flex items-center gap-2">
                        <Award className="w-4 h-4 text-cyan-400" />
                        <h3 className="text-sm font-bold font-sora text-white">
                          Pending Professional Certifications
                        </h3>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-[#151f38] text-slate-300 border border-[#26355d]">
                          {verificationsData.certifications?.length || 0}
                        </span>
                      </div>
                    </div>

                    {verificationsData.certifications && verificationsData.certifications.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-[#080d1a] border-b border-[#1b2542] text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Agent</th>
                              <th className="py-3.5 px-4 font-semibold">Certification Name</th>
                              <th className="py-3.5 px-4 font-semibold">Issuing Org</th>
                              <th className="py-3.5 px-4 font-semibold">Credential ID / URL</th>
                              <th className="py-3.5 px-4 font-semibold">Issue / Expiry Date</th>
                              <th className="py-3.5 px-4 font-semibold">Submitted</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1b2542]/60 text-slate-300">
                            {verificationsData.certifications.map((c) => (
                              <tr key={c.agent_cert_id} className="hover:bg-[#121a36]/40 transition-colors">
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold font-sora text-white leading-tight">{c.agent_name}</p>
                                  <p className="text-xs text-slate-400 font-normal">{c.agent_email}</p>
                                </td>
                                <td className="py-3.5 px-4 font-semibold text-slate-200">
                                  {c.certification_name}
                                </td>
                                <td className="py-3.5 px-4 text-slate-300">
                                  {c.issuing_organization || '—'}
                                </td>
                                <td className="py-3.5 px-4">
                                  {c.certificate_number && (
                                    <p className="font-mono text-xs text-indigo-300">{c.certificate_number}</p>
                                  )}
                                  {c.credential_url ? (
                                    <a
                                      href={c.credential_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 hover:underline mt-0.5"
                                    >
                                      <span>Verify Link</span>
                                      <ExternalLink className="w-3 h-3" />
                                    </a>
                                  ) : (
                                    <span className="text-xs text-slate-500">No link provided</span>
                                  )}
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-300">
                                  <span>{c.issue_date}</span>
                                  {c.expiry_date ? <span> &rarr; {c.expiry_date}</span> : <span className="text-slate-500"> (No Expiry)</span>}
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-400">
                                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <Button
                                      size="sm"
                                      className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium border border-emerald-500/40 shadow-sm"
                                      disabled={isReviewingAction}
                                      onClick={() => handleApproveCertification(c.agent_cert_id)}
                                    >
                                      Approve
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-xs text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 border border-transparent hover:border-rose-500/30"
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
                      <div className="p-8 text-center text-slate-400 bg-[#0b1020]">
                        <Award className="w-6 h-6 text-slate-500 mx-auto mb-2" />
                        <p className="text-sm font-semibold font-sora text-slate-200">No pending certifications</p>
                        <p className="text-xs text-slate-400 mt-0.5">All candidate submitted credentials have been audited.</p>
                      </div>
                    )}
                  </div>

                  {/* Section 2: Pending Work Experience */}
                  <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] shadow-xl overflow-hidden">
                    <div className="px-6 py-4 border-b border-[#1b2542] flex items-center justify-between bg-[#080d1a]">
                      <div className="flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-cyan-400" />
                        <h3 className="text-sm font-bold font-sora text-white">
                          Pending Work Experience Tenures
                        </h3>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-[#151f38] text-slate-300 border border-[#26355d]">
                          {verificationsData.experiences?.length || 0}
                        </span>
                      </div>
                    </div>

                    {verificationsData.experiences && verificationsData.experiences.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs sm:text-sm">
                          <thead>
                            <tr className="bg-[#080d1a] border-b border-[#1b2542] text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              <th className="py-3.5 px-4 font-semibold">Agent</th>
                              <th className="py-3.5 px-4 font-semibold">Role &amp; Company</th>
                              <th className="py-3.5 px-4 font-semibold">Category</th>
                              <th className="py-3.5 px-4 font-semibold">Tenure Period</th>
                              <th className="py-3.5 px-4 font-semibold">Supervisor Reference</th>
                              <th className="py-3.5 px-4 font-semibold">Submitted</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1b2542]/60 text-slate-300">
                            {verificationsData.experiences.map((exp) => (
                              <tr key={exp.experience_id} className="hover:bg-[#121a36]/40 transition-colors">
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold font-sora text-white leading-tight">{exp.agent_name}</p>
                                  <p className="text-xs text-slate-400 font-normal">{exp.agent_email}</p>
                                </td>
                                <td className="py-3.5 px-4">
                                  <p className="font-semibold font-sora text-white leading-tight">{exp.job_title}</p>
                                  <p className="text-xs text-slate-400 font-normal">{exp.company}</p>
                                </td>
                                <td className="py-3.5 px-4">
                                  <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
                                    {exp.work_category}
                                  </span>
                                </td>
                                <td className="py-3.5 px-4 text-xs text-slate-300">
                                  <span>{exp.start_date} &rarr; {exp.is_current ? 'Present' : (exp.end_date || 'Ongoing')}</span>
                                </td>
                                <td className="py-3.5 px-4 max-w-xs text-xs">
                                  {(exp.supervisor_name || exp.supervisor_email || exp.supervisor_phone) ? (
                                    <div className="p-3 rounded-xl bg-[#0d1428] border border-[#1e2a4a] space-y-1.5 shadow-sm">
                                      <div className="flex items-center gap-1.5 font-bold text-slate-200">
                                        <UserCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                                        <span className="truncate">{exp.supervisor_name || 'Former Employer / Manager'}</span>
                                      </div>

                                      {exp.supervisor_email && (
                                        <div className="flex items-center gap-1.5">
                                          <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                          <a 
                                            href={`mailto:${exp.supervisor_email}?subject=VerifyMesh%20Employment%20Verification%20for%20${encodeURIComponent(exp.agent_name || 'Candidate')}&body=Dear%20${encodeURIComponent(exp.supervisor_name || 'Manager')},%0D%0A%0D%0AWe%20are%20verifying%20prior%20employment%20for%20${encodeURIComponent(exp.agent_name || 'the candidate')}%20as%20${encodeURIComponent(exp.job_title)}%20at%20${encodeURIComponent(exp.company)}.%20Could%20you%20please%20confirm%20if%20their%20tenure%20is%20accurate?%0D%0A%0D%0AThank%20you,%0D%0AVerifyMesh%20Administration`}
                                            className="text-xs text-cyan-400 hover:text-cyan-300 hover:underline font-medium truncate"
                                            title="Click to send verification email"
                                          >
                                            {exp.supervisor_email}
                                          </a>
                                        </div>
                                      )}

                                      {exp.supervisor_phone && (
                                        <div className="flex items-center gap-1.5">
                                          <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                                          <a 
                                            href={`tel:${exp.supervisor_phone}`}
                                            className="text-xs text-slate-200 hover:text-white font-medium"
                                            title="Click to call supervisor"
                                          >
                                            {exp.supervisor_phone}
                                          </a>
                                        </div>
                                      )}

                                      <div className="pt-1 border-t border-[#1e2a4a] text-[10px] text-slate-400 italic">
                                        Contact former employer to verify tenure, then Approve or Reject below.
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="p-2 rounded-lg bg-[#0d1428]/60 border border-dashed border-[#1e2a4a] text-slate-500 italic text-[11px]">
                                      No supervisor contact details provided
                                    </div>
                                  )}
                                </td>

                                <td className="py-3.5 px-4 text-xs text-slate-400">
                                  {exp.submitted_at ? new Date(exp.submitted_at).toLocaleDateString() : '—'}
                                </td>
                                <td className="py-3.5 px-4 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <Button
                                      size="sm"
                                      className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium border border-emerald-500/40 shadow-sm"
                                      disabled={isReviewingAction}
                                      onClick={() => handleApproveExperience(exp.experience_id)}
                                    >
                                      Approve
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-xs text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 border border-transparent hover:border-rose-500/30"
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
                      <div className="p-8 text-center text-slate-400 bg-[#0b1020]">
                        <Briefcase className="w-6 h-6 text-slate-500 mx-auto mb-2" />
                        <p className="text-sm font-semibold font-sora text-slate-200">No pending work experience entries</p>
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
      {/* MODAL: INSPECT AGENT PROFILE & VERIFICATION DOSSIER */}
      {/* ================================================================= */}
      {isAgentModalOpen && selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div
            className="w-full max-w-3xl max-h-[90vh] bg-[#0b1020] rounded-2xl shadow-2xl border border-[#202e52] flex flex-col overflow-hidden transition-all text-[#e8ebf7]"
            role="dialog"
            aria-modal="true"
          >
            {/* Header */}
            <div className="p-5 sm:p-6 border-b border-[#1b2542] flex items-center justify-between bg-[#0d1428]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-sm flex items-center justify-center shrink-0 shadow-md">
                  {selectedAgent.full_name
                    ? selectedAgent.full_name.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
                    : 'AG'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold font-sora text-white">{selectedAgent.full_name}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                      selectedAgent.status === 'ACTIVE'
                        ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                        : 'bg-slate-900/70 text-slate-400 border-slate-700/50'
                    }`}>
                      {selectedAgent.status || 'ACTIVE'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{selectedAgent.email} &bull; Agent ID: #{selectedAgent.agent_id}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsAgentModalOpen(false);
                  setSelectedAgent(null);
                  setSelectedAgentProfile(null);
                }}
                className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer"
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Tabs Bar */}
            <div className="px-6 pt-2 border-b border-[#1b2542] flex items-center gap-2 bg-[#0d1428]/60 text-xs overflow-x-auto">
              {[
                { id: 'overview', label: 'Overview & Contact' },
                { 
                  id: 'experience', 
                  label: 'Verified Experience', 
                  count: selectedAgentProfile?.verified_experience?.verified_entries_count ?? selectedAgent?.verified_experiences_count ?? 0 
                },
                { 
                  id: 'certifications', 
                  label: 'Certifications', 
                  count: selectedAgentProfile?.verified_certifications?.verified_entries_count ?? selectedAgent?.verified_certifications_count ?? 0 
                },
                { id: 'assessments', label: 'Assessments & ML Fit' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setAgentModalTab(tab.id)}
                  className={`pb-2.5 pt-1.5 px-3 font-semibold transition-all cursor-pointer border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    agentModalTab === tab.id
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>{tab.label}</span>
                  {tab.count !== undefined && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-[#15203d] text-slate-300 border border-[#2b3a67]">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-300 flex-1">
              {isLoadingAgentProfile ? (
                <div className="py-12 text-center">
                  <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2.5" />
                  <p className="text-xs text-slate-400">Loading agent dossier and credential records...</p>
                </div>
              ) : (
                <>
                  {/* TAB 1: OVERVIEW & CONTACT */}
                  {agentModalTab === 'overview' && (
                    <div className="space-y-4">
                      {/* 4 Quick Metrics */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="p-3 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Status</span>
                          <span className="font-semibold text-white mt-0.5 block">{selectedAgent.status || 'ACTIVE'}</span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Availability</span>
                          <span className="font-semibold text-white mt-0.5 block">{selectedAgent.availability_status || 'AVAILABLE'}</span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Tenure Months</span>
                          <span className="font-semibold text-white mt-0.5 block">{selectedAgent.experience_months || 0} months</span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Assessments</span>
                          <span className="font-semibold text-white mt-0.5 block">{selectedAgent.total_attempts || 0} total</span>
                        </div>
                      </div>

                      {/* Contact & Location Details */}
                      <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1b2542] space-y-3">
                        <h4 className="text-xs font-bold font-sora text-white uppercase tracking-wider">Contact Information</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div>
                            <span className="text-[10px] text-slate-400 block font-semibold">Email Address</span>
                            <span className="text-xs text-white">{selectedAgent.email}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-semibold">Phone Number</span>
                            <span className="text-xs text-white">{selectedAgentProfile?.phone || selectedAgent.phone || 'None recorded'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-semibold">Location</span>
                            <span className="text-xs text-white">{selectedAgentProfile?.location || 'Not specified'}</span>
                          </div>
                        </div>
                      </div>

                      {/* Bio & Professional Summary */}
                      <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1b2542]">
                        <h4 className="text-xs font-bold font-sora text-white uppercase tracking-wider mb-1.5">Professional Background</h4>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {selectedAgentProfile?.bio || selectedAgent.education || 'No detailed background provided.'}
                        </p>
                      </div>

                      {/* Profile Readiness & Governance */}
                      {selectedAgentProfile?.readiness && (
                        <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-indigo-300">Profile Readiness Score</span>
                            <span className="text-xs font-bold text-white">{selectedAgentProfile.readiness.readiness_percentage}% Complete</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-[#12192e] overflow-hidden">
                            <div 
                              className="bg-indigo-500 h-full transition-all duration-500"
                              style={{ width: `${selectedAgentProfile.readiness.readiness_percentage}%` }}
                            />
                          </div>
                          <div className="grid grid-cols-3 gap-2 mt-3 text-[11px]">
                            <div className="flex items-center gap-1.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${selectedAgentProfile.readiness.checks?.personal_info ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                              <span className="text-slate-400">Personal Info</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${selectedAgentProfile.readiness.checks?.experience ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                              <span className="text-slate-400">Experience</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${selectedAgentProfile.readiness.checks?.certifications ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                              <span className="text-slate-400">Certifications</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 2: VERIFIED EXPERIENCE */}
                  {agentModalTab === 'experience' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between pb-2">
                        <span className="text-xs font-bold text-white uppercase tracking-wider">
                          Work Experience Records ({selectedAgentProfile?.verified_experience?.verified_entries?.length || 0})
                        </span>
                        <span className="text-[11px] text-slate-400">
                          Total Verified: {selectedAgentProfile?.verified_experience?.total_verified_months || 0} months
                        </span>
                      </div>

                      {selectedAgentProfile?.verified_experience?.verified_entries?.length > 0 ? (
                        <div className="space-y-3">
                          {selectedAgentProfile.verified_experience.verified_entries.map((exp, idx) => (
                            <div key={exp.experience_id || idx} className="p-4 rounded-xl bg-[#0d1428] border border-[#1b2542] space-y-2">
                              <div className="flex items-start justify-between">
                                <div>
                                  <h4 className="text-sm font-bold text-white">{exp.job_title}</h4>
                                  <p className="text-xs text-indigo-400 font-medium">{exp.company} &bull; {exp.work_category}</p>
                                </div>
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                                  exp.verification_status === 'VERIFIED'
                                    ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                                    : 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                                }`}>
                                  {exp.verification_status}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-400">
                                {exp.start_date} &rarr; {exp.is_current ? 'Present' : exp.end_date}
                              </p>
                              {exp.description && (
                                <p className="text-xs text-slate-300 leading-relaxed pt-1">
                                  {exp.description}
                                </p>
                              )}
                              {exp.supervisor_name && (
                                <div className="pt-2 border-t border-[#1b2542] text-[11px] text-slate-400 flex items-center gap-3">
                                  <span>Supervisor: <strong className="text-slate-300">{exp.supervisor_name}</strong></span>
                                  {exp.supervisor_email && <span>({exp.supervisor_email})</span>}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="py-10 text-center bg-[#0d1428] rounded-xl border border-[#1b2542]">
                          <Briefcase className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                          <p className="text-xs font-semibold text-slate-300">No work experience records logged</p>
                          <p className="text-[11px] text-slate-500 mt-0.5">Candidate has not yet submitted employment tenure entries.</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 3: CERTIFICATIONS */}
                  {agentModalTab === 'certifications' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between pb-2">
                        <span className="text-xs font-bold text-white uppercase tracking-wider">
                          Professional Certifications ({selectedAgentProfile?.verified_certifications?.verified_entries?.length || 0})
                        </span>
                      </div>

                      {selectedAgentProfile?.verified_certifications?.verified_entries?.length > 0 ? (
                        <div className="space-y-3">
                          {selectedAgentProfile.verified_certifications.verified_entries.map((cert, idx) => (
                            <div key={cert.agent_certification_id || idx} className="p-4 rounded-xl bg-[#0d1428] border border-[#1b2542] space-y-2">
                              <div className="flex items-start justify-between">
                                <div>
                                  <h4 className="text-sm font-bold text-white">{cert.certification_name || 'Certification'}</h4>
                                  <p className="text-xs text-indigo-400 font-medium">{cert.issuing_organization || 'Issuing Authority'}</p>
                                </div>
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                                  cert.status === 'VERIFIED'
                                    ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                                    : 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                                }`}>
                                  {cert.status}
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-400 grid grid-cols-2 gap-2">
                                <span>Certificate #: <strong className="text-slate-300">{cert.certificate_number}</strong></span>
                                <span>Issued: {cert.issue_date}</span>
                              </div>
                              {cert.credential_url && (
                                <div className="pt-2 border-t border-[#1b2542]">
                                  <a 
                                    href={cert.credential_url} 
                                    target="_blank" 
                                    rel="noreferrer"
                                    className="text-indigo-400 hover:text-indigo-300 text-xs inline-flex items-center gap-1"
                                  >
                                    <span>Verify Credential Link</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="py-10 text-center bg-[#0d1428] rounded-xl border border-[#1b2542]">
                          <Award className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                          <p className="text-xs font-semibold text-slate-300">No certifications recorded</p>
                          <p className="text-[11px] text-slate-500 mt-0.5">Candidate has not yet submitted verified certifications.</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 4: ASSESSMENTS & ML FIT */}
                  {agentModalTab === 'assessments' && (
                    <div className="space-y-4">
                      {/* Overall Assessment Score & Competency */}
                      <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1b2542] flex items-center justify-between">
                        <div>
                          <span className="text-[10px] text-slate-400 uppercase font-bold">Competency Classification</span>
                          <div className="mt-1 flex items-center gap-2">
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getCompetencyBadgeStyle(selectedAgent.predicted_competency)}`}>
                              {selectedAgent.predicted_competency || 'Unassessed'}
                            </span>
                            {selectedAgent.confidence_percent && (
                              <span className="text-xs text-slate-400 font-mono">
                                ({selectedAgent.confidence_percent}% confidence)
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 uppercase font-bold">Latest Score</span>
                          <p className="text-xl font-bold font-sora text-white">
                            {selectedAgent.assessment_score != null ? `${selectedAgent.assessment_score}%` : 'N/A'}
                          </p>
                        </div>
                      </div>

                      {/* Sub-skill Breakdown */}
                      {selectedAgentProfile?.assessment_summary?.scores && (
                        <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1b2542] space-y-3">
                          <h4 className="text-xs font-bold font-sora text-white uppercase tracking-wider">Sub-Competency Breakdown</h4>
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div className="p-2.5 rounded-lg bg-[#0b1020] border border-[#1e2a4a]">
                              <span className="text-slate-400 block text-[10px]">Communication</span>
                              <span className="font-bold text-white text-sm">
                                {selectedAgentProfile.assessment_summary.scores.communication ?? '—'}%
                              </span>
                            </div>
                            <div className="p-2.5 rounded-lg bg-[#0b1020] border border-[#1e2a4a]">
                              <span className="text-slate-400 block text-[10px]">Product Knowledge</span>
                              <span className="font-bold text-white text-sm">
                                {selectedAgentProfile.assessment_summary.scores.product_knowledge ?? '—'}%
                              </span>
                            </div>
                            <div className="p-2.5 rounded-lg bg-[#0b1020] border border-[#1e2a4a]">
                              <span className="text-slate-400 block text-[10px]">Sales Outreach</span>
                              <span className="font-bold text-white text-sm">
                                {selectedAgentProfile.assessment_summary.scores.sales_skill ?? '—'}%
                              </span>
                            </div>
                            <div className="p-2.5 rounded-lg bg-[#0b1020] border border-[#1e2a4a]">
                              <span className="text-slate-400 block text-[10px]">Customer Service</span>
                              <span className="font-bold text-white text-sm">
                                {selectedAgentProfile.assessment_summary.scores.customer_service ?? '—'}%
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-[#1b2542] flex items-center justify-between bg-[#0d1428]">
              <span className="text-xs text-slate-500">
                VerifyMesh Talent Dossier &bull; Officer Inspection Mode
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsAgentModalOpen(false);
                  setSelectedAgent(null);
                  setSelectedAgentProfile(null);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#12192e] text-slate-300 hover:text-white hover:bg-[#1a2542] border border-[#2b3a67] transition-all cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* MODAL: INSPECT ASSESSMENT FEATURES */}
      {/* ================================================================= */}
      {isAssessmentModalOpen && selectedAssessment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-xl bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 text-white shadow-2xl relative space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-[#1b2542]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                    EVALUATION DOSSIER #{selectedAssessment.exam_result_id}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getCompetencyBadgeStyle(selectedAssessment.predicted_competency)}`}>
                    {selectedAssessment.predicted_competency}
                  </span>
                </div>
                <h3 className="text-base font-bold font-sora text-white mt-1">
                  {selectedAssessment.agent_name}
                </h3>
                <p className="text-xs text-slate-400">
                  Attempt #{selectedAssessment.attempt_number} &bull; {selectedAssessment.completed_at ? new Date(selectedAssessment.completed_at).toLocaleString() : 'Date pending'}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsAssessmentModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Assessment Battery & Score Card */}
            <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1e2a4a] space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    {selectedAssessment.category_name || 'General Domain'}
                  </span>
                  <h4 className="text-sm font-bold text-white mt-0.5">
                    {selectedAssessment.exam_name || 'Standard Competency Assessment Battery'}
                  </h4>
                </div>
                <div className="text-right shrink-0">
                  <div className="flex items-center gap-1.5 justify-end">
                    <span className="text-lg font-bold font-mono text-white">
                      {selectedAssessment.assessment_score}%
                    </span>
                    {(selectedAssessment.passed === 1 || selectedAssessment.passed === true || (selectedAssessment.assessment_score >= (selectedAssessment.passing_score || 70))) ? (
                      <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                        Passed
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold text-rose-400 bg-rose-950/60 border border-rose-500/40 px-2 py-0.5 rounded-full">
                        Failed
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 block mt-0.5">
                    Passing Threshold: &ge;{selectedAssessment.passing_score || 70}%
                  </span>
                </div>
              </div>
            </div>

            {/* Feature Inputs for Inference */}
            <div>
              <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                Model Input Feature Vector
              </h5>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Exam Score</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.assessment_score ?? selectedAssessment.assessment_score}%
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Communication</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.communication_score != null ? `${selectedAssessment.features.communication_score}%` : '—'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Product Knowl.</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.product_knowledge_score != null ? `${selectedAssessment.features.product_knowledge_score}%` : '—'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Sales Skill</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.sales_skill_score != null ? `${selectedAssessment.features.sales_skill_score}%` : '—'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Customer Serv.</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.customer_service_score != null ? `${selectedAssessment.features.customer_service_score}%` : '—'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Total Exp.</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.previous_experience_months != null ? `${selectedAssessment.features.previous_experience_months} mos` : '—'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Sales Exp.</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.sales_experience_months != null ? `${selectedAssessment.features.sales_experience_months} mos` : '—'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a]">
                  <span className="text-[10px] text-slate-400 block font-medium">Verified Certs</span>
                  <span className="font-bold text-white mt-0.5 block font-mono">
                    {selectedAssessment.features?.certification_count ?? 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Inference Confidence */}
            <div className="p-3.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white block">AI Competency Confidence</span>
                <span className="text-[11px] text-slate-400">Random Forest binary classifier probability distribution</span>
              </div>
              <span className="text-sm font-mono font-bold text-indigo-400">
                {selectedAssessment.confidence_percent ? `${selectedAssessment.confidence_percent}%` : '—'}
              </span>
            </div>

            {/* Actions */}
            <div className="pt-2 flex justify-end border-t border-[#1b2542]">
              <button
                type="button"
                onClick={() => setIsAssessmentModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#151f38] hover:bg-[#1c294d] text-white border border-[#2b3a67] transition-all cursor-pointer"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* MODAL: INSPECT ELIGIBILITY REVIEW */}
      {/* ================================================================= */}
      {isReviewModalOpen && selectedReview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-xl bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 text-white shadow-2xl relative space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-[#1b2542]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                    ELIGIBILITY EVALUATION #{selectedReview.evaluation_id}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getReviewStatusBadgeStyle(selectedReview.review_status)}`}>
                    {selectedReview.review_status}
                  </span>
                </div>
                <h3 className="text-base font-bold font-sora text-white mt-1">
                  {selectedReview.agent_name}
                </h3>
                <p className="text-xs text-slate-400">
                  Target Role: <strong className="text-slate-200">{selectedReview.task_name}</strong> &bull; {selectedReview.evaluated_at ? new Date(selectedReview.evaluated_at).toLocaleString() : ''}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsReviewModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {isLoadingReviewDetail ? (
              <div className="py-8 text-center">
                <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-400">Loading evaluation checks...</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* System Evaluation Summary Card */}
                <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1e2a4a] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      Automated Evaluation Verdict
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                      selectedReview.eligibility_status === 'ELIGIBLE' 
                        ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                        : selectedReview.eligibility_status === 'PENDING_REVIEW'
                        ? 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                        : 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                    }`}>
                      {selectedReview.eligibility_status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {selectedReview.explanation || 'Automated deterministic rule evaluation executed across candidate credentials and assessment history.'}
                  </p>
                </div>

                {/* Individual Requirement Checks Breakdown */}
                {reviewDetail?.checks?.length > 0 && (
                  <div>
                    <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                      Deterministic Qualification Checks
                    </h5>
                    <div className="space-y-2">
                      {reviewDetail.checks.map((chk) => (
                        <div key={chk.check_id} className="p-3 rounded-xl bg-[#0d1428] border border-[#1e2a4a] flex items-center justify-between text-xs">
                          <div>
                            <span className="font-semibold text-white block">{chk.requirement_type}</span>
                            <span className="text-slate-400 block text-[11px] mt-0.5">
                              Expected: <strong className="text-slate-300">{chk.expected_value}</strong> &bull; Actual: <strong className="text-slate-300">{chk.actual_value || 'None'}</strong>
                            </span>
                            {chk.failure_reason && (
                              <span className="text-[10px] text-rose-400 block mt-1">
                                &bull; {chk.failure_reason}
                              </span>
                            )}
                          </div>
                          <span className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border ${
                            chk.passed 
                              ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40' 
                              : 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                          }`}>
                            {chk.passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Human-in-the-Loop Review Actions */}
                {selectedReview.review_status === 'PENDING' ? (
                  <div className="p-4 rounded-xl bg-[#0d1428] border border-indigo-500/30 space-y-3">
                    <span className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider block">
                      Workforce Officer Decision
                    </span>
                    <textarea
                      rows={2}
                      value={reviewActionComment}
                      onChange={(e) => setReviewActionComment(e.target.value)}
                      placeholder="Add compliance notes or justification for this eligibility decision (optional)..."
                      className="w-full px-3 py-2 rounded-xl bg-[#080d1a] border border-[#1e2a4a] text-white placeholder:text-slate-500 text-xs focus:outline-none focus:border-indigo-500 transition-all"
                    />
                    <div className="flex items-center justify-end gap-2.5 pt-1">
                      <button
                        type="button"
                        disabled={isSubmittingReviewDecision}
                        onClick={() => handleReviewDecisionSubmit('REJECTED')}
                        className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-md disabled:opacity-50 cursor-pointer transition-all flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Reject Eligibility
                      </button>
                      <button
                        type="button"
                        disabled={isSubmittingReviewDecision}
                        onClick={() => handleReviewDecisionSubmit('APPROVED')}
                        className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-600 to-teal-500 hover:brightness-110 text-white shadow-md disabled:opacity-50 cursor-pointer transition-all flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Approve Eligibility
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-xs space-y-1">
                    <span className="text-[10px] text-slate-400 block uppercase font-bold">Officer Review Record</span>
                    <p className="text-slate-300">
                      Decided as <strong className="text-white font-semibold">{selectedReview.review_status}</strong>
                      {selectedReview.reviewer_name ? ` by ${selectedReview.reviewer_name}` : ''}
                      {selectedReview.reviewed_at ? ` on ${new Date(selectedReview.reviewed_at).toLocaleString()}` : ''}.
                    </p>
                    {selectedReview.review_comments && (
                      <p className="text-slate-400 italic text-[11px] mt-1">
                        &quot;{selectedReview.review_comments}&quot;
                      </p>
                    )}
                  </div>
                )}

                {/* Footer Close Button */}
                <div className="pt-2 flex justify-end border-t border-[#1b2542]">
                  <button
                    type="button"
                    onClick={() => setIsReviewModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#151f38] hover:bg-[#1c294d] text-white border border-[#2b3a67] transition-all cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* MODAL: REJECT VERIFICATION SUBMISSION */}
      {/* ================================================================= */}
      {rejectionModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div
            className="w-full max-w-md bg-[#0b1020] rounded-2xl shadow-2xl border border-[#202e52] p-6 text-[#e8ebf7] relative space-y-4"
            role="dialog"
            aria-modal="true"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold font-sora text-white">Reject Verification Request</h3>
              </div>
              <button
                type="button"
                onClick={() => setRejectionModal({ isOpen: false, type: null, id: null, title: '', reason: '' })}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-[#151f38] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs sm:text-sm text-slate-300">
              <p className="text-xs text-slate-300">
                You are rejecting verification for: <strong className="text-white font-semibold">{rejectionModal.title}</strong>.
              </p>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Rejection Reason <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={3}
                  value={rejectionModal.reason}
                  onChange={(e) => setRejectionModal({ ...rejectionModal, reason: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[#080d1a] border border-[#1b2542] text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
                  placeholder="Explain why this credential or experience claim was rejected (e.g. invalid credential ID, unverified employer, expired certificate)..."
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRejectionModal({ isOpen: false, type: null, id: null, title: '', reason: '' })}
                  className="text-slate-400 hover:text-white hover:bg-[#151f38]"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  className="bg-rose-600 hover:bg-rose-700 text-white font-medium border border-rose-500/30"
                  disabled={isReviewingAction || !rejectionModal.reason?.trim()}
                  onClick={handleSubmitRejection}
                >
                  {isReviewingAction ? 'Submitting...' : 'Confirm Rejection'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: DELETE TASK CONFIRMATION */}
      {/* ========================================================= */}
      {isDeleteModalOpen && taskToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div
            className="w-full max-w-md bg-[#0b1020] rounded-2xl shadow-2xl border border-[#202e52] p-6 text-[#e8ebf7]"
            role="dialog"
            aria-modal="true"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-950/70 text-rose-400 flex items-center justify-center shrink-0 border border-rose-500/30">
                <AlertCircle className="w-5 h-5" />
              </div>
              <div>
                <p className="font-bold text-white text-sm font-sora">
                  Permanently delete &ldquo;{taskToDelete?.task_name}&rdquo;?
                </p>
                <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                  This action cannot be undone. The task, its prerequisites, assessment topic links, and candidate applications will be permanently removed.
                </p>
              </div>
            </div>

            <div className="pt-4 mt-4 flex items-center justify-end gap-2.5 border-t border-[#1b2542]">
              <button
                type="button"
                onClick={() => {
                  setIsDeleteModalOpen(false);
                  setTaskToDelete(null);
                }}
                disabled={isDeletingTask}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#12192e] text-slate-300 hover:text-white border border-[#2b3a67] transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteTask}
                disabled={isDeletingTask}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-900/30 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isDeletingTask ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: TASK APPLICANTS & ASSIGNMENT */}
      {/* ========================================================= */}
      {isApplicantsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div
            className="w-full max-w-4xl max-h-[90vh] bg-[#0b1020] rounded-2xl shadow-2xl border border-[#202e52] flex flex-col overflow-hidden transition-all text-[#e8ebf7]"
            role="dialog"
            aria-modal="true"
          >
            {/* Header */}
            <div className="p-5 sm:p-6 border-b border-[#1b2542] flex items-center justify-between bg-[#0d1428]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/70 text-indigo-300 border border-indigo-500/30">
                    {selectedTaskForApplicants?.category_name || 'General'}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getCompetencyBadgeStyle(selectedTaskForApplicants?.minimum_competency)}`}>
                    Min. {selectedTaskForApplicants?.minimum_competency || 'ELIGIBLE'}
                  </span>
                </div>
                <h3 className="text-base sm:text-lg font-bold font-sora text-white mt-1">
                  Applicants for &ldquo;{selectedTaskForApplicants?.task_name}&rdquo;
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Review applicant Stage 1 prerequisite compliance, Stage 2 advisory fit, and authoritatively assign candidates.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsApplicantsModalOpen(false);
                  setSelectedTaskForApplicants(null);
                  setTaskApplicants([]);
                }}
                className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer"
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content Body */}
            <div className="p-5 sm:p-6 overflow-y-auto flex-1 space-y-4">
              {isLoadingApplicants ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-xs font-medium text-slate-400">Loading candidate applicants...</p>
                </div>
              ) : taskApplicants.length === 0 ? (
                <div className="py-12 text-center bg-[#0d1428] rounded-xl border border-dashed border-[#1b2542] p-8">
                  <Users className="w-10 h-10 text-slate-600 mx-auto mb-2.5" />
                  <p className="text-sm font-semibold text-white">No Applications Yet</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    No agents have submitted an application for this task yet. Applications appear here as soon as eligible candidates apply.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {taskApplicants.map((app) => {
                    const isAssigned = app.status === 'Assigned';
                    const isShortlisted = app.status === 'Shortlisted';
                    const isRejected = app.status === 'Rejected';

                    return (
                      <div
                        key={app.application_id}
                        className={`p-5 rounded-xl border transition-all ${
                          isAssigned
                            ? 'bg-emerald-950/30 border-emerald-500/40'
                            : isShortlisted
                            ? 'bg-blue-950/30 border-blue-500/40'
                            : isRejected
                            ? 'bg-rose-950/20 border-rose-900/40 opacity-75'
                            : 'bg-[#0d1428] border-[#1b2542] hover:border-[#2b3a67]'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#1b2542]">
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm sm:text-base font-bold text-white font-sora">{app.full_name}</h4>
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                                  isAssigned
                                    ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                                    : isShortlisted
                                    ? 'bg-blue-950/70 text-blue-300 border-blue-500/40'
                                    : isRejected
                                    ? 'bg-rose-950/70 text-rose-300 border-rose-500/40'
                                    : 'bg-slate-900/70 text-slate-400 border-slate-700/50'
                                }`}
                              >
                                {app.status}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-slate-400 mt-1 flex-wrap">
                              <span className="flex items-center gap-1">
                                <Mail className="w-3.5 h-3.5 text-slate-500" />
                                {app.email}
                              </span>
                              {app.phone && (
                                <span className="flex items-center gap-1">
                                  <Phone className="w-3.5 h-3.5 text-slate-500" />
                                  {app.phone}
                                </span>
                              )}
                              <span className="flex items-center gap-1">
                                <Clock className="w-3.5 h-3.5 text-slate-500" />
                                Applied {new Date(app.applied_at).toLocaleDateString()}
                              </span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 shrink-0">
                            {!isAssigned && !isRejected && (
                              <>
                                {!isShortlisted && (
                                  <button
                                    type="button"
                                    onClick={() => handleUpdateApplicationStatus(app.application_id, 'Shortlisted')}
                                    disabled={isActionProcessing}
                                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#15203d] text-indigo-300 hover:text-white border border-[#2b3a67] transition-all cursor-pointer"
                                  >
                                    Shortlist
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleUpdateApplicationStatus(app.application_id, 'Rejected')}
                                  disabled={isActionProcessing}
                                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/40 text-rose-300 hover:text-white border border-rose-900/50 transition-all cursor-pointer"
                                >
                                  Reject
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleAssignTask(app.application_id)}
                                  disabled={isActionProcessing || !app.meets_prerequisites || selectedTaskForApplicants?.status === 'COMPLETED'}
                                  title={
                                    !app.meets_prerequisites
                                      ? 'Applicant does not satisfy all mandatory prerequisites'
                                      : selectedTaskForApplicants?.status === 'COMPLETED'
                                      ? 'Task is already completed/filled'
                                      : 'Assign this task to applicant'
                                  }
                                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-sm transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  <span>Assign Task</span>
                                </button>
                              </>
                            )}
                            {isAssigned && (
                              <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-300 bg-emerald-950/70 px-3 py-1 rounded-lg border border-emerald-500/40">
                                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                Assigned Agent
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Candidate Notes */}
                        {app.notes && (
                          <div className="mt-3 p-3 rounded-lg bg-[#070b14] border border-[#1b2542] text-xs text-slate-300">
                            <span className="font-semibold text-slate-400 block mb-0.5">Applicant Note:</span>
                            &ldquo;{app.notes}&rdquo;
                          </div>
                        )}

                        {/* Deterministic Prerequisites Breakdown */}
                        <div className="mt-3 pt-3 border-t border-[#1b2542] grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                          <div className="p-2.5 rounded-xl bg-[#070b14] border border-[#1b2542]">
                            <span className="text-[10px] text-slate-400 block font-medium">Stage 1 Gate</span>
                            <div className="flex items-center gap-1 mt-0.5">
                              {app.meets_prerequisites ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              ) : (
                                <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                              )}
                              <span className={`font-semibold ${app.meets_prerequisites ? 'text-emerald-300' : 'text-rose-300'}`}>
                                {app.meets_prerequisites ? 'Eligible' : 'Ineligible'}
                              </span>
                            </div>
                          </div>

                          <div className="p-2.5 rounded-xl bg-[#070b14] border border-[#1b2542]">
                            <span className="text-[10px] text-slate-400 block font-medium">Verified Experience</span>
                            <div className="flex items-center gap-1 mt-0.5">
                              {app.prerequisites?.exp_met ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              ) : (
                                <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                              )}
                              <span className="font-semibold text-white">{app.experience_months} mos</span>
                            </div>
                          </div>

                          <div className="p-2.5 rounded-xl bg-[#070b14] border border-[#1b2542]">
                            <span className="text-[10px] text-slate-400 block font-medium">Certifications</span>
                            <div className="flex items-center gap-1 mt-0.5">
                              {app.prerequisites?.cert_met ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              ) : (
                                <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                              )}
                              <span className="font-semibold text-white truncate" title={`${app.certifications?.length || 0} verified`}>
                                {app.certifications?.length ? `${app.certifications.length} verified` : 'None required'}
                              </span>
                            </div>
                          </div>

                          <div className="p-2.5 rounded-xl bg-[#070b14] border border-[#1b2542]">
                            <span className="text-[10px] text-slate-400 block font-medium">Assessment Score</span>
                            <div className="flex items-center gap-1 mt-0.5">
                              {app.prerequisites?.assessment_met ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              ) : (
                                <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                              )}
                              <span className="font-semibold text-white">
                                {app.latest_score !== null && app.latest_score !== undefined ? `${app.latest_score}%` : 'Not assessed'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Stage 1 Ineligible Notice — Explains why Stage 2 is not run */}
                        {!app.meets_prerequisites && (
                          <div className="mt-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 text-xs">
                              <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                              <div>
                                <span className="font-bold text-white">Ineligible — Stage 1 Gate Incomplete</span>
                                <p className="text-[11px] text-slate-400">
                                  Stage 2 suitability scoring is not executed for applicants who do not meet mandatory prerequisites.
                                </p>
                              </div>
                            </div>
                            <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-rose-950/70 text-rose-300 border border-rose-500/40 shrink-0">
                              Stage 2 Bypassed
                            </span>
                          </div>
                        )}

                        {/* Stage 2 Task Suitability Score (Advisory ML Scoring) */}
                        {app.meets_prerequisites && app.suitability_score !== null && app.suitability_score !== undefined && (
                          <div className="mt-3 p-3.5 rounded-xl bg-[#070b14] border border-indigo-500/30 flex flex-col gap-2.5">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="flex items-center gap-1.5 text-[11px] font-bold text-indigo-300 uppercase tracking-wide">
                                  <BrainCircuit className="w-3.5 h-3.5 text-indigo-400" />
                                  Stage 2 Advisory Fit
                                </span>
                                {app.eligible_rank && (
                                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-600 text-white shadow-xs">
                                    #{app.eligible_rank} Rank
                                  </span>
                                )}
                                <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-indigo-950 text-indigo-300 border border-indigo-500/30">
                                  Advisory
                                </span>
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                <div className={`px-2.5 py-1 rounded-xl text-xs font-bold border flex items-center gap-1.5 shadow-xs ${
                                  app.advisory_tier === 'Strong Fit' || app.advisory_tier_code === 'strong'
                                    ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                                    : app.advisory_tier === 'Moderate Fit' || app.advisory_tier_code === 'moderate'
                                    ? 'bg-blue-950/70 text-blue-300 border-blue-500/40'
                                    : 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                                }`}>
                                  <span className={`w-2 h-2 rounded-full ${
                                    app.advisory_tier === 'Strong Fit' || app.advisory_tier_code === 'strong'
                                      ? 'bg-emerald-400'
                                      : app.advisory_tier === 'Moderate Fit' || app.advisory_tier_code === 'moderate'
                                      ? 'bg-blue-400'
                                      : 'bg-amber-400'
                                  }`} />
                                  <span>{app.advisory_tier || app.suitability_label} ({app.suitability_percent}%)</span>
                                </div>
                              </div>
                            </div>

                            <p className="text-[11px] text-slate-400 leading-relaxed">
                              Fit Probability: <strong className="text-white">{app.suitability_percent}%</strong> &bull; Threshold: <strong className="text-white">&tau; = {app.applied_threshold || '0.60'}</strong> &bull; Model: <span className="font-mono text-indigo-300 text-[10px]">{app.model_traceability?.model_name || 'VerifyMesh_Stage2_Suitability_LR_v2'}</span>
                            </p>

                            {/* Factor Explanations */}
                            {Array.isArray(app.contributing_factors) && app.contributing_factors.length > 0 && (
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                {app.contributing_factors.map((factor, fIdx) => (
                                  <span
                                    key={fIdx}
                                    className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-md font-medium border ${
                                      factor.direction === 'positive'
                                        ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
                                        : factor.direction === 'negative'
                                        ? 'bg-rose-950/60 text-rose-300 border-rose-500/40'
                                        : 'bg-[#12192e] text-slate-300 border-[#2b3a67]'
                                    }`}
                                    title={factor.summary}
                                  >
                                    {factor.label}: {factor.value > 0 && factor.unit === 'pts' ? `+${factor.value}` : factor.value} {factor.unit}
                                  </span>
                                ))}
                              </div>
                            )}

                            <p className="text-[10px] text-slate-500 italic pt-0.5">
                              {app.suitability_disclaimer || 'Advisory Task Suitability Score: Workforce Officer retains final assignment authority.'}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-[#1b2542] bg-[#0d1428] flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">
                {taskApplicants.length} applicant{taskApplicants.length === 1 ? '' : 's'} on record
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsApplicantsModalOpen(false);
                  setSelectedTaskForApplicants(null);
                  setTaskApplicants([]);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#12192e] text-slate-300 hover:text-white border border-[#2b3a67] transition-all cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
