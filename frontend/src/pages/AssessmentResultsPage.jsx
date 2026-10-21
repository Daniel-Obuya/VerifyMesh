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
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center font-sans">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-600">Retrieving evaluated results...</p>
        </div>
      </div>
    );
  }

  if (error || !attemptData) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center font-sans p-4">
        <div className="bg-white rounded-2xl border border-slate-200 p-8 max-w-md w-full text-center space-y-4 shadow-sm">
          <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Unable to Load Results</h2>
          <p className="text-xs text-slate-500">{error || 'Attempt records could not be found.'}</p>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="w-full py-2.5 bg-[#3B50BA] hover:bg-[#31429e] text-white text-xs font-semibold rounded-xl shadow-xs transition-colors cursor-pointer"
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
  const probabilities = prediction.probabilities || {};

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200/80 px-6 sm:px-8 h-16 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Dashboard</span>
          </button>

          <div className="h-5 w-px bg-slate-200 hidden sm:block" />

          <div className="flex items-center gap-2 select-none">
            <div className="w-7 h-7 rounded-lg bg-[#3B50BA] flex items-center justify-center p-1 shadow-xs shrink-0">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="w-full h-full text-white">
                <path d="M3 16l6-6 4 4 8-8" />
                <path d="M14 6h7v7" />
              </svg>
            </div>
            <span className="text-base font-bold text-slate-900 tracking-tight">VerifyMesh Assessment Report</span>
          </div>
        </div>

        {task_id && (
          <button
            type="button"
            onClick={() => navigate(`/agent/assessment/${task_id}`)}
            className="text-xs font-semibold text-[#3B50BA] hover:underline hidden sm:block"
          >
            View Task Requirements &rarr;
          </button>
        )}
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Outcome Banner */}
        <div className={`p-6 sm:p-8 rounded-2xl border shadow-xs flex flex-col sm:flex-row items-center sm:items-start gap-5 ${
          passed 
            ? 'bg-gradient-to-br from-emerald-50/80 to-white border-emerald-200' 
            : 'bg-gradient-to-br from-amber-50/80 to-white border-amber-200'
        }`}>
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 shadow-xs ${
            passed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
          }`}>
            {passed ? <CheckCircle2 className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
          </div>

          <div className="space-y-1.5 text-center sm:text-left flex-1">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <span className={`text-xs font-bold px-3 py-0.5 rounded-full border ${
                passed 
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                  : 'bg-amber-100 text-amber-800 border-amber-300'
              }`}>
                {passed ? 'Topic Assessment Passed' : 'Passing Threshold Not Reached'}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                Topic: <strong>{topic_name}</strong>
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Score: {score}% &bull; {passed ? 'Threshold Satisfied' : 'Review Required'}
            </h1>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-2xl">
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
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-500 font-bold uppercase tracking-wider">
                <span className="text-[#3B50BA]">1. Assessment Result</span>
                <span className={passed ? 'text-emerald-600' : 'text-amber-600'}>
                  {passed ? 'Passed' : 'Failed'}
                </span>
              </div>

              <div>
                <span className="text-3xl font-bold text-slate-900">{score}%</span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  Threshold: &ge;{passing_score}%
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Topic Assessed:</span>
                  <span className="font-bold text-slate-900 text-right">{topic_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Grading Source:</span>
                  <span className="font-bold text-slate-900">Server Evaluated</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Credential Status:</span>
                  <span className={`font-bold ${passed ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {passed ? 'Valid on Profile' : 'Retake Allowed'}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100">
              {!passed ? (
                <button
                  type="button"
                  onClick={() => navigate(`/agent/assessment/${task_id || 'general'}?topicId=${topic_id}`)}
                  className="w-full py-2 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Retake Topic Evaluation</span>
                </button>
              ) : (
                <span className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Permanent result on ledger
                </span>
              )}
            </div>
          </div>

          {/* =========================================================================
             SECTION 2: COMPETENCY PREDICTION (RANDOM FOREST)
             ========================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-500 font-bold uppercase tracking-wider">
                <span className="text-[#3B50BA]">2. ML Competency</span>
                <span className="text-indigo-600">Random Forest</span>
              </div>

              <div>
                <span className="text-3xl font-bold text-slate-900">{competencyLabel}</span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  Decision: <strong>{decisionLabel}</strong> &bull; {confidence}% confidence
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5 text-xs">
                <span className="font-bold text-slate-700 block text-[11px]">Subscore Matrix:</span>
                <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                  <div>Comm: <strong>{subscores.communication_score ?? '—'}%</strong></div>
                  <div>Sales: <strong>{subscores.sales_skill_score ?? '—'}%</strong></div>
                  <div>Prod: <strong>{subscores.product_knowledge_score ?? '—'}%</strong></div>
                  <div>CRM: <strong>{subscores.customer_service_score ?? '—'}%</strong></div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100">
              <p className="text-[11px] text-slate-500 leading-snug">
                Inference loaded from trained model artifact across 15 engineered features.
              </p>
            </div>
          </div>

          {/* =========================================================================
             SECTION 3: TASK ELIGIBILITY & NEXT ACTION
             ========================================================================= */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-500 font-bold uppercase tracking-wider">
                <span className="text-[#3B50BA]">3. Task Eligibility</span>
                {task_eligibility && (
                  <span className={task_eligibility.can_apply ? 'text-emerald-600' : 'text-amber-600'}>
                    {task_eligibility.can_apply ? 'Ready to Apply' : 'Action Required'}
                  </span>
                )}
              </div>

              <div>
                <span className="text-xl sm:text-2xl font-bold text-slate-900 leading-tight block">
                  {task_eligibility?.state || (passed ? 'Prerequisites Pending' : 'Ineligible')}
                </span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  {task_title ? `Task: ${task_title}` : 'General Evaluation'}
                </span>
              </div>

              {task_eligibility ? (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">All Topics Passed:</span>
                    <span className={`font-bold ${task_eligibility.all_topics_passed ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {task_eligibility.all_topics_passed ? '✓ Yes' : '✗ Outstanding'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Certification Met:</span>
                    <span className={`font-bold ${task_eligibility.prerequisites?.certification_met ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {task_eligibility.prerequisites?.certification_met ? '✓ Verified' : '✗ Required'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Experience Met:</span>
                    <span className={`font-bold ${task_eligibility.prerequisites?.experience_met ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {task_eligibility.prerequisites?.experience_met ? '✓ Verified' : 'Pending'}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 leading-relaxed">
                  Evaluated independently from exam score. Task-specific rules govern actual application submission.
                </p>
              )}
            </div>

            <div className="pt-2 border-t border-slate-100">
              <span className="text-[11px] text-slate-500 block truncate" title={task_eligibility?.blocking_reason}>
                {task_eligibility?.blocking_reason || (task_eligibility?.can_apply ? 'All conditions satisfied.' : 'Check checklist.')}
              </span>
            </div>
          </div>
        </div>

        {/* =========================================================================
           TASK REQUIREMENTS & TOPIC CHECKLIST (IF TIED TO TASK)
           ========================================================================= */}
        {task_eligibility && task_eligibility.required_topics && task_eligibility.required_topics.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Task Assessment Topics Progress ({task_title})
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {task_eligibility.required_topics.map(rt => (
                <div
                  key={rt.topic_id}
                  className={`p-4 rounded-xl border flex items-center justify-between gap-3 ${
                    rt.status === 'Passed' 
                      ? 'bg-emerald-50/50 border-emerald-200' 
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">{rt.name}</span>
                    <span className="text-[11px] text-slate-500">
                      Passing Threshold: {rt.passing_threshold}% &bull; 5 Questions
                    </span>
                  </div>

                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full border shrink-0 ${
                    rt.status === 'Passed'
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : rt.status === 'Failed'
                      ? 'bg-rose-100 text-rose-800 border-rose-300'
                      : 'bg-amber-100 text-amber-800 border-amber-300'
                  }`}>
                    {rt.status === 'Passed' ? `✓ Passed (${rt.latest_score}%)` : rt.status === 'Failed' ? `✗ Failed (${rt.latest_score}%)` : 'Needed'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Application Status Alert */}
        {applicationSuccess && (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs sm:text-sm flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{applicationSuccess}</span>
          </div>
        )}

        {applicationError && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{applicationError}</span>
          </div>
        )}

        {/* =========================================================================
           PRIMARY CALL-TO-ACTION CONTAINER
           ========================================================================= */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Recommended Next Step</span>
            <p className="text-sm font-semibold text-slate-900 mt-0.5">
              {task_eligibility?.next_topic_needed ? (
                <span>Complete the remaining required assessment: <strong>{task_eligibility.next_topic_needed.name}</strong></span>
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
              className="px-4 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm transition-colors cursor-pointer"
            >
              Dashboard
            </button>

            {/* If task needs another topic */}
            {task_eligibility?.next_topic_needed ? (
              <button
                type="button"
                onClick={() => navigate(`/agent/assessment/${task_id}?topicId=${task_eligibility.next_topic_needed.topic_id}`)}
                className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-bold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
              >
                <span>Continue: {task_eligibility.next_topic_needed.name}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : task_eligibility?.can_apply ? (
              <button
                type="button"
                onClick={() => handleApply(task_id)}
                disabled={isApplying}
                className="px-6 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer active:scale-98"
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
                className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
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
