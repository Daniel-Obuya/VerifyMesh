import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  LayoutGrid, 
  User, 
  ListChecks, 
  Briefcase, 
  Award, 
  ShieldCheck, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Trash2, 
  ExternalLink, 
  Plus, 
  Edit3, 
  Save, 
  X, 
  ChevronDown, 
  LogOut, 
  Bell, 
  Sparkles, 
  Check, 
  Lock, 
  Building, 
  Calendar, 
  MapPin, 
  Phone, 
  Mail, 
  FileText,
  Info,
  Layers
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { competencyService } from '../services/competencyService';
import { Button } from '../components/ui/Button';
import { TakeAssessmentModal } from '../components/dashboard/TakeAssessmentModal';

export const ProfilePage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Navigation & Dropdown states
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isAssessmentModalOpen, setIsAssessmentModalOpen] = useState(false);

  // Core Data States
  const [isLoading, setIsLoading] = useState(true);
  const [profileData, setProfileData] = useState(null);
  const [experiences, setExperiences] = useState([]);
  const [certifications, setCertifications] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Edit Personal Info state
  const [isEditingPersonalInfo, setIsEditingPersonalInfo] = useState(false);
  const [personalForm, setPersonalForm] = useState({
    full_name: '',
    phone: '',
    location: '',
    bio: ''
  });
  const [isSavingPersonal, setIsSavingPersonal] = useState(false);

  // Add Experience Modal state
  const [isAddExpOpen, setIsAddExpOpen] = useState(false);
  const [isSavingExp, setIsSavingExp] = useState(false);
  const [expForm, setExpForm] = useState({
    job_title: '',
    company: '',
    work_category: 'Sales',
    start_date: '',
    end_date: '',
    is_current: false,
    description: ''
  });

  // Add Certification Modal state
  const [isAddCertOpen, setIsAddCertOpen] = useState(false);
  const [isSavingCert, setIsSavingCert] = useState(false);
  const [certForm, setCertForm] = useState({
    certification_name: '',
    issuing_organization: '',
    certificate_number: '',
    credential_url: '',
    issue_date: '',
    expiry_date: ''
  });

  // Delete Confirmation state
  const [deleteDialog, setDeleteDialog] = useState({
    isOpen: false,
    type: null, // 'experience' | 'certification'
    id: null,
    title: ''
  });

  // Helper to show temporary alerts
  const showNotification = (msg, type = 'success') => {
    if (type === 'success') {
      setSuccessMessage(msg);
      setTimeout(() => setSuccessMessage(null), 4000);
    } else {
      setErrorMessage(msg);
      setTimeout(() => setErrorMessage(null), 6000);
    }
  };

  // Fetch all profile related data
  const loadProfileData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [profileRes, expRes, certRes] = await Promise.all([
        competencyService.getProfile().catch(() => null),
        competencyService.getExperiences().catch(() => null),
        competencyService.getCertifications().catch(() => null)
      ]);

      if (profileRes?.data) {
        setProfileData(profileRes.data);
        setPersonalForm({
          full_name: profileRes.data.full_name || '',
          phone: profileRes.data.phone || '',
          location: profileRes.data.location || '',
          bio: profileRes.data.bio || ''
        });
      }

      if (expRes?.data) {
        setExperiences(expRes.data);
      }

      if (certRes?.data) {
        setCertifications(certRes.data);
      }
    } catch {
      setErrorMessage('Failed to load profile details. Please check connection and refresh.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfileData();
  }, [loadProfileData]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Personal Info update handler
  const handleSavePersonal = async (e) => {
    e.preventDefault();
    if (!personalForm.full_name.trim()) {
      showNotification('Legal name cannot be empty.', 'error');
      return;
    }

    setIsSavingPersonal(true);
    try {
      await competencyService.updateProfile(personalForm);
      showNotification('Personal details updated successfully.', 'success');
      setIsEditingPersonalInfo(false);
      await loadProfileData();
    } catch (err) {
      showNotification(err?.response?.data?.error || 'Failed to update personal details.', 'error');
    } finally {
      setIsSavingPersonal(false);
    }
  };

  // Experience form submission
  const handleAddExperience = async (e) => {
    e.preventDefault();
    if (!expForm.job_title.trim() || !expForm.company.trim() || !expForm.start_date) {
      showNotification('Please fill in Job Title, Company Name, and Start Date.', 'error');
      return;
    }
    if (!expForm.is_current && !expForm.end_date) {
      showNotification('Please provide an End Date or mark the role as Current.', 'error');
      return;
    }

    setIsSavingExp(true);
    try {
      await competencyService.addExperience(expForm);
      showNotification('Work experience submitted for administrator verification.', 'success');
      setIsAddExpOpen(false);
      setExpForm({
        job_title: '',
        company: '',
        work_category: 'Sales',
        start_date: '',
        end_date: '',
        is_current: false,
        description: ''
      });
      await loadProfileData();
    } catch (err) {
      showNotification(err?.response?.data?.error || 'Failed to submit work experience.', 'error');
    } finally {
      setIsSavingExp(false);
    }
  };

  // Certification form submission
  const handleAddCertification = async (e) => {
    e.preventDefault();
    if (!certForm.certification_name.trim() || !certForm.issue_date) {
      showNotification('Please provide Certification Name and Issue Date.', 'error');
      return;
    }

    setIsSavingCert(true);
    try {
      await competencyService.addCertification(certForm);
      showNotification('Certification submitted for administrator verification.', 'success');
      setIsAddCertOpen(false);
      setCertForm({
        certification_name: '',
        issuing_organization: '',
        certificate_number: '',
        credential_url: '',
        issue_date: '',
        expiry_date: ''
      });
      await loadProfileData();
    } catch (err) {
      showNotification(err?.response?.data?.error || 'Failed to submit certification.', 'error');
    } finally {
      setIsSavingCert(false);
    }
  };

  // Confirm and delete pending item
  const handleConfirmDelete = async () => {
    if (!deleteDialog.id || !deleteDialog.type) return;

    try {
      if (deleteDialog.type === 'experience') {
        await competencyService.deleteExperience(deleteDialog.id);
        showNotification('Work experience entry removed successfully.', 'success');
      } else if (deleteDialog.type === 'certification') {
        await competencyService.deleteCertification(deleteDialog.id);
        showNotification('Certification entry removed successfully.', 'success');
      }
      setDeleteDialog({ isOpen: false, type: null, id: null, title: '' });
      await loadProfileData();
    } catch (err) {
      showNotification(err?.response?.data?.error || 'Failed to remove entry.', 'error');
    }
  };

  // Assessment completion handler
  const handleAssessmentComplete = async () => {
    setIsAssessmentModalOpen(false);
    showNotification('Competency assessment submitted and evaluated by Random Forest model.', 'success');
    await loadProfileData();
  };

  // User initials
  const userInitials = profileData?.full_name
    ? profileData.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : (user?.fullName ? user.fullName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'AG');

  // Competency Styling Helper
  const getCompetencyBadgeStyle = (comp) => {
    switch (comp) {
      case 'ADVANCED':
      case 'Advanced':
      case 'COMPETENT':
      case 'Competent':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'BASIC':
      case 'Basic':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'NEEDS_IMPROVEMENT':
      case 'Needs Improvement':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  const getDecisionBadge = (decision) => {
    switch (decision) {
      case 'Eligible':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">Eligible (Auto-Approve)</span>;
      case 'Send to Review':
      case 'Borderline':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">Send to Review (Human Verification)</span>;
      case 'Ineligible':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">Ineligible</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">{decision || 'Pending'}</span>;
    }
  };

  // Verification status badge helper
  const renderVerificationBadge = (status, reason, reviewerName, reviewedAt) => {
    if (status === 'VERIFIED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <span>Verified{reviewerName ? ` by ${reviewerName}` : ''}</span>
        </span>
      );
    }
    if (status === 'REJECTED') {
      return (
        <div className="flex flex-col items-start gap-1">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
            <span>Verification Rejected</span>
          </span>
          {reason && (
            <p className="text-[11px] text-rose-600 font-medium">
              Reason: {reason}
            </p>
          )}
        </div>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
        <Clock className="w-3.5 h-3.5 text-amber-600 shrink-0" />
        <span>Pending Admin Verification</span>
      </span>
    );
  };

  const verifiedExp = profileData?.verified_experience || {
    total_experience_months: 0,
    sales_experience_months: 0,
    customer_service_experience_months: 0,
    other_experience_months: 0,
    verified_entries_count: 0
  };

  const verifiedCerts = profileData?.verified_certifications || {
    certification_count: 0,
    relevant_certification: 0,
    certified_leverage: 0
  };

  const assessmentSummary = profileData?.assessment_summary || {
    has_assessed: false,
    competency_level: 'Pending',
    evaluation_decision: 'Not Evaluated',
    overall_score: null,
    scores: {}
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans text-slate-800">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200/80 px-6 sm:px-8 h-16 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-2.5 select-none cursor-pointer" onClick={() => navigate('/dashboard')}>
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

        <div className="flex items-center gap-3 sm:gap-4">
          <button 
            type="button"
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-full transition-colors relative"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5" />
          </button>

          {/* User Profile Pill & Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2.5 p-1 sm:px-2 rounded-xl hover:bg-slate-50 transition-colors cursor-pointer select-none"
            >
              <div className="w-9 h-9 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-xs sm:text-sm flex items-center justify-center">
                {userInitials}
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-sm font-semibold text-slate-900 leading-tight">
                  {profileData?.full_name || user?.fullName || 'Agent'}
                </p>
                <p className="text-xs text-slate-400 leading-tight">
                  {user?.role || 'Agent'}
                </p>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg border border-slate-150 py-1.5 z-40 animate-in fade-in zoom-in-95 duration-150">
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/dashboard');
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <LayoutGrid className="w-3.5 h-3.5 text-slate-500" />
                  Dashboard
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/profile');
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-semibold text-[#3B50BA] bg-blue-50/60 flex items-center gap-2"
                >
                  <User className="w-3.5 h-3.5 text-[#3B50BA]" />
                  My Profile
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
        {/* Left Sidebar */}
        <aside className="w-full md:w-56 lg:w-60 bg-white border-r border-slate-200/80 flex flex-col justify-between p-4 shrink-0">
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <LayoutGrid className="w-4 h-4 text-slate-500" />
              <span>Dashboard</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/profile')}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold bg-[#EEF2FF] text-[#3B50BA] transition-colors cursor-pointer"
            >
              <User className="w-4 h-4 text-[#3B50BA]" />
              <span>My Profile</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/tasks')}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <ListChecks className="w-4 h-4 text-slate-500" />
              <span>Tasks</span>
            </button>
          </div>

          {/* Model Integration Widget */}
          <div className="my-6 p-4 rounded-2xl bg-gradient-to-br from-blue-50/80 to-indigo-50/40 border border-blue-100 hidden md:block">
            <div className="flex items-center gap-2 text-xs font-bold text-[#3B50BA]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Random Forest Sync</span>
            </div>
            <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed">
              Experience months &amp; certifications are verified by admins before model feature injection.
            </p>
            <div className="mt-3 pt-2.5 border-t border-blue-100/60 flex items-center justify-between text-[11px] text-slate-500">
              <span>Verified Months:</span>
              <span className="font-bold text-slate-800">{verifiedExp.total_experience_months} mos</span>
            </div>
            <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
              <span>Verified Certs:</span>
              <span className="font-bold text-slate-800">{verifiedCerts.certification_count}</span>
            </div>
          </div>

          <div className="space-y-1 pt-4 border-t border-slate-150">
            <button
              type="button"
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50/60 transition-colors"
            >
              <LogOut className="w-4 h-4 text-slate-500 hover:text-rose-600" />
              <span>Sign Out</span>
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 sm:p-8 lg:p-10 space-y-8 overflow-y-auto max-w-5xl">
          {/* Notifications */}
          {successMessage && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-3 shadow-xs animate-in fade-in duration-200">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-3 shadow-xs animate-in fade-in duration-200">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* ================================================================= */}
          {/* SECTION 1: PROFILE OVERVIEW & READINESS */}
          {/* ================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-6 border-b border-slate-100">
              <div className="flex items-center gap-4 sm:gap-5">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-[#E0E7FF] text-[#3B50BA] font-bold text-2xl sm:text-3xl flex items-center justify-center shadow-xs shrink-0">
                  {userInitials}
                </div>
                <div>
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
                      {profileData?.full_name || 'Agent Profile'}
                    </h1>
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {profileData?.agent_status === 'ACTIVE' ? 'Verified Active Agent' : (profileData?.agent_status || 'Verified Agent')}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1 flex items-center gap-2 flex-wrap">
                    <span>{profileData?.email || user?.email}</span>
                    <span>&bull;</span>
                    <span>System ID: <strong className="text-slate-700 font-mono">VM-AGT-{profileData?.agent_id || user?.id || '1'}</strong></span>
                    {profileData?.member_since && (
                      <>
                        <span>&bull;</span>
                        <span>Member since {new Date(profileData.member_since).toLocaleDateString()}</span>
                      </>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <Button variant="secondary" size="sm" onClick={() => navigate('/dashboard')}>
                  Back to Dashboard
                </Button>
                <Button size="sm" onClick={() => setIsAssessmentModalOpen(true)}>
                  {assessmentSummary.has_assessed ? 'Retake Assessment' : 'Take Initial Assessment'}
                </Button>
              </div>
            </div>

            {/* Profile Readiness Bar */}
            <div className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Profile Readiness Score
                  </span>
                  <span className="text-xs text-slate-400">
                    (4 Core Verification Pillars)
                  </span>
                </div>
                <span className="text-sm font-bold text-[#3B50BA]">
                  {profileData?.readiness_score ?? 75}% Complete
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                <div 
                  className="bg-[#3B50BA] h-2.5 rounded-full transition-all duration-500 ease-out" 
                  style={{ width: `${profileData?.readiness_score ?? 75}%` }}
                />
              </div>

              {/* Pillar Checklist */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 text-xs">
                <div className={`p-2.5 rounded-xl border flex items-center gap-2 ${profileData?.readiness_checks?.personal_info ? 'bg-emerald-50/60 border-emerald-200 text-emerald-800' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  {profileData?.readiness_checks?.personal_info ? <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> : <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                  <span className="font-medium">1. Contact &amp; Bio</span>
                </div>

                <div className={`p-2.5 rounded-xl border flex items-center gap-2 ${profileData?.readiness_checks?.assessment ? 'bg-emerald-50/60 border-emerald-200 text-emerald-800' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  {profileData?.readiness_checks?.assessment ? <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> : <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                  <span className="font-medium">2. Competency Battery</span>
                </div>

                <div className={`p-2.5 rounded-xl border flex items-center gap-2 ${profileData?.readiness_checks?.experience ? 'bg-emerald-50/60 border-emerald-200 text-emerald-800' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  {profileData?.readiness_checks?.experience ? <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> : <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                  <span className="font-medium">3. Verified Experience</span>
                </div>

                <div className={`p-2.5 rounded-xl border flex items-center gap-2 ${profileData?.readiness_checks?.certification ? 'bg-emerald-50/60 border-emerald-200 text-emerald-800' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  {profileData?.readiness_checks?.certification ? <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> : <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                  <span className="font-medium">4. Certifications</span>
                </div>
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* SECTION 2: PERSONAL & CONTACT INFORMATION */}
          {/* ================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Personal &amp; Contact Information</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Update your contact details and professional summary. System credentials and status remain read-only.
                </p>
              </div>

              {!isEditingPersonalInfo ? (
                <Button 
                  variant="secondary" 
                  size="sm" 
                  onClick={() => setIsEditingPersonalInfo(true)}
                  className="flex items-center gap-1.5"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Edit Profile</span>
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => {
                      setIsEditingPersonalInfo(false);
                      setPersonalForm({
                        full_name: profileData?.full_name || '',
                        phone: profileData?.phone || '',
                        location: profileData?.location || '',
                        bio: profileData?.bio || ''
                      });
                    }}
                  >
                    Cancel
                  </Button>
                  <Button 
                    size="sm" 
                    onClick={handleSavePersonal}
                    disabled={isSavingPersonal}
                    className="flex items-center gap-1.5"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{isSavingPersonal ? 'Saving...' : 'Save Changes'}</span>
                  </Button>
                </div>
              )}
            </div>

            {isEditingPersonalInfo ? (
              /* Edit Mode Form */
              <form onSubmit={handleSavePersonal} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Full Legal Name <span className="text-rose-500">*</span>
                    </label>
                    <input 
                      type="text"
                      value={personalForm.full_name}
                      onChange={(e) => setPersonalForm({ ...personalForm, full_name: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] focus:ring-1 focus:ring-[#3B50BA]"
                      placeholder="e.g. Alex Morgan"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Phone Number
                    </label>
                    <input 
                      type="tel"
                      value={personalForm.phone}
                      onChange={(e) => setPersonalForm({ ...personalForm, phone: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] focus:ring-1 focus:ring-[#3B50BA]"
                      placeholder="e.g. +1 (555) 234-5678"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Primary Location / Timezone
                  </label>
                  <input 
                    type="text"
                    value={personalForm.location}
                    onChange={(e) => setPersonalForm({ ...personalForm, location: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] focus:ring-1 focus:ring-[#3B50BA]"
                    placeholder="e.g. Chicago, IL (US Central)"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Professional Bio / Summary
                  </label>
                  <textarea 
                    rows={3}
                    value={personalForm.bio}
                    onChange={(e) => setPersonalForm({ ...personalForm, bio: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] focus:ring-1 focus:ring-[#3B50BA]"
                    placeholder="Highlight your key background, specialized domains, and communication strengths..."
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Brief summary displayed to task review evaluators.</p>
                </div>
              </form>
            ) : (
              /* View Mode Grid */
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                  <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50">
                    <span className="text-[11px] text-slate-400 block font-semibold uppercase">Legal Full Name</span>
                    <p className="text-sm font-semibold text-slate-900 mt-1 flex items-center gap-2">
                      <User className="w-4 h-4 text-slate-400" />
                      <span>{profileData?.full_name || 'Not provided'}</span>
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50">
                    <span className="text-[11px] text-slate-400 block font-semibold uppercase">Registered Email</span>
                    <p className="text-sm font-semibold text-slate-900 mt-1 flex items-center gap-2">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <span>{profileData?.email || user?.email}</span>
                      <Lock className="w-3 h-3 text-slate-300 ml-auto" title="System Locked" />
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50">
                    <span className="text-[11px] text-slate-400 block font-semibold uppercase">Contact Phone</span>
                    <p className="text-sm font-semibold text-slate-900 mt-1 flex items-center gap-2">
                      <Phone className="w-4 h-4 text-slate-400" />
                      <span>{profileData?.phone || 'No phone recorded'}</span>
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50">
                    <span className="text-[11px] text-slate-400 block font-semibold uppercase">Location &amp; Timezone</span>
                    <p className="text-sm font-semibold text-slate-900 mt-1 flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-slate-400" />
                      <span>{profileData?.location || 'No location specified'}</span>
                    </p>
                  </div>
                </div>

                {/* Bio Block */}
                <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50">
                  <span className="text-[11px] text-slate-400 block font-semibold uppercase mb-1">
                    Professional Summary &amp; Background
                  </span>
                  <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
                    {profileData?.bio || 'No professional bio provided yet. Click "Edit Profile" to add your professional introduction.'}
                  </p>
                </div>

                {/* Read-only System Metadata Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 text-xs">
                    <span className="text-[10px] text-slate-400 font-bold uppercase block">System Role</span>
                    <span className="font-semibold text-[#3B50BA] mt-0.5 block flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-[#3B50BA]" />
                      Agent (Workforce)
                    </span>
                  </div>

                  <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 text-xs">
                    <span className="text-[10px] text-slate-400 font-bold uppercase block">Account Identifier</span>
                    <span className="font-mono font-semibold text-slate-800 mt-0.5 block">
                      VM-AGT-{profileData?.agent_id || user?.id || '1'}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 text-xs">
                    <span className="text-[10px] text-slate-400 font-bold uppercase block">Account Security</span>
                    <span className="font-semibold text-emerald-600 mt-0.5 block flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Email Verified &amp; Active
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ================================================================= */}
          {/* SECTION 3: WORK HISTORY & VERIFIED EXPERIENCE */}
          {/* ================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-[#3B50BA]" />
                  <h2 className="text-lg font-bold text-slate-900">Work Experience &amp; Verified Tenures</h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Records are reviewed by administrators. Verified months are calculated without double-counting overlapping tenures.
                </p>
              </div>

              <Button 
                size="sm" 
                onClick={() => setIsAddExpOpen(true)}
                className="flex items-center gap-1.5 shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Work Experience</span>
              </Button>
            </div>

            {/* Verified Experience Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Total Verified Experience
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {verifiedExp.total_experience_months} <span className="text-sm font-normal text-slate-500">months</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  ({(verifiedExp.total_experience_months / 12).toFixed(1)} years merged)
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Verified Sales Experience
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {verifiedExp.sales_experience_months} <span className="text-sm font-normal text-slate-500">months</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Input: <code className="text-xs font-mono text-slate-600">sales_experience_months</code>
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Verified Customer Service
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {verifiedExp.customer_service_experience_months} <span className="text-sm font-normal text-slate-500">months</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Input: <code className="text-xs font-mono text-slate-600">customer_service_experience_months</code>
                </p>
              </div>
            </div>

            {/* Experience Records List */}
            <div className="space-y-3">
              {experiences.length > 0 ? (
                experiences.map((exp) => (
                  <div 
                    key={exp.experience_id} 
                    className="p-4 rounded-xl border border-slate-200/80 hover:border-slate-300 transition-colors bg-white shadow-2xs"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-sm font-bold text-slate-900">{exp.job_title}</h4>
                          <span className="text-xs text-slate-400">&bull;</span>
                          <span className="text-xs font-semibold text-slate-700">{exp.company}</span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                            {exp.work_category}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-1 flex-wrap">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>
                            {exp.start_date} &rarr; {exp.is_current ? 'Present (Current Role)' : (exp.end_date || 'Ongoing')}
                          </span>
                        </div>

                        {exp.description && (
                          <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                            {exp.description}
                          </p>
                        )}
                      </div>

                      <div className="flex sm:flex-col items-end justify-between sm:justify-start gap-2 shrink-0">
                        {renderVerificationBadge(
                          exp.verification_status, 
                          exp.rejection_reason, 
                          exp.reviewer_name, 
                          exp.reviewed_at
                        )}

                        {/* Allow deleting pending or rejected records */}
                        {exp.verification_status !== 'VERIFIED' && (
                          <button
                            type="button"
                            onClick={() => setDeleteDialog({
                              isOpen: true,
                              type: 'experience',
                              id: exp.experience_id,
                              title: `${exp.job_title} at ${exp.company}`
                            })}
                            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                            title="Withdraw/Delete this entry"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center border border-dashed border-slate-200 rounded-xl bg-slate-50/50">
                  <Briefcase className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No work experience submitted</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Add past roles to build verified experience months and unlock tasks that require domain experience.
                  </p>
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => setIsAddExpOpen(true)}
                    className="mt-3"
                  >
                    + Add Your First Role
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* ================================================================= */}
          {/* SECTION 4: CERTIFICATIONS & CREDENTIALS */}
          {/* ================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-[#3B50BA]" />
                  <h2 className="text-lg font-bold text-slate-900">Professional Certifications &amp; Credentials</h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Verified certifications satisfy mandatory task requirements and add leverage to ML competency scores.
                </p>
              </div>

              <Button 
                size="sm" 
                onClick={() => setIsAddCertOpen(true)}
                className="flex items-center gap-1.5 shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Certification</span>
              </Button>
            </div>

            {/* Verified Certifications Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Verified Credentials Count
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {verifiedCerts.certification_count} <span className="text-sm font-normal text-slate-500">active</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Input: <code className="text-xs font-mono text-slate-600">certification_count</code>
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Domain Relevant Certification
                </span>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${verifiedCerts.relevant_certification ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                    {verifiedCerts.relevant_certification ? 'Domain Qualified (1)' : 'Standard (0)'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Input: <code className="text-xs font-mono text-slate-600">relevant_certification</code>
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Certified Leverage Multiplier
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {verifiedCerts.certified_leverage}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Input: <code className="text-xs font-mono text-slate-600">certified_leverage</code>
                </p>
              </div>
            </div>

            {/* Certifications List */}
            <div className="space-y-3">
              {certifications.length > 0 ? (
                certifications.map((cert) => (
                  <div 
                    key={cert.agent_cert_id} 
                    className="p-4 rounded-xl border border-slate-200/80 hover:border-slate-300 transition-colors bg-white shadow-2xs"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-sm font-bold text-slate-900">{cert.certification_name}</h4>
                          {cert.issuing_organization && (
                            <span className="text-xs font-semibold text-slate-600">
                              &bull; {cert.issuing_organization}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 flex-wrap">
                          {cert.certificate_number && (
                            <span>ID: <strong className="font-mono text-slate-700">{cert.certificate_number}</strong></span>
                          )}
                          <span>Issued: {cert.issue_date}</span>
                          {cert.expiry_date ? (
                            <span>Expires: {cert.expiry_date}</span>
                          ) : (
                            <span className="text-slate-400">No Expiration</span>
                          )}
                        </div>

                        {cert.credential_url && (
                          <div className="mt-2">
                            <a 
                              href={cert.credential_url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="inline-flex items-center gap-1 text-xs font-semibold text-[#3B50BA] hover:underline"
                            >
                              <span>Verify Credential Online</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        )}
                      </div>

                      <div className="flex sm:flex-col items-end justify-between sm:justify-start gap-2 shrink-0">
                        {renderVerificationBadge(
                          cert.status, 
                          cert.rejection_reason, 
                          cert.reviewer_name, 
                          cert.reviewed_at
                        )}

                        {cert.status !== 'VERIFIED' && (
                          <button
                            type="button"
                            onClick={() => setDeleteDialog({
                              isOpen: true,
                              type: 'certification',
                              id: cert.agent_cert_id,
                              title: cert.certification_name
                            })}
                            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                            title="Withdraw/Delete this certification"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center border border-dashed border-slate-200 rounded-xl bg-slate-50/50">
                  <Award className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No certifications submitted yet</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Submit your professional licenses or training credentials to satisfy task requirements and boost model evaluation scores.
                  </p>
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => setIsAddCertOpen(true)}
                    className="mt-3"
                  >
                    + Submit a Certification
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* ================================================================= */}
          {/* SECTION 5: COMPETENCY BATTERY & MODEL INPUTS */}
          {/* ================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[#3B50BA]" />
                  <h2 className="text-lg font-bold text-slate-900">Competency Assessment Battery &amp; ML Contract</h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Latest battery results feeding the Random Forest inference engine alongside your verified experience and credentials.
                </p>
              </div>

              <Button 
                size="sm" 
                variant="secondary"
                onClick={() => setIsAssessmentModalOpen(true)}
                className="shrink-0"
              >
                {assessmentSummary.has_assessed ? 'Retake Assessment Battery' : 'Take Initial Battery'}
              </Button>
            </div>

            {/* Assessment Battery Outcomes */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Overall Battery Score
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {assessmentSummary.overall_score ? `${assessmentSummary.overall_score}%` : 'Not Assessed'}
                </p>
                {assessmentSummary.completed_at && (
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Evaluated on {new Date(assessmentSummary.completed_at).toLocaleDateString()}
                  </p>
                )}
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Predicted Competency
                </span>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getCompetencyBadgeStyle(assessmentSummary.competency_level)}`}>
                    {assessmentSummary.competency_level}
                  </span>
                  {assessmentSummary.confidence && (
                    <span className="text-xs text-slate-500 font-mono">
                      ({Math.round(assessmentSummary.confidence > 1 ? assessmentSummary.confidence : assessmentSummary.confidence * 100)}%)
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Random Forest 3-class classifier</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  3-Way Decision Outcome
                </span>
                <div className="mt-1">
                  {getDecisionBadge(assessmentSummary.evaluation_decision)}
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Eligible / Review / Ineligible</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Attempt History
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  #{assessmentSummary.attempt_number || 1}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Cumulative evaluations</p>
              </div>
            </div>

            {/* 4 Assessment Subscores */}
            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-3">
                Core Domain Competency Subscores
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/60">
                  <span className="text-[11px] text-slate-500 block font-medium">Communication</span>
                  <p className="text-lg font-bold text-slate-900 mt-0.5">
                    {assessmentSummary.scores?.communication ? `${assessmentSummary.scores.communication}%` : '—'}
                  </p>
                </div>

                <div className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/60">
                  <span className="text-[11px] text-slate-500 block font-medium">Product Knowledge</span>
                  <p className="text-lg font-bold text-slate-900 mt-0.5">
                    {assessmentSummary.scores?.product_knowledge ? `${assessmentSummary.scores.product_knowledge}%` : '—'}
                  </p>
                </div>

                <div className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/60">
                  <span className="text-[11px] text-slate-500 block font-medium">Sales Skills</span>
                  <p className="text-lg font-bold text-slate-900 mt-0.5">
                    {assessmentSummary.scores?.sales_skill ? `${assessmentSummary.scores.sales_skill}%` : '—'}
                  </p>
                </div>

                <div className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/60">
                  <span className="text-[11px] text-slate-500 block font-medium">Customer Service</span>
                  <p className="text-lg font-bold text-slate-900 mt-0.5">
                    {assessmentSummary.scores?.customer_service ? `${assessmentSummary.scores.customer_service}%` : '—'}
                  </p>
                </div>
              </div>
            </div>

            {/* Model Vector Contract Explanation */}
            <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 text-xs text-indigo-950 space-y-2">
              <div className="flex items-center gap-2 font-bold text-[#3B50BA]">
                <Layers className="w-4 h-4" />
                <span>Model Contract Transparency</span>
              </div>
              <p className="leading-relaxed text-slate-600">
                VerifyMesh preserves the exact 11-feature contract of <strong className="font-mono text-slate-800">threeway_decision_model.joblib</strong>:
                Experience months (<code className="font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-indigo-100">previous_experience_months</code>, <code className="font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-indigo-100">sales_experience_months</code>, <code className="font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-indigo-100">customer_service_experience_months</code>) 
                and certifications (<code className="font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-indigo-100">certification_count</code>, <code className="font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-indigo-100">relevant_certification</code>, <code className="font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-indigo-100">certified_leverage</code>) 
                are automatically populated from your verified database records rather than unverified form inputs.
              </p>
            </div>
          </div>
        </main>
      </div>

      {/* ================================================================= */}
      {/* MODAL: ADD WORK EXPERIENCE */}
      {/* ================================================================= */}
      {isAddExpOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-100 p-6 sm:p-7 relative max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-[#3B50BA]" />
                <h3 className="text-lg font-bold text-slate-900">Add Work Experience</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAddExpOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddExperience} className="space-y-4 mt-4 text-xs sm:text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Job Title <span className="text-rose-500">*</span>
                </label>
                <input 
                  type="text"
                  value={expForm.job_title}
                  onChange={(e) => setExpForm({ ...expForm, job_title: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  placeholder="e.g. Senior Sales Specialist"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Company / Organization <span className="text-rose-500">*</span>
                </label>
                <input 
                  type="text"
                  value={expForm.company}
                  onChange={(e) => setExpForm({ ...expForm, company: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  placeholder="e.g. Apex Global Solutions"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Work Category <span className="text-rose-500">*</span>
                </label>
                <select
                  value={expForm.work_category}
                  onChange={(e) => setExpForm({ ...expForm, work_category: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:border-[#3B50BA]"
                >
                  <option value="Sales">Sales &amp; Business Development</option>
                  <option value="Customer Service">Customer Service &amp; Support</option>
                  <option value="Other">General / Other Professional Experience</option>
                </select>
                <p className="text-[11px] text-slate-400 mt-1">
                  Category determines which model feature input (Sales vs Customer Service) is credited.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Start Date <span className="text-rose-500">*</span>
                  </label>
                  <input 
                    type="date"
                    value={expForm.start_date}
                    onChange={(e) => setExpForm({ ...expForm, start_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    End Date
                  </label>
                  <input 
                    type="date"
                    value={expForm.end_date}
                    disabled={expForm.is_current}
                    onChange={(e) => setExpForm({ ...expForm, end_date: e.target.value })}
                    className={`w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] ${expForm.is_current ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : ''}`}
                    required={!expForm.is_current}
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input 
                  type="checkbox"
                  id="is_current"
                  checked={expForm.is_current}
                  onChange={(e) => setExpForm({ ...expForm, is_current: e.target.checked, end_date: e.target.checked ? '' : expForm.end_date })}
                  className="w-4 h-4 rounded text-[#3B50BA] focus:ring-[#3B50BA] border-slate-300"
                />
                <label htmlFor="is_current" className="text-xs font-medium text-slate-700 cursor-pointer">
                  I currently work in this role
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Role Description &amp; Responsibilities
                </label>
                <textarea 
                  rows={3}
                  value={expForm.description}
                  onChange={(e) => setExpForm({ ...expForm, description: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  placeholder="Summarize key tasks, quotas, deliverables, or customer interactions handled..."
                />
              </div>

              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-2">
                <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>
                  Submitted roles enter the <strong>Pending Verification</strong> status and are reviewed by administrators before being credited to your verified months.
                </span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <Button 
                  type="button" 
                  variant="ghost" 
                  onClick={() => setIsAddExpOpen(false)}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={isSavingExp}
                >
                  {isSavingExp ? 'Submitting...' : 'Submit for Verification'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* MODAL: ADD CERTIFICATION */}
      {/* ================================================================= */}
      {isAddCertOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-100 p-6 sm:p-7 relative max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-[#3B50BA]" />
                <h3 className="text-lg font-bold text-slate-900">Add Professional Certification</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAddCertOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddCertification} className="space-y-4 mt-4 text-xs sm:text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Certification Name <span className="text-rose-500">*</span>
                </label>
                <input 
                  type="text"
                  value={certForm.certification_name}
                  onChange={(e) => setCertForm({ ...certForm, certification_name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  placeholder="e.g. HubSpot Inbound Sales Certified"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Issuing Organization
                </label>
                <input 
                  type="text"
                  value={certForm.issuing_organization}
                  onChange={(e) => setCertForm({ ...certForm, issuing_organization: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  placeholder="e.g. HubSpot Academy, Google, AWS"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Credential / License ID
                  </label>
                  <input 
                    type="text"
                    value={certForm.certificate_number}
                    onChange={(e) => setCertForm({ ...certForm, certificate_number: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm font-mono focus:outline-none focus:border-[#3B50BA]"
                    placeholder="e.g. HS-CERT-98214"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Verification URL
                  </label>
                  <input 
                    type="url"
                    value={certForm.credential_url}
                    onChange={(e) => setCertForm({ ...certForm, credential_url: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                    placeholder="https://..."
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Issue Date <span className="text-rose-500">*</span>
                  </label>
                  <input 
                    type="date"
                    value={certForm.issue_date}
                    onChange={(e) => setCertForm({ ...certForm, issue_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Expiration Date <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input 
                    type="date"
                    value={certForm.expiry_date}
                    onChange={(e) => setCertForm({ ...certForm, expiry_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  />
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-2">
                <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>
                  Admin reviewers verify the credential link and issuing authority before marking it <strong>VERIFIED</strong>.
                </span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <Button 
                  type="button" 
                  variant="ghost" 
                  onClick={() => setIsAddCertOpen(false)}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={isSavingCert}
                >
                  {isSavingCert ? 'Submitting...' : 'Submit Certification'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* DIALOG: CONFIRM DELETE */}
      {/* ================================================================= */}
      {deleteDialog.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-sm bg-white rounded-2xl shadow-2xl border border-slate-100 p-6 relative">
            <div className="w-10 h-10 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mb-3">
              <Trash2 className="w-5 h-5" />
            </div>
            <h4 className="text-base font-bold text-slate-900">Withdraw Submission?</h4>
            <p className="text-xs text-slate-600 mt-1">
              Are you sure you want to remove <strong className="text-slate-800">"{deleteDialog.title}"</strong>? 
              This will withdraw it from the verification queue.
            </p>
            <div className="flex items-center justify-end gap-2.5 mt-5">
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setDeleteDialog({ isOpen: false, type: null, id: null, title: '' })}
              >
                Cancel
              </Button>
              <Button 
                size="sm"
                onClick={handleConfirmDelete}
                className="bg-rose-600 hover:bg-rose-700 text-white"
              >
                Confirm Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Assessment Modal if user wants to take/retake test directly */}
      {isAssessmentModalOpen && (
        <TakeAssessmentModal
          isOpen={isAssessmentModalOpen}
          onClose={() => setIsAssessmentModalOpen(false)}
          onAssessmentComplete={handleAssessmentComplete}
          currentData={assessmentSummary.scores}
          userId={profileData?.user_id || user?.id}
        />
      )}
    </div>
  );
};

export default ProfilePage;
