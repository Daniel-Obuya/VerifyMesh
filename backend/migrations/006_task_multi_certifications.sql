-- Migration 006: Task Multi-Certifications Support
-- Compatible with MySQL 8.0+

CREATE TABLE IF NOT EXISTS `task_certifications` (
  `task_id` int unsigned NOT NULL,
  `certification_id` int unsigned NOT NULL,
  `is_mandatory` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`, `certification_id`),
  KEY `idx_tc_task` (`task_id`),
  KEY `idx_tc_certification` (`certification_id`),
  CONSTRAINT `fk_tc_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_tc_certification` FOREIGN KEY (`certification_id`) REFERENCES `certifications` (`certification_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Backfill from existing task requirements
INSERT IGNORE INTO `task_certifications` (`task_id`, `certification_id`, `is_mandatory`)
SELECT `task_id`, `required_certification_id`, 1
FROM `task_requirements`
WHERE `required_certification_id` IS NOT NULL;

