import React, { useState, useEffect } from 'react';
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
  Trash2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BrandLogo } from '../components/auth/BrandLogo';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Alert } from '../components/ui/Alert';
import { adminService } from '../services/adminService';

const COMPETENCY_TIERS = [
  {
    tier: 'ELIGIBLE',
    label: 'Verified Competent (Eligible)',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    description: 'Candidate must be classified as Eligible by the Gatekeeper Random Forest model.'
  },
  {
    tier: 'NOT_ELIGIBLE',
    label: 'Open to All (No Competency Gate)',
    badge: 'bg-slate-50 text-slate-700 border-slate-200',
    description: 'No prerequisite gatekeeper competency requirement; open to all registered agents.'
  }
];

const SKILL_SUGGESTIONS = [
  'Customer Support',
  'Technical Diagnostics',
  'Incident De-escalation',
  'SLA Adherence',
  'CRM Management',
  'Consultative Selling',
  'Ticket Triage',
  'Enterprise Communication'
];

export const CreateTaskPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { taskId } = useParams();
  const isEditMode = Boolean(taskId);

  // Loading & Metadata
  const [isLoading, setIsLoading] = useState(isEditMode);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [metadata, setMetadata] = useState({ categories: [], certifications: [], skills: [], exams: [] });
  const [formError, setFormError] = useState(null);
  const [formSuccess, setFormSuccess] = useState(null);
  const [inlineErrors, setInlineErrors] = useState({});
  const [isDirty, setIsDirty] = useState(false);

  // Modals
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

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
    minimum_competency: 'ELIGIBLE',
    required_certification_id: '',
    minimum_experience_months: 0,
    exam_required: false,
    exam_id: '',
    status: 'ACTIVE'
  });

  const [skillInput, setSkillInput] = useState('');

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
              minimum_competency: t.minimum_competency || 'ELIGIBLE',
              required_certification_id: t.required_certification_id ? String(t.required_certification_id) : '',
              minimum_experience_months: t.minimum_experience_months || 0,
              exam_required: Boolean(t.exam_required),
              exam_id: t.exam_id ? String(t.exam_id) : '',
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

  // Set default exam when exam_required is toggled or category changes
  useEffect(() => {
    if (formData.exam_required && formData.category_id) {
      const availableExams = metadata.exams.filter(
        e => String(e.category_id) === String(formData.category_id)
      );
      if (availableExams.length > 0 && !formData.exam_id) {
        setFormData(prev => ({ ...prev, exam_id: String(availableExams[0].exam_id) }));
      }
    }
  }, [formData.exam_required, formData.category_id, metadata.exams, formData.exam_id]);

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
        if (!formData.exam_id) {
          errors.exam_id = 'Please select an assessment template for this category.';
        } else {
          const selectedExam = metadata.exams.find(e => String(e.exam_id) === String(formData.exam_id));
          if (!selectedExam) {
            errors.exam_id = 'Selected assessment template is not valid.';
          } else if (selectedExam.question_count === 0) {
            errors.exam_id = 'Selected assessment template has no configured questions in server bank.';
          }
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
        currency: formData.currency,
        hourly_rate_min: formData.payment_type === 'Hourly' && formData.hourly_rate_min ? parseFloat(formData.hourly_rate_min) : null,
        hourly_rate_max: formData.payment_type === 'Hourly' && formData.hourly_rate_max ? parseFloat(formData.hourly_rate_max) : null,
        fixed_budget: formData.payment_type === 'Fixed Budget' && formData.fixed_budget ? parseFloat(formData.fixed_budget) : null,
        positions_count: parseInt(formData.positions_count, 10) || 1,
        application_deadline: formData.application_deadline || null,
        expected_duration: formData.expected_duration || null,
        minimum_competency: formData.minimum_competency,
        required_certification_id: formData.required_certification_id ? parseInt(formData.required_certification_id, 10) : null,
        minimum_experience_months: parseInt(formData.minimum_experience_months, 10) || 0,
        exam_required: Boolean(formData.exam_required),
        exam_id: formData.exam_required && formData.exam_id ? parseInt(formData.exam_id, 10) : null,
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

      // Return to task catalog after brief confirmation
      setTimeout(() => {
        navigate('/admin/dashboard');
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
      navigate('/admin/dashboard');
    }
  };

  // Selected Category & Certification info for badges
  const selectedCategory = metadata.categories.find(c => String(c.category_id) === String(formData.category_id));
  const selectedCert = metadata.certifications.find(c => String(c.certification_id) === String(formData.required_certification_id));
  const categoryExams = metadata.exams.filter(e => String(e.category_id) === String(formData.category_id));
  const selectedExam = metadata.exams.find(e => String(e.exam_id) === String(formData.exam_id));

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans">
      {/* Top Header */}
      <header className="h-16 bg-white border-b border-slate-200/80 px-6 sm:px-8 flex items-center justify-between shrink-0 sticky top-0 z-20">
        <div className="flex items-center gap-4">
          <Link to="/admin/dashboard" className="flex items-center gap-2 text-slate-500 hover:text-slate-900 transition-colors">
            <BrandLogo />
          </Link>
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
            <span>/</span>
            <span>Admin Portal</span>
            <span>/</span>
            <span>Tasks</span>
            <span>/</span>
            <span className="font-semibold text-slate-700">
              {isEditMode ? `Edit Task #${taskId}` : 'Create New Task'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleCancelClick}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Catalog
          </button>
          <div className="w-8 h-8 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-xs flex items-center justify-center">
            {user?.fullName ? user.fullName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'AD'}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8 max-w-4xl w-full mx-auto space-y-6">
        {/* Page Title & Status Banner */}
        <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-[#3B50BA] tracking-wider uppercase">
                TASK MARKETPLACE &bull; WORKFORCE ALLOCATION
              </span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                formData.status === 'ACTIVE' 
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                {isEditMode ? `Mode: Editing (${formData.status})` : 'New Task Formulation'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1 tracking-tight">
              {isEditMode ? 'Edit Task Specifications' : 'Create Task Specification'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Define deliverable requirements, compensation structure, eligibility thresholds, and automated qualification rules.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsPreviewOpen(true)}
              className="text-xs"
            >
              <Eye className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Preview Card
            </Button>
          </div>
        </div>

        {/* Global Notifications */}
        {formError && (
          <Alert type="error" message={formError} onClose={() => setFormError(null)} />
        )}
        {formSuccess && (
          <Alert type="success" message={formSuccess} onClose={() => setFormSuccess(null)} />
        )}

        {isLoading ? (
          <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-xs">
            <div className="w-8 h-8 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">Loading Task Details...</p>
          </div>
        ) : (
          <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
            {/* ========================================================= */}
            {/* SECTION A: TASK OVERVIEW */}
            {/* ========================================================= */}
            <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#3B50BA] flex items-center justify-center font-bold text-xs">
                  A
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">Task Overview</h2>
                  <p className="text-xs text-slate-500">Essential role identity, domain classification, and execution arrangement.</p>
                </div>
              </div>

              {/* Task Title */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700">
                    Task Title <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {formData.task_name.length}/150
                  </span>
                </div>
                <input
                  type="text"
                  maxLength={150}
                  placeholder="e.g. Enterprise Escalation Specialist"
                  value={formData.task_name}
                  onChange={(e) => updateField('task_name', e.target.value)}
                  className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                    inlineErrors.task_name 
                      ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20' 
                      : 'border-slate-200 focus:border-[#3B50BA]'
                  }`}
                />
                {inlineErrors.task_name ? (
                  <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {inlineErrors.task_name}
                  </p>
                ) : (
                  <p className="text-[11px] text-slate-400 mt-1">
                    Provide a descriptive business title (avoid generic names like "Task 1").
                  </p>
                )}
              </div>

              {/* Category & Work Arrangement Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Category */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Task Category <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.category_id}
                    onChange={(e) => updateField('category_id', e.target.value)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none bg-white transition-colors ${
                      inlineErrors.category_id
                        ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                        : 'border-slate-200 focus:border-[#3B50BA]'
                    }`}
                  >
                    <option value="">Select Domain Category</option>
                    {metadata.categories.map((c) => (
                      <option key={c.category_id} value={c.category_id}>
                        {c.category_name}
                      </option>
                    ))}
                  </select>
                  {inlineErrors.category_id && (
                    <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {inlineErrors.category_id}
                    </p>
                  )}
                  {selectedCategory && (
                    <p className="text-[11px] text-slate-500 mt-1 italic">
                      {selectedCategory.description}
                    </p>
                  )}
                </div>

                {/* Work Arrangement */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Work Arrangement <span className="text-rose-500">*</span>
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'Remote', label: 'Remote', icon: Globe },
                      { id: 'Hybrid', label: 'Hybrid', icon: Building },
                      { id: 'On-site', label: 'On-site', icon: MapPin }
                    ].map(({ id, label, icon: Icon }) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => updateField('work_arrangement', id)}
                        className={`flex flex-col items-center justify-center p-2 rounded-xl border text-xs font-semibold transition-all ${
                          formData.work_arrangement === id
                            ? 'bg-[#EEF2FF] text-[#3B50BA] border-[#3B50BA] shadow-xs'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
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
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Location / Eligible Region <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Nairobi Central Hub / Kenya Regional Offices"
                    value={formData.location}
                    onChange={(e) => updateField('location', e.target.value)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                      inlineErrors.location
                        ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                        : 'border-slate-200 focus:border-[#3B50BA]'
                    }`}
                  />
                  {inlineErrors.location && (
                    <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {inlineErrors.location}
                    </p>
                  )}
                </div>
              )}

              {/* Detailed Description */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700">
                    Detailed Description <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {formData.description.length} chars (min 20)
                  </span>
                </div>
                <textarea
                  rows={4}
                  placeholder="Comprehensive description of the engagement scope, day-to-day responsibilities, and team collaboration model..."
                  value={formData.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                    inlineErrors.description
                      ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                      : 'border-slate-200 focus:border-[#3B50BA]'
                  }`}
                />
                {inlineErrors.description && (
                  <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {inlineErrors.description}
                  </p>
                )}
              </div>

              {/* Deliverables & Expected Outcomes */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Responsibilities &amp; Expected Deliverables
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. - Maintain >95% First-Contact Resolution&#10;- Resolve up to 25 ticket escalations weekly&#10;- File weekly incident post-mortem documentation"
                  value={formData.deliverables}
                  onChange={(e) => updateField('deliverables', e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Bullet points outlining concrete milestones or qualitative standards expected from the assigned agent.
                </p>
              </div>

              {/* Required Skills Chips */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Required Competency Skills &amp; Keywords
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
                    className="flex-1 px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleAddSkill()}
                    type="button"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" /> Add
                  </Button>
                </div>

                {/* Selected Skills Tags */}
                {formData.required_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2.5">
                    {formData.required_skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 text-[#3B50BA] border border-blue-100 text-xs font-semibold"
                      >
                        {skill}
                        <button
                          type="button"
                          onClick={() => handleRemoveSkill(skill)}
                          className="hover:text-rose-600 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {/* Popular Skill Presets */}
                <div className="flex items-center gap-1.5 flex-wrap pt-1">
                  <span className="text-[11px] text-slate-400 font-medium">Suggestions:</span>
                  {SKILL_SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleAddSkill(s)}
                      disabled={formData.required_skills.includes(s)}
                      className="text-[11px] px-2 py-0.5 rounded-full border border-slate-200 text-slate-600 hover:border-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                    >
                      + {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* SECTION B: COMPENSATION AND AVAILABILITY */}
            {/* ========================================================= */}
            <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold text-xs">
                  B
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">Compensation &amp; Availability</h2>
                  <p className="text-xs text-slate-500">Define remuneration structure, quota capacity, and application window.</p>
                </div>
              </div>

              {/* Payment Type Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Payment Type <span className="text-rose-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => updateField('payment_type', 'Hourly')}
                    className={`flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all ${
                      formData.payment_type === 'Hourly'
                        ? 'bg-[#EEF2FF] text-[#3B50BA] border-[#3B50BA] shadow-xs'
                        : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-lg bg-blue-100/60 text-[#3B50BA] flex items-center justify-center shrink-0">
                      <Clock className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold">Hourly Rate Model</p>
                      <p className="text-[11px] text-slate-500">Compensate per verified logged hour</p>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => updateField('payment_type', 'Fixed Budget')}
                    className={`flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all ${
                      formData.payment_type === 'Fixed Budget'
                        ? 'bg-[#EEF2FF] text-[#3B50BA] border-[#3B50BA] shadow-xs'
                        : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-lg bg-blue-100/60 text-[#3B50BA] flex items-center justify-center shrink-0">
                      <DollarSign className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold">Fixed Project Budget</p>
                      <p className="text-[11px] text-slate-500">Total milestone allocation</p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Currency & Compensation Amounts */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Currency <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.currency}
                    onChange={(e) => updateField('currency', e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] bg-white font-semibold"
                  >
                    <option value="KES">KES (Kenyan Shilling)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>

                {formData.payment_type === 'Hourly' ? (
                  <>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Min Hourly Rate ({formData.currency}) <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="100"
                        placeholder="e.g. 2500"
                        value={formData.hourly_rate_min}
                        onChange={(e) => updateField('hourly_rate_min', e.target.value)}
                        className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                          inlineErrors.hourly_rate_min
                            ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                            : 'border-slate-200 focus:border-[#3B50BA]'
                        }`}
                      />
                      {inlineErrors.hourly_rate_min && (
                        <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />
                          {inlineErrors.hourly_rate_min}
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Max Hourly Rate ({formData.currency})
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="100"
                        placeholder="e.g. 4500 (Optional)"
                        value={formData.hourly_rate_max}
                        onChange={(e) => updateField('hourly_rate_max', e.target.value)}
                        className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                          inlineErrors.hourly_rate_max
                            ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                            : 'border-slate-200 focus:border-[#3B50BA]'
                        }`}
                      />
                      {inlineErrors.hourly_rate_max && (
                        <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />
                          {inlineErrors.hourly_rate_max}
                        </p>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Total Fixed Budget ({formData.currency}) <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="500"
                      placeholder="e.g. 120000"
                      value={formData.fixed_budget}
                      onChange={(e) => updateField('fixed_budget', e.target.value)}
                      className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                        inlineErrors.fixed_budget
                          ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                          : 'border-slate-200 focus:border-[#3B50BA]'
                      }`}
                    />
                    {inlineErrors.fixed_budget && (
                      <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" />
                        {inlineErrors.fixed_budget}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Positions Count, Deadline & Expected Duration */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-100">
                {/* Positions */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Available Positions <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      min="1"
                      value={formData.positions_count}
                      onChange={(e) => updateField('positions_count', Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                    />
                    <Users className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">Number of agents to assign</p>
                </div>

                {/* Application Deadline */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Application Deadline <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      value={formData.application_deadline}
                      onChange={(e) => updateField('application_deadline', e.target.value)}
                      className={`w-full pl-9 pr-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${
                        inlineErrors.application_deadline
                          ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                          : 'border-slate-200 focus:border-[#3B50BA]'
                      }`}
                    />
                    <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  </div>
                  {inlineErrors.application_deadline ? (
                    <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {inlineErrors.application_deadline}
                    </p>
                  ) : (
                    <div className="flex items-center gap-1 mt-1">
                      <button
                        type="button"
                        onClick={() => setDeadlinePreset(14)}
                        className="text-[10px] text-slate-500 hover:text-[#3B50BA] underline"
                      >
                        +14d
                      </button>
                      <span className="text-[10px] text-slate-300">&bull;</span>
                      <button
                        type="button"
                        onClick={() => setDeadlinePreset(30)}
                        className="text-[10px] text-slate-500 hover:text-[#3B50BA] underline"
                      >
                        +30d
                      </button>
                      <span className="text-[10px] text-slate-300">&bull;</span>
                      <button
                        type="button"
                        onClick={() => setDeadlinePreset(60)}
                        className="text-[10px] text-slate-500 hover:text-[#3B50BA] underline"
                      >
                        +60d
                      </button>
                    </div>
                  )}
                </div>

                {/* Expected Duration */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Expected Duration
                  </label>
                  <select
                    value={formData.expected_duration}
                    onChange={(e) => updateField('expected_duration', e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] bg-white"
                  >
                    <option value="1 month">1 Month</option>
                    <option value="3 months">3 Months</option>
                    <option value="6 months">6 Months</option>
                    <option value="12 months">12 Months</option>
                    <option value="Ongoing / Milestone-based">Ongoing / Milestone-based</option>
                  </select>
                  <p className="text-[11px] text-slate-400 mt-1">Engagement period</p>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* SECTION C: ELIGIBILITY REQUIREMENTS */}
            {/* ========================================================= */}
            <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-xs">
                  C
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">Eligibility Requirements</h2>
                  <p className="text-xs text-slate-500">Configure machine learning competency thresholds and mandatory certifications.</p>
                </div>
              </div>

              {/* Competency Tier Selector */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-slate-700">
                    Required Minimum Competency Tier <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-slate-400 font-medium">
                    Evaluated by Random Forest inference
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {COMPETENCY_TIERS.map(({ tier, label, badge, description }) => {
                    const isSelected = formData.minimum_competency === tier;
                    return (
                      <button
                        key={tier}
                        type="button"
                        onClick={() => updateField('minimum_competency', tier)}
                        className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between ${
                          isSelected
                            ? 'bg-[#EEF2FF] border-[#3B50BA] shadow-xs'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div>
                          <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold border mb-2 ${badge}`}>
                            {label}
                          </span>
                          <p className="text-[11px] text-slate-600 leading-relaxed font-normal">
                            {description}
                          </p>
                        </div>
                        <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-semibold">
                          <span className={isSelected ? 'text-[#3B50BA]' : 'text-slate-400'}>
                            {isSelected ? 'Selected Tier' : 'Select'}
                          </span>
                          {isSelected && <Check className="w-3.5 h-3.5 text-[#3B50BA]" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Mandatory Certification Dropdown */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Mandatory Certification Requirement
                </label>
                <select
                  value={formData.required_certification_id}
                  onChange={(e) => updateField('required_certification_id', e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA] bg-white"
                >
                  <option value="">No mandatory certification required (Open Eligibility)</option>
                  {metadata.certifications.map((cert) => (
                    <option key={cert.certification_id} value={cert.certification_id}>
                      {cert.certification_name} {cert.validity_period_months ? `(Valid ${cert.validity_period_months} mos)` : ''}
                    </option>
                  ))}
                </select>

                {selectedCert ? (
                  <div className="mt-2.5 p-3 rounded-xl bg-emerald-50/60 border border-emerald-200 flex items-start gap-2.5 text-xs">
                    <Award className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-emerald-900">
                        Mandatory: {selectedCert.certification_name}
                      </p>
                      <p className="text-emerald-700 mt-0.5 leading-relaxed">
                        {selectedCert.description}
                      </p>
                      <p className="text-[11px] text-emerald-800 mt-1 font-semibold">
                        &bull; Strict Precedence Blocker: Agents without this verified active accreditation are blocked from submitting applications.
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-400 mt-1">
                    Select a required credential only if the task legally or operationally requires verified compliance.
                  </p>
                )}
              </div>

              {/* Minimum Experience */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Minimum Experience (Months)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min="0"
                    step="3"
                    value={formData.minimum_experience_months}
                    onChange={(e) => updateField('minimum_experience_months', Math.max(0, parseInt(e.target.value, 10) || 0))}
                    className="w-40 px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-[#3B50BA]"
                  />
                  <div className="flex items-center gap-1">
                    {[0, 6, 12, 18, 24].map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => updateField('minimum_experience_months', m)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                          formData.minimum_experience_months === m
                            ? 'bg-[#EEF2FF] text-[#3B50BA] border-[#3B50BA]'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {m === 0 ? 'None' : `${m}m`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* SECTION D: ASSESSMENT CONFIGURATION */}
            {/* ========================================================= */}
            <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs space-y-5">
              <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-700 flex items-center justify-center font-bold text-xs">
                  D
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">Assessment Configuration</h2>
                  <p className="text-xs text-slate-500">Configure task-specific assessment requirements and server question banks.</p>
                </div>
              </div>

              {/* Assessment Switch */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-150">
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-slate-800">
                    Require Task-Specific Competency Assessment
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    When enabled, agents must achieve a passing score on the designated assessment battery before applying.
                  </p>
                </div>
                <input
                  type="checkbox"
                  id="exam_required_toggle"
                  checked={formData.exam_required}
                  onChange={(e) => updateField('exam_required', e.target.checked)}
                  className="w-5 h-5 text-[#3B50BA] rounded border-slate-300 focus:ring-[#3B50BA] cursor-pointer"
                />
              </div>

              {formData.exam_required && (
                <div className="space-y-4 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Select Server Assessment Template <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={formData.exam_id}
                      onChange={(e) => updateField('exam_id', e.target.value)}
                      className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none bg-white transition-colors ${
                        inlineErrors.exam_id
                          ? 'border-rose-400 focus:border-rose-500 bg-rose-50/20'
                          : 'border-slate-200 focus:border-[#3B50BA]'
                      }`}
                    >
                      <option value="">Select Assessment Template</option>
                      {metadata.exams.map((exam) => (
                        <option key={exam.exam_id} value={exam.exam_id}>
                          {exam.exam_name} ({exam.category_name} &bull; Passing Score: {exam.passing_score}%)
                        </option>
                      ))}
                    </select>
                    {inlineErrors.exam_id && (
                      <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" />
                        {inlineErrors.exam_id}
                      </p>
                    )}
                  </div>

                  {selectedExam && (
                    <div className="p-4 rounded-xl bg-purple-50/50 border border-purple-200 space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="text-[10px] font-bold text-purple-700 tracking-wider uppercase">
                            SERVER QUESTION POOL &bull; {selectedExam.category_name}
                          </span>
                          <h4 className="text-sm font-bold text-slate-900 mt-0.5">
                            {selectedExam.exam_name}
                          </h4>
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                            {selectedExam.description}
                          </p>
                        </div>
                        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                          {selectedExam.status}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-purple-100 text-xs">
                        <div className="p-2.5 rounded-lg bg-white border border-purple-100">
                          <span className="text-[10px] text-slate-400 block font-medium">Configured Question Count</span>
                          <span className="font-bold text-slate-900 mt-0.5 block">
                            {selectedExam.question_count} Questions
                          </span>
                        </div>
                        <div className="p-2.5 rounded-lg bg-white border border-purple-100">
                          <span className="text-[10px] text-slate-400 block font-medium">Scoring Policy Threshold</span>
                          <span className="font-bold text-emerald-700 mt-0.5 block">
                            {selectedExam.passing_score}% Passing Score
                          </span>
                        </div>
                      </div>

                      <p className="text-[11px] text-purple-900 font-medium">
                        &bull; Assessment questions, correct keys, and passing thresholds are strictly server-controlled to maintain exam integrity.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ========================================================= */}
            {/* SECTION E: PUBLICATION SETTINGS & ACTION BAR */}
            {/* ========================================================= */}
            <div className="sticky bottom-4 z-10 bg-white rounded-2xl border border-slate-200/80 p-4 sm:p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 self-start sm:self-auto">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleCancelClick}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsPreviewOpen(true)}
                  disabled={isSubmitting}
                >
                  <Eye className="w-3.5 h-3.5 mr-1 text-slate-500" />
                  Preview
                </Button>
                {isEditMode && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => setIsDeleteModalOpen(true)}
                    disabled={isSubmitting || isDeleting}
                    className="border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 hover:border-rose-300"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1 text-rose-600" />
                    Delete Task
                  </Button>
                )}
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => handleSubmit('DRAFT')}
                  isLoading={isSubmitting && formData.status === 'DRAFT'}
                  disabled={isSubmitting}
                  className="flex-1 sm:flex-initial"
                >
                  <Save className="w-4 h-4 mr-1.5 text-slate-600" />
                  Save Draft
                </Button>

                <Button
                  variant="primary"
                  size="md"
                  onClick={() => handleSubmit('ACTIVE')}
                  isLoading={isSubmitting && formData.status === 'ACTIVE'}
                  disabled={isSubmitting}
                  className="flex-1 sm:flex-initial"
                >
                  <Send className="w-4 h-4 mr-1.5" />
                  {isEditMode ? 'Update & Publish' : 'Publish Task'}
                </Button>
              </div>
            </div>
          </form>
        )}
      </main>

      {/* ========================================================= */}
      {/* MODAL: PREVIEW TASK CARD */}
      {/* ========================================================= */}
      <Modal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        title="Agent Marketplace Preview"
      >
        <div className="space-y-4 text-slate-800">
          <p className="text-xs text-slate-500">
            This preview simulates how your task specifications will appear to agents browsing the active catalog.
          </p>

          <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-xs space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  {selectedCategory?.category_name || 'Category Pending'}
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {formData.task_name || 'Untitled Task'}
                </h3>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Ready to Apply
              </span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              {formData.description || 'No detailed description specified yet.'}
            </p>

            {/* Compensation & Work arrangement badges */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 font-semibold border border-emerald-100 flex items-center gap-1">
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

              <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 font-medium flex items-center gap-1">
                <Globe className="w-3.5 h-3.5 text-slate-500" />
                {formData.work_arrangement} {formData.location ? `(${formData.location})` : ''}
              </span>

              <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 font-medium flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                Deadline: {formData.application_deadline || 'Open'}
              </span>
            </div>

            {/* Required Prerequisites */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-150 space-y-2 text-xs">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Required Agent Qualifications
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-400 block">Minimum Competency</span>
                  <span className="font-bold text-slate-800">
                    {formData.minimum_competency}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Mandatory Certification</span>
                  <span className="font-bold text-slate-800">
                    {selectedCert ? selectedCert.certification_name : 'None Required'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Experience</span>
                  <span className="font-bold text-slate-800">
                    {formData.minimum_experience_months ? `${formData.minimum_experience_months} months` : 'Open'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Assessment Exam</span>
                  <span className="font-bold text-slate-800">
                    {formData.exam_required ? (selectedExam?.exam_name || 'Exam Required') : 'No Exam Required'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <Button size="sm" onClick={() => setIsPreviewOpen(false)}>
              Close Preview
            </Button>
          </div>
        </div>
      </Modal>

      {/* ========================================================= */}
      {/* MODAL: UNSAVED CHANGES WARNING */}
      {/* ========================================================= */}
      <Modal
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
        title="Discard Unsaved Changes?"
      >
        <div className="space-y-4 text-xs sm:text-sm text-slate-700">
          <p>
            You have unsaved changes in this task specification form. If you leave now, any unsubmitted information will be lost.
          </p>
          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
            <Button variant="secondary" size="sm" onClick={() => setIsCancelModalOpen(false)}>
              Continue Editing
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIsCancelModalOpen(false);
                navigate('/admin/dashboard');
              }}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              Discard &amp; Exit
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
          if (!isDeleting) setIsDeleteModalOpen(false);
        }}
        title="Delete Task"
      >
        <div className="space-y-4 text-xs sm:text-sm text-slate-700">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center shrink-0 border border-rose-100">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-slate-900">
                Are you sure you want to permanently delete this task?
              </p>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                This action is permanent and cannot be undone. The task and all associated requirements, topics, and applications will be permanently removed.
              </p>
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={async () => {
                if (!taskId) return;
                setIsDeleting(true);
                try {
                  await adminService.deleteTask(taskId);
                  navigate('/admin/dashboard');
                } catch (err) {
                  setFormError(err?.response?.data?.error || err.message || 'Failed to delete task.');
                  setIsDeleteModalOpen(false);
                } finally {
                  setIsDeleting(false);
                }
              }}
              isLoading={isDeleting}
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
