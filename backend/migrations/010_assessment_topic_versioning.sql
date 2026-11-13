-- Migration 010: Assessment Topic Versioning
-- Adds version to assessment_topics and topic_version to assessment_attempts
-- to guarantee that historical attempts remain locked to their exact configuration version.

SET @dbname = DATABASE();

-- 1. Add version to assessment_topics
SET @precheck = (
  SELECT COUNT(*) FROM information_schema.COLUMNS 
  WHERE TABLE_SCHEMA = @dbname 
    AND TABLE_NAME = 'assessment_topics' 
    AND COLUMN_NAME = 'version'
);

SET @stmt = IF(
  @precheck = 0,
  'ALTER TABLE assessment_topics ADD COLUMN version INT UNSIGNED NOT NULL DEFAULT 1 AFTER status;',
  'SELECT "version already exists in assessment_topics";'
);
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add topic_version to assessment_attempts
SET @precheck2 = (
  SELECT COUNT(*) FROM information_schema.COLUMNS 
  WHERE TABLE_SCHEMA = @dbname 
    AND TABLE_NAME = 'assessment_attempts' 
    AND COLUMN_NAME = 'topic_version'
);

SET @stmt2 = IF(
  @precheck2 = 0,
  'ALTER TABLE assessment_attempts ADD COLUMN topic_version INT UNSIGNED NOT NULL DEFAULT 1 AFTER closure_reason;',
  'SELECT "topic_version already exists in assessment_attempts";'
);
PREPARE stmt2 FROM @stmt2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

