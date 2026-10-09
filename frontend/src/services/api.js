/**
 * VerifyMesh API Client
 * Provides a clean abstraction for calling the Flask REST API.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  getAuthHeader() {
    const token = localStorage.getItem('verifymesh_token') || sessionStorage.getItem('verifymesh_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeader(),
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const contentType = response.headers.get('content-type');
      let data = null;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        data = { message: text };
      }

      if (!response.ok) {
        const errorMessage = data?.error || data?.message || `Request failed with status ${response.status}`;
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        // Network connection error
        const netErr = new Error('Unable to connect to VerifyMesh server. Please verify the backend is running.');
        netErr.status = 503;
        throw netErr;
      }
      throw err;
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { method: 'GET', ...options });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
      ...options,
    });
  }
}

export const api = new ApiClient(API_BASE_URL);
