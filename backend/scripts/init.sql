CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    role TEXT NOT NULL CHECK (role IN ('patient', 'doctor')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (id, role)
);
CREATE UNIQUE INDEX users_email_unique ON users (lower(email));

CREATE TABLE doctor_profiles (
    user_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'doctor' CHECK (role = 'doctor'),
    specialization TEXT,
    FOREIGN KEY (user_id, role) REFERENCES users (id, role) ON DELETE RESTRICT
);

CREATE TABLE patient_profiles (
    user_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'patient' CHECK (role = 'patient'),
    birth_date TEXT,
    FOREIGN KEY (user_id, role) REFERENCES users (id, role) ON DELETE RESTRICT
);

CREATE TABLE doctor_patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL REFERENCES doctor_profiles (user_id) ON DELETE RESTRICT,
    patient_id INTEGER NOT NULL REFERENCES patient_profiles (user_id) ON DELETE RESTRICT,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    ended_at TEXT,
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);
CREATE UNIQUE INDEX doctor_patients_active_unique
    ON doctor_patients (doctor_id, patient_id) WHERE ended_at IS NULL;
CREATE INDEX doctor_patients_patient_idx ON doctor_patients (patient_id);

CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE CHECK (length(trim(code)) > 0),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('motor', 'speech', 'memory')),
    component_key TEXT NOT NULL,
    default_config TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(default_config)),
    scoring_version TEXT NOT NULL DEFAULT 'v1',
    created_by INTEGER REFERENCES doctor_profiles (user_id) ON DELETE RESTRICT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (json_type(default_config) = 'object')
);

CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_patient_id INTEGER NOT NULL REFERENCES doctor_patients (id) ON DELETE RESTRICT,
    exercise_id INTEGER NOT NULL REFERENCES exercises (id) ON DELETE RESTRICT,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    target_attempts INTEGER NOT NULL DEFAULT 1 CHECK (target_attempts > 0),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'cancelled')),
    doctor_note TEXT,
    config_snapshot TEXT NOT NULL CHECK (json_valid(config_snapshot)),
    scoring_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (ends_on >= starts_on),
    CHECK (json_type(config_snapshot) = 'object')
);
CREATE INDEX assignments_relationship_idx ON assignments (doctor_patient_id, status);
CREATE INDEX assignments_exercise_idx ON assignments (exercise_id);

CREATE TABLE attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES assignments (id) ON DELETE RESTRICT,
    submission_key TEXT NOT NULL UNIQUE CHECK (length(submission_key) = 36),
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    auto_score NUMERIC CHECK (auto_score IS NULL OR auto_score BETWEEN 0 AND 100),
    doctor_score NUMERIC CHECK (doctor_score IS NULL OR doctor_score BETWEEN 0 AND 100),
    raw_result TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(raw_result)),
    patient_comment TEXT,
    doctor_feedback TEXT,
    reviewed_by INTEGER REFERENCES doctor_profiles (user_id) ON DELETE RESTRICT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (completed_at >= started_at),
    CHECK (json_type(raw_result) = 'object'),
    CHECK ((reviewed_by IS NULL) = (reviewed_at IS NULL)),
    CHECK (doctor_score IS NULL OR reviewed_by IS NOT NULL),
    CHECK (doctor_feedback IS NULL OR reviewed_by IS NOT NULL)
);
CREATE INDEX attempts_assignment_time_idx ON attempts (assignment_id, completed_at);
CREATE INDEX attempts_reviewer_idx ON attempts (reviewed_by) WHERE reviewed_by IS NOT NULL;

CREATE TABLE media_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uploaded_by INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    exercise_id INTEGER REFERENCES exercises (id) ON DELETE RESTRICT,
    attempt_id INTEGER REFERENCES attempts (id) ON DELETE RESTRICT,
    media_type TEXT NOT NULL CHECK (media_type IN ('audio', 'video')),
    storage_key TEXT NOT NULL UNIQUE CHECK (length(trim(storage_key)) > 0),
    original_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'ready', 'failed')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK ((exercise_id IS NOT NULL) <> (attempt_id IS NOT NULL)),
    CHECK (
        (media_type = 'audio' AND mime_type LIKE 'audio/%') OR
        (media_type = 'video' AND mime_type LIKE 'video/%')
    )
);
CREATE INDEX media_files_exercise_idx ON media_files (exercise_id) WHERE exercise_id IS NOT NULL;
CREATE INDEX media_files_attempt_idx ON media_files (attempt_id) WHERE attempt_id IS NOT NULL;
CREATE INDEX media_files_uploader_idx ON media_files (uploaded_by);

CREATE TABLE diary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patient_profiles (user_id) ON DELETE RESTRICT,
    entry_date TEXT NOT NULL,
    wellbeing INTEGER NOT NULL CHECK (wellbeing BETWEEN 1 AND 5),
    mood INTEGER CHECK (mood IS NULL OR mood BETWEEN 1 AND 5),
    fatigue INTEGER CHECK (fatigue IS NULL OR fatigue BETWEEN 0 AND 10),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (patient_id, entry_date)
);

CREATE TRIGGER diary_entries_touch_updated_at
AFTER UPDATE ON diary_entries
FOR EACH ROW
BEGIN
    UPDATE diary_entries
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')