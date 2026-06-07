-- Initial MySQL schema draft for NJY zuoti.
-- No passwords or secrets belong in this file.

CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(64) PRIMARY KEY,
  openid VARCHAR(128) NOT NULL UNIQUE,
  nickname VARCHAR(128),
  avatar_url VARCHAR(512),
  status VARCHAR(32) NOT NULL DEFAULT 'REGISTERED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
  id VARCHAR(64) PRIMARY KEY,
  username VARCHAR(128) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'ENABLED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS banks (
  id VARCHAR(64) PRIMARY KEY,
  type VARCHAR(32) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  cache_version VARCHAR(64),
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chapters (
  id VARCHAR(64) PRIMARY KEY,
  bank_id VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL,
  parent_id VARCHAR(64),
  sort_order INT NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'ENABLED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_chapters_bank_id (bank_id)
);

CREATE TABLE IF NOT EXISTS user_authorizations (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  target_type VARCHAR(32) NOT NULL,
  target_id VARCHAR(64) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_target (user_id, target_type, target_id),
  INDEX idx_auth_user_id (user_id)
);

CREATE TABLE IF NOT EXISTS question_indexes (
  id VARCHAR(64) PRIMARY KEY,
  bank_id VARCHAR(64) NOT NULL,
  chapter_id VARCHAR(64) NOT NULL,
  mongo_id VARCHAR(128) NOT NULL,
  question_type VARCHAR(32) NOT NULL,
  difficulty VARCHAR(32),
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  version VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_question_bank_chapter (bank_id, chapter_id)
);

CREATE TABLE IF NOT EXISTS papers (
  id VARCHAR(64) PRIMARY KEY,
  bank_id VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL,
  question_count INT NOT NULL DEFAULT 0,
  duration_minutes INT NOT NULL DEFAULT 0,
  total_score INT NOT NULL DEFAULT 100,
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_papers_bank_id (bank_id)
);

CREATE TABLE IF NOT EXISTS practice_records (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  bank_id VARCHAR(64),
  chapter_id VARCHAR(64),
  total_count INT NOT NULL DEFAULT 0,
  correct_count INT NOT NULL DEFAULT 0,
  duration_seconds INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_practice_user_id (user_id)
);

CREATE TABLE IF NOT EXISTS mistakes (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  question_id VARCHAR(64) NOT NULL,
  correct_times INT NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_question_mistake (user_id, question_id)
);

CREATE TABLE IF NOT EXISTS favorites (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  question_id VARCHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_question_favorite (user_id, question_id)
);

CREATE TABLE IF NOT EXISTS exam_records (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  paper_id VARCHAR(64) NOT NULL,
  score DECIMAL(6,2) NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_exam_user_id (user_id)
);

CREATE TABLE IF NOT EXISTS feedbacks (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64),
  category VARCHAR(64) NOT NULL DEFAULT 'general',
  content VARCHAR(500) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
