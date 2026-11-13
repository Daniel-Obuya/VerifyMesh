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
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Assigned
        </span>
      );
    }
    if (hasApplied) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/60 text-blue-300 border border-blue-500/40">
          <Clock className="w-3.5 h-3.5 text-blue-400" /> {currentAppStatus}
        </span>
      );
    }
    if (task.can_apply) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Ready to Apply
        </span>
      );
    }
    if (task.state === 'Assessment Needed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-300 border border-amber-500/40">
          <AlertCircle className="w-3.5 h-3.5 text-amber-400" /> Assessment Needed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-900/60 text-slate-400 border border-slate-700/60">
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-xl bg-[#0d1428] rounded-2xl shadow-2xl border border-[#2b3a67] flex flex-col max-h-[92vh] overflow-hidden text-white"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-4 sm:px-6 sm:py-4 border-b border-[#1b2542] flex items-center justify-between bg-[#080d1a] shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${
              task.can_apply 
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' 
                : 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400'
            }`}>
              <Briefcase className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold font-sora text-white leading-snug">
                {task.title}
              </h3>
              <div className="mt-0.5 flex flex-wrap items-center gap-2">
                {getStatusBadge()}
                {task.category && (
                  <span className="text-xs text-indigo-400/90 font-medium">&bull; {task.category}</span>
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
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#151f38] transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 text-slate-300 text-xs sm:text-[13px]">
          <div>
            <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Opportunity Overview</h4>
            <p className="text-slate-300 mt-1.5 leading-relaxed">
              {task.description}
            </p>
          </div>

          {task.deliverables && (
            <div className="p-3.5 bg-[#0e162d] border border-[#232f52] rounded-xl text-xs space-y-1">
              <span className="font-bold text-indigo-300 uppercase tracking-wide block">Deliverables &amp; Scope</span>
              <p className="text-slate-300 leading-relaxed">{task.deliverables}</p>
            </div>
          )}

          {/* Key Terms Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
            <div className="p-3 bg-[#0e162d] border border-[#232f52] rounded-xl">
              <span className="text-slate-400 font-medium block">Compensation</span>
              <span className="font-bold text-white text-sm mt-0.5 block">{task.payout || '$30 - $40 / hr'}</span>
            </div>
            <div className="p-3 bg-[#0e162d] border border-[#232f52] rounded-xl">
              <span className="text-slate-400 font-medium block">Positions</span>
              <span className="font-bold text-white text-sm mt-0.5 block">{task.positions_count || 1} Opening(s)</span>
            </div>
            <div className="p-3 bg-[#0e162d] border border-[#232f52] rounded-xl col-span-2 sm:col-span-1">
              <span className="text-slate-400 font-medium block">Duration</span>
              <span className="font-bold text-white text-sm mt-0.5 block">{task.expected_duration || 'Ongoing'}</span>
            </div>
          </div>

          {/* Section: Task Prerequisites & Assessment Breakdown */}
          <div className="space-y-3 pt-1">
            <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
              Prerequisites &amp; Qualification Requirements
            </h4>

            {/* Assessment Topic Card (Task-Driven Assessment Highlight) */}
            <div className={`p-4 rounded-xl border transition-all ${
              isAssessmentPassed 
                ? 'bg-emerald-950/20 border-emerald-500/30' 
                : 'bg-[#0e162d] border-[#232f52]'
            }`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5 border ${
                    isAssessmentPassed 
                      ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' 
                      : 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400'
                  }`}>
                    {isAssessmentPassed ? <CheckCircle2 className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 block">
                      Required Assessment Topics
                    </span>
                    <h5 className="text-sm font-bold text-white mt-0.5">
                      {task.required_topics?.length > 1 ? `${task.required_topics.length} Qualification Topics` : examName}
                    </h5>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {task.topics_total ? `${task.topics_passed_count || 0} of ${task.topics_total} topics satisfied` : `Pass Threshold: ${examPassingScore}%`}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                    isAssessmentPassed
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                      : examStatus === 'Failed'
                      ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                      : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                  }`}>
                    {isAssessmentPassed ? '✓ All Passed' : examStatus === 'Failed' ? '✗ Action Needed' : 'Required'}
                  </span>
                </div>
              </div>

              {task.required_topics && task.required_topics.length > 0 && (
                <div className="mt-3.5 pt-3 border-t border-[#1e2a4a] space-y-2">
                  {task.required_topics.map(rt => (
                    <div key={rt.topic_id} className="flex items-center justify-between text-xs bg-[#12192e] p-2.5 rounded-xl border border-[#232f52]">
                      <span className="font-semibold text-white truncate" title={rt.name || rt.topic_name}>{rt.name || rt.topic_name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${
                        rt.status === 'Passed'
                          ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                          : rt.status === 'Failed'
                          ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                          : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                      }`}>
                        {rt.status === 'Passed' ? `✓ Passed (${rt.latest_score ?? rt.score ?? 0}%)` : rt.status === 'Failed' ? `✗ Failed (${rt.latest_score ?? rt.score ?? 0}%)` : `Needed (≥${rt.passing_threshold ?? rt.passing_score ?? 70}%)`}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {!isAssessmentPassed && (
                <div className="mt-3.5 pt-3 border-t border-[#1e2a4a] flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    Complete evaluation on the dedicated assessment page.
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      if (onOpenAssessment) onOpenAssessment(task);
                    }}
                    className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-[#2942d9] to-[#5a6ef0] hover:brightness-110 text-white text-xs font-semibold shadow-[0_0_15px_rgba(70,93,235,0.4)] flex items-center gap-1.5 cursor-pointer transition-all"
                  >
                    <span>Go to Assessment</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>

            {/* Prerequisite Requirements Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
              {/* Mandatory Certification */}
              <div className="p-3 rounded-xl bg-[#0e162d] border border-[#232f52]">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">Certification</span>
                <p className="text-xs font-bold text-white mt-0.5 truncate" title={task.required_certification}>
                  {task.required_certification || 'None required'}
                </p>
                <p className={`text-[11px] mt-1 font-medium ${
                  task.prerequisites?.certification_met ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {task.prerequisites?.certification_met ? '✓ Verified on file' : '✗ Missing / Unverified'}
                </p>
              </div>

              {/* Minimum Experience */}
              <div className="p-3 rounded-xl bg-[#0e162d] border border-[#232f52]">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">Min. Experience</span>
                <p className="text-xs font-bold text-white mt-0.5">
                  {task.minimum_experience_months ? `${task.minimum_experience_months} Months` : 'None required'}
                </p>
                <p className={`text-[11px] mt-1 font-medium ${
                  task.prerequisites?.experience_met ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {task.prerequisites?.experience_met ? '✓ Experience verified' : 'Prerequisite pending'}
                </p>
              </div>
            </div>
          </div>

          {/* Feedback & Notice Area */}
          {applyError && (
            <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{applyError}</span>
            </div>
          )}

          {hasApplied ? (
            <div className="p-3.5 rounded-xl bg-blue-950/40 border border-blue-500/30 flex items-start gap-2.5">
              <Clock className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-white">Application Recorded in Platform Ledger</p>
                <p className="text-xs text-slate-300 mt-0.5">
                  Current lifecycle status: <strong className="text-indigo-400">{currentAppStatus}</strong>.
                  {task.applied_at && ` Applied on ${new Date(task.applied_at).toLocaleDateString()}.`}
                </p>
              </div>
            </div>
          ) : task.blocking_reason && !canApply ? (
            <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/30 space-y-1">
              <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Eligibility Prerequisite Notice</span>
              </div>
              <p className="text-xs text-amber-200/90 leading-relaxed">
                {task.blocking_reason}
              </p>
            </div>
          ) : canApply ? (
            <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>All mandatory certifications, competency evaluations, and experience requirements are verified. You are ready to apply.</span>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 sm:px-6 border-t border-[#1b2542] flex items-center justify-between bg-[#080d1a] shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer"
          >
            Close
          </button>

          {hasApplied ? (
            <span className="text-xs font-semibold text-slate-400 py-2">
              Status: <strong className="text-white">{currentAppStatus}</strong>
            </span>
          ) : !isAssessmentPassed && task.exam_required ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                if (onOpenAssessment) onOpenAssessment(task);
              }}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#2942d9] to-[#5a6ef0] hover:brightness-110 text-white font-semibold text-xs shadow-[0_0_15px_rgba(70,93,235,0.4)] flex items-center gap-1.5 cursor-pointer transition-all"
            >
              <span>Complete Assessment ({examName.split(' ')[0]})</span>
              <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          ) : canApply ? (
            <button
              type="button"
              onClick={handleApply}
              disabled={isApplying}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:brightness-110 text-white font-semibold text-xs shadow-[0_0_15px_rgba(16,185,129,0.35)] flex items-center gap-1.5 cursor-pointer transition-all"
            >
              {isApplying ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Submitting Application...</span>
                </>
              ) : (
                <>
                  <span>Submit Application</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              disabled
              className="px-4 py-2 rounded-xl bg-[#12192e] text-slate-500 font-semibold text-xs border border-[#232f52] cursor-not-allowed"
            >
              Ineligible for Application
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
