import React from 'react';
import { X, User, ShieldCheck, Mail, Award, Calendar, CheckCircle2 } from 'lucide-react';

export const ProfileModal = ({ isOpen, onClose, user, competency, confidence }) => {
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
            <div className="w-10 h-10 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-sm flex items-center justify-center">
              DO
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 leading-tight">
                {user?.fullName || 'Daniel Obuya'}
              </h3>
              <p className="text-xs text-slate-500">Verified Agent Profile</p>
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

        <div className="p-5 space-y-4 overflow-y-auto">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">Account ID</span>
              <span className="font-mono font-semibold text-slate-800">VM-AGT-2049</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">Email Address</span>
              <span className="font-medium text-slate-800">{user?.email || 'daniel.obuya@verifymesh.io'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">Mesh Role</span>
              <span className="font-semibold text-[#3B50BA]">Agent</span>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wide">
              Verified Competency &amp; Status
            </h4>
            <div className="p-3.5 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Current AI Rating:</span>
                <span className="font-bold text-slate-900">{competency} ({confidence}% conf)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Customer Service Cert:</span>
                <span className="font-bold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Background Verification:</span>
                <span className="font-bold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Cleared
                </span>
              </div>
            </div>
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
