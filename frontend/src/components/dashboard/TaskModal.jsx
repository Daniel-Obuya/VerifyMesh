import React, { useState } from 'react';
import { 
  X, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight, 
  Briefcase, 
  ShieldCheck, 
  Clock, 
  Lock, 
  FileCheck2, 
  Award 
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
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
        <Lock className="w-3.5 h-3.5" /> {task.state || 'Requirements Pending'}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-5 sm:px-6 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              task.can_apply ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-600'
            }`}>
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 leading-snug">
                {task.title}
              </h3>
              <div className="mt-1 flex items-center gap-2">
                {getStatusBadge()}
                {task.category && (
                  <span className="text-xs text-slate-400 font-medium">&bull; {task.category}</span>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 text-slate-700">
          <p className="text-sm text-slate-600 leading-relaxed">
            {task.description}
          </p>

          {/* Requirements Grid */}
          <div className="grid grid-cols-2 gap-3 text-left">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Required Competency</span>
              <p className="text-sm font-bold text-slate-900 mt-0.5">
                {task.required_competency || task.requiredCompetency || 'Competent'}
              </p>
              <p className={`text-[11px] mt-0.5 font-medium ${
                task.prerequisites?.competency_met ? 'text-emerald-600' : 'text-amber-600'
              }`}>
                {task.prerequisites?.competency_met ? '✓ Met' : `Current: ${userCompetency || 'Not Assessed'}`}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Mandatory Certification</span>
              <p className="text-sm font-bold text-slate-900 mt-0.5">
                {task.required_certification || task.certification || 'None required'}
              </p>
              <p className={`text-[11px] mt-0.5 font-medium ${
                task.prerequisites?.certification_met ? 'text-emerald-600' : 'text-rose-600'
              }`}>
                {task.prerequisites?.certification_met ? '✓ Active on file' : '✗ Missing / Unverified'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Minimum Experience</span>
              <p className="text-sm font-bold text-slate-900 mt-0.5">
                {task.minimum_experience_months || 0} months
              </p>
              <p className={`text-[11px] mt-0.5 font-medium ${
                task.prerequisites?.experience_met ? 'text-emerald-600' : 'text-amber-600'
              }`}>
                {task.prerequisites?.experience_met ? '✓ Experience verified' : 'Prerequisite pending'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Task Assessment</span>
              <p className="text-sm font-bold text-slate-900 mt-0.5">
                {task.exam_required ? 'Required (Passed)' : 'Not Required'}
              </p>
              <p className={`text-[11px] mt-0.5 font-medium ${
                task.prerequisites?.assessment_met ? 'text-emerald-600' : 'text-amber-600'
              }`}>
                {task.prerequisites?.assessment_met ? '✓ Completed' : 'Pending test battery'}
              </p>
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
            <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 flex items-start gap-3">
              <Clock className="w-5 h-5 text-[#3B50BA] shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-slate-900">Application Recorded</p>
                <p className="text-xs text-slate-600 mt-0.5">
                  Current lifecycle status: <strong className="text-[#3B50BA]">{currentAppStatus}</strong>.
                  Administrative team reviews applications against active roster quotas.
                </p>
              </div>
            </div>
          ) : task.blocking_reason ? (
            <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200 space-y-1.5">
              <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs sm:text-sm">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Eligibility Requirement Notice</span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                {task.blocking_reason}
              </p>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>All mandatory certifications and competency thresholds are verified. You are eligible to apply.</span>
            </div>
          )}
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
          ) : task.state === 'Assessment Needed' ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                if (onOpenAssessment) onOpenAssessment();
              }}
              className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
            >
              Take Assessment to Qualify
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
                  Submitting Application...
                </>
              ) : (
                'Submit Application'
              )}
            </button>
          ) : (
            <button
              type="button"
              disabled
              className="px-5 py-2.5 rounded-xl bg-slate-100 text-slate-400 font-semibold text-xs sm:text-sm border border-slate-200 cursor-not-allowed"
            >
              {task.state || 'Not Eligible'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
