-- Migration 004: Binary Eligibility Alignment
-- Extends ml_predictions and task_requirements to support binary classification (ELIGIBLE / NOT_ELIGIBLE)
-- Preserves legacy values for backward compatibility and historical record safety.

-- 1. Extend ml_predictions.predicted_competency ENUM
ALTER TABLE `ml_predictions`
  MODIFY COLUMN `predicted_competency` ENUM('ELIGIBLE', 'NOT_ELIGIBLE', 'NEEDS_IMPROVEMENT', 'BASIC', 'COMPETENT', 'ADVANCED') 
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

-- 2. Extend task_requirements.minimum_competency ENUM
ALTER TABLE `task_requirements`
  MODIFY COLUMN `minimum_competency` ENUM('ELIGIBLE', 'NOT_ELIGIBLE', 'NEEDS_IMPROVEMENT', 'BASIC', 'COMPETENT', 'ADVANCED') 
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ELIGIBLE';

-- 3. Update existing task requirements to require ELIGIBLE competency standard
UPDATE `task_requirements` SET `minimum_competency` = 'ELIGIBLE';
