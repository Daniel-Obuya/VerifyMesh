import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ShieldCheck, 
  Check, 
  Briefcase, 
  Sparkles, 
  RotateCcw,
  AlertTriangle,
  Award,
  Layers,
  ChevronRight
} from 'lucide-react';
import { competencyService } from '../services/competencyService';
import { useAuth } from '../context/AuthContext';

export const AssessmentResultsPage = () => {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [attemptData, setAttemptData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Application submission state (if eligible)
  const [isApplying, setIsApplying] = useState(false);
  const [applicationSuccess, setApplicationSuccess] = useState(null);
  const [applicationError, setApplicationError] = useState(null);

  // Candidate display formatting
  const rawName = user?.fullName || user?.username || 'Candidate';
  const cleanName = rawName.replace(/\s*\(Verified\)/gi, '').trim();
  const userInitials = cleanName
    ? cleanName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'CA';

  useEffect(() => {
    let isMounted = true;

    const fetchAttempt = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const res = await competencyService.getAttemptDetails(attemptId);
        if (res?.success && res.data) {
          if (isMounted) setAttemptData(res.data);
        } else {
          throw new Error(res?.error || 'Assessment attempt not found.');
        }
      } catch (err) {
        console.error('Error fetching attempt details:', err);
        if (isMounted) {
          setError(err?.data?.error || err?.message || 'Failed to retrieve assessment results.');
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    if (attemptId) {
      fetchAttempt();
    } else {
      setIsLoading(false);
      setError('Invalid attempt ID.');
    }

    return () => {
      isMounted = false;
    };
  }, [attemptId]);

  const handleApply = async (taskId) => {
    setIsApplying(true);
    setApplicationError(null);

    try {
      const res = await competencyService.applyForTask(taskId);
      if (res?.success) {
        setApplicationSuccess('Your application was submitted successfully!');
        // Refresh attempt and task state
        const refRes = await competencyService.getAttemptDetails(attemptId);
        if (refRes?.success && refRes.data) {
          setAttemptData(refRes.data);
        }
      } else {
        setApplicationError(res?.error || 'Failed to submit application.');
      }
    } catch (err) {
      console.error('Apply error:', err);
      setApplicationError(err?.data?.error || err?.message || 'Error submitting application.');
    } finally {
      setIsApplying(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex items-center justify-center font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-indigo-600/6 blur-[140px] rounded-full" />
          <div className="absolute top-1/3 right-10 w-[500px] h-[350px] bg-blue-500/5 blur-[130px] rounded-full" />
        </div>
        <div className="text-center space-y-3 relative z-10">
          <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-400">Retrieving evaluated results...</p>
        </div>
      </div>
    );
  }

  if (error || !attemptData) {
    return (
      <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex items-center justify-center font-sans p-4 relative selection:bg-[#5a69f0]/40 selection:text-white">
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-indigo-600/6 blur-[140px] rounded-full" />
          <div className="absolute top-1/3 right-10 w-[500px] h-[350px] bg-blue-500/5 blur-[130px] rounded-full" />
        </div>
        <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-8 max-w-md w-full text-center space-y-4 shadow-xl relative z-10">
          <div className="w-12 h-12 rounded-full bg-rose-950/60 border border-rose-500/40 text-rose-400 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold font-sora text-white">Unable to Load Results</h2>
          <p className="text-xs text-slate-400">{error || 'Attempt records could not be found.'}</p>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const {
    topic_id,
    topic_name,
    task_id,
    task_title,
    score,
    passed,
    passing_score,
    subscores = {},
    prediction = {},
    task_eligibility = null
  } = attemptData;

  const competencyLabel = prediction.competency_label || 'Eligible';
  const decisionLabel = prediction.decision_label || 'Eligible';
  const confidence = prediction.confidence ?? 78;

  return (
    <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex flex-col font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-indigo-600/6 blur-[140px] rounded-full" />
        <div className="absolute top-1/3 right-10 w-[500px] h-[350px] bg-blue-500/5 blur-[130px] rounded-full" />
      </div>

      {/* Top Header */}
      <header className="h-16 bg-[#080d1a]/95 border-b border-[#1b2542] px-4 sm:px-8 flex items-center justify-between shrink-0 sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-[#151f38]/60 hover:bg-[#151f38] border border-[#1e2a4a] transition-all cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </button>

          <div className="h-5 w-px bg-[#1b2542] hidden sm:block" />

          <div className="flex items-center gap-2.5 text-white select-none">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#4b5bd8] to-[#6f7dff] flex items-center justify-center p-1.5 shadow-lg shadow-indigo-500/25 shrink-0">
              <svg viewBox="0 0 28 28" fill="none" className="w-full h-full text-white">
                <path d="M6 8V18C6 20.2091 7.79086 22 10 22H20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M10 17L15 13L21 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="10" cy="17" r="2.2" fill="currentColor" />
                <circle cx="15" cy="13" r="2.2" fill="currentColor" />
                <circle cx="21" cy="16" r="2.2" fill="currentColor" />
              </svg>
            </div>
            <div>
              <span className="font-sora text-sm sm:text-base font-bold text-white tracking-tight block">
                VerifyMesh
              </span>
              <span className="text-[10px] font-semibold tracking-wider text-indigo-400 uppercase block -mt-1">
                Assessment Report
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {task_id && (
            <button
              type="button"
              onClick={() => navigate(`/agent/assessment/${task_id}`)}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors hidden sm:flex items-center gap-1 cursor-pointer"
            >
              <span>View Task Requirements</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
            {userInitials}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8 max-w-4xl w-full mx-auto space-y-6 relative z-10">
        {/* Outcome Banner */}
        <div className={`p-6 sm:p-8 rounded-2xl border shadow-xl flex flex-col sm:flex-row items-center sm:items-start gap-5 ${
          passed 
            ? 'bg-gradient-to-br from-emerald-950/40 via-[#0b1020] to-[#080d1a] border-emerald-500/40' 
            : 'bg-gradient-to-br from-amber-950/40 via-[#0b1020] to-[#080d1a] border-amber-500/40'
        }`}>
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 shadow-lg ${
            passed 
              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 shadow-emerald-500/10' 
              : 'bg-amber-950/80 text-amber-400 border border-amber-500/40 shadow-amber-500/10'
          }`}>
            {passed ? <CheckCircle2 className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
          </div>

          <div className="space-y-2 text-center sm:text-left flex-1">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <span className={`text-xs font-bold px-3 py-0.5 rounded-full border ${
                passed 
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40' 
                  : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
              }`}>
                {passed ? 'Topic Assessment Passed' : 'Passing Threshold Not Reached'}
              </span>
              <span className="text-xs text-slate-400 font-medium">
                Topic: <strong className="text-white">{topic_name}</strong>
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold font-sora text-white tracking-tight">
              Score: {score}% &bull; {passed ? 'Threshold Satisfied' : 'Review Required'}
            </h1>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-2xl">
              {passed ? (
                <span>
                  Congratulations! Your responses met the required standard of &ge;{passing_score}%. This credential has been authoritatively recorded on your agent ledger and is valid for all matching opportunities.
                </span>
              ) : (
                <span>
                  Your score of {score}% was below the required threshold of &ge;{passing_score}%. Review the competency topics below and retake the evaluation when ready.
                </span>
              )}
            </p>
          </div>
        </div>

        {/* =========================================================================
           3 DISTINCT REQUIRED SECTIONS:
           1. Assessment Result
           2. ML Competency Prediction
           3. Task Eligibility
           ========================================================================= */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* =========================================================================
             SECTION 1: ASSESSMENT RESULT
             ========================================================================= */}
          <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-5 sm:p-6 shadow-xl flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-indigo-400">1. Assessment Result</span>
                <span className={passed ? 'text-emerald-400' : 'text-amber-400'}>
                  {passed ? 'Passed' : 'Failed'}
                </span>
              </div>

              <div>
                <span className="text-3xl font-bold font-sora text-white">{score}%</span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  Threshold: &ge;{passing_score}%
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#080d1a]/80 border border-[#1b2542] space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Topic Assessed:</span>
                  <span className="font-bold text-white text-right">{topic_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Grading Source:</span>
                  <span className="font-bold text-white">Server Evaluated</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Credential Status:</span>
                  <span className={`font-bold ${passed ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {passed ? 'Valid on Profile' : 'Retake Allowed'}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-[#1b2542]">
              {!passed ? (
                <button
                  type="button"
                  onClick={() => navigate(`/agent/assessment/${task_id || 'general'}?topicId=${topic_id}`)}
                  className="w-full py-2 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-semibold text-xs rounded-xl shadow-md shadow-amber-600/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Retake Topic Evaluation</span>
                </button>
              ) : (
                <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Permanent result on ledger
                </span>
              )}
            </div>
          </div>

          {/* =========================================================================
             SECTION 2: COMPETENCY PREDICTION
             ========================================================================= */}
          <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-5 sm:p-6 shadow-xl flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-indigo-400">2. ML Competency</span>
                <span className="text-indigo-300">Stage 2 Advisory</span>
              </div>

              <div>
                <span className="text-3xl font-bold font-sora text-white">{competencyLabel}</span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  Decision: <strong className="text-white">{decisionLabel}</strong> &bull; {confidence}% confidence
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#080d1a]/80 border border-[#1b2542] space-y-1.5 text-xs">
                <span className="font-bold text-slate-300 block text-[11px]">Subscore Matrix:</span>
                <div className="grid grid-cols-2 gap-1.5 text-[11px] text-slate-300">
                  <div>Comm: <strong className="text-white">{subscores.communication_score ?? '—'}%</strong></div>
                  <div>Sales: <strong className="text-white">{subscores.sales_skill_score ?? '—'}%</strong></div>
                  <div>Prod: <strong className="text-white">{subscores.product_knowledge_score ?? '—'}%</strong></div>
                  <div>CRM: <strong className="text-white">{subscores.customer_service_score ?? '—'}%</strong></div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-[#1b2542]">
              <p className="text-[11px] text-slate-400 leading-snug">
                Inference loaded from trained model artifact across candidate competency interactions.
              </p>
            </div>
          </div>

          {/* =========================================================================
             SECTION 3: TASK ELIGIBILITY & NEXT ACTION
             ========================================================================= */}
          <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-5 sm:p-6 shadow-xl flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-indigo-400">3. Task Eligibility</span>
                {task_eligibility && (
                  <span className={task_eligibility.can_apply ? 'text-emerald-400' : 'text-amber-400'}>
                    {task_eligibility.can_apply ? 'Ready to Apply' : 'Action Required'}
                  </span>
                )}
              </div>

              <div>
                <span className="text-xl sm:text-2xl font-bold font-sora text-white leading-tight block">
                  {task_eligibility?.state || (passed ? 'Prerequisites Pending' : 'Ineligible')}
                </span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  {task_title ? `Task: ${task_title}` : 'General Evaluation'}
                </span>
              </div>

              {task_eligibility ? (
                <div className="p-3 rounded-xl bg-[#080d1a]/80 border border-[#1b2542] space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">All Topics Passed:</span>
                    <span className={`font-bold ${
                      task_eligibility.all_topics_passed === 'Not Required'
                        ? 'text-slate-400'
                        : task_eligibility.all_topics_passed
                        ? 'text-emerald-400'
                        : 'text-amber-400'
                    }`}>
                      {task_eligibility.all_topics_passed === 'Not Required'
                        ? 'Not Required'
                        : task_eligibility.all_topics_passed
                        ? '✓ Yes'
                        : '✗ Outstanding'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Certification Met:</span>
                    <span className={`font-bold ${task_eligibility.prerequisites?.certification_met ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {task_eligibility.prerequisites?.certification_met ? '✓ Verified' : '✗ Required'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Experience Met:</span>
                    <span className={`font-bold ${task_eligibility.prerequisites?.experience_met ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {task_eligibility.prerequisites?.experience_met ? '✓ Verified' : 'Pending'}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-400 leading-relaxed">
                  Evaluated independently from exam score. Task-specific rules govern actual application submission.
                </p>
              )}
            </div>

            <div className="pt-2 border-t border-[#1b2542]">
              <span className="text-[11px] text-slate-400 block truncate" title={task_eligibility?.blocking_reason}>
                {task_eligibility?.blocking_reason || (task_eligibility?.can_apply ? 'All conditions satisfied.' : 'Check checklist.')}
              </span>
            </div>
          </div>
        </div>

        {/* =========================================================================
           TASK REQUIREMENTS & TOPIC CHECKLIST (IF TIED TO TASK)
           ========================================================================= */}
        {task_eligibility && task_eligibility.required_topics && task_eligibility.required_topics.length > 0 && (
          <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold font-sora text-white uppercase tracking-wider">
              Task Assessment Topics Progress ({task_title})
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {task_eligibility.required_topics.map(rt => (
                <div
                  key={rt.topic_id}
                  className={`p-4 rounded-xl border flex items-center justify-between gap-3 ${
                    rt.status === 'Passed' 
                      ? 'bg-emerald-950/20 border-emerald-500/40' 
                      : 'bg-[#080d1a]/80 border-[#1b2542]'
                  }`}
                >
                  <div>
                    <span className="text-xs font-bold text-white block">{rt.name || rt.topic_name}</span>
                    <span className="text-[11px] text-slate-400">
                      Passing Threshold: {rt.passing_threshold ?? rt.passing_score ?? 70}% &bull; 5 Questions
                    </span>
                  </div>

                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full border shrink-0 ${
                    rt.status === 'Passed'
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                      : rt.status === 'Failed'
                      ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                      : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                  }`}>
                    {rt.status === 'Passed' ? `✓ Passed (${rt.latest_score ?? rt.score ?? 0}%)` : rt.status === 'Failed' ? `✗ Failed (${rt.latest_score ?? rt.score ?? 0}%)` : 'Needed'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Application Status Alert */}
        {applicationSuccess && (
          <div className="p-4 rounded-2xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs sm:text-sm flex items-center gap-3 shadow-lg">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>{applicationSuccess}</span>
          </div>
        )}

        {applicationError && (
          <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs sm:text-sm flex items-center gap-3 shadow-lg">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{applicationError}</span>
          </div>
        )}

        {/* =========================================================================
           PRIMARY CALL-TO-ACTION CONTAINER
           ========================================================================= */}
        <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-6 shadow-xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">Recommended Next Step</span>
            <p className="text-sm font-semibold text-white mt-0.5">
              {task_eligibility?.next_topic_needed ? (
                <span>Complete the remaining required assessment: <strong className="text-indigo-300">{task_eligibility.next_topic_needed.name}</strong></span>
              ) : task_eligibility?.can_apply ? (
                'All task requirements verified. You are authorized to submit your application.'
              ) : !passed ? (
                'Retake the assessment after reviewing the scenario competency rules.'
              ) : (
                'Review your profile and explore matching task opportunities.'
              )}
            </p>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2.5 rounded-xl border border-[#1e2a4a] bg-[#151f38]/60 hover:bg-[#151f38] text-slate-300 hover:text-white font-semibold text-xs sm:text-sm transition-all cursor-pointer"
            >
              Dashboard
            </button>

            {/* If task needs another topic */}
            {task_eligibility?.next_topic_needed ? (
              <button
                type="button"
                onClick={() => navigate(`/agent/assessment/${task_id}?topicId=${task_eligibility.next_topic_needed.topic_id}`)}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs sm:text-sm shadow-lg shadow-indigo-600/25 transition-all flex items-center gap-2 cursor-pointer active:scale-98"
              >
                <span>Continue: {task_eligibility.next_topic_needed.name}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : task_eligibility?.can_apply ? (
              <button
                type="button"
                onClick={() => handleApply(task_id)}
                disabled={isApplying}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-lg shadow-emerald-600/30 transition-all flex items-center gap-2 cursor-pointer active:scale-98"
              >
                {isApplying ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Submitting Application...</span>
                  </>
                ) : (
                  <>
                    <Briefcase className="w-4 h-4" />
                    <span>Submit Application Now</span>
                  </>
                )}
              </button>
            ) : !passed ? (
              <button
                type="button"
                onClick={() => navigate(`/agent/assessment/${task_id || 'general'}?topicId=${topic_id}`)}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-bold text-xs sm:text-sm shadow-md shadow-amber-600/20 transition-all flex items-center gap-2 cursor-pointer active:scale-98"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Retake Assessment</span>
              </button>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
};
export default AssessmentResultsPage;
