import { api } from './api';

export const competencyService = {
  /**
   * Send agent features to Flask backend for inference using the 3-way decision model
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
};
