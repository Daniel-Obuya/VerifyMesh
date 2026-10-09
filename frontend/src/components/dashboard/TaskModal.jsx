import React, { useState } from 'react';
import { X, CheckCircle2, AlertTriangle, ArrowRight, Briefcase, ShieldCheck, DollarSign, Clock } from 'lucide-react';

export const TaskModal = ({ isOpen, onClose, task, userCompetency, onOpenAssessment }) => {
  const [applied, setApplied] = useState(false);

  if (!isOpen || !task) return null;

  const isEligible = task.isEligible;

  const handleApply = () => {
    setApplied(true);
    setTimeout(() => {
      // Keep feedback visible
    }, 1000);
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
              isEligible ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'
            }`}>
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 leading-snug">
                {task.title}
              </h3>
              <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border mt-0.5 ${
                isEligible 
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                {isEligible ? '✓ Eligible for Immediate Assignment' : 'Requirements Pending'}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              setApplied(false);
              onClose();
            }}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4">
          <p className="text-sm text-slate-600 leading-relaxed">
            {task.description}
          </p>

          {/* Quick Specifications */}
          <div className="grid grid-cols-2 gap-3 text-left">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase">Required Competency</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">{task.requiredCompetency}</p>
              <p className={`text-[11px] mt-0.5 font-medium ${
                isEligible ? 'text-emerald-600' : 'text-amber-600'
              }`}>
                Your Tier: {userCompetency}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase">Certification Status</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">{task.certification}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">Verified via SalesMesh</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase">Compensation Rate</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">{task.payout || '$32 - $38 / hr'}</p>
              <p className="text-[11px] text-emerald-600 font-medium mt-0.5">Automated Escrow</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase">Engagement Model</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">Flexible Shift</p>
              <p className="text-[11px] text-slate-500 mt-0.5">Real-time matching</p>
            </div>
          </div>

          {/* Eligibility Guidance Alert */}
          {!isEligible ? (
            <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200 space-y-2">
              <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs sm:text-sm">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Eligibility Prerequisite Notice</span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                This task requires an <strong>{task.requiredCompetency}</strong> competency rating. Your current verified rating is <strong>{userCompetency}</strong>. 
                Complete our quick competency assessment to demonstrate your experience and unlock this task.
              </p>
            </div>
          ) : applied ? (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <div>
                <p className="text-xs sm:text-sm font-bold text-emerald-900">Application Submitted!</p>
                <p className="text-xs text-emerald-700 mt-0.5">
                  Your verified agent profile has been matched. Check your notification inbox shortly.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>You meet all verified requirements for immediate engagement.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 sm:px-6 border-t border-slate-100 flex items-center justify-between bg-white shrink-0">
          <button
            type="button"
            onClick={() => {
              setApplied(false);
              onClose();
            }}
            className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-colors"
          >
            Close
          </button>

          {!isEligible ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                if (onOpenAssessment) onOpenAssessment();
              }}
              className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2"
            >
              Take Assessment to Qualify
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleApply}
              disabled={applied}
              className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:bg-emerald-600 text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2"
            >
              {applied ? '✓ Assigned' : 'Accept & Start Task'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
