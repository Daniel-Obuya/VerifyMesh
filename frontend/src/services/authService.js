import { api } from './api';

export const authService = {
  /**
   * Send login credentials to Flask authentication endpoint
   * @param {Object} credentials - { identifier, password, rememberMe }
   * @returns {Promise<Object>} - { success, token, user, message }
   */
  async login({ identifier, password, rememberMe = false }) {
    const data = await api.post('/auth/login', {
      email: identifier,
      identifier,
      password,
      rememberMe,
    });

    if (data?.token) {
      if (rememberMe) {
        localStorage.setItem('verifymesh_token', data.token);
        localStorage.setItem('verifymesh_user', JSON.stringify(data.user));
        localStorage.setItem('verifymesh_remember', 'true');
        sessionStorage.removeItem('verifymesh_token');
        sessionStorage.removeItem('verifymesh_user');
      } else {
        sessionStorage.setItem('verifymesh_token', data.token);
        sessionStorage.setItem('verifymesh_user', JSON.stringify(data.user));
        localStorage.removeItem('verifymesh_token');
        localStorage.removeItem('verifymesh_user');
        localStorage.removeItem('verifymesh_remember');
      }
    }

    return data;
  },

  /**
   * Request password reset instructions
   * @param {string} email
   * @returns {Promise<Object>}
   */
  async forgotPassword(email) {
    return api.post('/auth/forgot-password', { email });
  },

  /**
   * Verify token and fetch current user profile
   * @returns {Promise<Object>}
   */
  async getCurrentUser() {
    return api.get('/auth/me');
  },

  /**
   * Clear active session credentials
   */
  async logout() {
    try {
      await api.post('/auth/logout', {});
    } catch {
      // Ignore network errors during logout
    } finally {
      localStorage.removeItem('verifymesh_token');
      localStorage.removeItem('verifymesh_user');
      localStorage.removeItem('verifymesh_remember');
      sessionStorage.removeItem('verifymesh_token');
      sessionStorage.removeItem('verifymesh_user');
    }
  },

  /**
   * Retrieve cached user from browser storage
   */
  getStoredUser() {
    const userStr = localStorage.getItem('verifymesh_user') || sessionStorage.getItem('verifymesh_user');
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  },

  /**
   * Retrieve cached token
   */
  getStoredToken() {
    return localStorage.getItem('verifymesh_token') || sessionStorage.getItem('verifymesh_token');
  },

  /**
   * Authenticate using Google ID token
   * @param {string} credential - Google ID token from @react-oauth/google
   * @returns {Promise<Object>} - { success, token, user, message }
   */
  async googleLogin(credential) {
    const data = await api.post('/auth/google', { credential });
    if (data?.token) {
      localStorage.setItem('verifymesh_token', data.token);
      localStorage.setItem('verifymesh_user', JSON.stringify(data.user));
      localStorage.setItem('verifymesh_remember', 'true');
      sessionStorage.removeItem('verifymesh_token');
      sessionStorage.removeItem('verifymesh_user');
    }
    return data;
  },
};
