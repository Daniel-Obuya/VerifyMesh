import React, { useState } from 'react';
import { 
  X, 
  CheckCircle2, 
  AlertTriangle, 
  AlertCircle,
  ArrowRight, 
  Briefcase, 
  ShieldCheck, 
  Clock, 
  Lock, 
  FileCheck2, 
  Award,
  Sparkles,
  MapPin,
  Calendar,
  DollarSign,
  ChevronRight
} from 'lucide-react';
import { competencyService } from '../../services/competencyService';

export const TaskModal = ({ 
  isOpen, 
  onClose, 
  task, 
  userCompetency, 
  onOpenAssessment,
  onApplySuccess 
}) => {
  const [isApplying, setIsApplying] = useState(false);
  const [applyError, setApplyError] = useState(null);
  const [appliedStatus, setAppliedStatus] = useState(null);

  if (!isOpen || !task) return null;

  const taskId = task.task_id || task.id;
  const currentAppStatus = appliedStatus || task.application_status || 'Not Applied';
  const hasApplied = currentAppStatus !== 'Not Applied';
  const isAssigned = currentAppStatus === 'Assigned' || task.state === 'Assigned';
  const canApply = task.can_apply && !hasApplied;

  const handleApply = async () => {
    setIsApplying(true);
    setApplyError(null);
    try {
      const res = await competencyService.applyForTask(taskId);
      if (res?.success) {
        setAppliedStatus('Application Submitted');
        if (onApplySuccess) onApplySuccess(taskId, 'Application Submitted');
      } else {
        setApplyError(res?.error || 'Failed to submit application.');
      }
    } catch (err) {
      setApplyError(err?.message || 'Error communicating with server.');
    } finally {
      setIsApplying(false);
    }
  };

  const getStatusBadge = () => {
    if (isAssigned) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5" /> Assigned
        </span>
      );
    }
    if (hasApplied) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-[#3B50BA] border border-blue-200">
          <Clock className="w-3.5 h-3.5" /> {currentAppStatus}
        </span>
      );
    }
    if (task.can_apply) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5" /> Ready to Apply
        </span>
      );
    }
    if (task.state === 'Assessment Needed') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
          <AlertCircle className="w-3.5 h-3.5" /> Assessment Needed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
        <Lock className="w-3.5 h-3.5" /> {task.state || 'Requirements Pending'}
      </span>
    );
  };

  const examRequired = task.exam_required;
  const examName = task.exam_name || (task.exam_id === 3 ? 'Customer Support Diagnostic Assessment' : 'VerifyMesh Competency Assessment');
  const examPassingScore = task.exam_passing_score ?? 70;
  const examStatus = task.exam_status || (task.prerequisites?.assessment_met ? 'Passed' : 'Not Started');
  const isAssessmentPassed = examStatus === 'Passed' || task.prerequisites?.assessment_met;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[92vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-4 sm:px-6 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              task.can_apply ? 'bg-emerald-50 text-emerald-600' : 'bg-[#EEF2FF] text-[#3B50BA]'
            }`}>
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                {task.title}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {getStatusBadge()}
                {task.category && (
                  <span className="text-xs text-slate-400 font-medium">&bull; {task.category}</span>
                )}
                {task.work_arrangement && (
                  <span className="text-xs text-slate-400 font-medium">&bull; {task.work_arrangement}</span>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-4 text-slate-700">
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Opportunity Overview</h4>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              {task.description}
            </p>
          </div>

          {task.deliverables && (
            <div className="p-3 bg-slate-50/70 border border-slate-200/70 rounded-xl text-xs space-y-1">
              <span className="font-bold text-slate-700 uppercase tracking-wide block">Deliverables &amp; Scope</span>
              <p className="text-slate-600 leading-relaxed">{task.deliverables}</p>
            </div>
          )}

          {/* Key Terms Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
            <div className="p-2.5 bg-slate-50 border border-slate-200/80 rounded-xl">
              <span className="text-slate-400 font-medium block">Compensation</span>
              <span className="font-bold text-slate-900 mt-0.5 block">{task.payout || '$30 - $40 / hr'}</span>
            </div>
            <div className="p-2.5 bg-slate-50 border border-slate-200/80 rounded-xl">
              <span className="text-slate-400 font-medium block">Positions</span>
              <span className="font-bold text-slate-900 mt-0.5 block">{task.positions_count || 1} Opening(s)</span>
            </div>
            <div className="p-2.5 bg-slate-50 border border-slate-200/80 rounded-xl col-span-2 sm:col-span-1">
              <span className="text-slate-400 font-medium block">Duration</span>
              <span className="font-bold text-slate-900 mt-0.5 block">{task.expected_duration || 'Ongoing'}</span>
            </div>
          </div>

          {/* Section: Task Prerequisites & Assessment Breakdown */}
          <div className="space-y-2.5 pt-1">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Prerequisites &amp; Qualification Requirements
            </h4>

            {/* Assessment Topic Card (Task-Driven Assessment Highlight) */}
            <div className={`p-4 rounded-xl border transition-all ${
              isAssessmentPassed 
                ? 'bg-emerald-50/40 border-emerald-200' 
                : 'bg-gradient-to-br from-blue-50/60 to-indigo-50/40 border-blue-200'
            }`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2.5">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    isAssessmentPassed ? 'bg-emerald-100 text-emerald-700' : 'bg-[#EEF2FF] text-[#3B50BA]'
                  }`}>
                    {isAssessmentPassed ? <CheckCircle2 className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B50BA] block">
                      Required Assessment Topics
                    </span>
                    <h5 className="text-sm font-bold text-slate-900 mt-0.5">
                      {task.required_topics?.length > 1 ? `${task.required_topics.length} Qualification Topics` : examName}
                    </h5>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {task.topics_total ? `${task.topics_passed_count || 0} of ${task.topics_total} topics satisfied` : `Pass Threshold: ${examPassingScore}%`}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                    isAssessmentPassed
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : examStatus === 'Failed'
                      ? 'bg-rose-100 text-rose-800 border-rose-300'
                      : 'bg-amber-100 text-amber-800 border-amber-300'
                  }`}>
                    {isAssessmentPassed ? '✓ All Passed' : examStatus === 'Failed' ? '✗ Action Needed' : 'Required'}
                  </span>
                </div>
              </div>

              {task.required_topics && task.required_topics.length > 0 && (
                <div className="mt-3 pt-3 border-t border-blue-100/80 space-y-2">
                  {task.required_topics.map(rt => (
                    <div key={rt.topic_id} className="flex items-center justify-between text-xs bg-white/70 p-2 rounded-lg border border-slate-200/60">
                      <span className="font-semibold text-slate-800 truncate" title={rt.name}>{rt.name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${
                        rt.status === 'Passed'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : rt.status === 'Failed'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}>
                        {rt.status === 'Passed' ? `✓ Passed (${rt.latest_score}%)` : rt.status === 'Failed' ? `✗ Failed (${rt.latest_score}%)` : `Needed (≥${rt.passing_threshold}%)`}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {!isAssessmentPassed && (
                <div className="mt-3 pt-3 border-t border-blue-100/80 flex items-center justify-between">
                  <span className="text-xs text-slate-600">
                    Complete evaluation on the dedicated assessment page.
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      if (onOpenAssessment) onOpenAssessment(task);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[#3B50BA] hover:bg-[#31429e] text-white text-xs font-semibold shadow-xs flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <span>Go to Assessment</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>

            {/* Other 3 Requirements Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-left">
              {/* Competency Level */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">Required Competency</span>
                <p className="text-xs font-bold text-slate-900 mt-0.5">
                  {task.required_competency || 'Eligible'}
                </p>
                <p className={`text-[11px] mt-1 font-medium ${
                  task.prerequisites?.competency_met ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {task.prerequisites?.competency_met ? '✓ Met' : `Current: ${userCompetency || 'Unassessed'}`}
                </p>
              </div>

              {/* Mandatory Certification */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">Certification</span>
                <p className="text-xs font-bold text-slate-900 mt-0.5 truncate" title={task.required_certification}>
                  {task.required_certification || 'None required'}
                </p>
                <p className={`text-[11px] mt-1 font-medium ${
                  task.prerequisites?.certification_met ? 'text-emerald-600' : 'text-rose-600'
                }`}>
                  {task.prerequisites?.certification_met ? '✓ Verified on file' : '✗ Missing / Unverified'}
                </p>
              </div>

              {/* Minimum Experience */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">Min. Experience</span>
                <p className="text-xs font-bold text-slate-900 mt-0.5">
                  {task.minimum_experience_months || 0} Months
                </p>
                <p className={`text-[11px] mt-1 font-medium ${
                  task.prerequisites?.experience_met ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {task.prerequisites?.experience_met ? '✓ Experience verified' : 'Prerequisite pending'}
                </p>
              </div>
            </div>
          </div>

          {/* Feedback & Notice Area */}
          {applyError && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{applyError}</span>
            </div>
          )}

          {hasApplied ? (
            <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 flex items-start gap-2.5">
              <Clock className="w-4 h-4 text-[#3B50BA] shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-slate-900">Application Recorded in Platform Ledger</p>
                <p className="text-xs text-slate-600 mt-0.5">
                  Current lifecycle status: <strong className="text-[#3B50BA]">{currentAppStatus}</strong>.
                  {task.applied_at && ` Applied on ${new Date(task.applied_at).toLocaleDateString()}.`}
                </p>
              </div>
            </div>
          ) : task.blocking_reason && !canApply ? (
            <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 space-y-1">
              <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Eligibility Prerequisite Notice</span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                {task.blocking_reason}
              </p>
            </div>
          ) : canApply ? (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>All mandatory certifications, competency evaluations, and experience requirements are verified. You are ready to apply.</span>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 sm:px-6 border-t border-slate-100 flex items-center justify-between bg-white shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Close
          </button>

          {hasApplied ? (
            <span className="text-xs font-semibold text-slate-500 py-2">
              Status: <strong className="text-slate-900">{currentAppStatus}</strong>
            </span>
          ) : !isAssessmentPassed && task.exam_required ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                if (onOpenAssessment) onOpenAssessment(task);
              }}
              className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
            >
              <span>Complete Assessment ({examName.split(' ')[0]})</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : canApply ? (
            <button
              type="button"
              onClick={handleApply}
              disabled={isApplying}
              className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:opacity-50 text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
            >
              {isApplying ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Submitting Application...</span>
                </>
              ) : (
                <>
                  <span>Submit Application</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              disabled
              className="px-5 py-2.5 rounded-xl bg-slate-100 text-slate-400 font-semibold text-xs sm:text-sm cursor-not-allowed"
            >
              Ineligible for Application
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
