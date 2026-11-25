/* AgriNovva — database.js
   SQLite data layer using @capacitor-community/sqlite v8.

   Tables (from database/schema.sql):
     farmers      — registered farmers (optional; diagnosis works without it)
     diagnoses    — one row per capture/inference
     diseases     — seeded read-only reference from assets/model/disease_db.json
     settings     — key/value app preferences
     schema_version — migration tracking

   Public API:
     initDB()                       → open / create DB, run migrations, seed diseases
     saveFarmer(farmer)             → upsert a farmer row, returns the id
     getFarmers()                   → all farmers ordered by name
     saveDiagnosis(diag)            → insert a diagnosis row, returns the id
     getRecentDiagnoses(limit = 10) → most-recent diagnoses (joined to farmer name where available)
     getSetting(key)                → string value or null
     setSetting(key, value)         → upsert setting
*/

'use strict';

const DB_NAME    = 'naijaharvest';
const DB_VERSION = 1;
const BROWSER_STORAGE_KEY = 'naijaharvest-browser-data';

let _db = null; // cached SQLiteConnection handle
let _browserMode = false;

/* ─── helpers ─────────────────────────────────────────────────────────────── */

function uuid() {
  // Crypto-random UUID (browser + Android WebView both support crypto.randomUUID)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  // Fallback: timestamp + random
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function nowSec() {
  return Math.floor(Date.now() / 1000);
}

function browserData() {
  try {
    const stored = JSON.parse(localStorage.getItem(BROWSER_STORAGE_KEY) || '{}');
    return {
      farmers: Array.isArray(stored.farmers) ? stored.farmers : [],
      diagnoses: Array.isArray(stored.diagnoses) ? stored.diagnoses : [],
      settings: stored.settings && typeof stored.settings === 'object' ? stored.settings : {
        language: 'English',
        offline_mode: '1',
      },
    };
  } catch (err) {
    console.warn('[DB] Could not read browser data:', err);
    return { farmers: [], diagnoses: [], settings: { language: 'English', offline_mode: '1' } };
  }
}

function saveBrowserData(data) {
  localStorage.setItem(BROWSER_STORAGE_KEY, JSON.stringify(data));
}

/** Resolve the SQLite plugin handle, or null in plain-browser preview. */
function getSQLitePlugin() {
  return window.Capacitor?.Plugins?.CapacitorSQLite ?? null;
}

/* ─── schema ───────────────────────────────────────────────────────────────── */

const SCHEMA_STATEMENTS = [
  `PRAGMA journal_mode = WAL`,
  `PRAGMA foreign_keys = ON`,
  `CREATE TABLE IF NOT EXISTS schema_version (
      version    INTEGER PRIMARY KEY,
      applied_at INTEGER NOT NULL
   )`,
  `CREATE TABLE IF NOT EXISTS farmers (
      id         TEXT    PRIMARY KEY,
      nin        TEXT    UNIQUE,
      name       TEXT,
      phone      TEXT,
      language   TEXT    DEFAULT 'English',
      village    TEXT,
      state      TEXT,
      created_at INTEGER,
      last_sync  INTEGER
   )`,
  `CREATE TABLE IF NOT EXISTS diagnoses (
      id           TEXT    PRIMARY KEY,
      farmer_id    TEXT,
      image_path   TEXT,
      disease_name TEXT,
      confidence   REAL,
      crop_name    TEXT,
      treatment    TEXT,
      treatment_ha TEXT,
      treatment_yo TEXT,
      treatment_ig TEXT,
      treatment_pcm TEXT,
      created_at   INTEGER,
      synced       INTEGER DEFAULT 0,
      FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE SET NULL
   )`,
  `CREATE INDEX IF NOT EXISTS idx_diagnoses_farmer  ON diagnoses (farmer_id)`,
  `CREATE INDEX IF NOT EXISTS idx_diagnoses_created ON diagnoses (created_at DESC)`,
  `CREATE TABLE IF NOT EXISTS diseases (
      id             TEXT    PRIMARY KEY,
      crop           TEXT,
      disease_name   TEXT,
      symptoms       TEXT,
      treatment      TEXT,
      treatment_ha   TEXT,
      treatment_yo   TEXT,
      treatment_ig   TEXT,
      treatment_pcm  TEXT,
      model_class_id INTEGER
   )`,
  `CREATE INDEX IF NOT EXISTS idx_diseases_crop        ON diseases (crop)`,
  `CREATE INDEX IF NOT EXISTS idx_diseases_model_class ON diseases (model_class_id)`,
  `CREATE TABLE IF NOT EXISTS settings (
      key   TEXT PRIMARY KEY,
      value TEXT NOT NULL
   )`,
  `INSERT OR IGNORE INTO settings (key, value) VALUES ('language', 'English')`,
  `INSERT OR IGNORE INTO settings (key, value) VALUES ('offline_mode', '1')`,
  `INSERT OR IGNORE INTO schema_version (version, applied_at)
   VALUES (1, CAST(strftime('%s', 'now') AS INTEGER))`,
];

/* ─── init ─────────────────────────────────────────────────────────────────── */

/**
 * Open (or create) the database, run schema migrations, seed diseases.
 * Safe to call multiple times — subsequent calls return the cached connection.
 * In plain-browser preview (no Capacitor) this is a graceful no-op.
 */
export async function initDB() {
  const plugin = getSQLitePlugin();
  if (!plugin) {
    _browserMode = true;
    console.info('[DB] Browser mode enabled; using localStorage for offline data.');
    return;
  }

  if (_db) return; // already initialised

  try {
    let conn;
    const isConn = (await plugin.isConnection({ database: DB_NAME }))?.result;
    if (isConn) {
      conn = await plugin.retrieveConnection({ database: DB_NAME });
    } else {
      conn = await plugin.createConnection({
        database: DB_NAME,
        version:  DB_VERSION,
        encrypted: false,
        mode: 'no-encryption',
      });
    }

    const isDbOpen = (await conn.isDBOpen())?.result;
    if (!isDbOpen) {
      await conn.open();
    }
    _db = conn;

    // Run all schema statements in one transaction
    await _db.execute({ statements: SCHEMA_STATEMENTS.join(';\n') });

    // Seed the diseases reference table from bundled JSON (once)
    await _seedDiseases();

    console.log('[DB] naijaharvest.db ready (v' + DB_VERSION + ')');
  } catch (err) {
    console.error('[DB] initDB failed:', err);
    _db = null;
  }
}

/**
 * Clear local user data (farmers and diagnoses).
 * Does not clear the reference 'diseases' table or 'settings'.
 */
export async function clearDatabase() {
  if (_browserMode) {
    const data = browserData();
    data.farmers = [];
    data.diagnoses = [];
    saveBrowserData(data);
    return;
  }
  if (!_db) return;
  try {
    await _db.execute({ statements: 'DELETE FROM diagnoses;\nDELETE FROM farmers;' });
    console.log('[DB] Local data cleared.');
  } catch (err) {
    console.error('[DB] Failed to clear data:', err);
    throw err;
  }
}

/** Seed diseases table from the bundled disease_db.json asset (INSERT OR IGNORE). */
async function _seedDiseases() {
  if (!_db) return;
  try {
    const res = await fetch('assets/model/disease_db.json');
    const db  = await res.json();
    const rows = db.diseases ?? [];
    if (!rows.length) return;

    // Check if already seeded with current row count
    const existing = await _db.query({ statement: 'SELECT COUNT(*) AS cnt FROM diseases', values: [] });
    const cnt = existing?.values?.[0]?.cnt ?? 0;
    if (cnt === rows.length) return; // already seeded

    if (cnt > 0) {
      await _db.execute({ statements: 'DELETE FROM diseases;' });
    }

    const inserts = rows.map((d) =>
      `INSERT OR REPLACE INTO diseases (id, crop, disease_name, symptoms, treatment,
        treatment_ha, treatment_yo, treatment_ig, treatment_pcm, model_class_id)
       VALUES (
         '${_esc(d.id ?? String(d.model_class_id))}',
         '${_esc(d.crop)}',
         '${_esc(d.disease_name)}',
         '${_esc(d.symptoms ?? '')}',
         '${_esc(d.treatment ?? '')}',
         '${_esc(d.treatment_ha ?? '')}',
         '${_esc(d.treatment_yo ?? '')}',
         '${_esc(d.treatment_ig ?? '')}',
         '${_esc(d.treatment_pcm ?? '')}',
         ${Number(d.model_class_id)}
       )`
    ).join(';\n');

    await _db.execute({ statements: inserts });
    console.log('[DB] Seeded ' + rows.length + ' disease entries.');
  } catch (err) {
    console.warn('[DB] Disease seed failed:', err);
  }
}

/** Escape single-quotes for inline SQL (safe because these are trusted local assets). */
function _esc(str) {
  return String(str ?? '').replace(/'/g, "''");
}

/* ─── farmers ──────────────────────────────────────────────────────────────── */

/**
 * Save (insert or replace) a farmer record.
 * @param {{ name, nin?, phone?, language?, village?, state? }} farmer
 * @returns {Promise<string>} the farmer id
 */
export async function saveFarmer(farmer) {
  const now = nowSec();
  if (_browserMode) {
    const data = browserData();
    let id = uuid();
    const existingIndex = farmer.nin
      ? data.farmers.findIndex((row) => row.nin === farmer.nin)
      : -1;
    if (existingIndex >= 0) {
      id = data.farmers[existingIndex].id;
    }
    const farmerRow = {
      id,
      nin: farmer.nin || null,
      name: farmer.name || '',
      phone: farmer.phone || null,
      language: farmer.language || 'English',
      village: farmer.village || null,
      state: farmer.state || null,
      created_at: now,
    };
    if (existingIndex >= 0) {
      data.farmers[existingIndex] = farmerRow;
    } else {
      data.farmers.push(farmerRow);
    }
    saveBrowserData(data);
    return farmerRow.id;
  }
  if (!_db) throw new Error('Database not available in browser preview.');

  let farmerId = uuid();
  if (farmer.nin) {
    try {
      const existing = await _db.query({
        statement: 'SELECT id FROM farmers WHERE nin = ? LIMIT 1',
        values: [farmer.nin],
      });
      if (existing?.values?.length && existing.values[0].id) {
        farmerId = existing.values[0].id;
      }
    } catch (_) {
      // If query fails, fall back to new UUID
    }
  }

  await _db.run({
    statement: `INSERT OR REPLACE INTO farmers
      (id, nin, name, phone, language, village, state, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    values: [
      farmerId,
      farmer.nin    || null,
      farmer.name   || '',
      farmer.phone  || null,
      farmer.language || 'English',
      farmer.village || null,
      farmer.state   || null,
      now,
    ],
  });
  return farmerId;
}

/**
 * Return all farmers ordered by name.
 * @returns {Promise<Array>}
 */
export async function getFarmers() {
  if (_browserMode) return browserData().farmers.sort((a, b) => a.name.localeCompare(b.name));
  if (!_db) return [];
  const result = await _db.query({
    statement: 'SELECT * FROM farmers ORDER BY name',
    values: [],
  });
  return result?.values ?? [];
}

/* ─── diagnoses ────────────────────────────────────────────────────────────── */

/**
 * Save a diagnosis result from the inference pipeline.
 * @param {{
 *   farmerId?: string,
 *   diseaseName: string,
 *   confidence: number,
 *   cropName: string,
 *   treatment?: string,
 *   treatment_ha?: string,
 *   treatment_yo?: string,
 *   treatment_ig?: string,
 *   treatment_pcm?: string,
 * }} diag
 * @returns {Promise<string>} the diagnosis id
 */
export async function saveDiagnosis(diag) {
  const id  = uuid();
  const now = nowSec();
  if (_browserMode) {
    const data = browserData();
    data.diagnoses.push({
      id,
      farmer_id: diag.farmerId || null,
      disease_name: diag.diseaseName || '',
      confidence: diag.confidence || 0,
      crop_name: diag.cropName || '',
      treatment: diag.treatment || '',
      treatment_ha: diag.treatment_ha || '',
      treatment_yo: diag.treatment_yo || '',
      treatment_ig: diag.treatment_ig || '',
      treatment_pcm: diag.treatment_pcm || '',
      created_at: now,
    });
    saveBrowserData(data);
    return id;
  }
  if (!_db) throw new Error('Database not available in browser preview.');

  await _db.run({
    statement: `INSERT INTO diagnoses
      (id, farmer_id, disease_name, confidence, crop_name, treatment,
       treatment_ha, treatment_yo, treatment_ig, treatment_pcm, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    values: [
      id,
      diag.farmerId    || null,
      diag.diseaseName || '',
      diag.confidence  || 0,
      diag.cropName    || '',
      diag.treatment   || '',
      diag.treatment_ha  || '',
      diag.treatment_yo  || '',
      diag.treatment_ig  || '',
      diag.treatment_pcm || '',
      now,
    ],
  });
  return id;
}

/**
 * Return the most-recent diagnoses with farmer name if available.
 * @param {number} limit
 * @returns {Promise<Array>}
 */
export async function getRecentDiagnoses(limit = 10) {
  if (_browserMode) {
    return browserData().diagnoses
      .slice()
      .sort((a, b) => b.created_at - a.created_at)
      .slice(0, limit);
  }
  if (!_db) return [];
  const result = await _db.query({
    statement: `SELECT d.*, f.name AS farmer_name
      FROM diagnoses d
      LEFT JOIN farmers f ON f.id = d.farmer_id
      ORDER BY d.created_at DESC
      LIMIT ?`,
    values: [limit],
  });
  return result?.values ?? [];
}

/* ─── settings ─────────────────────────────────────────────────────────────── */

/**
 * Get a setting value by key.
 * @param {string} key
 * @returns {Promise<string|null>}
 */
export async function getSetting(key) {
  if (_browserMode) return browserData().settings[key] ?? null;
  if (!_db) return null;
  const result = await _db.query({
    statement: 'SELECT value FROM settings WHERE key = ? LIMIT 1',
    values: [key],
  });
  return result?.values?.[0]?.value ?? null;
}

/**
 * Set (upsert) a setting value.
 * @param {string} key
 * @param {string} value
 */
export async function setSetting(key, value) {
  if (_browserMode) {
    const data = browserData();
    data.settings[key] = String(value);
    saveBrowserData(data);
    return;
  }
  if (!_db) return;
  await _db.run({
    statement: `INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)`,
    values: [key, String(value)],
  });
}
