import React from 'react';
import { X, Sparkles, BrainCircuit, CheckCircle2, Award, ArrowRight } from 'lucide-react';

export const CompetencyDetailsModal = ({ 
  isOpen, 
  onClose, 
  prediction, 
  formData, 
  onOpenAssessment 
}) => {
  if (!isOpen) return null;

  const competency = prediction?.predicted_competency || 'Eligible';
  const confidence = prediction?.confidence || 78;
  const probabilities = prediction?.probabilities || {
    Eligible: 78,
    'Not Eligible': 22,
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-xl bg-[#0d1428] rounded-2xl shadow-2xl border border-[#2b3a67] flex flex-col max-h-[90vh] overflow-hidden text-white"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-4 sm:px-6 sm:py-4 border-b border-[#1b2542] flex items-center justify-between bg-[#080d1a] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
              <BrainCircuit className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold font-sora text-white leading-snug">
                Competency Profile &amp; Model Insights
              </h3>
              <p className="text-[11px] text-slate-400">
                Deterministic Eligibility Engine &bull; Verification Summary
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#151f38] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 text-xs sm:text-[13px] text-slate-300">
          {/* Main Status Banner */}
          <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52] flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                Current Level
              </span>
              <h4 className="text-xl font-bold font-sora text-white mt-0.5">{competency}</h4>
              <p className="text-xs text-indigo-400 font-medium mt-0.5">
                {confidence}% AI Confidence
              </p>
            </div>
            <div className="text-right">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Verified Active
              </span>
            </div>
          </div>

          {/* Model Probability Breakdown */}
          <div className="space-y-2">
            <h5 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
              Random Forest Probability Breakdown
            </h5>
            <div className="p-4 rounded-xl bg-[#0e162d] border border-[#232f52] space-y-3">
              {Object.entries(probabilities).map(([cls, prob]) => {
                const isEligibleClass = cls === 'Eligible';
                return (
                  <div key={cls} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-300">{cls}</span>
                      <span className="text-white font-bold">{prob}%</span>
                    </div>
                    <div className="w-full bg-[#141c33] h-2 rounded-full overflow-hidden border border-[#1b2542]">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          isEligibleClass 
                            ? 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_10px_rgba(16,185,129,0.5)]' 
                            : 'bg-slate-600'
                        }`}
                        style={{ width: `${Math.min(prob, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Battery Test Scores */}
          <div className="space-y-2">
            <h5 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
              Core Test Battery Breakdown
            </h5>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              <div className="p-3 bg-[#0e162d] rounded-xl border border-[#232f52]">
                <span className="text-[10px] text-slate-400 font-medium block">Overall Score</span>
                <span className="text-sm font-bold text-white">{formData?.assessment_score || 82.5} / 100</span>
              </div>
              <div className="p-3 bg-[#0e162d] rounded-xl border border-[#232f52]">
                <span className="text-[10px] text-slate-400 font-medium block">Communication</span>
                <span className="text-sm font-bold text-white">{formData?.communication_score || 85.0} / 100</span>
              </div>
              <div className="p-3 bg-[#0e162d] rounded-xl border border-[#232f52]">
                <span className="text-[10px] text-slate-400 font-medium block">Product Knowledge</span>
                <span className="text-sm font-bold text-white">{formData?.product_knowledge_score || 80.0} / 100</span>
              </div>
              <div className="p-3 bg-[#0e162d] rounded-xl border border-[#232f52]">
                <span className="text-[10px] text-slate-400 font-medium block">Sales Skill</span>
                <span className="text-sm font-bold text-white">{formData?.sales_skill_score || 88.0} / 100</span>
              </div>
              <div className="p-3 bg-[#0e162d] rounded-xl border border-[#232f52]">
                <span className="text-[10px] text-slate-400 font-medium block">Customer Service</span>
                <span className="text-sm font-bold text-white">{formData?.customer_service_score || 84.0} / 100</span>
              </div>
              <div className="p-3 bg-[#0e162d] rounded-xl border border-[#232f52]">
                <span className="text-[10px] text-slate-400 font-medium block">Domain Experience</span>
                <span className="text-sm font-bold text-white">{formData?.previous_experience_months || 24} mos</span>
              </div>
            </div>
          </div>

          {/* Model Decoupling Architecture Note */}
          <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/30 text-xs text-slate-300 leading-relaxed">
            <p className="font-semibold text-indigo-300 mb-1 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              Eligibility Architecture &amp; Rules Engine
            </p>
            VerifyMesh employs deterministic server-side business rules to evaluate verified profile credentials, passed assessments, and tenure into an authoritative eligibility status: <strong className="text-emerald-400">Eligible</strong> or <strong className="text-rose-400">Not Eligible</strong>. Active tasks feature advisory machine learning suitability scoring for administrator review.
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 sm:px-6 border-t border-[#1b2542] flex items-center justify-between bg-[#080d1a] shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              onClose();
              if (onOpenAssessment) onOpenAssessment();
            }}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#2942d9] to-[#5a6ef0] hover:brightness-110 text-white font-semibold text-xs shadow-[0_0_15px_rgba(70,93,235,0.4)] flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <span>Retake Assessment</span>
            <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
