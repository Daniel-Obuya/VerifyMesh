-- Migration 008: Add assessment autosave version and timestamp
-- Non-destructive schema expansion for concurrency-controlled attempt autosave.

SET @dbname = DATABASE();

-- 1. Add answers_version to assessment_attempts
SET @precheck = (
  SELECT COUNT(*) FROM information_schema.COLUMNS 
  WHERE TABLE_SCHEMA = @dbname 
    AND TABLE_NAME = 'assessment_attempts' 
    AND COLUMN_NAME = 'answers_version'
);

SET @stmt = IF(
  @precheck = 0,
  'ALTER TABLE assessment_attempts ADD COLUMN answers_version INT NOT NULL DEFAULT 0 AFTER answers_json;',
  'SELECT "answers_version already exists in assessment_attempts";'
);
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add last_saved_at to assessment_attempts
SET @precheck2 = (
  SELECT COUNT(*) FROM information_schema.COLUMNS 
  WHERE TABLE_SCHEMA = @dbname 
    AND TABLE_NAME = 'assessment_attempts' 
    AND COLUMN_NAME = 'last_saved_at'
);

SET @stmt2 = IF(
  @precheck2 = 0,
  'ALTER TABLE assessment_attempts ADD COLUMN last_saved_at DATETIME NULL AFTER answers_version;',
  'SELECT "last_saved_at already exists in assessment_attempts";'
);
PREPARE stmt2 FROM @stmt2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

