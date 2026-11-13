-- VerifyMesh Migration: 007_assessment_snapshots_and_attempt_limits
-- Adds max_attempts to assessment_topics, question_snapshot_json to assessment_attempts, and status to exam_questions.

-- 1. Add max_attempts to assessment_topics if not present
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_topics' AND COLUMN_NAME = 'max_attempts'
);
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `assessment_topics` ADD COLUMN `max_attempts` int unsigned NOT NULL DEFAULT 3 AFTER `estimated_minutes`',
    'SELECT "max_attempts already exists in assessment_topics"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add question_snapshot_json to assessment_attempts if not present
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_attempts' AND COLUMN_NAME = 'question_snapshot_json'
);
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `assessment_attempts` ADD COLUMN `question_snapshot_json` json NULL DEFAULT NULL AFTER `subscores_json`',
    'SELECT "question_snapshot_json already exists in assessment_attempts"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3. Add status to exam_questions if not present
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'exam_questions' AND COLUMN_NAME = 'status'
);
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `exam_questions` ADD COLUMN `status` enum("ACTIVE","INACTIVE","DRAFT") NOT NULL DEFAULT "ACTIVE" AFTER `options_json`',
    'SELECT "status already exists in exam_questions"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

