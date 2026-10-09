import React, { useState } from 'react';
import { 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  BrainCircuit, 
  Award, 
  ArrowRight,
  Sliders,
  HelpCircle,
  Clock,
  ShieldCheck
} from 'lucide-react';
import { competencyService } from '../../services/competencyService';

// Sample quiz questions representing the 4 core competency domains
const QUESTIONS = [
  {
    id: 1,
    domain: 'Customer Service & De-escalation',
    field: 'customer_service_score',
    question: 'A high-value client contacts you upset that a critical task delivery was delayed due to a misunderstanding. What is your primary response?',
    options: [
      { text: 'Acknowledge the delay immediately, validate their frustration, explain the concrete corrective steps, and provide an updated resolution ETA.', score: 95 },
      { text: 'Apologize and issue a standard system support credit without analyzing the root cause.', score: 75 },
      { text: 'Inform them that task delivery terms include occasional processing queues according to platform terms.', score: 50 },
      { text: 'Forward the message to second-level administrative escalation without replying to the client.', score: 35 }
    ]
  },
  {
    id: 2,
    domain: 'Communication & Clarity',
    field: 'communication_score',
    question: 'How do you structure complex technical instructions when onboarding a new business partner to VerifyMesh task workflows?',
    options: [
      { text: 'Break down workflows into numbered chronological milestones, highlight prerequisite certifications, and verify understanding at each milestone.', score: 96 },
      { text: 'Send the full 40-page API and system requirements documentation link and ask them to read thoroughly.', score: 65 },
      { text: 'Provide a brief summary and tell them to ping on Slack if any step fails.', score: 60 },
      { text: 'Assume they are experienced and instruct them to run the default setup commands.', score: 40 }
    ]
  },
  {
    id: 3,
    domain: 'Product Knowledge & Verification Architecture',
    field: 'product_knowledge_score',
    question: 'In the VerifyMesh architecture, what is the operational relationship between the Google Colab model and real-time task eligibility?',
    options: [
      { text: 'Colab trains and exports the tuned Random Forest model (.joblib); the backend runs inference for competency, and the rules engine checks eligibility.', score: 98 },
      { text: 'The frontend trains the machine learning model directly in the browser on each button click.', score: 45 },
      { text: 'Google Colab must be active and running live on port 5000 for every single task request.', score: 55 },
      { text: 'Task eligibility is manually assigned by administrators without predictive competency analysis.', score: 30 }
    ]
  },
  {
    id: 4,
    domain: 'Sales Skill & Solution Matching',
    field: 'sales_skill_score',
    question: 'An enterprise prospect is deciding between a basic task quota and an advanced full-mesh plan. They express hesitation about ROI. How do you counsel them?',
    options: [
      { text: 'Analyze their specific monthly verification volume, demonstrate how verified competency reduces dispute overhead, and showcase milestone savings.', score: 94 },
      { text: 'Offer an immediate 50% discount on the highest tier to secure the deal today.', score: 68 },
      { text: 'Recommend the basic tier because it has the lowest upfront commitment.', score: 55 },
      { text: 'Tell them to consult their internal finance team and contact you when ready.', score: 40 }
    ]
  }
];

