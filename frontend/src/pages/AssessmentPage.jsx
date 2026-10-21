import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
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
  FileCheck2, 
  Eye, 
  HelpCircle,
  ChevronRight,
  AlertTriangle
} from 'lucide-react';
import { competencyService } from '../services/competencyService';
import { useAuth } from '../context/AuthContext';

export const AssessmentPage = () => {
  const { taskId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTopicId = searchParams.get('topicId');
  const navigate = useNavigate();
  const { user } = useAuth();

  // Page state
  const [task, setTask] = useState(null);
  const [isLoadingTask, setIsLoadingTask] = useState(true);
  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);

  // Assessment flow states
  const [isInProgress, setIsInProgress] = useState(false);
  const [isReviewMode, setIsReviewMode] = useState(false);
  const [attemptId, setAttemptId] = useState(null);
  const [attemptExpiresAt, setAttemptExpiresAt] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Loading and error states
  const [isStartingAttempt, setIsStartingAttempt] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // 1. Fetch Task Details and Required Topics
  useEffect(() => {
    let isMounted = true;

    const loadTaskAndTopics = async () => {
      setIsLoadingTask(true);
      setErrorMessage(null);

      try {
        let loadedTask = null;
        let availableTopics = [];

        // Check if taskId is valid number or 'general'
        const isNumericTask = taskId && !isNaN(Number(taskId));

        if (isNumericTask) {
          const taskRes = await competencyService.getTaskDetails(Number(taskId));
          if (taskRes?.success && taskRes.data) {
            loadedTask = taskRes.data;
          }
        }

        // Fetch all active topics from backend
        const topicsRes = await competencyService.getTopics();
        if (topicsRes?.success && Array.isArray(topicsRes.data)) {
          availableTopics = topicsRes.data;
        }

        if (!isMounted) return;

        setTask(loadedTask);
        setTopics(availableTopics);

        // Determine which topic to present:
        // Priority:
        // 1. requestedTopicId from query params
        // 2. First unpassed topic required by task
        // 3. First required topic
        // 4. First available topic in system
        let activeTopic = null;
        if (requestedTopicId) {
          activeTopic = availableTopics.find(t => t.topic_id === Number(requestedTopicId));
        }

        if (!activeTopic && loadedTask && Array.isArray(loadedTask.required_topics) && loadedTask.required_topics.length > 0) {
          // Find first unpassed topic
          const needed = loadedTask.required_topics.find(rt => rt.status !== 'Passed');
          const targetReq = needed || loadedTask.required_topics[0];
          activeTopic = availableTopics.find(t => t.topic_id === targetReq.topic_id) || targetReq;
        }

        if (!activeTopic && availableTopics.length > 0) {
          activeTopic = availableTopics[0];
        }

        setSelectedTopic(activeTopic);
      } catch (err) {
        console.error('Error loading task or topics:', err);
        if (isMounted) {
          setErrorMessage('Unable to load assessment requirements. Please check your connection.');
        }
      } finally {
        if (isMounted) setIsLoadingTask(false);
      }
    };

    loadTaskAndTopics();

    return () => {
      isMounted = false;
    };
  }, [taskId, requestedTopicId]);

  // 2. Handle Starting Assessment Attempt
  const handleStartAssessment = async () => {
    if (!selectedTopic) return;

    setIsStartingAttempt(true);
    setErrorMessage(null);

    try {
      const numericTaskId = task?.task_id || (taskId && !isNaN(Number(taskId)) ? Number(taskId) : null);
      
      // Authoritative attempt creation on server
      const attemptRes = await competencyService.startTopicAttempt(selectedTopic.topic_id, numericTaskId);
      
      if (!attemptRes?.success || !attemptRes.data) {
        throw new Error(attemptRes?.error || 'Failed to initialize assessment attempt.');
      }

      const { attempt_id, expires_at } = attemptRes.data;
      setAttemptId(attempt_id);
      setAttemptExpiresAt(expires_at);

      // Load server-gradeable questions (omits correct_answer)
      const qRes = await competencyService.getTopicQuestions(selectedTopic.topic_id);
      if (!qRes?.success || !Array.isArray(qRes.data) || qRes.data.length === 0) {
        throw new Error(qRes?.error || 'No questions configured for this topic.');
      }

      const loadedQuestions = qRes.data;
      setQuestions(loadedQuestions);

      // Initialize answers map
      const initialAnswers = {};
      loadedQuestions.forEach(q => {
        initialAnswers[String(q.question_id)] = null;
      });
      setSelectedAnswers(initialAnswers);

      setCurrentQuestionIndex(0);
      setIsReviewMode(false);
      setIsInProgress(true);
    } catch (err) {
      console.error('Error starting assessment:', err);
      setErrorMessage(err?.data?.error || err?.message || 'Failed to start assessment.');
    } finally {
      setIsStartingAttempt(false);
    }
  };

  // 3. Option Selection
  const handleSelectOption = (questionId, optionId) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [String(questionId)]: optionId
    }));
  };

  // 4. Stepper Navigation
  const totalQuestions = questions.length;
  const answeredCount = Object.values(selectedAnswers).filter(v => v !== null && v !== undefined).length;
  const allAnswered = totalQuestions > 0 && answeredCount === totalQuestions;

  const currentQuestion = questions[currentQuestionIndex] || null;
  const currentQIdStr = currentQuestion ? String(currentQuestion.question_id) : '';
  const currentSelectedOpt = currentQIdStr ? selectedAnswers[currentQIdStr] : null;

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

  // 5. Final Submission (Server-side grading & ML evaluation)
  const handleSubmitAssessment = async () => {
    if (!allAnswered) {
      setErrorMessage(`Please answer all ${totalQuestions} scenario questions before submitting.`);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const numericTaskId = task?.task_id || (taskId && !isNaN(Number(taskId)) ? Number(taskId) : null);
      
      const submitRes = await competencyService.submitTopicExam(
        selectedTopic.topic_id,
        selectedAnswers,
        numericTaskId,
        attemptId
      );

      if (submitRes?.success && submitRes.data) {
        const resultingAttemptId = submitRes.data.attempt_id || attemptId;
        // Navigate to dedicated assessment results page
        navigate(`/agent/assessment/results/${resultingAttemptId}`);
      } else {
        throw new Error(submitRes?.error || 'Server-side grading failed.');
      }
    } catch (err) {
      console.error('Submission error:', err);
      setErrorMessage(err?.data?.error || err?.message || 'Error submitting assessment. Progress was preserved.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const OPTION_LETTERS = ['A', 'B', 'C', 'D'];

  if (isLoadingTask) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center font-sans">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-3 border-[#3B50BA] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-600">Loading qualification requirements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col">
      {/* Top Professional Header */}
      <header className="bg-white border-b border-slate-200/80 px-6 sm:px-8 h-16 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => {
              if (isInProgress) {
                if (window.confirm('Are you sure you want to exit? Your selected answers are preserved on this page, but exiting will return you to your dashboard.')) {
                  navigate('/dashboard');
                }
              } else {
                navigate('/dashboard');
              }
            }}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Back to Dashboard</span>
          </button>

          <div className="h-5 w-px bg-slate-200 hidden sm:block" />

          <div className="flex items-center gap-2 select-none">
            <div className="w-7 h-7 rounded-lg bg-[#3B50BA] flex items-center justify-center p-1 shadow-xs shrink-0">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="w-full h-full text-white">
                <path d="M3 16l6-6 4 4 8-8" />
                <path d="M14 6h7v7" />
              </svg>
            </div>
            <span className="text-base font-bold text-slate-900 tracking-tight">VerifyMesh Assessment</span>
          </div>
        </div>

        {/* Candidate & Assessment Status Pill */}
        <div className="flex items-center gap-3">
          <div className="text-right hidden md:block">
            <span className="text-xs font-bold text-slate-900 block">{user?.fullName || user?.username || 'Agent'}</span>
            <span className="text-[11px] text-slate-400">Authenticated Candidate</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#E0E7FF] text-[#3B50BA] font-bold text-xs flex items-center justify-center">
            {user?.fullName ? user.fullName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'AG'}
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Error Alert */}
        {errorMessage && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-xs sm:text-sm text-rose-800 animate-in fade-in duration-200">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <span className="flex-1">{errorMessage}</span>
          </div>
        )}

        {/* =========================================================================
           STAGE B: INTRODUCTION & REQUIREMENTS OVERVIEW SCREEN
           ========================================================================= */}
        {!isInProgress ? (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Task Context Card */}
            {task && (
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <span className="text-xs font-bold text-[#3B50BA] tracking-wider uppercase">
                      Qualifying For Task
                    </span>
                    <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-0.5">
                      {task.title}
                    </h1>
                    {task.category && (
                      <span className="text-xs text-slate-500 font-medium">{task.category} &bull; {task.work_arrangement || 'Remote'}</span>
                    )}
                  </div>
                  <div className="sm:text-right">
                    <span className="text-xs font-semibold text-slate-500 block">Compensation</span>
                    <span className="text-base font-bold text-slate-900">{task.payout || '$30 - $40 / hr'}</span>
                  </div>
                </div>

                {/* Required Topics Progress Bar & Pills */}
                {task.required_topics && task.required_topics.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-700">Required Qualification Topics</span>
                      <span className="font-semibold text-slate-500">
                        {task.topics_passed_count || 0} of {task.topics_total || task.required_topics.length} Passed
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {task.required_topics.map(rt => {
                        const isCurrentSelected = selectedTopic?.topic_id === rt.topic_id;
                        const isPassed = rt.status === 'Passed';
                        const isFailed = rt.status === 'Failed';

                        return (
                          <div
                            key={rt.topic_id}
                            onClick={() => {
                              const found = topics.find(t => t.topic_id === rt.topic_id);
                              if (found) setSelectedTopic(found);
                            }}
                            className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                              isCurrentSelected 
                                ? 'bg-blue-50/70 border-[#3B50BA] shadow-xs' 
                                : 'bg-white border-slate-200/80 hover:border-slate-300'
                            }`}
                          >
                            <div className="space-y-0.5">
                              <span className="text-xs font-bold text-slate-900 block">
                                {rt.name}
                              </span>
                              <span className="text-[11px] text-slate-500">
                                5 Scenario Questions &bull; Pass Threshold: {rt.passing_threshold}%
                              </span>
                            </div>

                            <span className={`px-2.5 py-1 rounded-full text-xs font-bold shrink-0 border ${
                              isPassed
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : isFailed
                                ? 'bg-rose-50 text-rose-700 border-rose-200'
                                : 'bg-amber-50 text-amber-700 border-amber-200'
                            }`}>
                              {isPassed 
                                ? `✓ Passed (${rt.latest_score}%)` 
                                : isFailed 
                                ? `✗ Failed (${rt.latest_score}%)` 
                                : 'Needed'}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Assessment Details & Instructions Card */}
            {selectedTopic && (
              <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-blue-50 text-[#3B50BA] flex items-center justify-center shrink-0 shadow-xs">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#3B50BA]">
                        Competency Evaluation
                      </span>
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                        Topic {selectedTopic.topic_id}
                      </span>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900">
                      {selectedTopic.topic_name}
                    </h2>
                    <p className="text-sm text-slate-600 leading-relaxed pt-1">
                      {selectedTopic.description || 'Demonstrate professional situational judgment and problem-solving techniques for this competency topic.'}
                    </p>
                  </div>
                </div>

                {/* Specification Badges */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Questions</span>
                    <span className="text-sm font-bold text-slate-900 mt-0.5 block">5 Scenarios</span>
                  </div>
                  <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Estimated Time</span>
                    <span className="text-sm font-bold text-slate-900 mt-0.5 block">8 - 12 Minutes</span>
                  </div>
                  <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Passing Score</span>
                    <span className="text-sm font-bold text-slate-900 mt-0.5 block">
                      &ge; {selectedTopic.passing_score ?? 70}%
                    </span>
                  </div>
                  <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Result Reuse</span>
                    <span className="text-sm font-bold text-emerald-700 mt-0.5 block">Permanent / Valid</span>
                  </div>
                </div>

                {/* Important Rules Checklist */}
                <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100 space-y-2 text-xs sm:text-sm text-slate-700">
                  <h3 className="font-bold text-slate-900 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#3B50BA]" />
                    <span>Assessment Protocol &amp; Guidelines</span>
                  </h3>
                  <ul className="space-y-1.5 list-disc list-inside text-slate-600 text-xs leading-relaxed">
                    <li>One question presented at a time with full freedom to navigate forward and backward.</li>
                    <li>Answers are safely preserved during navigation and verified on a final review screen.</li>
                    <li>Submissions are graded authoritatively on the server; correct answers are never revealed in transit.</li>
                    <li>Passing results are permanently credited to your agent record and satisfy requirements on any task needing this topic.</li>
                    <li>If the score falls below the passing threshold, a retake is permitted after reviewing the outcome.</li>
                  </ul>
                </div>

                {/* Action CTA */}
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-100">
                  <span className="text-xs text-slate-500">
                    Ready to begin? Click below to launch the dedicated evaluation workspace.
                  </span>

                  <button
                    type="button"
                    onClick={handleStartAssessment}
                    disabled={isStartingAttempt}
                    className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:opacity-50 text-white font-bold text-sm shadow-xs hover:shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-98"
                  >
                    {isStartingAttempt ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Initializing Attempt...</span>
                      </>
                    ) : (
                      <>
                        <span>Start Assessment</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* =========================================================================
             STAGE C: DISTRACTION-FREE ASSESSMENT TAKING WORKSPACE
             ========================================================================= */
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* Workspace Header Bar */}
            <div className="bg-white rounded-2xl border border-slate-200/80 p-4 sm:p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <span className="text-xs font-bold text-[#3B50BA] uppercase tracking-wider block">
                    {selectedTopic?.topic_name}
                  </span>
                  <h2 className="text-lg font-bold text-slate-900 mt-0.5">
                    {isReviewMode ? 'Review Responses & Confirmation' : `Question ${currentQuestionIndex + 1} of ${totalQuestions}`}
                  </h2>
                </div>

                <div className="text-right">
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                    allAnswered 
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                      : 'bg-blue-50 text-[#3B50BA] border-blue-200'
                  }`}>
                    {answeredCount} of {totalQuestions} Answered {allAnswered && '✓'}
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-[#3B50BA] h-full rounded-full transition-all duration-300"
                  style={{ width: `${((currentQuestionIndex + 1) / totalQuestions) * 100}%` }}
                />
              </div>

              {/* Numbered Question Pill Nav */}
              <div className="flex items-center gap-2 pt-1">
                {questions.map((q, idx) => {
                  const isAns = selectedAnswers[String(q.question_id)] !== null && selectedAnswers[String(q.question_id)] !== undefined;
                  const isCur = !isReviewMode && currentQuestionIndex === idx;

                  return (
                    <button
                      key={q.question_id}
                      type="button"
                      onClick={() => handleJumpToQuestion(idx)}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-bold flex items-center justify-center gap-1 transition-all cursor-pointer ${
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

            {/* Assessment Workspace Body */}
            {isReviewMode ? (
              /* Confirmation / Review Screen */
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-7 shadow-xs space-y-5 animate-in fade-in duration-200">
                <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 text-xs sm:text-sm text-blue-900 flex items-start gap-3">
                  <FileCheck2 className="w-5 h-5 text-[#3B50BA] shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-semibold">Review your scenario responses before final grading:</strong>
                    <span className="text-xs text-blue-800">
                      All responses will be graded securely by the backend engine. Click 'Edit' next to any question to modify your selection.
                    </span>
                  </div>
                </div>

                {/* Questions Checklist */}
                <div className="space-y-3">
                  {questions.map((q, idx) => {
                    const qIdStr = String(q.question_id);
                    const chosenOptId = selectedAnswers[qIdStr];
                    const isUnanswered = chosenOptId === null || chosenOptId === undefined;

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
                        className={`p-4 rounded-xl border transition-all flex items-start justify-between gap-3 ${
                          isUnanswered
                            ? 'bg-amber-50/60 border-amber-200'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-900">Question {idx + 1}</span>
                            {isUnanswered ? (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                                Unanswered
                              </span>
                            ) : (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                                Answered
                              </span>
                            )}
                          </div>
                          <p className="text-xs sm:text-sm text-slate-700 line-clamp-2 leading-relaxed">
                            {q.question_text}
                          </p>
                          <div className="flex items-center gap-2 pt-1 text-xs">
                            <span className="font-bold text-[#3B50BA] bg-blue-50 px-2 py-0.5 rounded border border-blue-200 text-[11px]">
                              Option {chosenOptId || 'None'}
                            </span>
                            <span className="text-slate-600 truncate max-w-md">{chosenText}</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleJumpToQuestion(idx)}
                          className="px-3 py-1.5 text-xs font-bold text-[#3B50BA] hover:bg-blue-50 rounded-lg transition-colors cursor-pointer shrink-0"
                        >
                          Edit
                        </button>
                      </div>
                    );
                  })}
                </div>

                {/* Review Footer Controls */}
                <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => setIsReviewMode(false)}
                    className="px-4 py-2.5 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back to Questions</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleSubmitAssessment}
                    disabled={isSubmitting || !allAnswered}
                    className="px-6 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2 cursor-pointer active:scale-98"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Grading &amp; Evaluating...</span>
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
              /* One Question at a Time View */
              currentQuestion && (
                <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-7 shadow-xs space-y-5 animate-in fade-in duration-200">
                  {/* Scenario Question Prompt */}
                  <div className="p-4 sm:p-5 rounded-xl bg-slate-50 border border-slate-200/90 space-y-1">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                      Workplace Scenario
                    </span>
                    <p className="text-sm sm:text-base font-semibold text-slate-900 leading-relaxed">
                      {currentQuestion.question_text}
                    </p>
                  </div>

                  {/* Answer Options */}
                  <div className="space-y-3 pt-1">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                      Select Your Response:
                    </span>
                    {currentQuestion.options && currentQuestion.options.map((opt, oIdx) => {
                      const optId = typeof opt === 'object' && opt.option_id ? opt.option_id : OPTION_LETTERS[oIdx];
                      const optText = typeof opt === 'object' && opt.text ? opt.text : (typeof opt === 'string' ? opt : String(opt));
                      const isSelected = currentSelectedOpt === optId;

                      return (
                        <label
                          key={optId || oIdx}
                          onClick={() => handleSelectOption(currentQuestion.question_id, optId)}
                          className={`flex items-start gap-3.5 p-4 rounded-xl border text-xs sm:text-sm cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-blue-50/90 border-[#3B50BA] text-slate-900 font-medium shadow-xs'
                              : 'bg-white border-slate-200/90 text-slate-700 hover:bg-slate-50 hover:border-slate-300'
                          }`}
                        >
                          <div className={`w-7 h-7 rounded-full border flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 transition-colors ${
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

                  {/* Navigation Controls */}
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
                          className={`px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
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
                          className={`px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
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
        )}
      </main>
    </div>
  );
};
export default AssessmentPage;
