-- Migration 002: Assessment Integrity & Attempt Verification
-- Adds assessment_attempts table for server-side attempt tracking, ownership validation,
-- expiration enforcement, and score integrity.
-- Compatible with MySQL 8.0+

CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `migration_id` int unsigned NOT NULL AUTO_INCREMENT,
  `migration_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`migration_id`),
  UNIQUE KEY `uq_migration_name` (`migration_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: assessment_attempts
CREATE TABLE IF NOT EXISTS `assessment_attempts` (
  `attempt_id` int unsigned NOT NULL AUTO_INCREMENT,
  `attempt_uuid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `agent_id` int unsigned NOT NULL,
  `exam_id` int unsigned NOT NULL,
  `task_id` int unsigned DEFAULT NULL,
  `attempt_number` int unsigned NOT NULL DEFAULT '1',
  `status` enum('IN_PROGRESS','SUBMITTED','EXPIRED','CLOSED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'IN_PROGRESS',
  `started_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime NOT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `score` decimal(5,2) DEFAULT NULL,
  `passed` tinyint(1) DEFAULT NULL,
  `answers_json` json DEFAULT NULL,
  `subscores_json` json DEFAULT NULL,
  `model_version` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exam_result_id` int unsigned DEFAULT NULL,
  `prediction_id` bigint unsigned DEFAULT NULL,
  `decision_details` json DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`attempt_id`),
  UNIQUE KEY `uq_attempt_uuid` (`attempt_uuid`),
  KEY `idx_attempts_agent` (`agent_id`),
  KEY `idx_attempts_exam` (`exam_id`),
  KEY `idx_attempts_task` (`task_id`),
  KEY `idx_attempts_status` (`status`),
  KEY `idx_attempts_agent_exam_status` (`agent_id`, `exam_id`, `status`),
  KEY `idx_attempts_exam_result` (`exam_result_id`),
  KEY `idx_attempts_prediction` (`prediction_id`),
  CONSTRAINT `fk_attempts_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_attempts_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_attempts_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_attempts_exam_result` FOREIGN KEY (`exam_result_id`) REFERENCES `exam_results` (`exam_result_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_attempts_prediction` FOREIGN KEY (`prediction_id`) REFERENCES `ml_predictions` (`prediction_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
