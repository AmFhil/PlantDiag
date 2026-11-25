/* AgriNovva — settings.js
   In-memory cache over the SQLite settings table.
   Call loadSettings() once at startup; all other exports are synchronous.

   Supported keys:
     language     → 'English' | 'Hausa' | 'Yoruba' | 'Igbo' | 'Pidgin'
     offline_mode → '1' | '0'
*/

'use strict';

import { getSetting, setSetting } from './database.js?v=2';

const DEFAULTS = {
  language:     'English',
  offline_mode: '1',
};

let _cache = { ...DEFAULTS };
let _ready = false;

/**
 * Load all settings from SQLite into the in-memory cache.
 * Safe to call multiple times; resolves immediately on subsequent calls.
 */
export async function loadSettings() {
  if (_ready) return;
  try {
    const [lang, offline] = await Promise.all([
      getSetting('language'),
      getSetting('offline_mode'),
    ]);
    if (lang   !== null) _cache.language     = lang;
    if (offline !== null) _cache.offline_mode = offline;
    _ready = true;
  } catch (err) {
    console.warn('[Settings] Could not load from DB, using defaults:', err);
    _ready = true;
  }
}

/** @returns {'English'|'Hausa'|'Yoruba'|'Igbo'|'Pidgin'} */
export function getLanguage() {
  return _cache.language;
}

/**
 * Persist and cache the selected language.
 * @param {string} lang
 */
export async function setLanguage(lang) {
  _cache.language = lang;
  await setSetting('language', lang);
}

/** @returns {boolean} */
export function getOfflineMode() {
  return _cache.offline_mode === '1';
}

/**
 * Persist and cache the offline-mode toggle.
 * @param {boolean} enabled
 */
export async function setOfflineMode(enabled) {
  const val = enabled ? '1' : '0';
  _cache.offline_mode = val;
  await setSetting('offline_mode', val);
}
