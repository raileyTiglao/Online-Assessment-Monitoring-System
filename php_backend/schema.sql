-- =============================================================================
-- schema.sql — Local MySQL schema (XAMPP / MariaDB)
-- Online Assessment Monitoring System
-- Holy Angel University — School of Computing
--
-- Local, no-billing alternative to the Firebase/Firestore data model built
-- earlier — same shape (users/exams/sessions/events), reimplemented as
-- relational tables instead of Firestore documents so it can run entirely
-- on XAMPP (Apache + MySQL/MariaDB + PHP) with no cloud account needed.
--
-- Load with:
--   "C:\xampp\mysql\bin\mysql.exe" -u root < schema.sql
-- or via phpMyAdmin -> Import.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS oams
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE oams;

-- ---------------------------------------------------------------------------
-- users — Professor/Admin accounts. Passwords hashed with PHP's
-- password_hash() (bcrypt) — never store plaintext, never roll custom
-- hashing when a secure standard library function already exists.
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name  VARCHAR(255) NOT NULL DEFAULT '',
    role          ENUM('admin', 'professor') NOT NULL,
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- exams — a professor-created exam, identified by a short human-typeable
-- code (the code students/examinees enter into the Python monitoring app
-- at startup — see main.py::_resolve_exam_code).
-- ---------------------------------------------------------------------------
CREATE TABLE exams (
    code            VARCHAR(32) PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    professor_id    INT NOT NULL,
    professor_email VARCHAR(255) NOT NULL, -- denormalized, avoids a join for display
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (professor_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_exams_professor (professor_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- sessions — one row per monitoring session, matching the shape of
-- monitoring/session_report.py's _build_report_dict(). professor_id/
-- exam_code are NULL for a session that proceeded without a valid exam
-- code (DatabaseConfig.REQUIRE_EXAM_CODE = False allows this — visible
-- only to Admin, enforced in application code the same way
-- firestore.rules did for the Firebase version).
-- ---------------------------------------------------------------------------
CREATE TABLE sessions (
    id                    VARCHAR(64) PRIMARY KEY,     -- session_uid, e.g. sess_20260803T...  _a1b2c3
    session_start         DATETIME(3) NOT NULL,
    session_end           DATETIME(3) NOT NULL,
    calibration_yaw       FLOAT,
    calibration_pitch     FLOAT,
    calibration_roll      FLOAT,
    calibration_samples   INT,
    total_flagged_events  INT NOT NULL DEFAULT 0,
    high_risk_count       INT NOT NULL DEFAULT 0,
    moderate_risk_count   INT NOT NULL DEFAULT 0,
    exam_code             VARCHAR(32) NULL,
    professor_id          INT NULL,
    exam_title             VARCHAR(255) NULL,          -- denormalized, avoids a join in the sessions list
    examinee_label        VARCHAR(255) NULL,
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_code) REFERENCES exams(code) ON DELETE SET NULL,
    FOREIGN KEY (professor_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_sessions_professor (professor_id, session_start)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- events — one row per flagged (MODERATE/HIGH) event within a session,
-- matching monitoring/session_report.py's FlaggedEvent dataclass.
-- screenshot_path is a path relative to php_backend/uploads/ (NULL for
-- every MODERATE event — EvidenceCapture only captures on HIGH risk).
-- ---------------------------------------------------------------------------
CREATE TABLE events (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    session_id            VARCHAR(64) NOT NULL,
    event_timestamp       DATETIME(3) NOT NULL,
    risk_level            ENUM('MODERATE', 'HIGH') NOT NULL,
    yaw                   FLOAT NOT NULL,
    pitch                 FLOAT NOT NULL,
    roll                  FLOAT NOT NULL,
    device_detected       BOOLEAN NOT NULL,
    behavioral_indicator  VARCHAR(500) NOT NULL DEFAULT '',
    trigger_reason        VARCHAR(500) NOT NULL DEFAULT '',
    screenshot_path       VARCHAR(500) NULL,
    -- Baseline-relative iris offset (eye-widths) at the moment this event
    -- fired. gaze_valid=0 means the eyes were too closed (blink/squint)
    -- for gaze to be measured — gaze_x/gaze_y are stale zeros then.
    gaze_x                FLOAT NULL,
    gaze_y                FLOAT NULL,
    gaze_valid            BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_events_session (session_id, event_timestamp)
) ENGINE=InnoDB;
