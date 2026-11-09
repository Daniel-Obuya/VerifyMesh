import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Check, 
  Clock, 
  AlertCircle, 
  Sparkles, 
  Briefcase, 
  ShieldCheck, 
  Award, 
  Calendar, 
  DollarSign, 
  Users, 
  Globe, 
  Building, 
  MapPin, 
  Eye, 
  Save, 
  Send, 
  X, 
  Plus, 
  CheckCircle2, 
  HelpCircle,
  FileText,
  Trash2,
  Search,
  BookOpen
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { adminService } from '../services/adminService';

const SKILL_SUGGESTIONS = [
  'Customer Communication',
  'CRM Management',
  'Ticket Management',
  'Conflict Resolution',
  'Technical Troubleshooting',
  'SLA Adherence',
  'Consultative Selling',
  'Data Accuracy'
];

export const CreateTaskPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { taskId } = useParams();
  const isEditMode = Boolean(taskId);

  // Loading & Metadata
  const [isLoading, setIsLoading] = useState(isEditMode);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [metadata, setMetadata] = useState({ categories: [], certifications: [], skills: [], exams: [], topics: [] });
  const [formError, setFormError] = useState(null);
  const [formSuccess, setFormSuccess] = useState(null);
  const [inlineErrors, setInlineErrors] = useState({});
  const [isDirty, setIsDirty] = useState(false);

  // Modals
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Search & input states
  const [skillInput, setSkillInput] = useState('');
  const [certSearch, setCertSearch] = useState('');

  // Form State
  const [formData, setFormData] = useState({
    task_name: '',
    category_id: '',
    description: '',
    deliverables: '',
    required_skills: [],
    work_arrangement: 'Remote',
    location: '',
    payment_type: 'Hourly',
    currency: 'KES',
    hourly_rate_min: '',
    hourly_rate_max: '',
    fixed_budget: '',
    positions_count: 1,
    application_deadline: '',
    expected_duration: '3 months',
    minimum_experience_months: 0,
    required_certification_ids: [],
    exam_required: false,
    required_topic_ids: [],
    status: 'ACTIVE'
  });

  // Fetch Metadata & Existing Task (if edit mode)
  useEffect(() => {
    let isMounted = true;

    const loadPageData = async () => {
      try {
        const metaRes = await adminService.getTaskMetadata();
        if (isMounted && metaRes?.data) {
          setMetadata(metaRes.data);
        }

        if (isEditMode) {
          const taskRes = await adminService.getTask(taskId);
          if (isMounted && taskRes?.data) {
            const t = taskRes.data;
            const skillsArr = t.required_skills 
              ? t.required_skills.split(',').map(s => s.trim()).filter(Boolean)
              : [];

            let certIds = [];
            if (Array.isArray(t.required_certification_ids) && t.required_certification_ids.length > 0) {
              certIds = t.required_certification_ids.map(String);
            } else if (t.required_certification_id) {
              certIds = [String(t.required_certification_id)];
            }

            let topicIds = [];
            if (Array.isArray(t.required_topic_ids) && t.required_topic_ids.length > 0) {
              topicIds = t.required_topic_ids.map(String);
            }

            setFormData({
              task_name: t.task_name || '',
              category_id: t.category_id ? String(t.category_id) : '',
              description: t.description || '',
              deliverables: t.deliverables || '',
              required_skills: skillsArr,
              work_arrangement: t.work_arrangement || 'Remote',
              location: t.location || '',
              payment_type: t.payment_type || 'Hourly',
              currency: t.currency || 'KES',
              hourly_rate_min: t.hourly_rate_min != null ? String(t.hourly_rate_min) : '',
              hourly_rate_max: t.hourly_rate_max != null ? String(t.hourly_rate_max) : '',
              fixed_budget: t.fixed_budget != null ? String(t.fixed_budget) : '',
              positions_count: t.positions_count || 1,
              application_deadline: t.application_deadline ? t.application_deadline.split('T')[0] : '',
              expected_duration: t.expected_duration || '3 months',
              minimum_experience_months: t.minimum_experience_months || 0,
              required_certification_ids: certIds,
              exam_required: Boolean(t.exam_required),
              required_topic_ids: topicIds,
              status: t.status || 'ACTIVE'
            });
          }
        }
      } catch (err) {
        if (isMounted) {
          setFormError('Failed to load form prerequisites. Please verify server connection.');
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadPageData();

    return () => {
      isMounted = false;
    };
  }, [taskId, isEditMode]);

  // Track form changes
  const updateField = (field, value) => {
    setIsDirty(true);
    setFormData(prev => ({ ...prev, [field]: value }));
    if (inlineErrors[field]) {
      setInlineErrors(prev => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  // Skill Tags Handlers
  const handleAddSkill = (skillToAdd) => {
    const val = (skillToAdd || skillInput).trim();
    if (!val) return;
    if (!formData.required_skills.includes(val)) {
      updateField('required_skills', [...formData.required_skills, val]);
    }
    setSkillInput('');
  };

  const handleRemoveSkill = (skillToRemove) => {
    updateField(
      'required_skills',
      formData.required_skills.filter(s => s !== skillToRemove)
    );
  };

  // Certification Multi-select Handlers
  const handleToggleCertification = (certId) => {
    const idStr = String(certId);
    const exists = formData.required_certification_ids.includes(idStr);
    if (exists) {
      updateField(
        'required_certification_ids',
        formData.required_certification_ids.filter(id => id !== idStr)
      );
    } else {
      updateField(
        'required_certification_ids',
        [...formData.required_certification_ids, idStr]
      );
    }
  };

  const handleClearCertifications = () => {
    updateField('required_certification_ids', []);
  };

  // Assessment Topic Multi-select Handlers
  const handleToggleTopic = (topicId) => {
    const idStr = String(topicId);
    const exists = formData.required_topic_ids.includes(idStr);
    if (exists) {
      updateField(
        'required_topic_ids',
        formData.required_topic_ids.filter(id => id !== idStr)
      );
    } else {
      updateField(
        'required_topic_ids',
        [...formData.required_topic_ids, idStr]
      );
    }
  };

  // Quick Preset for Application Deadline
  const setDeadlinePreset = (days) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    updateField('application_deadline', d.toISOString().split('T')[0]);
  };

  // Validate form client-side
  const validateForm = (isPublishing = true) => {
    const errors = {};

    if (!formData.task_name.trim()) {
      errors.task_name = 'Task title is required.';
    } else if (formData.task_name.trim().length < 5) {
      errors.task_name = 'Task title must be at least 5 characters.';
    } else {
      const generic = ['task 1', 'task 2', 'test', 'test task', 'new task', 'sample task', 'task'];
      if (generic.includes(formData.task_name.trim().toLowerCase())) {
        errors.task_name = 'Task title is too generic. Provide a descriptive title.';
      }
    }

    if (!formData.category_id) {
      errors.category_id = 'Task category is required.';
    }

    if (isPublishing) {
      if (!formData.description.trim()) {
        errors.description = 'Detailed task description is required.';
      } else if (formData.description.trim().length < 20) {
        errors.description = 'Description must be at least 20 characters.';
      }

      if (['Hybrid', 'On-site'].includes(formData.work_arrangement) && !formData.location.trim()) {
        errors.location = `Location is required for ${formData.work_arrangement} work arrangement.`;
      }

      if (formData.payment_type === 'Hourly') {
        const minRate = parseFloat(formData.hourly_rate_min);
        const maxRate = parseFloat(formData.hourly_rate_max);

        if (!formData.hourly_rate_min || isNaN(minRate) || minRate <= 0) {
          errors.hourly_rate_min = 'Valid minimum hourly rate is required.';
        }
        if (formData.hourly_rate_max && !isNaN(maxRate) && maxRate < minRate) {
          errors.hourly_rate_max = 'Maximum hourly rate cannot be less than minimum rate.';
        }
      } else if (formData.payment_type === 'Fixed Budget') {
        const budget = parseFloat(formData.fixed_budget);
        if (!formData.fixed_budget || isNaN(budget) || budget <= 0) {
          errors.fixed_budget = 'Valid total fixed budget is required.';
        }
      }

      if (!formData.application_deadline) {
        errors.application_deadline = 'Application deadline is required when publishing.';
      } else {
        const deadlineDate = new Date(formData.application_deadline);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (deadlineDate < today) {
          errors.application_deadline = 'Application deadline must be a future date.';
        }
      }

      if (formData.exam_required) {
        if (!formData.required_topic_ids || formData.required_topic_ids.length === 0) {
          errors.required_topic_ids = 'Please select at least one assessment topic required for this task.';
        }
      }
    }

    setInlineErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Submit Handler: Draft or Publish
  const handleSubmit = async (targetStatus) => {
    setFormError(null);
    setFormSuccess(null);

    const isPublishing = targetStatus === 'ACTIVE';
    const isValid = validateForm(isPublishing);

    if (!isValid) {
      setFormError('Please review and correct highlighted fields before submitting.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        task_name: formData.task_name.trim(),
        category_id: parseInt(formData.category_id, 10),
        description: formData.description.trim(),
        deliverables: formData.deliverables.trim() || null,
        required_skills: formData.required_skills,
        work_arrangement: formData.work_arrangement,
        location: formData.location.trim() || null,
        payment_type: formData.payment_type,
        currency: formData.currency || 'KES',
        hourly_rate_min: formData.payment_type === 'Hourly' && formData.hourly_rate_min ? parseFloat(formData.hourly_rate_min) : null,
        hourly_rate_max: formData.payment_type === 'Hourly' && formData.hourly_rate_max ? parseFloat(formData.hourly_rate_max) : null,
        fixed_budget: formData.payment_type === 'Fixed Budget' && formData.fixed_budget ? parseFloat(formData.fixed_budget) : null,
        positions_count: parseInt(formData.positions_count, 10) || 1,
        application_deadline: formData.application_deadline || null,
        expected_duration: formData.expected_duration || null,
        minimum_experience_months: parseInt(formData.minimum_experience_months, 10) || 0,
        required_certification_ids: formData.required_certification_ids.map(id => parseInt(id, 10)).filter(Boolean),
        required_certification_id: formData.required_certification_ids.length > 0 ? parseInt(formData.required_certification_ids[0], 10) : null,
        exam_required: Boolean(formData.exam_required),
        required_topic_ids: formData.exam_required ? formData.required_topic_ids.map(id => parseInt(id, 10)).filter(Boolean) : [],
        status: targetStatus
      };

      if (isEditMode) {
        await adminService.updateTask(taskId, payload);
        setFormSuccess(`Task #${taskId} updated successfully as ${targetStatus}.`);
      } else {
        await adminService.createTask(payload);
        setFormSuccess(`Task created successfully as ${targetStatus}.`);
      }

      setIsDirty(false);

      setTimeout(() => {
        navigate('/workforce/dashboard');
      }, 1200);

    } catch (err) {
      const message = err.response?.data?.error || err.message || 'Operation failed. Please try again.';
      setFormError(message);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Safe Cancel handler
  const handleCancelClick = () => {
    if (isDirty) {
      setIsCancelModalOpen(true);
    } else {
      navigate('/workforce/dashboard');
    }
  };

  // Selected Category & Metadata Lookups
  const selectedCategory = metadata.categories.find(c => String(c.category_id) === String(formData.category_id));

  const selectedCerts = useMemo(() => {
    return (metadata.certifications || []).filter(c => 
      formData.required_certification_ids.includes(String(c.certification_id))
    );
  }, [metadata.certifications, formData.required_certification_ids]);

  const filteredCerts = useMemo(() => {
    if (!certSearch.trim()) return metadata.certifications || [];
    const term = certSearch.toLowerCase();
    return (metadata.certifications || []).filter(c => 
      c.certification_name?.toLowerCase().includes(term) ||
      c.description?.toLowerCase().includes(term)
    );
  }, [metadata.certifications, certSearch]);

  const availableTopics = useMemo(() => {
    if (metadata.topics && metadata.topics.length > 0) {
      return metadata.topics;
    }
    return (metadata.exams || []).map(e => ({
      topic_id: e.exam_id,
      topic_name: e.exam_name,
      category_name: e.category_name,
      description: e.description,
      passing_score: e.passing_score || 70.0,
      estimated_minutes: 15
    }));
  }, [metadata.topics, metadata.exams]);

  const selectedTopics = useMemo(() => {
    return availableTopics.filter(top => 
      formData.required_topic_ids.includes(String(top.topic_id))
    );
  }, [availableTopics, formData.required_topic_ids]);

  // Officer display name
  const rawOfficerName = user?.full_name || user?.fullName || 'Workforce Officer';
  const officerName = rawOfficerName.replace(/\s*\(Verified\)/gi, '').trim();
  const officerInitials = officerName
    ? officerName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'WO';

  return (
    <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex flex-col font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-indigo-600/6 blur-[140px] rounded-full" />
        <div className="absolute top-1/3 right-10 w-[500px] h-[350px] bg-blue-500/5 blur-[130px] rounded-full" />
      </div>

      {/* Top Header */}
      <header className="h-16 bg-[#080d1a]/95 border-b border-[#1b2542] px-6 sm:px-8 flex items-center justify-between shrink-0 sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <Link to="/workforce/dashboard" className="flex items-center gap-2.5 text-white hover:text-indigo-300 transition-colors">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#4b5bd8] to-[#6f7dff] flex items-center justify-center p-1.5 shadow-lg shadow-indigo-500/25 shrink-0">
              <svg viewBox="0 0 28 28" fill="none" className="w-full h-full text-white">
                <path d="M6 8V18C6 20.2091 7.79086 22 10 22H20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M10 17L15 13L21 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="10" cy="17" r="2.2" fill="currentColor" />
                <circle cx="15" cy="13" r="2.2" fill="currentColor" />
                <circle cx="21" cy="16" r="2.2" fill="currentColor" />
              </svg>
            </div>
            <span className="font-sora text-base sm:text-lg font-bold text-white tracking-tight">VerifyMesh</span>
          </Link>
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500">
            <span>/</span>
            <span>Workforce Portal</span>
            <span>/</span>
            <span>Tasks</span>
            <span>/</span>
            <span className="font-semibold text-slate-300">
              {isEditMode ? `Edit Task #${taskId}` : 'Create New Task'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleCancelClick}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-[#151f38]/60 hover:bg-[#151f38] border border-[#1e2a4a] transition-all cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Catalog
          </button>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
            {officerInitials}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8 max-w-4xl w-full mx-auto space-y-6 relative z-10">
        {/* Page Title & Status Banner */}
        <div className="bg-[#0b1020] rounded-2xl p-6 sm:p-7 border border-[#1b2542] shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase">
                WORKFORCE ALLOCATION &bull; TASK SPECIFICATION
              </span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                formData.status === 'ACTIVE' 
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40' 
                  : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
              }`}>
                {isEditMode ? `Mode: Editing (${formData.status})` : 'New Task Formulation'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold font-sora text-white mt-1 tracking-tight">
              {isEditMode ? 'Edit Task Specifications' : 'Create Task Specification'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Define task deliverables, compensation parameters, mandatory qualifications, and prerequisite assessment topics.
            </p>
          </div>
        </div>

        {/* Global Alert / Feedback */}
        {formError && (
          <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 flex items-start gap-3 animate-in fade-in duration-200">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-rose-200">Task Submission Error</p>
              <p className="text-xs text-rose-300 mt-0.5 leading-relaxed">{formError}</p>
            </div>
          </div>
        )}

        {formSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/40 flex items-start gap-3 animate-in fade-in duration-200">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-emerald-200">Success</p>
              <p className="text-xs text-emerald-300 mt-0.5 leading-relaxed">{formSuccess}</p>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="py-20 text-center">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-400">Loading task specification and metadata...</p>
          </div>
        ) : (
          <form onSubmit={(e) => e.preventDefault()} className="space-y-6">

            {/* ========================================================= */}
            {/* SECTION A: TASK OVERVIEW */}
            {/* ========================================================= */}
            <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 sm:p-7 shadow-xl space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-[#1b2542]">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center font-bold text-xs font-sora">
                  A
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold font-sora text-white">Task Overview</h2>
                  <p className="text-xs text-slate-400">
                    Provide the essential information about the task and what the assigned agents will be expected to do.
                  </p>
                </div>
              </div>

              {/* Task Title */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Task Title <span className="text-rose-400">*</span>
                  </label>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {formData.task_name.length}/150
                  </span>
                </div>
                <input
                  type="text"
                  maxLength={150}
                  placeholder="e.g. Customer Support Representative"
                  value={formData.task_name}
                  onChange={(e) => updateField('task_name', e.target.value)}
                  className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                    inlineErrors.task_name
                      ? 'border-rose-500/60 bg-rose-950/20 text-white placeholder:text-rose-300 focus:border-rose-500'
                      : 'bg-[#0d1428] border-[#1e2a4a] text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                  }`}
                />
                {inlineErrors.task_name && (
                  <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {inlineErrors.task_name}
                  </p>
                )}
              </div>

              {/* Category & Work Arrangement */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Category Dropdown */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Task Category <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={formData.category_id}
                    onChange={(e) => updateField('category_id', e.target.value)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                      inlineErrors.category_id
                        ? 'border-rose-500/60 bg-rose-950/20 text-white focus:border-rose-500'
                        : 'bg-[#0d1428] border-[#1e2a4a] text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                    }`}
                  >
                    <option value="" className="bg-[#0d1428] text-slate-400">Select Supported Category</option>
                    {metadata.categories.map((cat) => (
                      <option key={cat.category_id} value={cat.category_id} className="bg-[#0d1428] text-white">
                        {cat.category_name}
                      </option>
                    ))}
                  </select>
                  {inlineErrors.category_id && (
                    <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {inlineErrors.category_id}
                    </p>
                  )}
                </div>

                {/* Work Arrangement */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Work Arrangement <span className="text-rose-400">*</span>
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { val: 'Remote', label: 'Remote', icon: Globe },
                      { val: 'Hybrid', label: 'Hybrid', icon: Building },
                      { val: 'On-site', label: 'On-site', icon: MapPin }
                    ].map(({ val, label, icon: Icon }) => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => updateField('work_arrangement', val)}
                        className={`flex flex-col items-center justify-center py-2 px-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                          formData.work_arrangement === val
                            ? 'bg-indigo-600/25 border-indigo-500/60 text-white shadow-xs'
                            : 'bg-[#0d1428] border-[#1e2a4a] text-slate-400 hover:text-slate-200 hover:border-[#2b3a67]'
                        }`}
                      >
                        <Icon className="w-4 h-4 mb-1" />
                        <span>{label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Location (conditional when Hybrid or On-site) */}
              {formData.work_arrangement !== 'Remote' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Location / Eligible Region <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Nairobi Central Hub / Kenya Regional Offices"
                    value={formData.location}
                    onChange={(e) => updateField('location', e.target.value)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                      inlineErrors.location
                        ? 'border-rose-500/60 bg-rose-950/20 text-white placeholder:text-rose-300 focus:border-rose-500'
                        : 'bg-[#0d1428] border-[#1e2a4a] text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                    }`}
                  />
                  {inlineErrors.location && (
                    <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {inlineErrors.location}
                    </p>
                  )}
                </div>
              )}

              {/* Detailed Description */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Detailed Description <span className="text-rose-400">*</span>
                  </label>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {formData.description.length} chars (min 20)
                  </span>
                </div>
                <textarea
                  rows={4}
                  placeholder="Explain the purpose, scope and nature of the task..."
                  value={formData.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                    inlineErrors.description
                      ? 'border-rose-500/60 bg-rose-950/20 text-white placeholder:text-rose-300 focus:border-rose-500'
                      : 'bg-[#0d1428] border-[#1e2a4a] text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                  }`}
                />
                {inlineErrors.description && (
                  <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {inlineErrors.description}
                  </p>
                )}
              </div>

              {/* Responsibilities & Expected Deliverables */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Responsibilities &amp; Expected Deliverables
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe concrete responsibilities and expected outputs (e.g.&#10;- Respond to customer enquiries within SLA&#10;- Resolve support tickets promptly&#10;- Submit weekly activity reports)"
                  value={formData.deliverables}
                  onChange={(e) => updateField('deliverables', e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white placeholder:text-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition-all"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Clear outline of responsibilities, operational deliverables, and qualitative standards.
                </p>
              </div>

              {/* Relevant Skills & Keywords */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Relevant Skills &amp; Keywords
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="Type a skill and press Enter (or select suggestions below)..."
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddSkill();
                      }
                    }}
                    className="flex-1 px-3.5 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white placeholder:text-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition-all"
                  />
                  <button
                    onClick={() => handleAddSkill()}
                    type="button"
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#151f38] hover:bg-[#1c294d] text-white border border-[#2b3a67] flex items-center gap-1 transition-all cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>

                {/* Selected Skills Tags */}
                {formData.required_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2.5">
                    {formData.required_skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 text-xs font-semibold"
                      >
                        {skill}
                        <button
                          type="button"
                          onClick={() => handleRemoveSkill(skill)}
                          className="hover:text-rose-400 transition-colors cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {/* Suggestions */}
                <div className="flex items-center gap-1.5 flex-wrap pt-1">
                  <span className="text-[11px] text-slate-500 font-medium">Suggestions:</span>
                  {SKILL_SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleAddSkill(s)}
                      disabled={formData.required_skills.includes(s)}
                      className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#0d1428] border border-[#1e2a4a] text-slate-400 hover:text-white hover:border-indigo-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
                    >
                      + {s}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-slate-500 mt-1.5 italic">
                  * Descriptive task tags only. These do not independently gate qualification.
                </p>
              </div>
            </div>

            {/* ========================================================= */}
            {/* SECTION B: COMPENSATION AND AVAILABILITY */}
            {/* ========================================================= */}
            <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 sm:p-7 shadow-xl space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-[#1b2542]">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center font-bold text-xs font-sora">
                  B
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold font-sora text-white">Compensation &amp; Availability</h2>
                  <p className="text-xs text-slate-400">
                    Define how the agent will be compensated, the number of available positions and the engagement period.
                  </p>
                </div>
              </div>

              {/* Payment Type Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Payment Type <span className="text-rose-400">*</span>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => updateField('payment_type', 'Hourly')}
                    className={`flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      formData.payment_type === 'Hourly'
                        ? 'bg-indigo-600/20 text-white border-indigo-500/60 shadow-sm'
                        : 'bg-[#0d1428] text-slate-400 border-[#1e2a4a] hover:border-[#2b3a67] hover:text-slate-200'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      formData.payment_type === 'Hourly' ? 'bg-indigo-500/25 text-indigo-400' : 'bg-[#151f38] text-slate-400'
                    }`}>
                      <Clock className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-white">Hourly Rate</p>
                      <p className="text-[11px] text-slate-400">Compensate per verified logged hour</p>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => updateField('payment_type', 'Fixed Budget')}
                    className={`flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      formData.payment_type === 'Fixed Budget'
                        ? 'bg-indigo-600/20 text-white border-indigo-500/60 shadow-sm'
                        : 'bg-[#0d1428] text-slate-400 border-[#1e2a4a] hover:border-[#2b3a67] hover:text-slate-200'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      formData.payment_type === 'Fixed Budget' ? 'bg-indigo-500/25 text-indigo-400' : 'bg-[#151f38] text-slate-400'
                    }`}>
                      <DollarSign className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-white">Fixed Project Budget</p>
                      <p className="text-[11px] text-slate-400">Total milestone allocation</p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Currency & Compensation Amounts */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Currency <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={formData.currency}
                    onChange={(e) => updateField('currency', e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white focus:outline-none focus:border-indigo-500 text-sm font-semibold transition-all"
                  >
                    <option value="KES" className="bg-[#0d1428] text-white">KES (Kenyan Shilling) — Standard</option>
                  </select>
                </div>

                {formData.payment_type === 'Hourly' ? (
                  <>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Minimum Hourly Rate ({formData.currency}) <span className="text-rose-400">*</span>
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="100"
                        placeholder="e.g. 2500"
                        value={formData.hourly_rate_min}
                        onChange={(e) => updateField('hourly_rate_min', e.target.value)}
                        className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                          inlineErrors.hourly_rate_min
                            ? 'border-rose-500/60 bg-rose-950/20 text-white placeholder:text-rose-300 focus:border-rose-500'
                            : 'bg-[#0d1428] border-[#1e2a4a] text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                        }`}
                      />
                      {inlineErrors.hourly_rate_min && (
                        <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />
                          {inlineErrors.hourly_rate_min}
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Maximum Hourly Rate ({formData.currency})
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="100"
                        placeholder="e.g. 4500 (Optional)"
                        value={formData.hourly_rate_max}
                        onChange={(e) => updateField('hourly_rate_max', e.target.value)}
                        className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                          inlineErrors.hourly_rate_max
                            ? 'border-rose-500/60 bg-rose-950/20 text-white placeholder:text-rose-300 focus:border-rose-500'
                            : 'bg-[#0d1428] border-[#1e2a4a] text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                        }`}
                      />
                      {inlineErrors.hourly_rate_max && (
                        <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />
                          {inlineErrors.hourly_rate_max}
                        </p>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Total Project Budget ({formData.currency}) <span className="text-rose-400">*</span>
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="500"
                      placeholder="e.g. 120000"
                      value={formData.fixed_budget}
                      onChange={(e) => updateField('fixed_budget', e.target.value)}
                      className={`w-full px-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                        inlineErrors.fixed_budget
                          ? 'border-rose-500/60 bg-rose-950/20 text-white placeholder:text-rose-300 focus:border-rose-500'
                          : 'bg-[#0d1428] border-[#1e2a4a] text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                      }`}
                    />
                    {inlineErrors.fixed_budget && (
                      <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" />
                        {inlineErrors.fixed_budget}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Positions Count, Deadline & Expected Duration */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-[#1b2542]">
                {/* Positions */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Available Positions <span className="text-rose-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      min="1"
                      value={formData.positions_count}
                      onChange={(e) => updateField('positions_count', Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="w-full pl-9 pr-3.5 py-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition-all"
                    />
                    <Users className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Maximum assignable candidates</p>
                </div>

                {/* Application Deadline */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Application Deadline <span className="text-rose-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      value={formData.application_deadline}
                      onChange={(e) => updateField('application_deadline', e.target.value)}
                      className={`w-full pl-9 pr-3.5 py-2.5 rounded-xl border text-sm transition-all focus:outline-none ${
                        inlineErrors.application_deadline
                          ? 'border-rose-500/60 bg-rose-950/20 text-white focus:border-rose-500'
                          : 'bg-[#0d1428] border-[#1e2a4a] text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40'
                      }`}
                    />
                    <Calendar className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  </div>
                  {inlineErrors.application_deadline ? (
                    <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {inlineErrors.application_deadline}
                    </p>
                  ) : (
                    <div className="flex items-center gap-1 mt-1">
                      <button
                        type="button"
                        onClick={() => setDeadlinePreset(14)}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
                      >
                        +14 days
                      </button>
                      <span className="text-[10px] text-slate-600">&bull;</span>
                      <button
                        type="button"
                        onClick={() => setDeadlinePreset(30)}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
                      >
                        +30 days
                      </button>
                      <span className="text-[10px] text-slate-600">&bull;</span>
                      <button
                        type="button"
                        onClick={() => setDeadlinePreset(60)}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
                      >
                        +60 days
                      </button>
                    </div>
                  )}
                </div>

                {/* Expected Duration */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Expected Duration <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={formData.expected_duration}
                    onChange={(e) => updateField('expected_duration', e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white text-sm focus:outline-none focus:border-indigo-500 transition-all"
                  >
                    <option value="1 month" className="bg-[#0d1428] text-white">1 Month</option>
                    <option value="3 months" className="bg-[#0d1428] text-white">3 Months</option>
                    <option value="6 months" className="bg-[#0d1428] text-white">6 Months</option>
                    <option value="12 months" className="bg-[#0d1428] text-white">12 Months</option>
                    <option value="Ongoing / Milestone-based" className="bg-[#0d1428] text-white">Ongoing / Milestone-based</option>
                  </select>
                  <p className="text-[11px] text-slate-500 mt-1">Engagement timeframe</p>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* SECTION C: ELIGIBILITY REQUIREMENTS */}
            {/* ========================================================= */}
            <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 sm:p-7 shadow-xl space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-[#1b2542]">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center font-bold text-xs font-sora">
                  C
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold font-sora text-white">Eligibility Requirements</h2>
                  <p className="text-xs text-slate-400">
                    Define the mandatory conditions an agent must satisfy before being allowed to apply for the task.
                  </p>
                </div>
              </div>

              {/* 1. Minimum Verified Work Experience */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Minimum Verified Work Experience
                </label>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="relative">
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={formData.minimum_experience_months}
                      onChange={(e) => updateField('minimum_experience_months', Math.max(0, parseInt(e.target.value, 10) || 0))}
                      className="w-36 px-3.5 py-2.5 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white text-sm focus:outline-none focus:border-indigo-500 transition-all font-mono"
                    />
                    <span className="text-xs text-slate-500 absolute right-3 top-1/2 -translate-y-1/2">
                      months
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    {[
                      { m: 0, label: 'No minimum' },
                      { m: 6, label: '6 months' },
                      { m: 12, label: '12 months' },
                      { m: 18, label: '18 months' },
                      { m: 24, label: '24 months' }
                    ].map(({ m, label }) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => updateField('minimum_experience_months', m)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                          formData.minimum_experience_months === m
                            ? 'bg-indigo-600/25 text-indigo-300 border-indigo-500/60 shadow-xs'
                            : 'bg-[#0d1428] text-slate-400 border-[#1e2a4a] hover:border-[#2b3a67] hover:text-slate-200'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-[11px] text-slate-500 mt-1.5">
                  The system evaluates verified work experience. Unverified, pending, or rejected entries do not qualify.
                </p>
              </div>

              {/* 2. Required Certifications (Searchable Multi-select) */}
              <div className="pt-2 border-t border-[#1b2542] space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">
                    Required Certifications (Accreditation Catalogue)
                  </label>
                  {formData.required_certification_ids.length > 0 && (
                    <button
                      type="button"
                      onClick={handleClearCertifications}
                      className="text-[11px] text-rose-400 hover:text-rose-300 transition-colors cursor-pointer"
                    >
                      Clear all certifications (Open)
                    </button>
                  )}
                </div>

                {/* Selected Certifications Chips */}
                {selectedCerts.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-[11px] text-slate-400 font-medium">
                      Mandatory Credentials ({selectedCerts.length} selected — all must be active &amp; verified):
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedCerts.map((cert) => (
                        <div
                          key={cert.certification_id}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-950/40 text-emerald-300 border border-emerald-500/40 text-xs font-semibold"
                        >
                          <Award className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>{cert.certification_name}</span>
                          <button
                            type="button"
                            onClick={() => handleToggleCertification(cert.certification_id)}
                            className="text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
                            title="Remove certification"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-[#0d1428] border border-dashed border-[#1e2a4a] text-slate-400 text-xs flex items-center justify-between">
                    <span>No mandatory certifications required (Open to all verified agents).</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">Open Gating</span>
                  </div>
                )}

                {/* Search & Certification Selection Grid */}
                <div className="space-y-2">
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search certification catalogue by name or topic..."
                      value={certSearch}
                      onChange={(e) => setCertSearch(e.target.value)}
                      className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-[#0d1428] border border-[#1e2a4a] text-white text-xs focus:outline-none focus:border-indigo-500 transition-all placeholder:text-slate-500"
                    />
                    <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  </div>

                  <div className="max-h-48 overflow-y-auto space-y-1.5 p-2 rounded-xl bg-[#080d1a] border border-[#1b2542]">
                    {filteredCerts.map((cert) => {
                      const isSelected = formData.required_certification_ids.includes(String(cert.certification_id));
                      return (
                        <button
                          key={cert.certification_id}
                          type="button"
                          onClick={() => handleToggleCertification(cert.certification_id)}
                          className={`w-full text-left p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between cursor-pointer ${
                            isSelected
                              ? 'bg-emerald-950/30 border-emerald-500/60 text-white'
                              : 'bg-[#0d1428] border-[#1e2a4a] text-slate-300 hover:border-[#2b3a67]'
                          }`}
                        >
                          <div className="flex items-start gap-2.5">
                            <div className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center border transition-all ${
                              isSelected ? 'bg-emerald-500 border-emerald-400 text-black' : 'border-slate-600 bg-transparent'
                            }`}>
                              {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                            </div>
                            <div>
                              <p className="font-bold text-white leading-tight">{cert.certification_name}</p>
                              {cert.description && (
                                <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">{cert.description}</p>
                              )}
                            </div>
                          </div>
                          {cert.validity_period_months && (
                            <span className="text-[10px] text-slate-400 font-medium shrink-0 ml-2">
                              {cert.validity_period_months}m validity
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <p className="text-[11px] text-slate-500">
                  Selected certifications must be verified before they satisfy task requirements. Pending and rejected certifications do not qualify an agent.
                </p>
              </div>

              {/* 3. Dynamic Eligibility Rule Summary */}
              <div className="pt-2 border-t border-[#1b2542]">
                <div className="p-4 rounded-xl bg-[#0d1428] border border-[#1e2a4a] space-y-2.5">
                  <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4" />
                    <span>Eligibility Rule Summary (Generated Live)</span>
                  </div>

                  <ul className="text-xs text-slate-300 space-y-1.5 list-disc pl-4">
                    <li>
                      <strong>Work Experience:</strong>{' '}
                      {formData.minimum_experience_months > 0 
                        ? `Minimum ${formData.minimum_experience_months} months of verified employment tenure required.`
                        : 'No minimum experience requirement (Open).'}
                    </li>
                    <li>
                      <strong>Accreditation:</strong>{' '}
                      {selectedCerts.length > 0 
                        ? `${selectedCerts.length} mandatory certification(s) required (${selectedCerts.map(c => c.certification_name).join(', ')}). All must be active and verified.`
                        : 'No mandatory certifications required.'}
                    </li>
                    <li>
                      <strong>Competency Assessments:</strong>{' '}
                      {formData.exam_required 
                        ? (selectedTopics.length > 0 
                            ? `Must pass ${selectedTopics.length} assessment topic(s) with at least 70% passing score (${selectedTopics.map(t => t.topic_name).join(', ')}).`
                            : 'Assessment required; select at least one topic in Section D below.')
                        : 'No prerequisite assessment required.'}
                    </li>
                  </ul>

                  <div className="pt-2 border-t border-[#1e2a4a] text-[11px] text-slate-400">
                    &bull; The deterministic eligibility engine evaluates all configured mandatory requirements. An agent qualifies only when every applicable requirement is satisfied.
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* SECTION D: ASSESSMENT CONFIGURATION */}
            {/* ========================================================= */}
            <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 sm:p-7 shadow-xl space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-[#1b2542]">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center font-bold text-xs font-sora">
                  D
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold font-sora text-white">Assessment Configuration</h2>
                  <p className="text-xs text-slate-400">
                    Configure the task-specific assessments agents must pass before applying.
                  </p>
                </div>
              </div>

              {/* 1. Require Task-Specific Competency Assessment Toggle */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Require Task-Specific Competency Assessment? <span className="text-rose-400">*</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => updateField('exam_required', false)}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      !formData.exam_required
                        ? 'bg-indigo-600/20 border-indigo-500/60 text-white shadow-xs'
                        : 'bg-[#0d1428] border-[#1e2a4a] text-slate-400 hover:border-[#2b3a67]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">No</span>
                      {!formData.exam_required && <Check className="w-4 h-4 text-indigo-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      No prerequisite competency assessment required for this task.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => updateField('exam_required', true)}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      formData.exam_required
                        ? 'bg-purple-600/20 border-purple-500/60 text-white shadow-xs'
                        : 'bg-[#0d1428] border-[#1e2a4a] text-slate-400 hover:border-[#2b3a67]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Yes</span>
                      {formData.exam_required && <Check className="w-4 h-4 text-purple-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Require candidates to complete and pass designated topic assessments.
                    </p>
                  </button>
                </div>
              </div>

              {/* Conditional Section D inputs when exam_required is True */}
              {formData.exam_required && (
                <div className="space-y-4 pt-2 border-t border-[#1b2542]">
                  {/* Topic selection */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-semibold text-slate-300">
                        Required Assessment Topics <span className="text-rose-400">*</span>
                      </label>
                      <span className="text-[11px] text-purple-400 font-medium">
                        {formData.required_topic_ids.length} topic(s) selected
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {availableTopics.map((topic) => {
                        const isSelected = formData.required_topic_ids.includes(String(topic.topic_id));
                        return (
                          <button
                            key={topic.topic_id}
                            type="button"
                            onClick={() => handleToggleTopic(topic.topic_id)}
                            className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between cursor-pointer ${
                              isSelected
                                ? 'bg-purple-950/30 border-purple-500/60 text-white shadow-xs'
                                : 'bg-[#0d1428] border-[#1e2a4a] text-slate-300 hover:border-[#2b3a67]'
                            }`}
                          >
                            <div>
                              <div className="flex items-start justify-between gap-2">
                                <span className="text-xs font-bold text-white leading-tight">
                                  {topic.topic_name}
                                </span>
                                <div className={`w-4 h-4 rounded shrink-0 flex items-center justify-center border transition-all ${
                                  isSelected ? 'bg-purple-500 border-purple-400 text-black' : 'border-slate-600 bg-transparent'
                                }`}>
                                  {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                                </div>
                              </div>

                              {topic.description && (
                                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                                  {topic.description}
                                </p>
                              )}
                            </div>

                            <div className="mt-3 pt-2 border-t border-[#1e2a4a] flex items-center justify-between text-[10px] text-slate-400">
                              <span>Passing Benchmark: {topic.passing_score || 70}%</span>
                              <span>~{topic.estimated_minutes || 10} mins</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>

                    {inlineErrors.required_topic_ids && (
                      <p className="text-xs text-rose-400 mt-2 flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" />
                        {inlineErrors.required_topic_ids}
                      </p>
                    )}
                  </div>

                  {/* Passing Score Benchmark (Read-Only) */}
                  <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-500/30 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-white block">System Passing Benchmark</span>
                      <span className="text-slate-400 text-[11px]">
                        Server-calculated threshold required for each selected topic.
                      </span>
                    </div>
                    <div className="px-3 py-1.5 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-500/40 font-mono font-bold text-sm">
                      70%
                    </div>
                  </div>

                  <p className="text-[11px] text-purple-300 font-medium">
                    &bull; Candidates must achieve a passing score (70%) on every selected assessment topic. Scores are calculated and validated strictly on the server.
                  </p>
                </div>
              )}
            </div>

            {/* ========================================================= */}
            {/* SECTION E: PUBLICATION SETTINGS & ACTION BAR */}
            {/* ========================================================= */}
            <div className="sticky bottom-4 z-20 bg-[#080d1a]/95 backdrop-blur-md rounded-2xl border border-[#1b2542] p-4 sm:p-5 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 self-start sm:self-auto">
                <button
                  type="button"
                  onClick={handleCancelClick}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#151f38] border border-[#1e2a4a] transition-all cursor-pointer disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => setIsPreviewOpen(true)}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#151f38] border border-[#1e2a4a] transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Eye className="w-3.5 h-3.5 text-indigo-400" />
                  Preview
                </button>
                {isEditMode && (
                  <button
                    type="button"
                    onClick={() => setIsDeleteModalOpen(true)}
                    disabled={isSubmitting || isDeleting}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-500/40 transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                    Delete Task
                  </button>
                )}
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={() => handleSubmit('DRAFT')}
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white bg-[#151f38] hover:bg-[#1c294d] border border-[#2b3a67] transition-all cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50 flex-1 sm:flex-initial"
                >
                  <Save className="w-4 h-4 text-slate-400" />
                  {isSubmitting && formData.status === 'DRAFT' ? 'Saving...' : 'Save Draft'}
                </button>

                <button
                  type="button"
                  onClick={() => handleSubmit('ACTIVE')}
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:brightness-110 shadow-[0_0_20px_rgba(79,70,229,0.4)] transition-all cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50 flex-1 sm:flex-initial"
                >
                  <Send className="w-4 h-4" />
                  {isSubmitting && formData.status === 'ACTIVE' 
                    ? 'Publishing...' 
                    : isEditMode ? 'Update & Publish' : 'Publish Task'}
                </button>
              </div>
            </div>
          </form>
        )}
      </main>

      {/* ========================================================= */}
      {/* MODAL: PREVIEW TASK CARD */}
      {/* ========================================================= */}
      {isPreviewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 text-white shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
              <h3 className="text-base font-bold font-sora text-white">Agent Marketplace Preview</h3>
              <button
                type="button"
                onClick={() => setIsPreviewOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <p className="text-xs text-slate-400">
                This preview simulates how your task specifications will appear to agents browsing the active catalog.
              </p>

              <div className="p-5 rounded-2xl border border-[#1e2a4a] bg-[#0d1428] space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block mb-1">
                      {selectedCategory?.category_name || 'Category Pending'}
                    </span>
                    <h3 className="text-base font-bold font-sora text-white">
                      {formData.task_name || 'Untitled Task'}
                    </h3>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
                    Ready to Apply
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {formData.description || 'No detailed description specified yet.'}
                </p>

                {/* Compensation & Work arrangement badges */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="px-2.5 py-1 rounded-lg bg-emerald-950/60 text-emerald-400 font-semibold border border-emerald-500/40 flex items-center gap-1">
                    <DollarSign className="w-3.5 h-3.5" />
                    {formData.payment_type === 'Hourly' ? (
                      formData.hourly_rate_min 
                        ? `${formData.currency} ${formData.hourly_rate_min}${formData.hourly_rate_max ? ` - ${formData.hourly_rate_max}` : ''} / hr`
                        : 'Compensation Pending'
                    ) : (
                      formData.fixed_budget
                        ? `${formData.currency} ${formData.fixed_budget} (Fixed)`
                        : 'Budget Pending'
                    )}
                  </span>

                  <span className="px-2.5 py-1 rounded-lg bg-[#151f38] text-slate-300 font-medium border border-[#23315c] flex items-center gap-1">
                    <Globe className="w-3.5 h-3.5 text-slate-400" />
                    {formData.work_arrangement} {formData.location ? `(${formData.location})` : ''}
                  </span>

                  <span className="px-2.5 py-1 rounded-lg bg-[#151f38] text-slate-300 font-medium border border-[#23315c] flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    Deadline: {formData.application_deadline || 'Open'}
                  </span>
                </div>

                {/* Required Prerequisites */}
                <div className="p-3.5 rounded-xl bg-[#090e1c] border border-[#1b2542] space-y-2 text-xs">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Required Agent Qualifications
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-slate-500 block">Verified Experience</span>
                      <span className="font-bold text-slate-200">
                        {formData.minimum_experience_months ? `${formData.minimum_experience_months} months` : 'Open'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Mandatory Certifications</span>
                      <span className="font-bold text-slate-200">
                        {selectedCerts.length > 0 ? selectedCerts.map(c => c.certification_name).join(', ') : 'None Required'}
                      </span>
                    </div>
                    <div className="sm:col-span-2">
                      <span className="text-slate-500 block">Required Assessment Topics</span>
                      <span className="font-bold text-slate-200">
                        {formData.exam_required 
                          ? (selectedTopics.length > 0 ? `${selectedTopics.map(t => t.topic_name).join(', ')} (Benchmark: 70%)` : 'Assessment Required')
                          : 'No Assessment Required'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => setIsPreviewOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#151f38] hover:bg-[#1c294d] text-white border border-[#2b3a67] transition-all cursor-pointer"
                >
                  Close Preview
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: UNSAVED CHANGES WARNING */}
      {/* ========================================================= */}
      {isCancelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 text-white shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
              <h3 className="text-base font-bold font-sora text-white">Discard Unsaved Changes?</h3>
              <button
                type="button"
                onClick={() => setIsCancelModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs sm:text-sm text-slate-300">
              <p>
                You have unsaved changes in this task specification form. If you leave now, any unsubmitted information will be lost.
              </p>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#1b2542]">
                <button
                  type="button"
                  onClick={() => setIsCancelModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-[#151f38] cursor-pointer"
                >
                  Continue Editing
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCancelModalOpen(false);
                    navigate('/workforce/dashboard');
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-md cursor-pointer"
                >
                  Discard &amp; Exit
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: DELETE TASK CONFIRMATION */}
      {/* ========================================================= */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 text-white shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2542]">
              <h3 className="text-base font-bold font-sora text-white">Delete Task</h3>
              <button
                type="button"
                onClick={() => {
                  if (!isDeleting) setIsDeleteModalOpen(false);
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs sm:text-sm text-slate-300">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-rose-950/60 text-rose-400 border border-rose-500/40 flex items-center justify-center shrink-0">
                  <AlertCircle className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-semibold text-white">
                    Are you sure you want to permanently delete this task?
                  </p>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    This action is permanent and cannot be undone. The task and all associated requirements, topics, and applications will be permanently removed.
                  </p>
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#1b2542]">
                <button
                  type="button"
                  onClick={() => setIsDeleteModalOpen(false)}
                  disabled={isDeleting}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-[#151f38] cursor-pointer disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={async () => {
                    if (!taskId) return;
                    setIsDeleting(true);
                    try {
                      await adminService.deleteTask(taskId);
                      navigate('/workforce/dashboard');
                    } catch (err) {
                      setFormError(err?.response?.data?.error || err.message || 'Failed to delete task.');
                      setIsDeleteModalOpen(false);
                    } finally {
                      setIsDeleting(false);
                    }
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-md disabled:opacity-50 cursor-pointer"
                >
                  {isDeleting ? 'Deleting...' : 'Delete Permanently'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
