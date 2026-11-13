-- Migration 009: Assessment Lifecycle Statuses and Closure Reason
-- Non-destructive expansion of assessment_attempts status enum to support ABANDONED and CANCELLED states,
-- plus closure_reason for audit traceability.

SET @dbname = DATABASE();

-- 1. Modify status column to include ABANDONED and CANCELLED
ALTER TABLE assessment_attempts
  MODIFY COLUMN status ENUM('IN_PROGRESS','SUBMITTED','EXPIRED','CLOSED','ABANDONED','CANCELLED')
  COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'IN_PROGRESS';

-- 2. Add closure_reason column if not exists
SET @precheck = (
  SELECT COUNT(*) FROM information_schema.COLUMNS 
  WHERE TABLE_SCHEMA = @dbname 
    AND TABLE_NAME = 'assessment_attempts' 
    AND COLUMN_NAME = 'closure_reason'
);

SET @stmt = IF(
  @precheck = 0,
  'ALTER TABLE assessment_attempts ADD COLUMN closure_reason VARCHAR(255) NULL AFTER last_saved_at;',
  'SELECT "closure_reason already exists in assessment_attempts";'
);
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

