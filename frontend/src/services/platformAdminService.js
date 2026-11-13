import { api } from './api';

const buildQuery = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      qs.append(key, String(val));
    }
  });
  const str = qs.toString();
  return str ? `?${str}` : '';
};

export const platformAdminService = {
  /**
   * Fetch platform overview KPIs, user counts, real trends, and system status
   */
  async getOverview(params = {}) {
    return api.get(`/platform-admin/overview${buildQuery(params)}`);
  },

  /**
   * Fetch paginated users list with search, role, and status filters
   */
  async getUsers(params = {}) {
    return api.get(`/platform-admin/users${buildQuery(params)}`);
  },

  /**
   * Fetch individual user profile, verification summary, and recent actions
   */
  async getUserProfile(userId) {
    return api.get(`/platform-admin/users/${userId}`);
  },

  /**
   * Update a user's role (AGENT, WORKFORCE_OFFICER, PLATFORM_ADMIN)
   */
  async updateUserRole(userId, role) {
    return api.patch(`/platform-admin/users/${userId}/role`, { role });
  },

  /**
   * Toggle a user account active/suspended status
   */
  async updateUserStatus(userId, isActive) {
    return api.patch(`/platform-admin/users/${userId}/status`, { is_active: isActive });
  },

  /**
   * Fetch paginated audit events with filters
   */
  async getAuditLogs(params = {}) {
    return api.get(`/platform-admin/audit-logs${buildQuery(params)}`);
  },

  /**
   * Fetch system and database health telemetry
   */
  async getSystemHealth() {
    return api.get('/platform-admin/system-health');
  },

  /**
   * Fetch ML model v3 technical specifications, metadata metrics, and production usage
   */
  async getMlModelGovernance() {
    return api.get('/platform-admin/ml-model');
  },

  /**
   * Fetch historical assessments and AI inference logs for platform audit
   */
  async getAssessments() {
    return api.get('/admin/assessments');
  }
};
