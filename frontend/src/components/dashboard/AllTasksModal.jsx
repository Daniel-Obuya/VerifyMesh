import React from 'react';
import { X, Briefcase, CheckCircle2, ArrowRight } from 'lucide-react';

export const AllTasksModal = ({ isOpen, onClose, tasks, onSelectTask }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        <div className="p-5 sm:px-6 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center shrink-0">
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                All Available Tasks in Mesh
              </h3>
              <p className="text-xs text-slate-500">
                Active opportunities with verified eligibility requirements
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

        <div className="p-5 sm:p-6 overflow-y-auto space-y-4">
          <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white">
            {tasks.map((task) => (
              <div 
                key={task.id} 
                className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors cursor-pointer"
                onClick={() => {
                  onClose();
                  onSelectTask(task);
                }}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900">{task.title}</h4>
                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                      task.isEligible
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      {task.isEligible ? '✓ Eligible' : 'Requires ' + task.requiredCompetency}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 max-w-md">{task.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-400">
                    <span>Required: <strong className="text-slate-700">{task.requiredCompetency}</strong></span>
                    <span>Rate: <strong className="text-slate-700">{task.payout}</strong></span>
                  </div>
                </div>

                <div className="shrink-0 self-end sm:self-center">
                  <span className="text-xs font-semibold text-[#3B50BA] flex items-center gap-1 hover:underline">
                    {task.isEligible ? 'View task' : 'View requirements'} &rarr;
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 sm:px-6 border-t border-slate-100 flex justify-end bg-white">
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
