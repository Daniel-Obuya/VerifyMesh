import { api } from './api';

export const adminService = {
  /**
   * Fetch aggregate KPI metrics, active ML model runtime status, and recent assessments
   * @returns {Promise<Object>}
   */
  async getOverview() {
    return api.get('/admin/overview');
  },

  /**
   * Fetch full directory of agents with total attempts and latest competency assessment
   * @returns {Promise<Object>}
   */
  async getAgents() {
    return api.get('/admin/agents');
  },

  /**
   * Fetch full profile of an agent including verified experience, certs, and assessments
   * @param {number|string} agentId
   * @returns {Promise<Object>}
   */
  async getAgentProfile(agentId) {
    return api.get(`/admin/agents/${agentId}/profile`);
  },

  /**
   * Fetch all tasks with category and configured eligibility requirements
   * @returns {Promise<Object>}
   */
  async getTasks() {
    return api.get('/admin/tasks');
  },

  /**
   * Fetch category, certification, and skill lookup lists for task forms
   * @returns {Promise<Object>}
   */
  async getTaskMetadata() {
    return api.get('/admin/tasks/metadata');
  },

  /**
   * Fetch complete details of a single task
   * @param {number|string} taskId
   * @returns {Promise<Object>}
   */
  async getTask(taskId) {
    return api.get(`/admin/tasks/${taskId}`);
  },

  /**
   * Create a new task and its eligibility requirements
   * @param {Object} taskData
   * @returns {Promise<Object>}
   */
  async createTask(taskData) {
    return api.post('/admin/tasks', taskData);
  },

  /**
   * Update an existing task and its eligibility requirements
   * @param {number|string} taskId
   * @param {Object} taskData
   * @returns {Promise<Object>}
   */
  async updateTask(taskId, taskData) {
    return api.put(`/admin/tasks/${taskId}`, taskData);
  },

  /**
   * Update task lifecycle status (e.g. ACTIVE, INACTIVE, DRAFT, COMPLETED)
   * @param {number|string} taskId
   * @param {string} status
   * @returns {Promise<Object>}
   */
  async setTaskStatus(taskId, status) {
    return api.patch(`/admin/tasks/${taskId}/status`, { status });
  },

  /**
   * Delete a task and its associated configurations permanently
   * @param {number|string} taskId
   * @returns {Promise<Object>}
   */
  async deleteTask(taskId) {
    return api.delete(`/admin/tasks/${taskId}`);
  },

  /**
   * Fetch historical assessments across all agents with predictions and scores
   * @returns {Promise<Object>}
   */
  async getAssessments() {
    return api.get('/admin/assessments');
  },

  /**
   * Fetch eligibility evaluations list from v_eligibility_summary view
   * @returns {Promise<Object>}
   */
  async getReviews() {
    return api.get('/admin/reviews');
  },

  /**
   * Fetch detailed breakdown of an eligibility evaluation including criteria checks
   * @param {number|string} evaluationId
   * @returns {Promise<Object>}
   */
  async getReviewDetail(evaluationId) {
    return api.get(`/admin/reviews/${evaluationId}`);
  },

  /**
   * Submit Workforce Officer decision (APPROVED|REJECTED) on an eligibility evaluation
   * @param {number|string} evaluationId
   * @param {'APPROVED'|'REJECTED'} decision
   * @param {string} [comments]
   * @returns {Promise<Object>}
   */
  async submitReviewAction(evaluationId, decision, comments = '') {
    return api.post(`/admin/reviews/${evaluationId}/review`, { decision, comments });
  },

  /**
   * Fetch pending verification requests for agent certifications and work experience
   * @returns {Promise<Object>}
   */
  async getPendingVerifications() {
    return api.get('/admin/verifications');
  },

  /**
   * Approve or reject an agent certification submission
   * @param {number|string} certId
   * @param {'VERIFIED'|'REJECTED'} decision
   * @param {string} [rejectionReason]
   * @returns {Promise<Object>}
   */
  async reviewCertification(certId, decision, rejectionReason) {
    return api.post(`/admin/verifications/certifications/${certId}/review`, {
      decision,
      rejection_reason: rejectionReason,
    });
  },

  /**
   * Approve or reject an agent work experience submission
   * @param {number|string} expId
   * @param {'VERIFIED'|'REJECTED'} decision
   * @param {string} [rejectionReason]
   * @returns {Promise<Object>}
   */
  async reviewExperience(expId, decision, rejectionReason) {
    return api.post(`/admin/verifications/experiences/${expId}/review`, {
      decision,
      rejection_reason: rejectionReason,
    });
  },

  /**
   * Fetch applicants for a task with verified requirements fulfillment
   * @param {number|string} taskId
   * @returns {Promise<Object>}
   */
  async getTaskApplicants(taskId) {
    return api.get(`/admin/tasks/${taskId}/applications`);
  },

  /**
   * Assign an applicant to a task after verifying eligibility
   * @param {number|string} applicationId
   * @returns {Promise<Object>}
   */
  async assignTaskApplication(applicationId, data = {}) {
    return api.post(`/admin/applications/${applicationId}/assign`, data);
  },

  /**
   * Update status of an application (e.g. Shortlisted, Rejected, Under Review)
   * @param {number|string} applicationId
   * @param {string} status
   * @param {string} [notes]
   * @returns {Promise<Object>}
   */
  async updateApplicationStatus(applicationId, status, notes) {
    return api.post(`/admin/applications/${applicationId}/status`, {
      status,
      notes,
    });
  },

  /**
   * Apply administrative exception/override to an agent's assessment attempt or topic limit
   * @param {number|string} agentId
   * @param {Object} data { topic_id, action, reason, attempt_id }
   * @returns {Promise<Object>}
   */
  async overrideAssessmentAttempt(agentId, data) {
    return api.post(`/admin/agents/${agentId}/assessment-override`, data);
  },

  /**
   * Fetch complete assessment attempt history for an agent
   * @param {number|string} agentId
   * @param {number|string} [topicId]
   * @returns {Promise<Object>}
   */
  async getAgentAssessmentHistory(agentId, topicId = null) {
    const params = topicId ? `?topic_id=${topicId}` : '';
    return api.get(`/admin/agents/${agentId}/assessment-history${params}`);
  },
};
