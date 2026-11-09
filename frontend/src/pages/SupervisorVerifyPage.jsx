import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Building2, 
  Calendar, 
  UserCheck, 
  ShieldCheck, 
  Briefcase,
  HelpCircle,
  Clock,
  ArrowRight
} from 'lucide-react';
import { competencyService } from '../services/competencyService';

export const SupervisorVerifyPage = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [isLoading, setIsLoading] = useState(true);
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);

  // Form state
  const [answers, setAnswers] = useState({
    role_accurate: 'yes',
    tenure_accurate: 'yes',
    performance_standing: 'good'
  });
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedResult, setSubmittedResult] = useState(null);

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short' });
    } catch {
      return dateStr;
    }
  };

  useEffect(() => {
    if (!token) {
      setError('Verification token is missing from the URL. Please use the exact link sent to your email.');
      setIsLoading(false);
      return;
    }

    const fetchRecord = async () => {
      try {
        setIsLoading(true);
        const res = await competencyService.getPublicExperienceVerification(token);
        const recordData = res?.data?.data || res?.data;
        if (recordData && (recordData.company || recordData.id)) {
          setRecord(recordData);
        } else {
          setError('Could not retrieve candidate record.');
        }
      } catch (err) {
        setError(err?.data?.error || err?.message || 'Verification link is invalid, expired, or has already been used.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecord();
  }, [token]);

  const handleSubmit = async (decision) => {
    if (decision === 'DISPUTE' && !feedback.trim()) {
      alert('Please provide a brief reason or comment explaining the dispute.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await competencyService.submitPublicExperienceVerification(token, {
        decision,
        feedback: feedback.trim() || (decision === 'CONFIRM' ? 'Confirmed by supervisor' : 'Disputed'),
        answers
      });
      setSubmittedResult({
        decision,
        message: res?.message || res?.data?.message || (decision === 'CONFIRM' ? 'Employment successfully verified.' : 'Record marked as disputed.')
      });
    } catch (err) {
      alert(err?.data?.error || err?.message || 'Failed to submit verification. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#3B50BA] flex items-center justify-center text-white font-bold text-lg shadow-sm">
              V
            </div>
            <span className="font-bold text-slate-900 tracking-tight text-lg">
              Verify<span className="text-[#3B50BA]">Mesh</span>
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1.5 rounded-full">
            <ShieldCheck className="w-4 h-4 text-[#3B50BA]" />
            <span>Secure Reference Portal</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 my-6">
        <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200/80 overflow-hidden">
          {/* Header Banner */}
          <div className="bg-linear-to-r from-slate-900 to-[#1E293B] text-white p-6 sm:p-8">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-white/10 text-slate-200 mb-3 backdrop-blur-xs">
              <UserCheck className="w-3.5 h-3.5 text-indigo-300" />
              Automated Employment Verification
            </span>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight">
              Employment Verification Request
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-lg">
              Confirm whether the employment tenure and title submitted by this candidate are legitimate. Takes under 1 minute.
            </p>
          </div>

          <div className="p-6 sm:p-8">
            {isLoading ? (
              <div className="py-16 text-center space-y-3">
                <div className="w-9 h-9 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm font-medium text-slate-600">Retrieving candidate record...</p>
              </div>
            ) : error ? (
              <div className="py-10 text-center space-y-4">
                <div className="w-14 h-14 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto">
                  <AlertTriangle className="w-7 h-7" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Verification Link Unavailable</h2>
                <p className="text-sm text-slate-600 max-w-md mx-auto">{error}</p>
                <div className="pt-2">
                  <Link 
                    to="/login"
                    className="inline-flex items-center gap-1 text-sm font-semibold text-[#3B50BA] hover:underline"
                  >
                    Go to VerifyMesh Home &rarr;
                  </Link>
                </div>
              </div>
            ) : submittedResult ? (
              /* Success / Result Screen */
              <div className="py-10 text-center space-y-5 animate-in fade-in zoom-in-95 duration-300">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto shadow-sm ${
                  submittedResult.decision === 'CONFIRM' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-amber-50 text-amber-600 border border-amber-200'
                }`}>
                  {submittedResult.decision === 'CONFIRM' ? (
                    <CheckCircle2 className="w-9 h-9" />
                  ) : (
                    <XCircle className="w-9 h-9" />
                  )}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">
                    {submittedResult.decision === 'CONFIRM' ? 'Employment Verified!' : 'Feedback Recorded'}
                  </h2>
                  <p className="text-sm text-slate-600 max-w-md mx-auto mt-1.5 leading-relaxed">
                    {submittedResult.message}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 max-w-md mx-auto text-xs text-slate-600 space-y-1">
                  <p><span className="font-semibold text-slate-800">Candidate:</span> {record.agent_name}</p>
                  <p><span className="font-semibold text-slate-800">Organization:</span> {record.company}</p>
                  <p><span className="font-semibold text-slate-800">Role:</span> {record.job_title}</p>
                  <p><span className="font-semibold text-slate-800">Status:</span> {submittedResult.decision === 'CONFIRM' ? 'VERIFIED' : 'DISPUTED'}</p>
                </div>
                <p className="text-xs text-slate-400">
                  You may now safely close this window. Thank you for maintaining integrity on VerifyMesh.
                </p>
              </div>
            ) : record.verification_status !== 'PENDING' ? (
              /* Already Reviewed State */
              <div className="py-10 text-center space-y-4">
                <div className="w-14 h-14 bg-indigo-50 text-[#3B50BA] rounded-full flex items-center justify-center mx-auto">
                  <Clock className="w-7 h-7" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Already Reviewed</h2>
                <p className="text-sm text-slate-600 max-w-md mx-auto">
                  This experience submission for <strong>{record.agent_name}</strong> at <strong>{record.company}</strong> has already been marked as <span className="font-bold text-slate-800">{record.verification_status}</span>.
                </p>
                {record.supervisor_feedback && (
                  <p className="text-xs text-slate-500 italic bg-slate-50 p-3 rounded-xl border border-slate-200 max-w-md mx-auto">
                    "{record.supervisor_feedback}"
                  </p>
                )}
              </div>
            ) : (
              /* Active Verification Questions */
              <div className="space-y-6">
                {/* Candidate & Role Profile Card */}
                <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200 text-xs sm:text-sm">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
                    <span className="font-semibold text-slate-500 uppercase tracking-wider text-[11px]">
                      Candidate Submission
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                      Pending Your Confirmation
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3">
                    <div>
                      <span className="text-slate-400 text-xs block">Candidate Name</span>
                      <span className="font-bold text-slate-900 text-sm">{record.agent_name}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-xs block">Organization / Company</span>
                      <span className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-slate-500" />
                        {record.company}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-xs block">Job Title / Position</span>
                      <span className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                        <Briefcase className="w-3.5 h-3.5 text-slate-500" />
                        {record.job_title}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-xs block">Reported Employment Dates</span>
                      <span className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {formatDate(record.start_date)} &rarr; {record.is_current ? 'Present (Current)' : (formatDate(record.end_date) || 'End')}
                      </span>
                    </div>
                  </div>

                  {record.description && (
                    <div className="mt-3 pt-3 border-t border-slate-200/80">
                      <span className="text-slate-400 text-xs block">Reported Responsibilities:</span>
                      <p className="text-xs text-slate-600 mt-1 italic leading-relaxed">
                        "{record.description}"
                      </p>
                    </div>
                  )}
                </div>

                {/* 3 Simple Verification Questions */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                    <HelpCircle className="w-4 h-4 text-[#3B50BA]" />
                    Please answer the 3 quick questions below:
                  </h3>

                  {/* Question 1: Role accuracy */}
                  <div className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors bg-white">
                    <p className="text-xs sm:text-sm font-semibold text-slate-800">
                      1. Did {record.agent_name} serve as <span className="text-[#3B50BA] font-bold">{record.job_title}</span> (or equivalent title) at {record.company}?
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-xs font-semibold">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input 
                          type="radio" 
                          name="role_accurate" 
                          checked={answers.role_accurate === 'yes'} 
                          onChange={() => setAnswers({ ...answers, role_accurate: 'yes' })}
                          className="text-[#3B50BA] focus:ring-[#3B50BA]" 
                        />
                        <span>Yes, role title is accurate</span>
                      </label>
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input 
                          type="radio" 
                          name="role_accurate" 
                          checked={answers.role_accurate === 'no'} 
                          onChange={() => setAnswers({ ...answers, role_accurate: 'no' })}
                          className="text-[#3B50BA] focus:ring-[#3B50BA]" 
                        />
                        <span>No, role title is inaccurate</span>
                      </label>
                    </div>
                  </div>

                  {/* Question 2: Dates accuracy */}
                  <div className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors bg-white">
                    <p className="text-xs sm:text-sm font-semibold text-slate-800">
                      2. Is the reported employment tenure (<span className="text-slate-900 font-bold">{formatDate(record.start_date)} to {record.is_current ? 'Present' : (formatDate(record.end_date) || 'End')}</span>) approximately correct?
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-xs font-semibold">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input 
                          type="radio" 
                          name="tenure_accurate" 
                          checked={answers.tenure_accurate === 'yes'} 
                          onChange={() => setAnswers({ ...answers, tenure_accurate: 'yes' })}
                          className="text-[#3B50BA] focus:ring-[#3B50BA]" 
                        />
                        <span>Yes, tenure is accurate</span>
                      </label>
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input 
                          type="radio" 
                          name="tenure_accurate" 
                          checked={answers.tenure_accurate === 'no'} 
                          onChange={() => setAnswers({ ...answers, tenure_accurate: 'no' })}
                          className="text-[#3B50BA] focus:ring-[#3B50BA]" 
                        />
                        <span>No, dates are significantly different</span>
                      </label>
                    </div>
                  </div>

                  {/* Question 3: Optional Feedback */}
                  <div className="p-4 rounded-xl border border-slate-200 bg-white">
                    <label className="block text-xs sm:text-sm font-semibold text-slate-800 mb-1">
                      3. Additional Supervisor Notes or Comments <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <textarea 
                      rows={2}
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      placeholder="e.g. Worked diligently, left in good standing, or note any discrepancies..."
                      className="w-full px-3 py-2 text-xs sm:text-sm rounded-lg border border-slate-200 focus:outline-none focus:border-[#3B50BA]"
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => handleSubmit('CONFIRM')}
                    className="w-full sm:flex-1 py-3 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs sm:text-sm shadow-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Confirm &amp; Verify Employment</span>
                  </button>

                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => handleSubmit('DISPUTE')}
                    className="w-full sm:w-auto py-3 px-5 rounded-xl border border-rose-300 hover:bg-rose-50 text-rose-700 font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    <XCircle className="w-4 h-4 text-rose-600" />
                    <span>Dispute Claim</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-xs text-slate-400">
        VerifyMesh AI-Assisted Workforce Qualification &bull; Automated Reference Authentication Service
      </footer>
    </div>
  );
};

export default SupervisorVerifyPage;
