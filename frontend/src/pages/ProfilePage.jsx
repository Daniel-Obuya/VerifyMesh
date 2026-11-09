import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  ChevronLeft,
  ChevronRight,
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
  UserCheck,
  Send,
  Camera,
  Upload
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { competencyService } from '../services/competencyService';

export const ProfilePage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Sidebar collapse/expand state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Active Tab state: 'personal' | 'experience' | 'certifications'
  const [activeTab, setActiveTab] = useState('personal');

  // Navigation & Dropdown states
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Core Data States
  const [isLoading, setIsLoading] = useState(true);
  const [profileData, setProfileData] = useState(null);
  const [experiences, setExperiences] = useState([]);
  const [certifications, setCertifications] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Optional User Avatar (Stored per agent)
  const avatarStorageKey = user?.id ? `verifymesh_agent_avatar_${user.id}` : 'verifymesh_agent_avatar';
  const [avatarUrl, setAvatarUrl] = useState(() => {
    try {
      return localStorage.getItem(avatarStorageKey) || null;
    } catch {
      return null;
    }
  });

  // Edit Personal Info state
  const [isEditingPersonalInfo, setIsEditingPersonalInfo] = useState(false);
  const [personalForm, setPersonalForm] = useState({
    full_name: '',
    phone: '',
    location: '',
    education: '',
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
    description: '',
    supervisor_name: '',
    supervisor_email: '',
    supervisor_phone: ''
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
  const [isDeleting, setIsDeleting] = useState(false);

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

  // Fetch all profile related data from backend
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
          education: profileRes.data.education || '',
          bio: profileRes.data.bio || ''
        });

        // If backend provided an avatar, sync it
        if (profileRes.data.avatar_url) {
          setAvatarUrl(profileRes.data.avatar_url);
        }
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

  // Avatar Upload / Change Handler
  const handleAvatarFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      showNotification('Please select a valid image file (JPG, PNG, WebP).', 'error');
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      showNotification('Profile image must be less than 2MB.', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64Data = event.target.result;
      setAvatarUrl(base64Data);
      try {
        localStorage.setItem(avatarStorageKey, base64Data);
      } catch {
        // LocalStorage quota fallback
      }
      showNotification('Profile photo updated successfully.', 'success');
    };
    reader.readAsDataURL(file);
  };

  // Avatar Removal Handler
  const handleRemoveAvatar = (e) => {
    e.stopPropagation();
    setAvatarUrl(null);
    try {
      localStorage.removeItem(avatarStorageKey);
    } catch {
      // Ignore
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    showNotification('Profile photo removed. Standard initials avatar restored.', 'success');
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
      await competencyService.updateProfile({
        full_name: personalForm.full_name,
        phone: personalForm.phone,
        location: personalForm.location,
        education: personalForm.education,
        bio: personalForm.bio
      });
      showNotification('Personal details updated successfully.', 'success');
      setIsEditingPersonalInfo(false);
      await loadProfileData();
    } catch (err) {
      showNotification(err?.message || err?.data?.error || err?.response?.data?.error || 'Failed to update personal details.', 'error');
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
    if (!expForm.supervisor_name.trim() || !expForm.supervisor_email.trim()) {
      showNotification('Supervisor / Manager Name and Corporate Email are mandatory for tenure verification.', 'error');
      return;
    }

    setIsSavingExp(true);
    try {
      await competencyService.addExperience(expForm);
      showNotification(
        expForm.supervisor_email 
          ? 'Work experience submitted! A 1-click verification email has been dispatched to your supervisor.'
          : 'Work experience submitted for administrator verification.', 
        'success'
      );
      setIsAddExpOpen(false);
      setExpForm({
        job_title: '',
        company: '',
        work_category: 'Sales',
        start_date: '',
        end_date: '',
        is_current: false,
        description: '',
        supervisor_name: '',
        supervisor_email: '',
        supervisor_phone: ''
      });
      await loadProfileData();
    } catch (err) {
      showNotification(err?.message || err?.data?.error || err?.response?.data?.error || 'Failed to submit work experience.', 'error');
    } finally {
      setIsSavingExp(false);
    }
  };

  const handleResendSupervisor = async (expId) => {
    try {
      const res = await competencyService.resendSupervisorEmail(expId);
      showNotification(res?.data?.message || 'Verification link resent to supervisor.', 'success');
      await loadProfileData();
    } catch (err) {
      showNotification(err?.response?.data?.error || 'Failed to resend verification.', 'error');
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
      showNotification(err?.message || err?.data?.error || err?.response?.data?.error || 'Failed to submit certification.', 'error');
    } finally {
      setIsSavingCert(false);
    }
  };

  // Confirm and delete pending item
  const handleConfirmDelete = async () => {
    if (!deleteDialog.id || !deleteDialog.type) return;

    setIsDeleting(true);
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
      const errMsg = err?.message || err?.data?.error || err?.response?.data?.error || 'Failed to remove entry.';
      showNotification(errMsg, 'error');
      setDeleteDialog({ isOpen: false, type: null, id: null, title: '' });
      await loadProfileData();
    } finally {
      setIsDeleting(false);
    }
  };

  // Real, authoritative name & initials
  const rawName = profileData?.full_name || user?.fullName || user?.username || 'Agent';
  const cleanName = rawName.replace(/\s*\(Verified\)/gi, '').trim();

  const userInitials = cleanName
    ? cleanName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'AG';

  // Format dates cleanly without raw GMT time strings
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return String(dateStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
    } catch {
      return String(dateStr);
    }
  };

  // Verification status badge helper
  const renderVerificationBadge = (status, reason, reviewerName) => {
    if (status === 'VERIFIED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span>Verified{reviewerName ? ` by ${reviewerName}` : ''}</span>
        </span>
      );
    }
    if (status === 'REJECTED') {
      return (
        <div className="flex flex-col items-start gap-1">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-500/40">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <span>Verification Rejected</span>
          </span>
          {reason && (
            <p className="text-[11px] text-rose-400 font-medium">
              Reason: {reason}
            </p>
          )}
        </div>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-300 border border-amber-500/40">
        <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
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

  // Authoritative Readiness Score & Pillar Checks computed directly from backend
  const readinessScore = profileData?.readiness_score !== undefined 
    ? profileData.readiness_score 
    : 0;

  const isContactComplete = Boolean(profileData?.readiness_checks?.personal_info);
  const isExpComplete = Boolean(profileData?.readiness_checks?.experience);
  const isCertComplete = Boolean(profileData?.readiness_checks?.certification);

  const isAgentActive = (profileData?.agent_status === 'ACTIVE' || user?.status === 'ACTIVE');

  return (
    <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex flex-col font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
      {/* Hidden file input for optional profile photo upload */}
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleAvatarFileChange} 
        accept="image/*" 
        className="hidden" 
      />

      {/* Ambient background glows */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed bottom-10 right-10 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* ================================================================= */}
      {/* TOP NAVBAR */}
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
            className="p-2 text-slate-400 hover:text-white hover:bg-[#151f38] rounded-xl transition-colors relative"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
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
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/dashboard');
                  }}
                  className="w-full text-left px-3.5 py-2.5 font-medium text-slate-300 hover:bg-[#15203d] hover:text-white flex items-center gap-2"
                >
                  <LayoutGrid className="w-3.5 h-3.5 text-slate-400" />
                  Dashboard
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    navigate('/profile');
                  }}
                  className="w-full text-left px-3.5 py-2.5 font-semibold text-white bg-[#1a2850] flex items-center gap-2"
                >
                  <User className="w-3.5 h-3.5 text-indigo-400" />
                  My Profile
                </button>
                <div className="border-t border-[#1e2a4a] my-1" />
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3.5 py-2.5 font-medium text-rose-400 hover:bg-rose-950/40 flex items-center gap-2"
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

            {/* Dashboard Link */}
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-[#121a30] transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
              title="Dashboard"
            >
              <LayoutGrid className="w-4 h-4 text-slate-400 shrink-0" />
              {!isSidebarCollapsed && <span>Dashboard</span>}
            </button>

            {/* My Profile Link (Active Glowing Pill) */}
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-[#2942d9] via-[#465deb] to-[#6074f7] shadow-[0_0_20px_rgba(70,93,235,0.45)] transition-all cursor-pointer relative overflow-hidden ${
                isSidebarCollapsed ? 'justify-center px-0' : ''
              }`}
              title="My Profile"
            >
              <User className="w-4 h-4 text-white shrink-0" />
              {!isSidebarCollapsed && <span>My Profile</span>}
            </button>

            {/* Tasks Link */}
            <button
              type="button"
              onClick={() => navigate('/tasks')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-[#121a30] transition-colors cursor-pointer ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
              title="Tasks"
            >
              <ListChecks className="w-4 h-4 text-slate-400 shrink-0" />
              {!isSidebarCollapsed && <span>Tasks</span>}
            </button>
          </div>

          {/* Bottom Sidebar Sign Out */}
          <div className="pt-4 border-t border-[#1b2542]">
            <button
              type="button"
              onClick={handleLogout}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors ${
                isSidebarCollapsed ? 'justify-center' : ''
              }`}
              title="Sign Out"
            >
              <LogOut className="w-4 h-4 text-slate-400 shrink-0" />
              {!isSidebarCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-5 sm:p-7 lg:p-8 space-y-6 overflow-y-auto max-w-5xl mx-auto w-full">
          {/* Notifications */}
          {successMessage && (
            <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs sm:text-sm flex items-center gap-3 shadow-lg shadow-emerald-950/50 animate-in fade-in duration-200">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs sm:text-sm flex items-center gap-3 shadow-lg shadow-rose-950/50 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* ================================================================= */}
          {/* PROFILE HERO / READINESS CARD */}
          {/* ================================================================= */}
          <div className="bg-[#0b1020]/90 border border-[#24335c]/80 rounded-2xl p-6 sm:p-7 shadow-[0_0_30px_rgba(15,23,42,0.8)] backdrop-blur-xl relative overflow-hidden">
            {/* Top Row: Avatar with Optional Upload, Name, Verified Badge, and Back to Dashboard */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
              <div className="flex items-center gap-4 sm:gap-5">
                {/* Avatar with optional upload/edit overlay */}
                <div className="relative group shrink-0">
                  {avatarUrl ? (
                    <img 
                      src={avatarUrl} 
                      alt={cleanName} 
                      className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border-2 border-[#2b3a67] shadow-lg"
                      onError={() => setAvatarUrl(null)}
                    />
                  ) : (
                    <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gradient-to-br from-indigo-600 to-purple-700 text-white font-bold text-xl sm:text-2xl flex items-center justify-center border-2 border-[#2b3a67] shadow-lg">
                      {userInitials}
                    </div>
                  )}

                  {/* Status Indicator Dots */}
                  {isAgentActive && (
                    <>
                      <span className="absolute top-1 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#0b1020] shadow-[0_0_8px_#34d399]" />
                      <span className="absolute bottom-1 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#0b1020] shadow-[0_0_8px_#34d399]" />
                    </>
                  )}

                  {/* Upload / Edit Button Overlay on Hover */}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white cursor-pointer"
                    title={avatarUrl ? 'Change profile photo' : 'Upload profile photo (optional)'}
                  >
                    <Camera className="w-5 h-5 text-indigo-300" />
                  </button>
                </div>

                {/* Name, Status Pill & Email */}
                <div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <h1 className="text-xl sm:text-2xl font-bold font-sora text-white tracking-tight">
                      {cleanName}
                    </h1>

                    {isAgentActive ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/50 text-emerald-400 border border-emerald-500/40 shadow-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        Verified Active Agent
                      </span>
                    ) : profileData?.agent_status === 'SUSPENDED' ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-rose-950/50 text-rose-400 border border-rose-500/40 shadow-xs">
                        <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                        Suspended
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-amber-950/50 text-amber-400 border border-amber-500/40 shadow-xs">
                        <Clock className="w-3.5 h-3.5 text-amber-400" />
                        Verification Pending
                      </span>
                    )}
                  </div>
                  <p className="text-xs sm:text-sm text-[#8d97b8] mt-1">
                    {profileData?.email || user?.email || 'No email registered'}
                  </p>
                </div>
              </div>

              {/* Back to Dashboard Button */}
              <div className="shrink-0">
                <button
                  type="button"
                  onClick={() => navigate('/dashboard')}
                  className="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-[#111933]/90 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-950/60 hover:border-indigo-400 hover:text-white transition-all shadow-[0_0_15px_rgba(99,102,241,0.2)] cursor-pointer"
                >
                  Back to Dashboard
                </button>
              </div>
            </div>

            {/* Middle Row: Profile Readiness Score */}
            <div className="mt-6 pt-5 border-t border-[#1b2542]/80">
              <div className="flex items-center justify-between text-xs font-semibold mb-2">
                <span className="text-[#8d97b8] uppercase tracking-wider font-bold">
                  Profile Readiness Score
                </span>
                <span className="text-white font-bold">
                  {readinessScore}% Complete
                </span>
              </div>

              {/* Glowing Progress Bar */}
              <div className="w-full bg-[#141c33] rounded-full h-2 overflow-hidden my-3">
                <div 
                  className="h-2 rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-[#6f7dff] shadow-[0_0_12px_rgba(99,102,241,0.7)] transition-all duration-500 ease-out" 
                  style={{ width: `${readinessScore}%` }}
                />
              </div>

              {/* 3 Verification Pillars Checklist (Authoritative Backend State) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 text-xs">
                {/* 1. Contact & Bio */}
                <div className={`py-2 px-3.5 rounded-xl border flex items-center gap-2 ${
                  isContactComplete 
                    ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-300' 
                    : 'border-[#202b4d] bg-[#0c1224] text-[#8d97b8]'
                }`}>
                  {isContactComplete ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="font-medium">1. Contact &amp; Bio</span>
                </div>

                {/* 2. Verified Experience */}
                <div className={`py-2 px-3.5 rounded-xl border flex items-center gap-2 ${
                  isExpComplete 
                    ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-300' 
                    : 'border-[#202b4d] bg-[#0c1224] text-[#8d97b8]'
                }`}>
                  {isExpComplete ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="font-medium">2. Verified Experience</span>
                </div>

                {/* 3. Certifications */}
                <div className={`py-2 px-3.5 rounded-xl border flex items-center gap-2 ${
                  isCertComplete 
                    ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-300' 
                    : 'border-[#202b4d] bg-[#0c1224] text-[#8d97b8]'
                }`}>
                  {isCertComplete ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="font-medium">3. Certifications</span>
                </div>
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* TABS NAVIGATION BAR */}
          {/* ================================================================= */}
          <div className="border-b border-[#1b2542] flex items-center gap-6 sm:gap-8 pt-2">
            <button
              type="button"
              onClick={() => setActiveTab('personal')}
              className={`pb-3 text-sm font-semibold transition-all relative cursor-pointer ${
                activeTab === 'personal'
                  ? 'text-white border-b-2 border-indigo-500 shadow-[0_4px_12px_rgba(99,102,241,0.5)]'
                  : 'text-[#8d97b8] hover:text-white border-b-2 border-transparent'
              }`}
            >
              Personal &amp; Contact Info
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('experience')}
              className={`pb-3 text-sm font-semibold transition-all relative cursor-pointer ${
                activeTab === 'experience'
                  ? 'text-white border-b-2 border-indigo-500 shadow-[0_4px_12px_rgba(99,102,241,0.5)]'
                  : 'text-[#8d97b8] hover:text-white border-b-2 border-transparent'
              }`}
            >
              Verified Experience
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('certifications')}
              className={`pb-3 text-sm font-semibold transition-all relative cursor-pointer ${
                activeTab === 'certifications'
                  ? 'text-white border-b-2 border-indigo-500 shadow-[0_4px_12px_rgba(99,102,241,0.5)]'
                  : 'text-[#8d97b8] hover:text-white border-b-2 border-transparent'
              }`}
            >
              Certifications
            </button>
          </div>

          {/* ================================================================= */}
          {/* TAB 1: PERSONAL & CONTACT INFO CARD */}
          {/* ================================================================= */}
          {activeTab === 'personal' && (
            <div className="bg-[#0b1020]/90 border border-[#24335c]/80 rounded-2xl p-6 sm:p-8 shadow-[0_0_30px_rgba(15,23,42,0.8)] backdrop-blur-xl space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
                <h2 className="text-lg font-bold font-sora text-white">Personal Info</h2>

                {!isEditingPersonalInfo ? (
                  <button 
                    type="button"
                    onClick={() => setIsEditingPersonalInfo(true)}
                    className="px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold bg-[#111933]/90 text-indigo-300 border border-indigo-500/50 hover:bg-indigo-950/60 hover:border-indigo-400 hover:text-white transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(99,102,241,0.25)] cursor-pointer"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Edit Profile</span>
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <button 
                      type="button"
                      onClick={() => {
                        setIsEditingPersonalInfo(false);
                        setPersonalForm({
                          full_name: profileData?.full_name || '',
                          phone: profileData?.phone || '',
                          location: profileData?.location || '',
                          education: profileData?.education || '',
                          bio: profileData?.bio || ''
                        });
                      }}
                      className="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded-lg transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button 
                      type="button"
                      onClick={handleSavePersonal}
                      disabled={isSavingPersonal}
                      className="px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>{isSavingPersonal ? 'Saving...' : 'Save Changes'}</span>
                    </button>
                  </div>
                )}
              </div>

              {isEditingPersonalInfo ? (
                /* Edit Mode Form */
                <form onSubmit={handleSavePersonal} className="space-y-4">
                  {/* Photo Management in Edit Mode */}
                  <div className="p-4 rounded-xl bg-[#080d1c] border border-[#232f52] flex items-center justify-between gap-4 flex-wrap">
                    <div className="flex items-center gap-3">
                      {avatarUrl ? (
                        <img 
                          src={avatarUrl} 
                          alt="Avatar Preview" 
                          className="w-12 h-12 rounded-full object-cover border border-[#2b3a67]"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-600 to-purple-700 text-white font-bold text-sm flex items-center justify-center border border-[#2b3a67]">
                          {userInitials}
                        </div>
                      )}
                      <div>
                        <p className="text-xs font-semibold text-white">Profile Photo (Optional)</p>
                        <p className="text-[11px] text-slate-400">JPG, PNG, or WebP up to 2MB</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[#131d36] text-indigo-300 border border-indigo-500/40 hover:bg-indigo-900/50 cursor-pointer flex items-center gap-1.5"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        <span>{avatarUrl ? 'Change Photo' : 'Upload Photo'}</span>
                      </button>

                      {avatarUrl && (
                        <button
                          type="button"
                          onClick={handleRemoveAvatar}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-950/40 text-rose-300 border border-rose-500/40 hover:bg-rose-900/50 cursor-pointer flex items-center gap-1.5"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Remove</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Full Legal Name <span className="text-rose-400">*</span>
                      </label>
                      <input 
                        type="text"
                        value={personalForm.full_name}
                        onChange={(e) => setPersonalForm({ ...personalForm, full_name: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0] focus:ring-1 focus:ring-[#5a69f0]"
                        placeholder="e.g. Full Legal Name"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Education &amp; Background
                      </label>
                      <input 
                        type="text"
                        value={personalForm.education}
                        onChange={(e) => setPersonalForm({ ...personalForm, education: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0] focus:ring-1 focus:ring-[#5a69f0]"
                        placeholder="e.g. B.S. in Business Administration"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Phone Number
                      </label>
                      <input 
                        type="tel"
                        value={personalForm.phone}
                        onChange={(e) => setPersonalForm({ ...personalForm, phone: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0] focus:ring-1 focus:ring-[#5a69f0]"
                        placeholder="e.g. +254 700 000000"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Location / City
                      </label>
                      <input 
                        type="text"
                        value={personalForm.location}
                        onChange={(e) => setPersonalForm({ ...personalForm, location: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0] focus:ring-1 focus:ring-[#5a69f0]"
                        placeholder="e.g. Nairobi, Kenya"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Professional Summary / Bio
                    </label>
                    <textarea 
                      rows={3}
                      value={personalForm.bio}
                      onChange={(e) => setPersonalForm({ ...personalForm, bio: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0] focus:ring-1 focus:ring-[#5a69f0]"
                      placeholder="Share your professional summary, background, domains of interest, or strengths..."
                    />
                  </div>
                </form>
              ) : (
                /* View Mode Grid - strictly genuine data only */
                <div className="space-y-6">
                  {/* Personal Info Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-8">
                    <div>
                      <span className="text-xs text-[#8d97b8] font-medium block">Full Name</span>
                      <p className="text-sm font-semibold text-white mt-1">
                        {cleanName}
                      </p>
                    </div>

                    <div>
                      <span className="text-xs text-[#8d97b8] font-medium block">Education &amp; Background</span>
                      <p className="text-sm font-semibold text-white mt-1">
                        {profileData?.education || 'Not specified'}
                      </p>
                    </div>

                    <div>
                      <span className="text-xs text-[#8d97b8] font-medium block">Availability Status</span>
                      <p className="text-sm font-semibold text-white mt-1">
                        {profileData?.availability_status === 'AVAILABLE' 
                          ? 'Available for Tasks' 
                          : profileData?.availability_status === 'PARTIALLY_AVAILABLE'
                          ? 'Partially Available'
                          : profileData?.availability_status || 'Available'}
                      </p>
                    </div>

                    <div>
                      <span className="text-xs text-[#8d97b8] font-medium block">Location</span>
                      <p className="text-sm font-semibold text-white mt-1">
                        {profileData?.location || 'Not specified'}
                      </p>
                    </div>
                  </div>

                  {/* Divider line */}
                  <div className="border-t border-[#1b2542]" />

                  {/* Contact Information Sub-Section */}
                  <div>
                    <h3 className="text-sm font-bold font-sora text-white mb-3">Contact Information</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-y-4 gap-x-6">
                      <div>
                        <span className="text-xs text-[#8d97b8] font-medium block">Email</span>
                        <p className="text-sm font-semibold text-white mt-1">
                          {profileData?.email || user?.email || 'Not specified'}
                        </p>
                      </div>

                      <div>
                        <span className="text-xs text-[#8d97b8] font-medium block">Phone</span>
                        <p className="text-sm font-semibold text-white mt-1">
                          {profileData?.phone || 'Not provided'}
                        </p>
                      </div>

                      <div>
                        <span className="text-xs text-[#8d97b8] font-medium block">Location</span>
                        <p className="text-sm font-semibold text-white mt-1">
                          {profileData?.location || 'Not specified'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Divider line */}
                  <div className="border-t border-[#1b2542]" />

                  {/* Summary Sub-Section */}
                  <div>
                    <h3 className="text-sm font-bold font-sora text-white mb-2">Summary</h3>
                    {profileData?.bio ? (
                      <p className="text-xs sm:text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                        {profileData.bio}
                      </p>
                    ) : (
                      <p className="text-xs sm:text-sm text-slate-400 italic">
                        No professional summary provided yet. Click &quot;Edit Profile&quot; to add your professional introduction.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ================================================================= */}
          {/* TAB 2: VERIFIED EXPERIENCE CARD */}
          {/* ================================================================= */}
          {activeTab === 'experience' && (
            <div className="bg-[#0b1020]/90 border border-[#24335c]/80 rounded-2xl p-6 sm:p-8 shadow-[0_0_30px_rgba(15,23,42,0.8)] backdrop-blur-xl space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#1b2542]">
                <div>
                  <h2 className="text-lg font-bold font-sora text-white">Work Experience &amp; Verified Tenures</h2>
                  <p className="text-xs text-[#8d97b8] mt-0.5">
                    Records are reviewed by administrators. Verified months are calculated without double-counting overlapping tenures.
                  </p>
                </div>

                <button 
                  type="button"
                  onClick={() => setIsAddExpOpen(true)}
                  className="px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.4)] hover:brightness-110 transition-all flex items-center gap-1.5 shrink-0 cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Work Experience</span>
                </button>
              </div>

              {/* Verified Experience Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52]">
                  <span className="text-[11px] font-semibold text-[#8d97b8] uppercase tracking-wider block">
                    Total Verified Experience
                  </span>
                  <p className="text-2xl font-bold text-white mt-1">
                    {verifiedExp.total_experience_months} <span className="text-xs font-normal text-slate-400">months</span>
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    ({(verifiedExp.total_experience_months / 12).toFixed(1)} years merged)
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52]">
                  <span className="text-[11px] font-semibold text-[#8d97b8] uppercase tracking-wider block">
                    Verified Sales Experience
                  </span>
                  <p className="text-2xl font-bold text-white mt-1">
                    {verifiedExp.sales_experience_months} <span className="text-xs font-normal text-slate-400">months</span>
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Input: <code className="text-xs font-mono text-indigo-300">sales_experience_months</code>
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52]">
                  <span className="text-[11px] font-semibold text-[#8d97b8] uppercase tracking-wider block">
                    Verified Customer Service
                  </span>
                  <p className="text-2xl font-bold text-white mt-1">
                    {verifiedExp.customer_service_experience_months} <span className="text-xs font-normal text-slate-400">months</span>
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Input: <code className="text-xs font-mono text-indigo-300">customer_service_experience_months</code>
                  </p>
                </div>
              </div>

              {/* Experience Records List */}
              <div className="space-y-3 pt-2">
                {experiences.length > 0 ? (
                  experiences.map((exp, idx) => (
                    <div 
                      key={exp.experience_id || `exp-${idx}`} 
                      className="p-4 rounded-xl border border-[#232f52] hover:border-indigo-500/50 transition-colors bg-[#0e162d]/80"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-sm font-bold text-white">{exp.job_title}</h4>
                            <span className="text-xs text-slate-500">&bull;</span>
                            <span className="text-xs font-semibold text-slate-300">{exp.company}</span>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-500/40">
                              {exp.work_category}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-xs text-slate-400 mt-1 flex-wrap">
                            <Calendar className="w-3.5 h-3.5 text-slate-500" />
                            <span>
                              {formatDate(exp.start_date)} &rarr; {exp.is_current ? 'Present (Current Role)' : (formatDate(exp.end_date) || 'Ongoing')}
                            </span>
                          </div>

                          {exp.description && (
                            <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                              {exp.description}
                            </p>
                          )}

                          {/* Supervisor Reference Details */}
                          {(exp.supervisor_name || exp.supervisor_email || exp.supervisor_phone) && (
                            <div className="mt-2.5 pt-2 border-t border-[#1b2542] flex flex-wrap items-center justify-between gap-2 text-xs">
                              <div className="flex items-center gap-1.5 text-slate-400">
                                <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                                <span>
                                  Employer Contact: <strong className="text-slate-200">{exp.supervisor_name || 'Former Manager'}</strong>
                                  {exp.supervisor_email && ` • ${exp.supervisor_email}`}
                                  {exp.supervisor_phone && ` • ${exp.supervisor_phone}`}
                                </span>
                              </div>

                              {(exp.verification_status || exp.status) !== 'VERIFIED' && exp.supervisor_email && (
                                <button
                                  type="button"
                                  onClick={() => handleResendSupervisor(exp.experience_id)}
                                  className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-1 cursor-pointer"
                                >
                                  <Send className="w-3 h-3" />
                                  <span>Resend Verification Link</span>
                                </button>
                              )}
                            </div>
                          )}
                        </div>

                        <div className="flex sm:flex-col items-end justify-between sm:justify-start gap-2 shrink-0">
                          {renderVerificationBadge(
                            exp.verification_status || exp.status, 
                            exp.rejection_reason, 
                            exp.reviewer_name
                          )}

                          {(exp.verification_status || exp.status) !== 'VERIFIED' && (
                            <button
                              type="button"
                              onClick={() => setDeleteDialog({
                                isOpen: true,
                                type: 'experience',
                                id: exp.experience_id,
                                title: `${exp.job_title} at ${exp.company}`
                              })}
                              className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-950/40 transition-colors cursor-pointer"
                              title="Withdraw/Delete this experience"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center border border-dashed border-[#232f52] rounded-xl bg-[#0c1224]">
                    <Briefcase className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-slate-300">No verified work experiences submitted yet</p>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                      Add your past sales or client support roles to earn verified tenure months for automated task allocation.
                    </p>
                    <button 
                      type="button"
                      onClick={() => setIsAddExpOpen(true)}
                      className="mt-3 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-900/60 cursor-pointer"
                    >
                      + Add Work Experience
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ================================================================= */}
          {/* TAB 3: CERTIFICATIONS CARD */}
          {/* ================================================================= */}
          {activeTab === 'certifications' && (
            <div className="bg-[#0b1020]/90 border border-[#24335c]/80 rounded-2xl p-6 sm:p-8 shadow-[0_0_30px_rgba(15,23,42,0.8)] backdrop-blur-xl space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#1b2542]">
                <div>
                  <h2 className="text-lg font-bold font-sora text-white">Professional Certifications</h2>
                  <p className="text-xs text-[#8d97b8] mt-0.5">
                    Credentials submitted here are verified against issuer registers. Verified certifications satisfy mandatory task requirements.
                  </p>
                </div>

                <button 
                  type="button"
                  onClick={() => setIsAddCertOpen(true)}
                  className="px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.4)] hover:brightness-110 transition-all flex items-center gap-1.5 shrink-0 cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Certification</span>
                </button>
              </div>

              {/* Verified Certifications Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52]">
                  <span className="text-[11px] font-semibold text-[#8d97b8] uppercase tracking-wider block">
                    Total Certifications
                  </span>
                  <p className="text-2xl font-bold text-white mt-1">
                    {verifiedCerts.certification_count}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Verified and active credentials
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52]">
                  <span className="text-[11px] font-semibold text-[#8d97b8] uppercase tracking-wider block">
                    Domain Relevant Certification
                  </span>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                      verifiedCerts.relevant_certification 
                        ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40' 
                        : 'bg-slate-900 text-slate-400 border-slate-700'
                    }`}>
                      {verifiedCerts.relevant_certification ? 'Domain Qualified (1)' : 'Standard (0)'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Input: <code className="text-xs font-mono text-indigo-300">relevant_certification</code>
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52]">
                  <span className="text-[11px] font-semibold text-[#8d97b8] uppercase tracking-wider block">
                    Certified Leverage Multiplier
                  </span>
                  <p className="text-2xl font-bold text-white mt-1">
                    {verifiedCerts.certified_leverage}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Input: <code className="text-xs font-mono text-indigo-300">certified_leverage</code>
                  </p>
                </div>
              </div>

              {/* Certifications List */}
              <div className="space-y-3 pt-2">
                {certifications.length > 0 ? (
                  certifications.map((cert, idx) => (
                    <div 
                      key={cert.agent_certification_id || cert.agent_cert_id || cert.certificate_number || `cert-${idx}`}
                      className="p-4 rounded-xl border border-[#232f52] hover:border-indigo-500/50 transition-colors bg-[#0e162d]/80"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-sm font-bold text-white">{cert.certification_name}</h4>
                            {cert.issuing_organization && (
                              <span className="text-xs font-semibold text-slate-400">
                                &bull; {cert.issuing_organization}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 flex-wrap">
                            {cert.certificate_number && (
                              <span>ID: <strong className="font-mono text-slate-300">{cert.certificate_number}</strong></span>
                            )}
                            <span>Issued: {formatDate(cert.issue_date)}</span>
                            {cert.expiry_date ? (
                              <span>Expires: {formatDate(cert.expiry_date)}</span>
                            ) : (
                              <span className="text-slate-500">No Expiration</span>
                            )}
                          </div>

                          {cert.credential_url && (
                            <div className="mt-2">
                              <a 
                                href={cert.credential_url} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 hover:underline"
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
                            cert.reviewer_name
                          )}

                          {cert.status !== 'VERIFIED' && (
                            <button
                              type="button"
                              onClick={() => setDeleteDialog({
                                isOpen: true,
                                type: 'certification',
                                id: cert.agent_certification_id || cert.agent_cert_id,
                                title: cert.certification_name
                              })}
                              className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-950/40 transition-colors cursor-pointer"
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
                  <div className="p-8 text-center border border-dashed border-[#232f52] rounded-xl bg-[#0c1224]">
                    <Award className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-slate-300">No certifications submitted yet</p>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                      Submit your professional licenses or training credentials to satisfy task requirements and boost model evaluation scores.
                    </p>
                    <button 
                      type="button"
                      onClick={() => setIsAddCertOpen(true)}
                      className="mt-3 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-900/60 cursor-pointer"
                    >
                      + Submit a Certification
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ================================================================= */}
      {/* MODAL: ADD WORK EXPERIENCE */}
      {/* ================================================================= */}
      {isAddExpOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-[#0d1428] rounded-2xl shadow-2xl border border-[#2b3a67] p-6 sm:p-7 relative max-h-[90vh] overflow-y-auto text-white">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-indigo-400" />
                <h3 className="text-lg font-bold font-sora text-white">Add Work Experience</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAddExpOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddExperience} className="space-y-4 mt-4 text-xs sm:text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Job Title <span className="text-rose-400">*</span>
                </label>
                <input 
                  type="text"
                  value={expForm.job_title}
                  onChange={(e) => setExpForm({ ...expForm, job_title: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                  placeholder="e.g. Senior Sales Specialist"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Company / Organization <span className="text-rose-400">*</span>
                </label>
                <input 
                  type="text"
                  value={expForm.company}
                  onChange={(e) => setExpForm({ ...expForm, company: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                  placeholder="e.g. Apex Global Solutions"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Work Category <span className="text-rose-400">*</span>
                </label>
                <select
                  value={expForm.work_category}
                  onChange={(e) => setExpForm({ ...expForm, work_category: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
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
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Start Date <span className="text-rose-400">*</span>
                  </label>
                  <input 
                    type="date"
                    value={expForm.start_date}
                    onChange={(e) => setExpForm({ ...expForm, start_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    End Date
                  </label>
                  <input 
                    type="date"
                    value={expForm.end_date}
                    disabled={expForm.is_current}
                    onChange={(e) => setExpForm({ ...expForm, end_date: e.target.value })}
                    className={`w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0] ${expForm.is_current ? 'opacity-40 cursor-not-allowed' : ''}`}
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
                  className="w-4 h-4 rounded text-indigo-500 focus:ring-indigo-500 bg-[#080d1c] border-[#232f52]"
                />
                <label htmlFor="is_current" className="text-xs font-medium text-slate-300 cursor-pointer">
                  I currently work in this role
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Role Description &amp; Responsibilities
                </label>
                <textarea 
                  rows={3}
                  value={expForm.description}
                  onChange={(e) => setExpForm({ ...expForm, description: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                  placeholder="Summarize key tasks, quotas, deliverables, or customer interactions handled..."
                />
              </div>

              {/* Supervisor / HR Reference Section */}
              <div className="p-3.5 rounded-xl bg-[#080d1c] border border-[#232f52] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                    <UserCheck className="w-4 h-4 text-indigo-400" />
                    <span>Former Supervisor / Manager Reference <span className="text-rose-400">*</span></span>
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-rose-950/60 text-rose-300 border border-rose-500/40">
                    Mandatory
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Provide your former manager or employer's contact details. Administrators will contact them via email or phone to confirm your role and tenure before approving.
                </p>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                    Supervisor / Manager Name <span className="text-rose-400">*</span>
                  </label>
                  <input 
                    type="text"
                    required
                    value={expForm.supervisor_name}
                    onChange={(e) => setExpForm({ ...expForm, supervisor_name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[#0e162d] border border-[#232f52] text-xs text-white focus:outline-none focus:border-[#5a69f0]"
                    placeholder="e.g. Sarah Jenkins (Direct Manager)"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                      Supervisor Corporate Email <span className="text-rose-400">*</span>
                    </label>
                    <input 
                      type="email"
                      required
                      value={expForm.supervisor_email}
                      onChange={(e) => setExpForm({ ...expForm, supervisor_email: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-[#0e162d] border border-[#232f52] text-xs text-white focus:outline-none focus:border-[#5a69f0]"
                      placeholder="e.g. s.jenkins@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                      Supervisor Phone <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <input 
                      type="tel"
                      value={expForm.supervisor_phone}
                      onChange={(e) => setExpForm({ ...expForm, supervisor_phone: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-[#0e162d] border border-[#232f52] text-xs text-white focus:outline-none focus:border-[#5a69f0]"
                      placeholder="e.g. +254 711 223344"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1b2542]">
                <button 
                  type="button" 
                  onClick={() => setIsAddExpOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isSavingExp}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] cursor-pointer disabled:opacity-50"
                >
                  {isSavingExp ? 'Submitting...' : 'Submit for Verification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* MODAL: ADD CERTIFICATION */}
      {/* ================================================================= */}
      {isAddCertOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-[#0d1428] rounded-2xl shadow-2xl border border-[#2b3a67] p-6 sm:p-7 relative max-h-[90vh] overflow-y-auto text-white">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-indigo-400" />
                <h3 className="text-lg font-bold font-sora text-white">Add Professional Certification</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAddCertOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddCertification} className="space-y-4 mt-4 text-xs sm:text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Certification Name <span className="text-rose-400">*</span>
                </label>
                <input 
                  type="text"
                  value={certForm.certification_name}
                  onChange={(e) => setCertForm({ ...certForm, certification_name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                  placeholder="e.g. HubSpot Inbound Sales Certified"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Issuing Organization
                </label>
                <input 
                  type="text"
                  value={certForm.issuing_organization}
                  onChange={(e) => setCertForm({ ...certForm, issuing_organization: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                  placeholder="e.g. HubSpot Academy, Google, AWS"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Credential / License ID
                  </label>
                  <input 
                    type="text"
                    value={certForm.certificate_number}
                    onChange={(e) => setCertForm({ ...certForm, certificate_number: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white font-mono focus:outline-none focus:border-[#5a69f0]"
                    placeholder="e.g. HS-CERT-98214"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Verification URL
                  </label>
                  <input 
                    type="url"
                    value={certForm.credential_url}
                    onChange={(e) => setCertForm({ ...certForm, credential_url: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                    placeholder="https://..."
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Issue Date <span className="text-rose-400">*</span>
                  </label>
                  <input 
                    type="date"
                    value={certForm.issue_date}
                    onChange={(e) => setCertForm({ ...certForm, issue_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Expiration Date <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input 
                    type="date"
                    value={certForm.expiry_date}
                    onChange={(e) => setCertForm({ ...certForm, expiry_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080d1c] border border-[#232f52] text-sm text-white focus:outline-none focus:border-[#5a69f0]"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1b2542]">
                <button 
                  type="button" 
                  onClick={() => setIsAddCertOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isSavingCert}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] cursor-pointer disabled:opacity-50"
                >
                  {isSavingCert ? 'Submitting...' : 'Submit Certification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* DIALOG: CONFIRM DELETE */}
      {/* ================================================================= */}
      {deleteDialog.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-sm bg-[#0d1428] rounded-2xl shadow-2xl border border-[#2b3a67] p-6 relative text-white">
            <div className="w-10 h-10 rounded-full bg-rose-950/60 text-rose-400 border border-rose-500/40 flex items-center justify-center mb-3">
              <Trash2 className="w-5 h-5" />
            </div>
            <h4 className="text-base font-bold font-sora text-white">Withdraw Submission?</h4>
            <p className="text-xs text-slate-300 mt-1">
              Are you sure you want to remove <strong className="text-white">&quot;{deleteDialog.title}&quot;</strong>? 
              This will withdraw it from the verification queue.
            </p>
            <div className="flex items-center justify-end gap-2.5 mt-5">
              <button 
                type="button"
                onClick={() => setDeleteDialog({ isOpen: false, type: null, id: null, title: '' })}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white cursor-pointer"
              >
                Cancel
              </button>
              <button 
                type="button"
                disabled={isDeleting}
                onClick={handleConfirmDelete}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-md disabled:opacity-50 cursor-pointer"
              >
                {isDeleting ? 'Removing...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
