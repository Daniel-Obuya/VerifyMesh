import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  AlertTriangle,
  RefreshCw
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

  // Autosave and attempt resumption states
  const [autosaveStatus, setAutosaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'failed'
  const [answersVersion, setAnswersVersion] = useState(0);
  const [lastSavedTime, setLastSavedTime] = useState(null);
  const autosaveTimeoutRef = useRef(null);
  const pendingAnswersRef = useRef(null);
  const answersVersionRef = useRef(0);

  // Loading and error states
  const [isStartingAttempt, setIsStartingAttempt] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Candidate display formatting
  const rawName = user?.fullName || user?.username || 'Candidate';
  const cleanName = rawName.replace(/\s*\(Verified\)/gi, '').trim();
  const userInitials = cleanName
    ? cleanName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'CA';

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
        // 3. First required topic for task
        // 4. Topic linked to loadedTask.exam_id
        // 5. First available topic ONLY if task does NOT require a specific assessment
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

        if (!activeTopic && loadedTask && loadedTask.exam_id) {
          activeTopic = availableTopics.find(t => t.exam_id === loadedTask.exam_id);
        }

        if (!activeTopic) {
          if (loadedTask && loadedTask.exam_required) {
            setErrorMessage('Configured task assessment template is not available or has no linked topics.');
          } else if (availableTopics.length > 0) {
            activeTopic = availableTopics[0];
          }
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

  // Sync version ref
  useEffect(() => {
    answersVersionRef.current = answersVersion;
  }, [answersVersion]);

  // Autosave background sync
  const performAutosave = useCallback(async (answersToSave) => {
    if (!attemptId || !selectedTopic) return;
    setAutosaveStatus('saving');
    try {
      const nextVer = answersVersionRef.current + 1;
      const res = await competencyService.autosaveTopicAnswers(
        selectedTopic.topic_id,
        attemptId,
        answersToSave,
        nextVer
      );
      if (res?.success && res.data) {
        setAnswersVersion(res.data.answers_version);
        answersVersionRef.current = res.data.answers_version;
        setLastSavedTime(res.data.last_saved_at || new Date().toISOString());
        setAutosaveStatus('saved');
      } else {
        setAutosaveStatus('failed');
      }
    } catch (err) {
      console.warn('Autosave background sync failed:', err);
      setAutosaveStatus('failed');
    }
  }, [attemptId, selectedTopic]);

  const queueAutosave = useCallback((newAnswers) => {
    pendingAnswersRef.current = newAnswers;
    if (autosaveTimeoutRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
    }
    setAutosaveStatus('saving');
    autosaveTimeoutRef.current = setTimeout(() => {
      performAutosave(pendingAnswersRef.current);
    }, 600);
  }, [performAutosave]);

  // Flush pending autosave before tab unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (autosaveTimeoutRef.current && pendingAnswersRef.current && attemptId && selectedTopic) {
        competencyService.autosaveTopicAnswers(
          selectedTopic.topic_id,
          attemptId,
          pendingAnswersRef.current,
          answersVersionRef.current + 1
        );
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (autosaveTimeoutRef.current) {
        clearTimeout(autosaveTimeoutRef.current);
      }
    };
  }, [attemptId, selectedTopic]);

  // 2. Handle Starting or Resuming Assessment Attempt
  const handleStartAssessment = async () => {
    if (!selectedTopic) return;

    setIsStartingAttempt(true);
    setErrorMessage(null);

    try {
      const numericTaskId = task?.task_id || (taskId && !isNaN(Number(taskId)) ? Number(taskId) : null);
      
      // Authoritative attempt creation or resumption on server
      const attemptRes = await competencyService.startTopicAttempt(selectedTopic.topic_id, numericTaskId);
      
      if (!attemptRes?.success || !attemptRes.data) {
        throw new Error(attemptRes?.error || 'Failed to initialize assessment attempt.');
      }

      const { 
        attempt_id, 
        expires_at, 
        questions: returnedQuestions,
        saved_answers,
        answers_version,
        last_saved_at
      } = attemptRes.data;

      setAttemptId(attempt_id);
      setAttemptExpiresAt(expires_at);
      if (answers_version) {
        setAnswersVersion(answers_version);
        answersVersionRef.current = answers_version;
      }
      if (last_saved_at) {
        setLastSavedTime(last_saved_at);
      }

      // Load server-gradeable questions using the attempt's snapshot
      let loadedQuestions = returnedQuestions;
      if (!Array.isArray(loadedQuestions) || loadedQuestions.length === 0) {
        const qRes = await competencyService.getTopicQuestions(selectedTopic.topic_id, attempt_id);
        if (!qRes?.success || !Array.isArray(qRes.data) || qRes.data.length === 0) {
          throw new Error(qRes?.error || 'No questions configured for this topic.');
        }
        loadedQuestions = qRes.data;
      }

      setQuestions(loadedQuestions);

      // Initialize answers map, restoring previously saved draft answers if resuming
      const initialAnswers = {};
      loadedQuestions.forEach(q => {
        const qStr = String(q.question_id);
        initialAnswers[qStr] = (saved_answers && saved_answers[qStr] !== undefined && saved_answers[qStr] !== null)
          ? saved_answers[qStr]
          : null;
      });
      setSelectedAnswers(initialAnswers);

      // Auto-jump to the first unanswered question
      const firstUnansweredIndex = loadedQuestions.findIndex(q => {
        const ans = initialAnswers[String(q.question_id)];
        return ans === null || ans === undefined;
      });
      setCurrentQuestionIndex(firstUnansweredIndex >= 0 ? firstUnansweredIndex : 0);

      if (saved_answers && Object.keys(saved_answers).length > 0) {
        setAutosaveStatus('saved');
      }

      setIsReviewMode(false);
      setIsInProgress(true);
    } catch (err) {
      console.error('Error starting assessment:', err);
      setErrorMessage(err?.data?.error || err?.message || 'Failed to start assessment.');
    } finally {
      setIsStartingAttempt(false);
    }
  };

  // 3. Option Selection with Debounced Autosave
  const handleSelectOption = (questionId, optionId) => {
    const updated = {
      ...selectedAnswers,
      [String(questionId)]: optionId
    };
    setSelectedAnswers(updated);
    queueAutosave(updated);
  };

  // 4. Stepper Navigation with Immediate Flush
  const totalQuestions = questions.length;
  const answeredCount = Object.values(selectedAnswers).filter(v => v !== null && v !== undefined).length;
  const allAnswered = totalQuestions > 0 && answeredCount === totalQuestions;

  const currentQuestion = questions[currentQuestionIndex] || null;
  const currentQIdStr = currentQuestion ? String(currentQuestion.question_id) : '';
  const currentSelectedOpt = currentQIdStr ? selectedAnswers[currentQIdStr] : null;

  const handleNext = () => {
    if (autosaveTimeoutRef.current && pendingAnswersRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
      performAutosave(pendingAnswersRef.current);
    }
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
    if (autosaveTimeoutRef.current && pendingAnswersRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
      performAutosave(pendingAnswersRef.current);
    }
    setCurrentQuestionIndex(idx);
    setIsReviewMode(false);
  };

  // 5. Final Submission (Server-side grading & ML evaluation)
  const handleSubmitAssessment = async () => {
    if (!allAnswered) {
      setErrorMessage(`Please answer all ${totalQuestions} scenario questions before submitting.`);
      return;
    }

    if (autosaveTimeoutRef.current && pendingAnswersRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
      performAutosave(pendingAnswersRef.current);
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

  // 6. Explicit Abandonment
  const handleAbandonAssessment = async () => {
    const confirmed = window.confirm(
      'Are you sure you want to abandon this assessment? This will forfeit your current attempt and count toward your maximum attempt limit.'
    );
    if (!confirmed || !attemptId || !selectedTopic) return;
    try {
      await competencyService.abandonTopicAttempt(
        selectedTopic.topic_id,
        attemptId,
        'Candidate explicitly abandoned assessment'
      );
      navigate('/dashboard');
    } catch (err) {
      console.error('Error abandoning assessment:', err);
      setErrorMessage(err?.data?.error || err?.message || 'Failed to abandon attempt.');
    }
  };

  const OPTION_LETTERS = ['A', 'B', 'C', 'D'];

  if (isLoadingTask) {
    return (
      <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex items-center justify-center font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-indigo-600/6 blur-[140px] rounded-full" />
          <div className="absolute top-1/3 right-10 w-[500px] h-[350px] bg-blue-500/5 blur-[130px] rounded-full" />
        </div>
        <div className="text-center space-y-3 relative z-10">
          <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-400">Loading qualification requirements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-[#e8ebf7] flex flex-col font-sans relative selection:bg-[#5a69f0]/40 selection:text-white">
      {/* Ambient background glows matching VerifyMesh Dashboard Design */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-indigo-600/6 blur-[140px] rounded-full" />
        <div className="absolute top-1/3 right-10 w-[500px] h-[350px] bg-blue-500/5 blur-[130px] rounded-full" />
      </div>

      {/* Top Professional Header Bar */}
      <header className="h-16 bg-[#080d1a]/95 border-b border-[#1b2542] px-4 sm:px-8 flex items-center justify-between shrink-0 sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-3 sm:gap-4">
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
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-[#151f38]/60 hover:bg-[#151f38] border border-[#1e2a4a] transition-all cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Back to Dashboard</span>
            <span className="sm:hidden">Back</span>
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
                Assessment Battery
              </span>
            </div>
          </div>
        </div>

        {/* Candidate & Assessment Status Pill */}
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <span className="text-xs font-bold text-white block">{cleanName}</span>
            <span className="text-[11px] text-slate-400 flex items-center justify-end gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              Authenticated Candidate
            </span>
          </div>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
            {userInitials}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8 max-w-4xl w-full mx-auto space-y-6 relative z-10">
        {/* Error Alert */}
        {errorMessage && (
          <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs sm:text-sm flex items-start gap-3 shadow-lg animate-in fade-in duration-200">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span className="flex-1 font-medium">{errorMessage}</span>
          </div>
        )}

        {/* =========================================================================
           STAGE B: INTRODUCTION & REQUIREMENTS OVERVIEW SCREEN
           ========================================================================= */}
        {!isInProgress ? (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Task Context Card */}
            {task && (
              <div className="bg-[#0b1020] rounded-2xl p-6 sm:p-7 border border-[#1b2542] shadow-xl space-y-5 relative overflow-hidden">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1b2542] pb-4">
                  <div>
                    <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase">
                      Qualifying For Task
                    </span>
                    <h1 className="text-xl sm:text-2xl font-bold font-sora text-white tracking-tight mt-1">
                      {task.title || task.task_name}
                    </h1>
                    {task.category && (
                      <span className="text-xs text-slate-400 font-medium">
                        {task.category} &bull; {task.work_arrangement || 'Remote'}
                      </span>
                    )}
                  </div>
                  <div className="sm:text-right">
                    <span className="text-xs font-semibold text-slate-400 block">Compensation</span>
                    <span className="text-base font-bold text-emerald-400 font-mono">
                      {task.payout || '$30 - $40 / hr'}
                    </span>
                  </div>
                </div>

                {/* Required Topics Progress Bar & Cards */}
                {task.required_topics && task.required_topics.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-300 uppercase tracking-wider">
                        Required Qualification Topics
                      </span>
                      <span className="font-semibold text-slate-400">
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
                            className={`p-4 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                              isCurrentSelected 
                                ? 'bg-indigo-950/40 border-indigo-500/80 shadow-lg shadow-indigo-500/10' 
                                : 'bg-[#080d1a]/80 border-[#1b2542] hover:border-[#2a3b66] hover:bg-[#0c1427]'
                            }`}
                          >
                            <div className="space-y-1">
                              <span className="text-xs font-bold text-white block">
                                {rt.name || rt.topic_name}
                              </span>
                              <span className="text-[11px] text-slate-400 block">
                                5 Scenario Questions &bull; Pass Threshold: {rt.passing_threshold ?? rt.passing_score ?? 70}%
                              </span>
                            </div>

                            <span className={`px-2.5 py-1 rounded-full text-xs font-bold shrink-0 border ${
                              isPassed
                                ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                                : isFailed
                                ? 'bg-rose-950/60 text-rose-400 border-rose-500/40'
                                : 'bg-amber-950/60 text-amber-300 border-amber-500/40'
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
              <div className="bg-[#0b1020] rounded-2xl p-6 sm:p-7 border border-[#1b2542] shadow-xl space-y-6 relative overflow-hidden">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-950/80 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/10">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                        Competency Evaluation
                      </span>
                      <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#131d35] text-indigo-300 border border-[#223055]">
                        Topic {selectedTopic.topic_id}
                      </span>
                    </div>
                    <h2 className="text-xl sm:text-2xl font-bold font-sora text-white">
                      {selectedTopic.topic_name}
                    </h2>
                    <p className="text-xs sm:text-sm text-slate-300 leading-relaxed pt-1">
                      {selectedTopic.description || 'Demonstrate professional situational judgment and problem-solving techniques for this competency topic.'}
                    </p>
                  </div>
                </div>

                {/* Specification Badges */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3.5 bg-[#080d1a]/80 border border-[#1b2542] rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Questions</span>
                    <span className="text-sm font-bold text-white mt-0.5 block">5 Scenarios</span>
                  </div>
                  <div className="p-3.5 bg-[#080d1a]/80 border border-[#1b2542] rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Estimated Time</span>
                    <span className="text-sm font-bold text-white mt-0.5 block">8 - 12 Minutes</span>
                  </div>
                  <div className="p-3.5 bg-[#080d1a]/80 border border-[#1b2542] rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Passing Score</span>
                    <span className="text-sm font-bold text-indigo-300 mt-0.5 block">
                      &ge; {selectedTopic.passing_score ?? 70}%
                    </span>
                  </div>
                  <div className="p-3.5 bg-[#080d1a]/80 border border-[#1b2542] rounded-xl">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">Result Reuse</span>
                    <span className="text-sm font-bold text-emerald-400 mt-0.5 block">Permanent / Valid</span>
                  </div>
                </div>

                {/* Important Rules Checklist */}
                <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 space-y-2 text-xs sm:text-sm text-slate-300">
                  <h3 className="font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span>Assessment Protocol &amp; Guidelines</span>
                  </h3>
                  <ul className="space-y-1.5 list-disc list-inside text-slate-400 text-xs leading-relaxed">
                    <li>One scenario question presented at a time with full freedom to navigate forward and backward.</li>
                    <li>Answers are safely preserved during navigation and verified on a final review screen.</li>
                    <li>Submissions are graded authoritatively on the server; correct answers are never exposed in transit.</li>
                    <li>Passing results are permanently credited to your agent record and satisfy requirements on any task needing this topic.</li>
                    <li>If the score falls below the passing threshold, a retake is permitted after reviewing the outcome.</li>
                  </ul>
                </div>

                {/* Action CTA */}
                {Boolean(task?.prerequisites && (task.prerequisites.certification_met === false || task.prerequisites.experience_met === false)) ? (
                  <div className="pt-4 p-4 rounded-xl bg-amber-950/40 border border-amber-500/30 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-start gap-2.5">
                      <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-semibold text-amber-200">Prerequisites Not Met</p>
                        <p className="text-xs text-amber-300/80 mt-0.5">{task.blocking_reason || 'You do not currently satisfy the minimum experience or certification prerequisites for this task.'}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate('/dashboard')}
                      className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs border border-slate-700 transition-colors cursor-pointer shrink-0"
                    >
                      Back to Opportunities
                    </button>
                  </div>
                ) : (
                  <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-[#1b2542]">
                    <span className="text-xs text-slate-400">
                      Ready to begin? Click below to launch the dedicated evaluation workspace.
                    </span>

                    <button
                      type="button"
                      onClick={handleStartAssessment}
                      disabled={isStartingAttempt}
                      className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 disabled:opacity-50 text-white font-bold text-sm shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-98"
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
                )}
              </div>
            )}
          </div>
        ) : (
          /* =========================================================================
             STAGE C: DISTRACTION-FREE ASSESSMENT TAKING WORKSPACE
             ========================================================================= */
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* Workspace Header Bar */}
            <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-4 sm:p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">
                    {selectedTopic?.topic_name}
                  </span>
                  <h2 className="text-base sm:text-lg font-bold font-sora text-white mt-0.5">
                    {isReviewMode ? 'Review Responses & Confirmation' : `Question ${currentQuestionIndex + 1} of ${totalQuestions}`}
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  {/* Autosave Status Pill */}
                  {autosaveStatus === 'saving' && (
                    <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-indigo-400 bg-indigo-950/40 px-2.5 py-1 rounded-full border border-indigo-500/30 animate-pulse">
                      <RefreshCw className="w-3 h-3 animate-spin text-indigo-400" />
                      <span>Saving draft...</span>
                    </span>
                  )}
                  {autosaveStatus === 'saved' && (
                    <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-full border border-emerald-500/30">
                      <Check className="w-3 h-3 stroke-[2.5]" />
                      <span>Answers saved</span>
                    </span>
                  )}
                  {autosaveStatus === 'failed' && (
                    <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-amber-400 bg-amber-950/40 px-2.5 py-1 rounded-full border border-amber-500/30">
                      <AlertCircle className="w-3 h-3 text-amber-400" />
                      <span>Sync pending</span>
                    </span>
                  )}

                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                    allAnswered 
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40' 
                      : 'bg-indigo-950/60 text-indigo-300 border border-indigo-500/40'
                  }`}>
                    {answeredCount} of {totalQuestions} Answered {allAnswered && '✓'}
                  </span>
                </div>
              </div>

              {/* Progress Bar Track */}
              <div className="w-full bg-[#080d1a] h-2 rounded-full overflow-hidden border border-[#1b2542]">
                <div
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-300 shadow-xs shadow-indigo-500/50"
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
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-indigo-500/30 border border-indigo-400/50'
                          : isAns
                          ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-900/60'
                          : 'bg-[#080d1a] text-slate-400 border border-[#1b2542] hover:border-[#2a3b66] hover:text-white'
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
              <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-5 sm:p-7 shadow-xl space-y-5 animate-in fade-in duration-200">
                <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-xs sm:text-sm text-indigo-200 flex items-start gap-3">
                  <FileCheck2 className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-semibold text-white">Review your scenario responses before final grading:</strong>
                    <span className="text-xs text-slate-300">
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
                            ? 'bg-amber-950/20 border-amber-500/40'
                            : 'bg-[#080d1a]/80 border-[#1b2542] hover:border-[#2a3b66]'
                        }`}
                      >
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-white">Question {idx + 1}</span>
                            {isUnanswered ? (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-300 border border-amber-500/40">
                                Unanswered
                              </span>
                            ) : (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-500/40">
                                Answered
                              </span>
                            )}
                          </div>
                          <p className="text-xs sm:text-sm text-slate-300 line-clamp-2 leading-relaxed">
                            {q.question_text}
                          </p>
                          <div className="flex items-center gap-2 pt-1 text-xs">
                            <span className="font-bold text-indigo-300 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-500/40 text-[11px]">
                              Option {chosenOptId || 'None'}
                            </span>
                            <span className="text-slate-400 truncate max-w-md">{chosenText}</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleJumpToQuestion(idx)}
                          className="px-3 py-1.5 text-xs font-bold text-indigo-400 hover:text-white hover:bg-indigo-900/40 rounded-lg border border-transparent hover:border-indigo-500/30 transition-all cursor-pointer shrink-0"
                        >
                          Edit
                        </button>
                      </div>
                    );
                  })}
                </div>

                {/* Review Footer Controls */}
                <div className="pt-4 border-t border-[#1b2542] flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsReviewMode(false)}
                      className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-slate-300 hover:text-white bg-[#151f38]/60 hover:bg-[#151f38] border border-[#1e2a4a] transition-all cursor-pointer"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      <span>Back to Questions</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleAbandonAssessment}
                      className="text-xs font-semibold text-rose-400 hover:text-rose-300 hover:underline px-3 py-2 cursor-pointer transition-colors"
                      title="Forfeit and abandon current attempt"
                    >
                      Abandon Attempt
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={handleSubmitAssessment}
                    disabled={isSubmitting || !allAnswered}
                    className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 transition-all flex items-center gap-2 cursor-pointer active:scale-98"
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
                <div className="bg-[#0b1020] rounded-2xl border border-[#1b2542] p-5 sm:p-7 shadow-xl space-y-5 animate-in fade-in duration-200">
                  {/* Scenario Question Prompt */}
                  <div className="p-4 sm:p-5 rounded-xl bg-[#080d1a]/90 border border-[#1b2542] space-y-1">
                    <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider block">
                      Workplace Scenario
                    </span>
                    <p className="text-sm sm:text-base font-semibold text-white leading-relaxed">
                      {currentQuestion.question_text}
                    </p>
                  </div>

                  {/* Answer Options */}
                  <div className="space-y-3 pt-1">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
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
                              ? 'bg-indigo-950/40 border-indigo-500 text-white font-medium shadow-md shadow-indigo-500/10'
                              : 'bg-[#080d1a]/80 border-[#1b2542] text-slate-300 hover:bg-[#0f172a] hover:border-[#2a3b66]'
                          }`}
                        >
                          <div className={`w-7 h-7 rounded-full border flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 transition-colors ${
                            isSelected
                              ? 'bg-indigo-600 text-white border-indigo-400 shadow-xs'
                              : 'bg-[#131d35] text-slate-400 border-[#223055]'
                          }`}>
                            {optId}
                          </div>
                          <span className="leading-relaxed flex-1 pt-0.5 text-slate-200">
                            {optText}
                          </span>
                        </label>
                      );
                    })}
                  </div>

                  {/* Navigation Controls */}
                  <div className="pt-4 border-t border-[#1b2542] flex items-center justify-between gap-3">
                    <button
                      type="button"
                      onClick={handlePrev}
                      disabled={currentQuestionIndex === 0}
                      className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
                        currentQuestionIndex === 0
                          ? 'text-slate-600 bg-transparent cursor-not-allowed border border-transparent'
                          : 'text-slate-300 hover:text-white bg-[#151f38]/60 hover:bg-[#151f38] border border-[#1e2a4a] cursor-pointer'
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
                          className="px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-[#131d35] hover:bg-[#1a2849] border border-[#223055] rounded-xl transition-all cursor-pointer hidden sm:flex items-center gap-1"
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
                          className={`px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm shadow-xs transition-all flex items-center gap-1.5 ${
                            currentSelectedOpt !== null && currentSelectedOpt !== undefined
                              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-indigo-600/20 cursor-pointer active:scale-98'
                              : 'bg-[#131d35] text-slate-500 border border-[#1b2542] cursor-not-allowed'
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
                          className={`px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm shadow-xs transition-all flex items-center gap-1.5 ${
                            allAnswered
                              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-indigo-600/20 cursor-pointer active:scale-98'
                              : 'bg-[#131d35] text-slate-500 border border-[#1b2542] cursor-not-allowed'
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
