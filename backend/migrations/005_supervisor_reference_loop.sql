-- Migration 005: Supervisor / Manager Reference Verification Loop
-- Adds columns to agent_experience to support automated 1-click verification

ALTER TABLE `agent_experience`
  ADD COLUMN `supervisor_name` VARCHAR(150) NULL AFTER `description`,
  ADD COLUMN `supervisor_email` VARCHAR(150) NULL AFTER `supervisor_name`,
  ADD COLUMN `supervisor_phone` VARCHAR(50) NULL AFTER `supervisor_email`,
  ADD COLUMN `verification_token` VARCHAR(64) NULL AFTER `rejection_reason`,
  ADD COLUMN `token_expires_at` DATETIME NULL AFTER `verification_token`,
  ADD COLUMN `verified_via` ENUM('ADMIN','SUPERVISOR_REFERENCE','SYSTEM') DEFAULT NULL AFTER `token_expires_at`,
  ADD COLUMN `supervisor_feedback` TEXT NULL AFTER `verified_via`,
  ADD KEY `idx_exp_verification_token` (`verification_token`);
