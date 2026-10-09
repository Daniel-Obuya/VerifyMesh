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

  const competency = prediction?.predicted_competency || 'Competent';
  const confidence = prediction?.confidence || 78;
  const probabilities = prediction?.probabilities || {
    Competent: 78,
    Advanced: 14,
    Basic: 6,
    'Needs Improvement': 2,
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-5 sm:px-6 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center shrink-0">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                Competency Profile &amp; Model Insights
              </h3>
              <p className="text-xs text-slate-500">
                Google Colab Random Forest Model &bull; Verification Summary
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-5">
          {/* Main Status Banner */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Current Level
              </span>
              <h4 className="text-2xl font-bold text-slate-900 mt-0.5">{competency}</h4>
              <p className="text-xs text-[#3B50BA] font-medium mt-0.5">
                {confidence}% AI Confidence
              </p>
            </div>
            <div className="text-right">
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Verified Active
              </span>
            </div>
          </div>

          {/* Model Probability Breakdown */}
          <div className="space-y-2">
            <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Random Forest Probability Breakdown
            </h5>
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-3">
              {Object.entries(probabilities).map(([cls, prob]) => (
                <div key={cls} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-700">{cls}</span>
                    <span className="text-slate-900">{prob}%</span>
                  </div>
                  <div className="w-full bg-slate-200/70 h-2 rounded-full overflow-hidden">
                    <div 
                      className="bg-[#3B50BA] h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(prob, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Battery Test Scores */}
          <div className="space-y-2">
            <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Core Test Battery Breakdown
            </h5>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-400 font-medium block">Overall Score</span>
                <span className="text-sm font-bold text-slate-900">{formData?.assessment_score || 82.5} / 100</span>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-400 font-medium block">Communication</span>
                <span className="text-sm font-bold text-slate-900">{formData?.communication_score || 85.0} / 100</span>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-400 font-medium block">Product Knowledge</span>
                <span className="text-sm font-bold text-slate-900">{formData?.product_knowledge_score || 80.0} / 100</span>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-400 font-medium block">Sales Skill</span>
                <span className="text-sm font-bold text-slate-900">{formData?.sales_skill_score || 88.0} / 100</span>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-400 font-medium block">Customer Service</span>
                <span className="text-sm font-bold text-slate-900">{formData?.customer_service_score || 84.0} / 100</span>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-400 font-medium block">Domain Experience</span>
                <span className="text-sm font-bold text-slate-900">{formData?.previous_experience_months || 24} mos</span>
              </div>
            </div>
          </div>

          {/* Model Decoupling Architecture Note */}
          <div className="p-3.5 rounded-xl bg-blue-50/60 border border-blue-100 text-xs text-slate-600 leading-relaxed">
            <p className="font-semibold text-blue-900 mb-1 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#3B50BA]" />
              Model Architecture &amp; Training
            </p>
            VerifyMesh decouples heavy model training (executed externally in Google Colab) from fast real-time inference in this dashboard. Assessment scores can be re-evaluated anytime to reflect newly acquired skills and unlock higher-paying tasks.
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 sm:px-6 border-t border-slate-100 flex items-center justify-between bg-white shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              onClose();
              if (onOpenAssessment) onOpenAssessment();
            }}
            className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2"
          >
            Retake Assessment
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
