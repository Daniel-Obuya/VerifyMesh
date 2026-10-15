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
};
