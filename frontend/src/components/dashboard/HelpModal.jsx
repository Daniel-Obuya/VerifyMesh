import React from 'react';
import { X, HelpCircle, BookOpen, MessageSquare, CheckCircle2 } from 'lucide-react';

export const HelpModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md bg-[#0d1428] rounded-2xl shadow-2xl border border-[#2b3a67] flex flex-col max-h-[90vh] overflow-hidden text-white"
        role="dialog"
        aria-modal="true"
      >
        <div className="p-4 sm:px-6 sm:py-4 border-b border-[#1b2542] flex items-center justify-between bg-[#080d1a] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
              <HelpCircle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold font-sora text-white leading-tight">
                Help &amp; Support
              </h3>
              <p className="text-[11px] text-slate-400">VerifyMesh Agent Guide</p>
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

        <div className="p-5 sm:p-6 space-y-4 overflow-y-auto text-xs text-slate-300">
          <div className="space-y-1.5">
            <h4 className="font-semibold text-white text-xs sm:text-sm">How does Competency work?</h4>
            <p className="leading-relaxed text-slate-300">
              VerifyMesh uses deterministic server-side business rules to evaluate your assessment scores, industry experience, and verified certifications into an authoritative eligibility status: <strong className="text-indigo-400">Eligible</strong> or <strong className="text-rose-400">Not Eligible</strong>.
            </p>
          </div>

          <div className="space-y-1.5">
            <h4 className="font-semibold text-white text-xs sm:text-sm">How do I qualify for tasks?</h4>
            <p className="leading-relaxed text-slate-300">
              Complete required topic assessments with passing scores (&ge;70%) and ensure your prerequisite certifications and experience months are verified on your profile to unlock task applications.
            </p>
          </div>

          <div className="p-3.5 bg-[#0e162d] border border-[#232f52] rounded-xl text-slate-300 space-y-1">
            <p className="font-semibold text-indigo-400">Need further assistance?</p>
            <p className="text-slate-400 text-[11px]">Contact the VerifyMesh coordinator at support@verifymesh.io</p>
          </div>
        </div>

        <div className="p-4 sm:px-6 border-t border-[#1b2542] flex justify-end bg-[#080d1a]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-[#151f38] transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
