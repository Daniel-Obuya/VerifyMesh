import React from 'react';
import { X, HelpCircle, BookOpen, MessageSquare, CheckCircle2 } from 'lucide-react';

export const HelpModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 leading-tight">
                Help &amp; Support
              </h3>
              <p className="text-xs text-slate-500">VerifyMesh Agent Guide</p>
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

        <div className="p-5 space-y-4 overflow-y-auto text-xs text-slate-600">
          <div className="space-y-1.5">
            <h4 className="font-bold text-slate-900 text-sm">How does Competency work?</h4>
            <p className="leading-relaxed">
              VerifyMesh uses a Random Forest ML model trained in Google Colab to evaluate your assessment scores and industry experience into a verified competency level (Basic, Competent, Advanced).
            </p>
          </div>

          <div className="space-y-1.5">
            <h4 className="font-bold text-slate-900 text-sm">How do I qualify for more tasks?</h4>
            <p className="leading-relaxed">
              Click the <strong>Take Assessment</strong> button to update your test battery scores or complete the interactive quiz. Reaching the <em>Advanced</em> level unlocks premium roles like Product Consultant.
            </p>
          </div>

          <div className="p-3 bg-blue-50/70 border border-blue-100 rounded-xl text-blue-900 space-y-1">
            <p className="font-semibold">Need further assistance?</p>
            <p className="text-blue-700">Contact the VerifyMesh coordinator at support@verifymesh.io</p>
          </div>
        </div>

        <div className="p-4 border-t border-slate-100 flex justify-end bg-white">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs sm:text-sm font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