export const TakeAssessmentModal = ({ 
  isOpen, 
  onClose, 
  onAssessmentComplete, 
  currentData,
  userId 
}) => {
  const [activeTab, setActiveTab] = useState('quiz'); // 'quiz' or 'quick'
  
  // Interactive Quiz State
  const [selectedAnswers, setSelectedAnswers] = useState({
    1: 0,
    2: 0,
    3: 0,
    4: 0,
  });

  // Battery inputs
  const [formData, setFormData] = useState({
    previous_experience_months: currentData?.previous_experience_months || 24,
    sales_experience_months: currentData?.sales_experience_months || 18,
    customer_service_experience_months: currentData?.customer_service_experience_months || 12,
    certification_count: currentData?.certification_count || 2,
    relevant_certification: currentData?.relevant_certification ?? 1,
    assessment_score: currentData?.assessment_score || 82.5,
    communication_score: currentData?.communication_score || 85.0,
    product_knowledge_score: currentData?.product_knowledge_score || 80.0,
    sales_skill_score: currentData?.sales_skill_score || 88.0,
    customer_service_score: currentData?.customer_service_score || 84.0,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleOptionSelect = (questionId, optionIndex) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [questionId]: optionIndex
    }));
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: parseFloat(value) || 0
    }));
  };

  const applyPreset = (type) => {
    if (type === 'competent') {
      setFormData({
        previous_experience_months: 24,
        sales_experience_months: 18,
        customer_service_experience_months: 12,
        certification_count: 2,
        relevant_certification: 1,
        assessment_score: 78.5,
        communication_score: 82.0,
        product_knowledge_score: 79.0,
        sales_skill_score: 80.0,
        customer_service_score: 85.0,
      });
      setSelectedAnswers({ 1: 0, 2: 0, 3: 0, 4: 1 });
    } else if (type === 'advanced') {
      setFormData({
        previous_experience_months: 48,
        sales_experience_months: 36,
        customer_service_experience_months: 24,
        certification_count: 4,
        relevant_certification: 1,
        assessment_score: 93.5,
        communication_score: 95.0,
        product_knowledge_score: 92.0,
        sales_skill_score: 94.0,
        customer_service_score: 96.0,
      });
      setSelectedAnswers({ 1: 0, 2: 0, 3: 0, 4: 0 });
    } else if (type === 'basic') {
      setFormData({
        previous_experience_months: 4,
        sales_experience_months: 2,
        customer_service_experience_months: 2,
        certification_count: 0,
        relevant_certification: 0,
        assessment_score: 52.0,
        communication_score: 55.0,
        product_knowledge_score: 50.0,
        sales_skill_score: 48.0,
        customer_service_score: 54.0,
      });
      setSelectedAnswers({ 1: 2, 2: 2, 3: 2, 4: 2 });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    let payload = { ...formData };

    if (activeTab === 'quiz') {
      // Calculate scores from selected options
      const q1Score = QUESTIONS[0].options[selectedAnswers[1]].score;
      const q2Score = QUESTIONS[1].options[selectedAnswers[2]].score;
      const q3Score = QUESTIONS[2].options[selectedAnswers[3]].score;
      const q4Score = QUESTIONS[3].options[selectedAnswers[4]].score;
      const composite = Math.round((q1Score + q2Score + q3Score + q4Score) / 4);

      payload = {
        ...formData,
        customer_service_score: q1Score,
        communication_score: q2Score,
        product_knowledge_score: q3Score,
        sales_skill_score: q4Score,
        assessment_score: composite,
      };
    }

    if (userId) {
      payload.user_id = userId;
    }

    try {
      const res = await competencyService.predictCompetency(payload);
      if (res?.success) {
        setResult(res);
        if (onAssessmentComplete) {
          onAssessmentComplete(res, payload);
        }
      } else {
        setError(res?.error || 'Failed to complete assessment evaluation.');
      }
    } catch (err) {
      setError(err?.message || 'Server error while running Google Colab model evaluation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFinish = () => {
    setResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-150 flex flex-col max-h-[90vh] overflow-hidden transition-all"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="p-5 sm:px-6 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EEF2FF] text-[#3B50BA] flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 leading-snug">
                Agent Competency Assessment
              </h3>
              <p className="text-xs text-slate-500">
                AI-driven evaluation for task eligibility &amp; verified proficiency
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6 overflow-y-auto flex-1 space-y-5">
          {result ? (
            /* Results View */
            <div className="text-center py-4 space-y-6 animate-in zoom-in-95 duration-200">
              <div className="w-16 h-16 mx-auto rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-200">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                  Assessment Completed
                </span>
                <h4 className="text-2xl font-bold text-slate-900 mt-3">
                  Predicted Competency: {result.predicted_competency || result.prediction}
                </h4>
                <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                  {result.tier_info?.description || 'Your assessment scores have been evaluated by the VerifyMesh inference model.'}
                </p>
              </div>

              {/* Score Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-left">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Model Confidence</span>
                  <p className="text-xl font-bold text-slate-900 mt-1">{result.confidence}%</p>
                  <p className="text-[11px] text-[#3B50BA] font-medium mt-0.5">Colab Random Forest</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Assigned Tier</span>
                  <p className="text-xl font-bold text-slate-900 mt-1">Level {result.level_tier || 3}</p>
                  <p className="text-[11px] text-emerald-600 font-medium mt-0.5">Verified in Mesh</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 col-span-2 sm:col-span-1">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Eligible Tasks</span>
                  <p className="text-xl font-bold text-slate-900 mt-1">
                    {(result.predicted_competency || result.prediction) === 'Advanced' ? '3 of 3 Tasks' : '2 of 3 Tasks'}
                  </p>
                  <p className="text-[11px] text-slate-500 font-medium mt-0.5">Updated live</p>
                </div>
              </div>

              {/* Class Probability Distribution */}
              {result.probabilities && (
                <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 text-left space-y-2">
                  <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">
                    Probability Distribution
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                    {Object.entries(result.probabilities).map(([cls, prob]) => (
                      <div key={cls} className="bg-white p-2 rounded-lg border border-slate-150">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="font-medium text-slate-600">{cls}</span>
                          <span className="font-bold text-slate-900">{prob}%</span>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <div 
                            className="bg-[#3B50BA] h-full rounded-full transition-all duration-500"
                            style={{ width: `${prob}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2 flex justify-center gap-3">
                <button
                  type="button"
                  onClick={handleFinish}
                  className="px-6 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] text-white font-semibold text-sm shadow-xs transition-colors flex items-center gap-2"
                >
                  Apply &amp; Return to Dashboard
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            /* Assessment Form View */
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Mode Switcher Tabs */}
              <div className="flex items-center justify-between bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => setActiveTab('quiz')}
                  className={`flex-1 py-1.5 px-3 text-xs sm:text-sm font-semibold rounded-lg transition-all ${
                    activeTab === 'quiz'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Interactive Assessment (4 Questions)
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('quick')}
                  className={`flex-1 py-1.5 px-3 text-xs sm:text-sm font-semibold rounded-lg transition-all ${
                    activeTab === 'quick'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Direct Score Input &amp; Presets
                </button>
              </div>

              {/* Presets Row */}
              <div className="flex items-center justify-between text-xs bg-blue-50/60 border border-blue-100 p-3 rounded-xl">
                <span className="text-blue-900 font-medium flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-[#3B50BA]" />
                  Quick Presets:
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => applyPreset('competent')}
                    className="px-2.5 py-1 rounded-lg bg-white border border-blue-200 text-[#3B50BA] font-semibold hover:bg-blue-50 transition-colors"
                  >
                    Competent (78%)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset('advanced')}
                    className="px-2.5 py-1 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 transition-colors"
                  >
                    Advanced (95%)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset('basic')}
                    className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    Needs Refresher
                  </button>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Mode 1: Interactive Questions */}
              {activeTab === 'quiz' ? (
                <div className="space-y-4">
                  {QUESTIONS.map((q) => (
                    <div key={q.id} className="p-4 rounded-xl border border-slate-200/90 bg-white hover:border-slate-300 transition-colors space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#3B50BA] uppercase tracking-wider">
                          Domain {q.id}: {q.domain}
                        </span>
                        <span className="text-xs text-slate-400">Question {q.id} of 4</span>
                      </div>
                      <p className="text-sm font-semibold text-slate-900 leading-snug">
                        {q.question}
                      </p>
                      <div className="space-y-1.5 pt-1">
                        {q.options.map((opt, oIdx) => {
                          const isSelected = selectedAnswers[q.id] === oIdx;
                          return (
                            <label
                              key={oIdx}
                              onClick={() => handleOptionSelect(q.id, oIdx)}
                              className={`flex items-start gap-3 p-2.5 rounded-lg border text-xs sm:text-sm cursor-pointer transition-all ${
                                isSelected
                                  ? 'bg-blue-50/70 border-[#3B50BA] text-slate-900 font-medium'
                                  : 'bg-slate-50/50 border-slate-200/70 text-slate-700 hover:bg-slate-50'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`question-${q.id}`}
                                checked={isSelected}
                                onChange={() => handleOptionSelect(q.id, oIdx)}
                                className="mt-0.5 text-[#3B50BA] focus:ring-[#3B50BA]"
                              />
                              <span className="leading-relaxed">{opt.text}</span>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  ))}

                  {/* Experience & Certification Quick Inputs */}
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                      Domain Experience &amp; Certification
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 mb-1">
                          Previous Exp (Months)
                        </label>
                        <input
                          type="number"
                          value={formData.previous_experience_months}
                          onChange={(e) => handleInputChange('previous_experience_months', e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs bg-white rounded-lg border border-slate-200 focus:outline-none focus:border-[#3B50BA]"
                          min="0"
                          max="400"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 mb-1">
                          Total Certifications
                        </label>
                        <input
                          type="number"
                          value={formData.certification_count}
                          onChange={(e) => handleInputChange('certification_count', e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs bg-white rounded-lg border border-slate-200 focus:outline-none focus:border-[#3B50BA]"
                          min="0"
                          max="20"
                        />
                      </div>
                      <div className="col-span-2 sm:col-span-1">
                        <label className="block text-[11px] font-medium text-slate-600 mb-1">
                          Relevant Certification
                        </label>
                        <select
                          value={formData.relevant_certification}
                          onChange={(e) => handleInputChange('relevant_certification', e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs bg-white rounded-lg border border-slate-200 focus:outline-none focus:border-[#3B50BA]"
                        >
                          <option value={1}>Verified (Accredited)</option>
                          <option value={0}>None / Unverified</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                /* Mode 2: Direct Battery Score Sliders */
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-3">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                      Core Battery Test Scores (0 - 100)
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                      <div>
                        <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                          <span>Overall Assessment</span>
                          <span className="font-bold text-[#3B50BA]">{formData.assessment_score} / 100</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={formData.assessment_score}
                          onChange={(e) => handleInputChange('assessment_score', e.target.value)}
                          className="w-full accent-[#3B50BA]"
                        />
                      </div>

                      <div>
                        <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                          <span>Communication Score</span>
                          <span className="font-bold text-[#3B50BA]">{formData.communication_score} / 100</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={formData.communication_score}
                          onChange={(e) => handleInputChange('communication_score', e.target.value)}
                          className="w-full accent-[#3B50BA]"
                        />
                      </div>

                      <div>
                        <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                          <span>Product Knowledge</span>
                          <span className="font-bold text-[#3B50BA]">{formData.product_knowledge_score} / 100</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={formData.product_knowledge_score}
                          onChange={(e) => handleInputChange('product_knowledge_score', e.target.value)}
                          className="w-full accent-[#3B50BA]"
                        />
                      </div>

                      <div>
                        <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                          <span>Sales Skill Score</span>
                          <span className="font-bold text-[#3B50BA]">{formData.sales_skill_score} / 100</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={formData.sales_skill_score}
                          onChange={(e) => handleInputChange('sales_skill_score', e.target.value)}
                          className="w-full accent-[#3B50BA]"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                          <span>Customer Service Score</span>
                          <span className="font-bold text-[#3B50BA]">{formData.customer_service_score} / 100</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={formData.customer_service_score}
                          onChange={(e) => handleInputChange('customer_service_score', e.target.value)}
                          className="w-full accent-[#3B50BA]"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                      Experience History
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 mb-1">Previous Exp (Mo)</label>
                        <input
                          type="number"
                          value={formData.previous_experience_months}
                          onChange={(e) => handleInputChange('previous_experience_months', e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs bg-white rounded-lg border border-slate-200"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 mb-1">Sales Exp (Mo)</label>
                        <input
                          type="number"
                          value={formData.sales_experience_months}
                          onChange={(e) => handleInputChange('sales_experience_months', e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs bg-white rounded-lg border border-slate-200"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 mb-1">Certifications</label>
                        <input
                          type="number"
                          value={formData.certification_count}
                          onChange={(e) => handleInputChange('certification_count', e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs bg-white rounded-lg border border-slate-200"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-5 py-2.5 rounded-xl bg-[#3B50BA] hover:bg-[#31429e] disabled:opacity-50 text-white font-semibold text-xs sm:text-sm shadow-xs transition-colors flex items-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Evaluating with Colab ML...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Submit &amp; Evaluate Competency
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
