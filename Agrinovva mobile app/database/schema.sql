-- Naija Harvest - Offline Database Schema
-- Uses @capacitor-community/sqlite (v8) — schema managed via SQLiteUpgrade for migrations.
-- Database name: naijaharvest.db

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Version tracking for schema migrations (used by capacitor-community/sqlite upgrade mechanism)
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL
);

-- Farmers Table — registered farmers (optional registration; diagnosis works without it)
CREATE TABLE IF NOT EXISTS farmers (
    id TEXT PRIMARY KEY,
    nin TEXT UNIQUE,
    name TEXT,
    phone TEXT,
    language TEXT DEFAULT 'English',
    village TEXT,
    state TEXT,
    created_at INTEGER,
    last_sync INTEGER
);

-- Diagnoses Table — each capture produces one row
CREATE TABLE IF NOT EXISTS diagnoses (
    id TEXT PRIMARY KEY,
    farmer_id TEXT,
    image_path TEXT,
    disease_name TEXT,
    confidence REAL,
    crop_name TEXT,
    treatment TEXT,
    treatment_ha TEXT,
    treatment_yo TEXT,
    treatment_ig TEXT,
    treatment_pcm TEXT,
    created_at INTEGER,
    synced INTEGER DEFAULT 0,
    FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_diagnoses_farmer ON diagnoses (farmer_id);
CREATE INDEX IF NOT EXISTS idx_diagnoses_created ON diagnoses (created_at DESC);

-- Diseases Reference Table — bundled seed data (disease_db.json), read-only in app
CREATE TABLE IF NOT EXISTS diseases (
    id TEXT PRIMARY KEY,
    crop TEXT,
    disease_name TEXT,
    symptoms TEXT,
    treatment TEXT,
    treatment_ha TEXT,
    treatment_yo TEXT,
    treatment_ig TEXT,
    treatment_pcm TEXT,
    model_class_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_diseases_crop ON diseases (crop);
CREATE INDEX IF NOT EXISTS idx_diseases_model_class ON diseases (model_class_id);

-- Settings Table — key/value app preferences (language, offline mode, etc.)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO settings (key, value) VALUES ('language', 'English');
INSERT OR IGNORE INTO settings (key, value) VALUES ('offline_mode', '1');
INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, CAST(strftime('%s', 'now') AS INTEGER));