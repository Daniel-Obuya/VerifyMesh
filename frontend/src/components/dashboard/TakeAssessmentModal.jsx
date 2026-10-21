import React, { useState, useEffect } from 'react';
import { 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  Briefcase, 
  Award, 
  ArrowRight,
  ArrowLeft,
  Clock, 
  ShieldCheck, 
  Check, 
  RotateCcw, 
  FileCheck2,
  ChevronRight,
  HelpCircle,
  Eye
} from 'lucide-react';
import { competencyService } from '../../services/competencyService';

export const TakeAssessmentModal = ({ 
  isOpen, 
  onClose, 
  onAssessmentComplete, 
  currentData,
  userId,
  examId = 3,
  taskId = null,
  taskTitle = null,
  onProceedToApply = null
}) => {
  // Authoritative Exam state
  const [examData, setExamData] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [attemptId, setAttemptId] = useState(null);
  const [attemptExpiresAt, setAttemptExpiresAt] = useState(null);
  const [isLoadingExam, setIsLoadingExam] = useState(false);
  const [agentProfile, setAgentProfile] = useState(null);

  // Stepper state: one question at a time (0 to 4)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isReviewMode, setIsReviewMode] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Load authoritative exam attempt and agent profile whenever modal is opened
  useEffect(() => {
    if (!isOpen) {
      setResult(null);
      setError(null);
      setAttemptId(null);
      setCurrentQuestionIndex(0);
      setIsReviewMode(false);
      return;
    }

    const loadExamAndProfile = async () => {
      setIsLoadingExam(true);
      setError(null);
      setCurrentQuestionIndex(0);
      setIsReviewMode(false);

      try {
        const activeExamId = examId || 3;
        
        // Initiate an authoritative attempt for this exam
        const [attemptRes, profileRes] = await Promise.allSettled([
          competencyService.startExamAttempt(activeExamId, taskId),
          competencyService.getProfile()
        ]);

        if (attemptRes.status === 'fulfilled' && attemptRes.value?.success) {
          const data = attemptRes.value.data;
          setExamData(data.exam);
          setAttemptId(data.attempt_id);
          setAttemptExpiresAt(data.expires_at);
          const qs = data.questions || [];
          setQuestions(qs);

          // Initialize answers map
          const initialAns = {};
          qs.forEach(q => {
            initialAns[String(q.question_id)] = null;
          });
          setSelectedAnswers(initialAns);
        } else {
          // Check for cooldown response (HTTP 429) or fallback to getExamQuestions
          const errResp = attemptRes.reason?.data || attemptRes.value;
          if (errResp?.error && (attemptRes.reason?.status === 429 || errResp.error.includes('cooldown'))) {
            setError(errResp.error);
          } else {
            // Fallback attempt to getExamQuestions
            try {
              const qRes = await competencyService.getExamQuestions(activeExamId);
              if (qRes?.success && qRes.data) {
                setExamData(qRes.data.exam);
                if (qRes.data.attempt_id) {
                  setAttemptId(qRes.data.attempt_id);
                  setAttemptExpiresAt(qRes.data.expires_at);
                }
                const qs = qRes.data.questions || [];
                setQuestions(qs);
                const initialAns = {};
                qs.forEach(q => {
                  initialAns[String(q.question_id)] = null;
                });
                setSelectedAnswers(initialAns);
              } else {
                setError(errResp?.error || 'Failed to load exam questions. Please try again.');
              }
            } catch (fallbackErr) {
              setError(fallbackErr?.data?.error || 'Failed to load exam questions. Please try again.');
            }
          }
        }

        if (profileRes.status === 'fulfilled' && profileRes.value?.success) {
          setAgentProfile(profileRes.value.profile || {});
        }
      } catch (err) {
        console.error('Error loading exam data:', err);
        setError('Error connecting to assessment server.');
      } finally {
        setIsLoadingExam(false);
      }
    };

    loadExamAndProfile();
  }, [isOpen, examId, taskId]);

  if (!isOpen) return null;

  const handleOptionSelect = (questionId, optionId) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [String(questionId)]: optionId
    }));
  };

  // Helper for topic label based on exam and question order
  const getTopicLabel = (questionOrder) => {
    const curExamId = examId || 3;
    if (curExamId === 3) {
      if (questionOrder === 1 || questionOrder === 2) {
        return { 
          topic: 'Diagnostic Troubleshooting', 
          desc: 'Systematic root-cause diagnosis & issue reproduction',
          badge: 'bg-blue-50 text-blue-700 border-blue-200' 
        };
      }
      if (questionOrder === 3 || questionOrder === 4) {
        return { 
          topic: 'Customer De-escalation & Communication', 
          desc: 'Active listening, empathy, and professional de-escalation',
          badge: 'bg-purple-50 text-purple-700 border-purple-200' 
        };
      }
      return { 
        topic: 'Ticket Priority & SLA Triage', 
        desc: 'Impact assessment and time-sensitive resolution routing',
        badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' 
      };
    }
    // Exam 1: Sales Competency
    if (questionOrder === 1) {
      return { 
        topic: 'Product Knowledge & Discovery', 
        desc: 'Consultative questioning and alignment with client operational needs',
        badge: 'bg-indigo-50 text-indigo-700 border-indigo-200' 
      };
    }
    if (questionOrder === 2) {
      return { 
        topic: 'Sales Techniques & Objection Handling', 
        desc: 'Value-oriented responses addressing automated verification benefits',
        badge: 'bg-blue-50 text-blue-700 border-blue-200' 
      };
    }
    if (questionOrder === 3) {
      return { 
        topic: 'Objection Handling & Implementation', 
        desc: 'Structured responses addressing rollout complexity and risk reduction',
        badge: 'bg-amber-50 text-amber-700 border-amber-200' 
      };
    }
    if (questionOrder === 4) {
      return { 
        topic: 'Product Knowledge & ROI Demonstration', 
        desc: 'Quantitative proof and measurable business impact for decision makers',
        badge: 'bg-purple-50 text-purple-700 border-purple-200' 
      };
    }
    return { 
      topic: 'Customer Relationship Management & Follow-up', 
      desc: 'Professional post-discovery follow-up, clarity, and account momentum',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' 
    };
  };

  const totalQuestions = questions.length;
  const answeredCount = Object.values(selectedAnswers).filter(val => val !== null && val !== undefined).length;
  const allAnswered = totalQuestions > 0 && answeredCount === totalQuestions;

  const currentQuestion = questions[currentQuestionIndex] || null;
  const currentQIdStr = currentQuestion ? String(currentQuestion.question_id) : '';
  const currentSelectedOpt = currentQIdStr ? selectedAnswers[currentQIdStr] : null;
  const currentTopic = currentQuestion ? getTopicLabel(currentQuestion.question_order) : null;

  // Navigation handlers
  const handleNext = () => {
    if (currentQuestionIndex < totalQuestions - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    } else {
      setIsReviewMode(true);
    }
  };

  const handlePrev = () => {
    if (isReviewMode) {
      setIsReviewMode(false);
    } else if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleJumpToQuestion = (idx) => {
    setCurrentQuestionIndex(idx);
    setIsReviewMode(false);
  };

  // Handle Submission for Exam
  const handleExamSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!allAnswered) {
      setError(`Please answer all ${totalQuestions} scenario questions before submitting.`);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const activeExamId = examId || 3;
      // Submit ONLY question IDs, selected option IDs, and authoritative attemptId
      const res = await competencyService.submitExam(activeExamId, selectedAnswers, taskId, attemptId);

      if (res?.success && res.data) {
        const d = res.data;
        const resultObj = {
          success: true,
          mode: 'exam',
          exam_id: d.exam_id,
          task_id: d.task_id,
          score: d.score,
          passed: d.passed,
          passing_score: d.passing_score,
          competency_level: d.competency_level,
          predicted_competency: d.competency_level,
          prediction: d.competency_level,
          evaluation_decision: d.evaluation_decision,
          confidence: d.confidence,
          probabilities: d.probabilities,
          subscores: d.subscores,
          feedback: d.feedback,
          features_used: d.features_used,
          level_tier: d.competency_level === 'Eligible' ? 1 : 0,
        };

        setResult(resultObj);
        if (onAssessmentComplete) {
          onAssessmentComplete(resultObj);
        }
      } else {
        setError(res?.error || 'Failed to grade and evaluate assessment.');
      }
    } catch (err) {
      const msg = err?.data?.message || err?.data?.error || err?.message || 'Server error during submission.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFinish = () => {
    setResult(null);
    onClose();
  };

  const OPTION_LETTERS = ['A', 'B', 'C', 'D'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[92vh] overflow-hidden transition-all"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="p-4 sm:px-6 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              taskId ? 'bg-[#EEF2FF] text-[#3B50BA]' : 'bg-slate-100 text-slate-700'
            }`}>
              {taskId ? <Briefcase className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                  {examData?.name || 'Scenario Assessment'}
                </h3>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-[#3B50BA] border border-blue-200">
                  {totalQuestions || 5} Questions • Pass Threshold: {examData?.passing_score ?? 70}%
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {taskTitle ? (
                  <span>
                    Qualifying for: <strong className="text-slate-800 font-semibold">{taskTitle}</strong>
                  </span>
                ) : (
                  'Task-Driven Scenario Assessment • Server-Graded Evaluation'
                )}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-4">
          {result ? (
            /* ==============================================================
               COMPREHENSIVE RESULTS BREAKDOWN VIEW (4 SEPARATE CONCEPTS)
               ============================================================== */
            <div className="text-center py-2 space-y-5 animate-in zoom-in-95 duration-200">
              <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center border shadow-xs ${
                result.passed ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-amber-50 text-amber-600 border-amber-200'
              }`}>
                {result.passed ? <CheckCircle2 className="w-8 h-8" /> : <AlertCircle className="w-8 h-8" />}
              </div>

              <div>
                <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${
                  result.passed ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-amber-700 bg-amber-50 border-amber-200'
                }`}>
                  {result.passed ? `Assessment Passed (Threshold: ${result.passing_score ?? 70}%)` : 'Passing Threshold Not Reached'}
                </span>
                <h4 className="text-2xl font-bold text-slate-900 mt-3">
                  Score: {result.score}% &bull; {result.predicted_competency || result.prediction}
                </h4>
                <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-md mx-auto">
                  {taskTitle ? (
                    <span>
                      Evaluated for task <strong className="text-slate-900 font-semibold">{taskTitle}</strong>.
                    </span>
                  ) : (
                    'Evaluated using Random Forest model on verified experience and situational answers.'
                  )}
                </p>
              </div>

              {/* 4 Distinct Concept Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-left">
                {/* Concept 1: Assessment Result */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
                      <span>1. Topic Assessment Result</span>
                      <span className={result.passed ? 'text-emerald-600 font-bold' : 'text-amber-600 font-bold'}>
                        {result.passed ? 'PASSED' : 'NOT PASSED'}
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-slate-900">{result.score}%</span>
                      <span className="text-xs text-slate-400">vs {result.passing_score ?? 70}% required</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-200/60">
                    Graded server-side across all 5 scenario questions.
                  </p>
                </div>

                {/* Concept 2: ML Competency Prediction */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
                      <span>2. ML Competency Level</span>
                      <span className="text-[#3B50BA] font-bold">Random Forest</span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-slate-900">{result.predicted_competency || 'Eligible'}</span>
                      <span className="text-xs text-slate-400">{result.confidence}% confidence</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-200/60">
                    Evaluated from verified profile history and situational answers.
                  </p>
                </div>

                {/* Concept 3: Task Eligibility */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
                      <span>3. Task Eligibility</span>
                      <span className={result.evaluation_decision === 'Eligible' ? 'text-emerald-600 font-bold' : 'text-amber-600 font-bold'}>
                        {result.evaluation_decision || 'Eligible'}
                      </span>
                    </div>
                    <p className="text-sm font-bold text-slate-900 mt-2">
                      {result.passed ? 'Assessment Prerequisite Met' : 'Requires Assessment Retake'}
                    </p>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-200/60">
                    {result.passed 
                      ? 'Task assessment is valid and recorded in your permanent audit record.'
                      : 'Review the required competency topics and try again when ready.'}
                  </p>
                </div>

                {/* Concept 4: Application Readiness */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
                      <span>4. Application Status</span>
                      <span className="text-slate-600 font-bold">Ready</span>
                    </div>
                    <p className="text-sm font-bold text-slate-900 mt-2">
                      {taskId ? (result.passed ? 'Ready to Apply' : 'Prerequisites Pending') : 'Profile Verified'}
                    </p>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-200/60">
                    {taskId 
                      ? (result.passed ? 'Proceed to review task deliverables and submit your application.' : 'Fulfill missing requirements before applying.')
                      : 'Explore matching task opportunities from your agent dashboard.'}
                  </p>
                </div>
              </div>

              {/* Question Feedback Breakdown */}
              {result.feedback && result.feedback.length > 0 && (
                <div className="p-4 rounded-xl bg-white border border-slate-200 text-left space-y-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wide block">
                    Scenario Questions Breakdown (Server Graded)
                  </span>
                  <div className="grid grid-cols-5 gap-2 pt-1">
                    {result.feedback.map((fb, idx) => (
                      <div 
                        key={idx} 
                        className={`p-2.5 rounded-lg border text-center ${
                          fb.is_correct ? 'bg-emerald-50/80 border-emerald-200 text-emerald-800' : 'bg-rose-50/80 border-rose-200 text-rose-800'
                        }`}
                      >
                        <span className="text-[11px] font-bold block">Q{fb.question_order}</span>
                        <span className="text-xs font-semibold">{fb.points_earned}/{fb.max_points} pts</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={handleFinish}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm transition-colors cursor-pointer"
                >
                  Return to Dashboard
                </button>
                {taskId && result.passed && (
                  <button
                    type="button"
                    onClick={() => {
                      handleFinish();
                      if (onProceedToApply) onProceedToApply(taskId);
                    }}
                    className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-sm shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <span>Proceed to Task Application</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* ==============================================================
               STEP-BY-STEP QUESTION VIEW (ONE QUESTION AT A TIME)
               ============================================================== */
            <div className="space-y-4">
              {/* Candidate Info Strip */}
              {agentProfile && (
                <div className="p-2.5 px-3.5 bg-slate-50 border border-slate-200/90 rounded-xl flex items-center justify-between text-xs text-slate-600">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>
                      Candidate: <strong className="text-slate-900">{agentProfile.full_name || 'Agent'}</strong> &bull; Verified Exp:{' '}
                      <strong className="text-slate-900">{agentProfile.verified_metrics?.total_experience_months || 0} mo</strong>
                    </span>
                  </div>
                  <span className="text-[11px] font-semibold text-[#3B50BA] bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">
                    {agentProfile.verified_metrics?.active_certifications_count || 0} Verified Cert(s)
                  </span>
                </div>
              )}

              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {isLoadingExam ? (
                <div className="py-16 text-center space-y-3">
                  <div className="w-8 h-8 mx-auto border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm text-slate-500 font-medium">Loading authoritative assessment questions...</p>
                </div>
              ) : questions.length > 0 ? (
                <div>
                  {/* Progress Header & Stepper */}
                  <div className="space-y-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-700">
                        {isReviewMode ? 'Review & Submit' : `Question ${currentQuestionIndex + 1} of ${totalQuestions}`}
                      </span>
                      <span className={`font-semibold ${allAnswered ? 'text-emerald-600' : 'text-[#3B50BA]'}`}>
                        {answeredCount} of {totalQuestions} answered {allAnswered && '✓'}
                      </span>
                    </div>

                    {/* Animated Progress Bar */}
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div 
                        className="bg-[#3B50BA] h-full rounded-full transition-all duration-300"
                        style={{ width: `${((currentQuestionIndex + 1) / totalQuestions) * 100}%` }}
                      />
                    </div>

                    {/* Stepper Pills */}
                    <div className="flex items-center justify-between pt-1 gap-1.5">
                      {questions.map((q, idx) => {
                        const isAns = selectedAnswers[String(q.question_id)] !== null && selectedAnswers[String(q.question_id)] !== undefined;
                        const isCur = !isReviewMode && currentQuestionIndex === idx;

                        return (
                          <button
                            key={q.question_id}
                            type="button"
                            onClick={() => handleJumpToQuestion(idx)}
                            className={`flex-1 py-1 px-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-all cursor-pointer ${
                              isCur
                                ? 'bg-[#3B50BA] text-white shadow-xs'
                                : isAns
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                                : 'bg-slate-50 text-slate-500 border border-slate-200 hover:bg-slate-100'
                            }`}
                            title={`Jump to Question ${idx + 1}`}
                          >
                            <span>Q{idx + 1}</span>
                            {isAns && !isCur && <Check className="w-3 h-3 stroke-[2.5]" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {isReviewMode ? (
                    /* ==============================================================
                       REVIEW & SUBMISSION CONFIRMATION VIEW
                       ============================================================== */
                    <div className="py-2 space-y-4 animate-in fade-in duration-200">
                      <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-900 flex items-start gap-2.5">
                        <FileCheck2 className="w-4 h-4 text-[#3B50BA] shrink-0 mt-0.5" />
                        <div>
                          <strong className="block font-semibold">Review your responses before submitting:</strong>
                          <span>Each scenario is scored server-side. Click any question below to modify your response.</span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {questions.map((q, idx) => {
                          const qIdStr = String(q.question_id);
                          const chosenOptId = selectedAnswers[qIdStr];
                          const topicInfo = getTopicLabel(q.question_order);

                          // Find chosen option text
                          let chosenText = 'No option selected';
                          if (q.options) {
                            const matchOpt = q.options.find((opt, oIdx) => {
                              const oId = typeof opt === 'object' && opt.option_id ? opt.option_id : OPTION_LETTERS[oIdx];
                              return oId === chosenOptId;
                            });
                            if (matchOpt) {
                              chosenText = typeof matchOpt === 'object' && matchOpt.text ? matchOpt.text : String(matchOpt);
                            }
                          }

                          return (
                            <div 
                              key={q.question_id}
                              className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors flex items-start justify-between gap-3"
                            >
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-bold text-slate-900">Question {idx + 1}</span>
                                  <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full border ${topicInfo.badge}`}>
                                    {topicInfo.topic}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-600 line-clamp-1">{q.question_text}</p>
                                <div className="flex items-center gap-1.5 pt-0.5 text-xs text-slate-800">
                                  <span className="font-bold text-[#3B50BA] bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200 text-[11px]">
                                    Option {chosenOptId || '—'}
                                  </span>
                                  <span className="text-slate-600 text-[11px] truncate max-w-sm">{chosenText}</span>
                                </div>
                              </div>

                              <button
                                type="button"
                                onClick={() => handleJumpToQuestion(idx)}
                                className="px-2.5 py-1 text-xs font-semibold text-[#3B50BA] hover:bg-blue-50 rounded-lg transition-colors cursor-pointer shrink-0"
                              >
                                Edit
                              </button>
                            </div>
                          );
                        })}
                      </div>

                      <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                        <button
                          type="button"
                          onClick={() => setIsReviewMode(false)}
                          className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition-colors flex items-center gap-1.5 cursor-pointer"
                        >
                          <ArrowLeft className="w-4 h-4" />
                          <span>Back to Questions</span>
                        </button>

                        <button
                          type="button"
                          onClick={handleExamSubmit}
                          disabled={isLoading || !allAnswered}
                          className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:opacity-50 text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
                        >
                          {isLoading ? (
                            <>
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                              <span>Scoring &amp; Evaluating...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-4 h-4" />
                              <span>Submit Assessment</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* ==============================================================
                       ONE QUESTION AT A TIME VIEW
                       ============================================================== */
                    currentQuestion && (
                      <div className="py-2 space-y-4 animate-in fade-in duration-200">
                        {/* Topic Banner */}
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${currentTopic.badge}`}>
                              {currentTopic.topic}
                            </span>
                          </div>
                          <span className="text-xs text-slate-400 font-medium">
                            {currentTopic.desc}
                          </span>
                        </div>

                        {/* Question Text */}
                        <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/90">
                          <p className="text-sm sm:text-base font-semibold text-slate-900 leading-relaxed">
                            {currentQuestion.question_text}
                          </p>
                        </div>

                        {/* Answer Options */}
                        <div className="space-y-2.5 pt-1">
                          {currentQuestion.options && currentQuestion.options.map((opt, oIdx) => {
                            const optId = typeof opt === 'object' && opt.option_id ? opt.option_id : OPTION_LETTERS[oIdx];
                            const optText = typeof opt === 'object' && opt.text ? opt.text : (typeof opt === 'string' ? opt : String(opt));
                            const isSelected = currentSelectedOpt === optId;

                            return (
                              <label
                                key={optId || oIdx}
                                onClick={() => handleOptionSelect(currentQuestion.question_id, optId)}
                                className={`flex items-start gap-3 p-3.5 rounded-xl border text-xs sm:text-sm cursor-pointer transition-all ${
                                  isSelected
                                    ? 'bg-blue-50/90 border-[#3B50BA] text-slate-900 font-medium shadow-xs'
                                    : 'bg-white border-slate-200/90 text-slate-700 hover:bg-slate-50 hover:border-slate-300'
                                }`}
                              >
                                <div className={`w-6 h-6 rounded-full border flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 transition-colors ${
                                  isSelected 
                                    ? 'bg-[#3B50BA] text-white border-[#3B50BA]' 
                                    : 'bg-white text-slate-500 border-slate-300'
                                }`}>
                                  {optId}
                                </div>
                                <span className="leading-relaxed flex-1 pt-0.5">
                                  {optText}
                                </span>
                              </label>
                            );
                          })}
                        </div>

                        {/* Navigation Footer */}
                        <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
                          <button
                            type="button"
                            onClick={handlePrev}
                            disabled={currentQuestionIndex === 0}
                            className={`px-4 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-colors flex items-center gap-1.5 ${
                              currentQuestionIndex === 0
                                ? 'text-slate-300 cursor-not-allowed'
                                : 'text-slate-600 hover:text-slate-800 hover:bg-slate-100 cursor-pointer'
                            }`}
                          >
                            <ArrowLeft className="w-4 h-4" />
                            <span>Previous</span>
                          </button>

                          <div className="flex items-center gap-2">
                            {answeredCount > 0 && (
                              <button
                                type="button"
                                onClick={() => setIsReviewMode(true)}
                                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer hidden sm:flex items-center gap-1"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Review All</span>
                              </button>
                            )}

                            {currentQuestionIndex < totalQuestions - 1 ? (
                              <button
                                type="button"
                                onClick={handleNext}
                                disabled={currentSelectedOpt === null || currentSelectedOpt === undefined}
                                className={`px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
                                  currentSelectedOpt !== null && currentSelectedOpt !== undefined
                                    ? 'bg-[#3B50BA] hover:bg-[#31429e] text-white'
                                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                                }`}
                              >
                                <span>Next Question</span>
                                <ArrowRight className="w-4 h-4" />
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setIsReviewMode(true)}
                                disabled={!allAnswered}
                                className={`px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
                                  allAnswered
                                    ? 'bg-[#3B50BA] hover:bg-[#31429e] text-white'
                                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                                }`}
                              >
                                <span>Review &amp; Submit</span>
                                <ArrowRight className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500">
                  No questions found for this assessment topic.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
