import { api } from './api';

export const competencyService = {
  /**
   * Send agent features to Flask backend for inference using the binary eligibility model
   * @param {Object} agentData
   * @returns {Promise<Object>}
   */
  async predictCompetency(agentData) {
    return api.post('/competency/evaluate', agentData);
  },

  /**
   * Evaluate eligibility endpoint alias
   * @param {Object} agentData
   * @returns {Promise<Object>}
   */
  async evaluateEligibility(agentData) {
    return api.post('/competency/evaluate', agentData);
  },

  /**
   * Fetch active model metadata and load status
   * @returns {Promise<Object>}
   */
  async getModelInfo() {
    return api.get('/competency/model-info');
  },

  /**
   * Fetch pre-configured sample inputs
   * @returns {Promise<Object>}
   */
  async getSampleInputs() {
    return api.get('/competency/sample-inputs');
  },

  /**
   * Check whether the logged in agent has completed an assessment
   * @param {number|string} [userId]
   * @returns {Promise<Object>}
   */
  async getAgentStatus() {
    // Identity is resolved server-side from the Bearer token; no user_id param sent.
    return api.get('/competency/agent-status');
  },

  /**
   * Reset assessment back to unassessed state (for demo/testing)
   * Identity is resolved from the Bearer token; no body payload needed.
   * @returns {Promise<Object>}
   */
  async resetAssessment() {
    return api.post('/competency/reset-assessment', {});
  },

  /**
   * Fetch questions and exam metadata for a specific exam
   * @param {number|string} examId
   * @returns {Promise<Object>}
   */
  async getExamQuestions(examId) {
    return api.get(`/competency/exams/${examId}/questions`);
  },

  /**
   * Explicitly initiate an authoritative assessment attempt for a specific exam
   * @param {number|string} examId
   * @param {number|string} [taskId] - optional task ID being qualified for
   * @returns {Promise<Object>}
   */
  async startExamAttempt(examId, taskId = null) {
    return api.post(`/competency/exams/${examId}/start-attempt`, { task_id: taskId });
  },

  /**
   * Submit exam answers for server-side scoring, ML evaluation, and eligibility persistence.
   * Only question IDs and selected option IDs are submitted, never scores or subscores.
   * @param {number|string} examId
   * @param {Object} answers - mapping of question_id -> option ID ("A".."D")
   * @param {number|string} [taskId] - optional task ID being qualified for
   * @param {number|string} [attemptId] - authoritative attempt ID
   * @returns {Promise<Object>}
   */
  async submitExam(examId, answers, taskId = null, attemptId = null) {
    return api.post(`/competency/exams/${examId}/submit`, { 
      attempt_id: attemptId,
      answers, 
      task_id: taskId 
    });
  },

  /**
   * Fetch active tasks with server-calculated eligibility and application statuses
   * @returns {Promise<Object>}
   */
  async getAgentTasks() {
    return api.get('/competency/tasks');
  },

  /**
   * Submit an application for an eligible task
   * @param {number|string} taskId
   * @param {string} [notes]
   * @returns {Promise<Object>}
   */
  async applyForTask(taskId, notes = '') {
    return api.post(`/competency/tasks/${taskId}/apply`, { notes });
  },

  /**
   * Fetch genuine chronological activity records for the agent
   * @returns {Promise<Object>}
   */
  async getAgentActivities() {
    return api.get('/competency/activities');
  },

  /**
   * Fetch authenticated agent full profile, verified experience, and certs
   * @returns {Promise<Object>}
   */
  async getProfile() {
    return api.get('/competency/profile');
  },

  /**
   * Update personal profile information
   * @param {Object} data - { full_name, phone, location, bio }
   * @returns {Promise<Object>}
   */
  async updateProfile(data) {
    return api.put('/competency/profile', data);
  },

  /**
   * Fetch agent work-history records
   * @returns {Promise<Object>}
   */
  async getExperiences() {
    return api.get('/competency/experiences');
  },

  /**
   * Submit a new work-history entry for verification
   * @param {Object} data - { job_title, company, work_category, start_date, end_date, is_current, description }
   * @returns {Promise<Object>}
   */
  async addExperience(data) {
    return api.post('/competency/experiences', data);
  },

  /**
   * Withdraw or delete a pending/rejected work-history entry
   * @param {number|string} experienceId
   * @returns {Promise<Object>}
   */
  async deleteExperience(experienceId) {
    return api.delete(`/competency/experiences/${experienceId}`);
  },

  /**
   * Resend the supervisor verification email
   * @param {number|string} experienceId
   * @returns {Promise<Object>}
   */
  async resendSupervisorEmail(experienceId) {
    return api.post(`/competency/experiences/${experienceId}/resend`);
  },

  /**
   * Public: Fetch details of a work experience record using verification token
   * @param {string} token
   * @returns {Promise<Object>}
   */
  async getPublicExperienceVerification(token) {
    return api.get(`/competency/public/verify-experience/${token}`);
  },

  /**
   * Public: Submit supervisor confirmation or dispute
   * @param {string} token
   * @param {Object} data - { decision: 'CONFIRM'|'DISPUTE', feedback, answers }
   * @returns {Promise<Object>}
   */
  async submitPublicExperienceVerification(token, data) {
    return api.post(`/competency/public/verify-experience/${token}`, data);
  },

  /**
   * Fetch agent certification records
   * @returns {Promise<Object>}
   */
  async getCertifications() {
    return api.get('/competency/certifications');
  },

  /**
   * Submit a new certification for verification
   * @param {Object} data - { certification_id, certification_name, issuing_organization, certificate_number, credential_url, issue_date, expiry_date }
   * @returns {Promise<Object>}
   */
  async addCertification(data) {
    return api.post('/competency/certifications', data);
  },

  /**
   * Withdraw or delete a pending/rejected certification
   * @param {number|string} certId
   * @returns {Promise<Object>}
   */
  async deleteCertification(certId) {
    return api.delete(`/competency/certifications/${certId}`);
  },

  /**
   * Fetch all active competency assessment topics
   * @returns {Promise<Object>}
   */
  async getTopics() {
    return api.get('/competency/topics');
  },

  /**
   * Fetch specific topic details
   * @param {number|string} topicId
   * @returns {Promise<Object>}
   */
  async getTopicDetail(topicId) {
    return api.get(`/competency/topics/${topicId}`);
  },

  /**
   * Fetch questions for a specific topic (correct answers omitted on backend)
   * @param {number|string} topicId
   * @param {number|string} [attemptId]
   * @returns {Promise<Object>}
   */
  async getTopicQuestions(topicId, attemptId = null) {
    const query = attemptId ? `?attempt_id=${attemptId}` : '';
    return api.get(`/competency/topics/${topicId}/questions${query}`);
  },

  /**
   * Explicitly start an attempt for a specific topic
   * @param {number|string} topicId
   * @param {number|string} [taskId]
   * @returns {Promise<Object>}
   */
  async startTopicAttempt(topicId, taskId = null) {
    return api.post(`/competency/topics/${topicId}/start-attempt`, { task_id: taskId });
  },

  /**
   * Autosave intermediate draft answers for an active assessment attempt.
   * Uses monotonic revision versioning to prevent race condition overwrites.
   * @param {number|string} topicId
   * @param {number|string} attemptId
   * @param {Object} answers - mapping of question_id -> option letter ('A'..'D')
   * @param {number} [version=0]
   * @returns {Promise<Object>}
   */
  async autosaveTopicAnswers(topicId, attemptId, answers, version = 0) {
    return api.post(`/competency/topics/${topicId}/autosave`, {
      attempt_id: attemptId,
      answers,
      version,
    });
  },

  /**
   * Submit answers for a specific topic assessment.
   * Graded strictly on the server; updates ML prediction and task eligibility.
   * @param {number|string} topicId
   * @param {Object} answers - mapping of question_id -> option letter ('A'..'D')
   * @param {number|string} [taskId]
   * @param {number|string} [attemptId]
   * @returns {Promise<Object>}
   */
  async submitTopicExam(topicId, answers, taskId = null, attemptId = null) {
    return api.post(`/competency/topics/${topicId}/submit`, {
      attempt_id: attemptId,
      answers,
      task_id: taskId,
    });
  },

  /**
   * Fetch stored attempt result and evaluated task eligibility
   * @param {number|string} attemptId
   * @returns {Promise<Object>}
   */
  async getAttemptDetails(attemptId) {
    return api.get(`/competency/attempts/${attemptId}`);
  },

  /**
   * Explicitly abandon an in-progress assessment attempt.
   * @param {number|string} topicId
   * @param {number|string} attemptId
   * @param {string} [reason]
   * @returns {Promise<Object>}
   */
  async abandonTopicAttempt(topicId, attemptId, reason = 'Candidate abandoned assessment') {
    return api.post(`/competency/topics/${topicId}/abandon`, {
      attempt_id: attemptId,
      reason,
    });
  },

  /**
   * Fetch historical attempts for the authenticated agent on a topic.
   * @param {number|string} topicId
   * @returns {Promise<Object>}
   */
  async getTopicAttemptHistory(topicId) {
    return api.get(`/competency/topics/${topicId}/history`);
  },

  /**
   * Fetch single task with evaluated topic requirements
   * @param {number|string} taskId
   * @returns {Promise<Object>}
   */
  async getTaskDetails(taskId) {
    return api.get(`/competency/tasks/${taskId}`);
  },

  /**
   * Fetch all submitted task applications and live assignment statuses for the authenticated agent
   * @returns {Promise<Object>}
   */
  async getAgentApplications() {
    return api.get('/competency/applications');
  },
};
