import { api } from './api';

export const competencyService = {
  /**
   * Send agent features to Flask backend for inference using Google Colab model
   * @param {Object} agentData
   * @returns {Promise<Object>}
   */
  async predictCompetency(agentData) {
    return api.post('/competency/predict', agentData);
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
  async getAgentStatus(userId) {
    const query = userId ? `?user_id=${userId}` : '';
    return api.get(`/competency/agent-status${query}`);
  },

  /**
   * Reset assessment back to unassessed state (for demo/testing)
   * @param {number|string} [userId]
   * @returns {Promise<Object>}
   */
  async resetAssessment(userId) {
    return api.post('/competency/reset-assessment', { user_id: userId });
  },
};
