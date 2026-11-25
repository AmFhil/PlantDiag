/* AgriNovva v2.1 — corrections.js
   IndexedDB store for farmer crop-type overrides.

   Why hand-rolled instead of the `idb` package: the app must run offline
   from a USB flash drive with zero installs and zero CDN access.

   Store layout: DB 'AgrinovvaDB' v1, object store 'corrections'
   (out-of-line keys) → key: image hash (hex string), value:
   { crop, disease, modelClassId, sourceAiCrop, timestamp } */

'use strict';

const DB_NAME = 'AgrinovvaDB';
const DB_VERSION = 1;
const STORE = 'corrections';

let dbPromise = null;

function openCorrectionsDB() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB not available in this environment.'));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error('Could not open AgrinovvaDB.'));
  });
  return dbPromise;
}

function runTx(mode, fn) {
  return openCorrectionsDB().then(
    (db) => new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const store = tx.objectStore(STORE);
      const result = fn(store);
      tx.oncomplete = () => resolve(result && result.result !== undefined ? result.result : result);
      tx.onerror = () => reject(tx.error || new Error('IndexedDB transaction failed.'));
      tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted.'));
    })
  );
}

/** SHA-256 (hex) of the data-URL string. Hashing the encoded string rather
    than decoded image bytes is deterministic, cheaper, and stable across
    browsers; identical captures produce identical data URLs. Falls back to
    FNV-1a when crypto.subtle is unavailable (non-secure contexts). */
export async function hashImage(dataUrl) {
  const text = String(dataUrl || '');
  if (typeof crypto !== 'undefined' && crypto.subtle && crypto.subtle.digest) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return 'fnv1a_' + hash.toString(16);
}

export async function storeCorrection(imgHash, correction) {
  const record = {
    crop: correction.crop,
    disease: correction.disease || null,
    modelClassId: correction.modelClassId ?? null,
    sourceAiCrop: correction.sourceAiCrop || null,
    timestamp: Date.now(),
  };
  await runTx('readwrite', (store) => store.put(record, imgHash));
  return record;
}

export async function lookupCorrection(imgHash) {
  return runTx('readonly', (store) => store.get(imgHash));
}

export async function countCorrections() {
  return runTx('readonly', (store) => store.count());
}
