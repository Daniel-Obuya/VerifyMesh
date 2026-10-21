-- VerifyMesh Complete Database Schema
-- Compatible with MySQL 8.0+

CREATE DATABASE IF NOT EXISTS verifymesh_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE verifymesh_db;

-- Table: agent_categories
CREATE TABLE IF NOT EXISTS `agent_categories` (
  `agent_id` int unsigned NOT NULL,
  `category_id` int unsigned NOT NULL,
  `joined_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`agent_id`,`category_id`),
  KEY `idx_agent_categories_category` (`category_id`),
  CONSTRAINT `fk_agent_categories_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_agent_categories_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: agent_certifications
CREATE TABLE IF NOT EXISTS `agent_certifications` (
  `agent_certification_id` int unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `certification_id` int unsigned NOT NULL,
  `certificate_number` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `issuing_organization` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `credential_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issue_date` date NOT NULL,
  `expiry_date` date DEFAULT NULL,
  `status` enum('PENDING','VERIFIED','REJECTED','EXPIRED','ACTIVE','REVOKED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `rejection_reason` text COLLATE utf8mb4_unicode_ci,
  `reviewed_by` int unsigned DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`agent_certification_id`),
  UNIQUE KEY `certificate_number` (`certificate_number`),
  KEY `idx_agent_certifications_agent` (`agent_id`),
  KEY `idx_agent_certifications_certification` (`certification_id`),
  KEY `idx_agent_certifications_status` (`status`),
  CONSTRAINT `fk_agent_certifications_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_agent_certifications_certification` FOREIGN KEY (`certification_id`) REFERENCES `certifications` (`certification_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_certification_dates` CHECK (((`expiry_date` is null) or (`expiry_date` >= `issue_date`)))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: agent_experience
CREATE TABLE IF NOT EXISTS `agent_experience` (
  `experience_id` int unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `job_title` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `company` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `work_category` enum('Sales','Customer Service','Other') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Other',
  `description` text COLLATE utf8mb4_unicode_ci,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `is_current` tinyint(1) NOT NULL DEFAULT '0',
  `verification_status` enum('PENDING','VERIFIED','REJECTED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `rejection_reason` text COLLATE utf8mb4_unicode_ci,
  `reviewed_by` int unsigned DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`experience_id`),
  KEY `idx_agent_exp` (`agent_id`),
  KEY `idx_agent_exp_status` (`agent_id`,`verification_status`),
  KEY `fk_agent_experience_reviewer` (`reviewed_by`),
  CONSTRAINT `fk_agent_experience_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_agent_experience_reviewer` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: agent_skills
CREATE TABLE IF NOT EXISTS `agent_skills` (
  `agent_id` int unsigned NOT NULL,
  `skill_id` int unsigned NOT NULL,
  `skill_score` decimal(5,2) NOT NULL,
  `assessed_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`agent_id`,`skill_id`),
  KEY `idx_agent_skills_skill` (`skill_id`),
  CONSTRAINT `fk_agent_skills_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_agent_skills_skill` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`skill_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_agent_skill_score` CHECK (((`skill_score` >= 0) and (`skill_score` <= 100)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: agents
CREATE TABLE IF NOT EXISTS `agents` (
  `agent_id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `phone` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `education` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bio` text COLLATE utf8mb4_unicode_ci,
  `location` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `experience_months` int unsigned NOT NULL DEFAULT '0',
  `availability_status` enum('AVAILABLE','UNAVAILABLE','PARTIALLY_AVAILABLE') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'AVAILABLE',
  `status` enum('ACTIVE','INACTIVE','SUSPENDED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`agent_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_agents_status` (`status`),
  KEY `idx_agents_availability` (`availability_status`),
  CONSTRAINT `fk_agents_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: audit_logs
CREATE TABLE IF NOT EXISTS `audit_logs` (
  `log_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned DEFAULT NULL,
  `action` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity_id` bigint unsigned DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `idx_audit_user` (`user_id`),
  KEY `idx_audit_action` (`action`),
  KEY `idx_audit_entity` (`entity_type`,`entity_id`),
  KEY `idx_audit_created` (`created_at`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=63 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: categories
CREATE TABLE IF NOT EXISTS `categories` (
  `category_id` int unsigned NOT NULL AUTO_INCREMENT,
  `category_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `category_name` (`category_name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: certifications
CREATE TABLE IF NOT EXISTS `certifications` (
  `certification_id` int unsigned NOT NULL AUTO_INCREMENT,
  `category_id` int unsigned NOT NULL,
  `certification_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `validity_period_months` int unsigned DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`certification_id`),
  UNIQUE KEY `uq_certification_category_name` (`category_id`,`certification_name`),
  KEY `idx_certifications_category` (`category_id`),
  CONSTRAINT `fk_certifications_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: eligibility_checks
CREATE TABLE IF NOT EXISTS `eligibility_checks` (
  `check_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `evaluation_id` bigint unsigned NOT NULL,
  `requirement_type` enum('COMPETENCY','CERTIFICATION','EXPERIENCE','SKILL','EXAM') COLLATE utf8mb4_unicode_ci NOT NULL,
  `expected_value` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `actual_value` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `passed` tinyint(1) NOT NULL,
  `failure_reason` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`check_id`),
  KEY `idx_eligibility_checks_evaluation` (`evaluation_id`),
  KEY `idx_eligibility_checks_type` (`requirement_type`),
  KEY `idx_eligibility_checks_passed` (`passed`),
  CONSTRAINT `fk_eligibility_checks_evaluation` FOREIGN KEY (`evaluation_id`) REFERENCES `eligibility_evaluations` (`evaluation_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: eligibility_evaluations
CREATE TABLE IF NOT EXISTS `eligibility_evaluations` (
  `evaluation_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `task_id` int unsigned NOT NULL,
  `prediction_id` bigint unsigned DEFAULT NULL,
  `eligibility_status` enum('ELIGIBLE','NOT_ELIGIBLE','PENDING_REVIEW') COLLATE utf8mb4_unicode_ci NOT NULL,
  `explanation` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `review_status` enum('NOT_REQUIRED','PENDING','APPROVED','REJECTED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'NOT_REQUIRED',
  `reviewer_id` int unsigned DEFAULT NULL,
  `review_comments` text COLLATE utf8mb4_unicode_ci,
  `evaluated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`evaluation_id`),
  KEY `idx_eligibility_agent` (`agent_id`),
  KEY `idx_eligibility_task` (`task_id`),
  KEY `idx_eligibility_prediction` (`prediction_id`),
  KEY `idx_eligibility_status` (`eligibility_status`),
  KEY `idx_eligibility_review_status` (`review_status`),
  KEY `idx_eligibility_reviewer` (`reviewer_id`),
  CONSTRAINT `fk_eligibility_evaluations_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_eligibility_evaluations_prediction` FOREIGN KEY (`prediction_id`) REFERENCES `ml_predictions` (`prediction_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_eligibility_evaluations_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_eligibility_evaluations_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_review_date` CHECK (((`reviewed_at` is null) or (`reviewed_at` >= `evaluated_at`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: email_verifications
CREATE TABLE IF NOT EXISTS `email_verifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `code` varchar(6) NOT NULL,
  `expires_at` datetime NOT NULL,
  `used` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_email_code` (`email`,`code`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: exam_questions
CREATE TABLE IF NOT EXISTS `exam_questions` (
  `question_id` int unsigned NOT NULL AUTO_INCREMENT,
  `exam_id` int unsigned NOT NULL,
  `question_text` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_type` enum('MULTIPLE_CHOICE','TRUE_FALSE') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'MULTIPLE_CHOICE',
  `points` decimal(6,2) NOT NULL DEFAULT '1.00',
  `correct_answer` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `options_json` json DEFAULT NULL,
  `question_order` int unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`question_id`),
  UNIQUE KEY `uq_exam_question_order` (`exam_id`,`question_order`),
  KEY `idx_exam_questions_exam` (`exam_id`),
  CONSTRAINT `fk_exam_questions_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_question_points` CHECK ((`points` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
  CONSTRAINT `fk_attempts_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: exam_results
CREATE TABLE IF NOT EXISTS `exam_results` (
  `exam_result_id` int unsigned NOT NULL AUTO_INCREMENT,
  `attempt_id` int unsigned DEFAULT NULL,
  `exam_id` int unsigned NOT NULL,
  `agent_id` int unsigned NOT NULL,
  `assessment_score` decimal(5,2) NOT NULL,
  `passed` tinyint(1) NOT NULL,
  `attempt_number` int unsigned NOT NULL DEFAULT '1',
  `completed_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`exam_result_id`),
  UNIQUE KEY `uq_agent_exam_attempt` (`agent_id`,`exam_id`,`attempt_number`),
  KEY `idx_exam_results_agent` (`agent_id`),
  KEY `idx_exam_results_exam` (`exam_id`),
  KEY `idx_exam_results_passed` (`passed`),
  KEY `idx_exam_results_attempt` (`attempt_id`),
  CONSTRAINT `fk_exam_results_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_exam_results_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_exam_attempt_number` CHECK ((`attempt_number` >= 1)),
  CONSTRAINT `chk_exam_result_score` CHECK (((`assessment_score` >= 0) and (`assessment_score` <= 100)))
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: exams
CREATE TABLE IF NOT EXISTS `exams` (
  `exam_id` int unsigned NOT NULL AUTO_INCREMENT,
  `category_id` int unsigned NOT NULL,
  `exam_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `passing_score` decimal(5,2) NOT NULL DEFAULT '70.00',
  `status` enum('ACTIVE','INACTIVE','DRAFT') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`exam_id`),
  KEY `idx_exams_category` (`category_id`),
  KEY `idx_exams_status` (`status`),
  CONSTRAINT `fk_exams_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_exam_passing_score` CHECK (((`passing_score` >= 0) and (`passing_score` <= 100)))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: ml_models
CREATE TABLE IF NOT EXISTS `ml_models` (
  `model_id` int unsigned NOT NULL AUTO_INCREMENT,
  `model_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_version` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `algorithm` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_set_version` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accuracy` decimal(6,4) DEFAULT NULL,
  `macro_f1` decimal(6,4) DEFAULT NULL,
  `training_date` datetime DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`model_id`),
  UNIQUE KEY `uq_model_version` (`model_name`,`model_version`),
  KEY `idx_ml_models_active` (`is_active`),
  CONSTRAINT `chk_model_accuracy` CHECK (((`accuracy` is null) or ((`accuracy` >= 0) and (`accuracy` <= 1)))),
  CONSTRAINT `chk_model_macro_f1` CHECK (((`macro_f1` is null) or ((`macro_f1` >= 0) and (`macro_f1` <= 1))))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: ml_predictions
CREATE TABLE IF NOT EXISTS `ml_predictions` (
  `prediction_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `model_id` int unsigned NOT NULL,
  `exam_result_id` int unsigned DEFAULT NULL,
  `predicted_competency` enum('ELIGIBLE','NOT_ELIGIBLE','NEEDS_IMPROVEMENT','BASIC','COMPETENT','ADVANCED') COLLATE utf8mb4_unicode_ci NOT NULL,
  `confidence` decimal(6,4) DEFAULT NULL,
  `predicted_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`prediction_id`),
  KEY `idx_ml_predictions_agent` (`agent_id`),
  KEY `idx_ml_predictions_model` (`model_id`),
  KEY `idx_ml_predictions_exam_result` (`exam_result_id`),
  KEY `idx_ml_predictions_competency` (`predicted_competency`),
  CONSTRAINT `fk_ml_predictions_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ml_predictions_exam_result` FOREIGN KEY (`exam_result_id`) REFERENCES `exam_results` (`exam_result_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_ml_predictions_model` FOREIGN KEY (`model_id`) REFERENCES `ml_models` (`model_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_prediction_confidence` CHECK (((`confidence` is null) or ((`confidence` >= 0) and (`confidence` <= 1))))
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: skills
CREATE TABLE IF NOT EXISTS `skills` (
  `skill_id` int unsigned NOT NULL AUTO_INCREMENT,
  `category_id` int unsigned NOT NULL,
  `skill_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`skill_id`),
  UNIQUE KEY `uq_skill_category_name` (`category_id`,`skill_name`),
  KEY `idx_skills_category` (`category_id`),
  CONSTRAINT `fk_skills_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: task_applications
CREATE TABLE IF NOT EXISTS `task_applications` (
  `application_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `task_id` int unsigned NOT NULL,
  `status` enum('Not Applied','Application Submitted','Under Review','Shortlisted','Assigned','Rejected','Withdrawn') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Application Submitted',
  `applied_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`application_id`),
  UNIQUE KEY `uq_agent_task` (`agent_id`,`task_id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `task_applications_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE,
  CONSTRAINT `task_applications_ibfk_2` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: task_recommendations
CREATE TABLE IF NOT EXISTS `task_recommendations` (
  `recommendation_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `task_id` int unsigned NOT NULL,
  `evaluation_id` bigint unsigned NOT NULL,
  `recommendation_score` decimal(6,4) DEFAULT NULL,
  `recommendation_reason` text COLLATE utf8mb4_unicode_ci,
  `status` enum('RECOMMENDED','ACCEPTED','DECLINED','EXPIRED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RECOMMENDED',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`recommendation_id`),
  KEY `idx_recommendation_agent` (`agent_id`),
  KEY `idx_recommendation_task` (`task_id`),
  KEY `idx_recommendation_evaluation` (`evaluation_id`),
  KEY `idx_recommendation_status` (`status`),
  CONSTRAINT `fk_recommendation_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_recommendation_evaluation` FOREIGN KEY (`evaluation_id`) REFERENCES `eligibility_evaluations` (`evaluation_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_recommendation_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_recommendation_score` CHECK (((`recommendation_score` is null) or ((`recommendation_score` >= 0) and (`recommendation_score` <= 1))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: task_requirements
CREATE TABLE IF NOT EXISTS `task_requirements` (
  `requirement_id` int unsigned NOT NULL AUTO_INCREMENT,
  `task_id` int unsigned NOT NULL,
  `minimum_competency` enum('ELIGIBLE','NOT_ELIGIBLE','NEEDS_IMPROVEMENT','BASIC','COMPETENT','ADVANCED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ELIGIBLE',
  `required_certification_id` int unsigned DEFAULT NULL,
  `minimum_experience_months` int unsigned NOT NULL DEFAULT '0',
  `required_skill_id` int unsigned DEFAULT NULL,
  `minimum_skill_score` decimal(5,2) DEFAULT NULL,
  `exam_required` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`requirement_id`),
  KEY `idx_task_requirements_task` (`task_id`),
  KEY `idx_task_requirements_certification` (`required_certification_id`),
  KEY `idx_task_requirements_skill` (`required_skill_id`),
  CONSTRAINT `fk_task_requirements_certification` FOREIGN KEY (`required_certification_id`) REFERENCES `certifications` (`certification_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_task_requirements_skill` FOREIGN KEY (`required_skill_id`) REFERENCES `skills` (`skill_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_task_requirements_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_task_min_skill_score` CHECK (((`minimum_skill_score` is null) or ((`minimum_skill_score` >= 0) and (`minimum_skill_score` <= 100))))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: tasks
CREATE TABLE IF NOT EXISTS `tasks` (
  `task_id` int unsigned NOT NULL AUTO_INCREMENT,
  `category_id` int unsigned NOT NULL,
  `task_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` enum('DRAFT','ACTIVE','INACTIVE','COMPLETED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'DRAFT',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `work_arrangement` enum('Remote','Hybrid','On-site') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Remote',
  `location` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `deliverables` text COLLATE utf8mb4_unicode_ci,
  `required_skills` text COLLATE utf8mb4_unicode_ci,
  `payment_type` enum('Hourly','Fixed Budget') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Fixed Budget',
  `currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'KES',
  `hourly_rate_min` decimal(10,2) DEFAULT NULL,
  `hourly_rate_max` decimal(10,2) DEFAULT NULL,
  `fixed_budget` decimal(10,2) DEFAULT NULL,
  `positions_count` int unsigned NOT NULL DEFAULT '1',
  `application_deadline` date DEFAULT NULL,
  `expected_duration` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exam_id` int unsigned DEFAULT NULL,
  PRIMARY KEY (`task_id`),
  KEY `idx_tasks_category` (`category_id`),
  KEY `idx_tasks_status` (`status`),
  KEY `fk_tasks_exams` (`exam_id`),
  CONSTRAINT `fk_tasks_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_tasks_exams` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: users
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` int unsigned NOT NULL AUTO_INCREMENT,
  `full_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('AGENT','ADMIN') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'AGENT',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `email_verified` tinyint(1) NOT NULL DEFAULT '0',
  `last_login_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_active` (`is_active`),
  KEY `idx_users_email_verified` (`email_verified`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- View: v_eligibility_summary
CREATE OR REPLACE VIEW `v_eligibility_summary` AS select `ee`.`evaluation_id`;
