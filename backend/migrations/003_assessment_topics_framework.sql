-- Migration 003: Assessment Topics Framework and Task-Topic Mapping
-- Compatible with MySQL 8.0+

CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `migration_id` int unsigned NOT NULL AUTO_INCREMENT,
  `migration_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`migration_id`),
  UNIQUE KEY `uq_migration_name` (`migration_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 1. Assessment Topics Table
CREATE TABLE IF NOT EXISTS `assessment_topics` (
  `topic_id` int unsigned NOT NULL AUTO_INCREMENT,
  `topic_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` int unsigned DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `passing_score` decimal(5,2) NOT NULL DEFAULT '70.00',
  `estimated_minutes` int unsigned NOT NULL DEFAULT '10',
  `status` enum('ACTIVE','INACTIVE') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`topic_id`),
  UNIQUE KEY `uq_topic_name` (`topic_name`),
  KEY `idx_topics_category` (`category_id`),
  CONSTRAINT `fk_topics_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Task-Required Assessment Topics (Many-to-Many)
CREATE TABLE IF NOT EXISTS `task_assessment_topics` (
  `task_id` int unsigned NOT NULL,
  `topic_id` int unsigned NOT NULL,
  `is_mandatory` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`, `topic_id`),
  KEY `idx_tat_task` (`task_id`),
  KEY `idx_tat_topic` (`topic_id`),
  CONSTRAINT `fk_tat_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_tat_topic` FOREIGN KEY (`topic_id`) REFERENCES `assessment_topics` (`topic_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Stored Agent Topic Results
CREATE TABLE IF NOT EXISTS `agent_topic_results` (
  `result_id` int unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `topic_id` int unsigned NOT NULL,
  `attempt_id` int unsigned DEFAULT NULL,
  `score` decimal(5,2) NOT NULL,
  `passed` tinyint(1) NOT NULL,
  `answers_json` json DEFAULT NULL,
  `completed_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`result_id`),
  KEY `idx_atr_agent_topic_passed` (`agent_id`, `topic_id`, `passed`),
  KEY `idx_atr_agent_completed` (`agent_id`, `completed_at`),
  KEY `idx_atr_attempt` (`attempt_id`),
  CONSTRAINT `fk_atr_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_atr_topic` FOREIGN KEY (`topic_id`) REFERENCES `assessment_topics` (`topic_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_atr_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`attempt_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

