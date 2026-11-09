import { api } from './api';
import { adminService } from './adminService';

/**
 * Workforce Officer Service Gateway
 * Provides clean semantic domain methods for managing the workforce recruitment,
 * credential verification, task lifecycle, and applicant qualification pipeline.
 * Wraps and extends administrative endpoints for complete backward compatibility.
 */
export const workforceService = {
  // --- Operational Overview & Telemetry ---
  getOverview: () => adminService.getOverview(),

  // --- Agent Directory & Profiles ---
  getAgents: () => adminService.getAgents(),
  getAgentProfile: (agentId) => adminService.getAgentProfile(agentId),

  // --- Task Management Lifecycle ---
  getTasks: () => adminService.getTasks(),
  getTaskMetadata: () => adminService.getTaskMetadata(),
  getTask: (taskId) => adminService.getTask(taskId),
  createTask: (taskData) => adminService.createTask(taskData),
  updateTask: (taskId, taskData) => adminService.updateTask(taskId, taskData),
  setTaskStatus: (taskId, status) => adminService.setTaskStatus(taskId, status),
  deleteTask: (taskId) => adminService.deleteTask(taskId),

  // --- Assessment & Attempt Audit ---
  getAssessments: () => adminService.getAssessments(),

  // --- Eligibility Reviews ---
  getReviews: () => adminService.getReviews(),
  getReviewDetail: (evaluationId) => adminService.getReviewDetail(evaluationId),
  submitReviewAction: (evaluationId, decision, comments) =>
    adminService.submitReviewAction(evaluationId, decision, comments),

  // --- Credential & Experience Verifications ---
  getPendingVerifications: () => adminService.getPendingVerifications(),
  reviewCertification: (certId, decision, rejectionReason) =>
    adminService.reviewCertification(certId, decision, rejectionReason),
  reviewExperience: (expId, decision, rejectionReason) =>
    adminService.reviewExperience(expId, decision, rejectionReason),

  // --- Task Applications & Human-in-the-Loop Allocation ---
  getTaskApplicants: (taskId) => adminService.getTaskApplicants(taskId),
  assignTaskApplication: (applicationId) => adminService.assignTaskApplication(applicationId),
  updateApplicationStatus: (applicationId, status, notes) =>
    adminService.updateApplicationStatus(applicationId, status, notes),
};

export default workforceService;

