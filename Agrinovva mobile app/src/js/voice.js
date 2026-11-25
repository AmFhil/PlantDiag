/* AgriNovva — voice.js
   Multilingual voice output — three-tier architecture (PRD §Feasibility Findings).

   TIER 1: Pre-generated audio clips (Phase 3 — loaded from assets/audio/MANIFEST.json)
   TIER 2: @capacitor-community/text-to-speech — native Android TTS (fallback)
           Falls back to Web Speech API in browser / dev preview.
   TIER 3: Cloud TTS on-demand (Phase 3 — 9jaLingo / Orinode / Azure - via pipeline)

   Language → BCP-47 mapping:
     English → en-NG   (Nigerian English accent where available, else en-US)
     Hausa   → ha      (Android TTS supports if language pack installed)
     Yoruba  → yo      (Android TTS supports if language pack installed)
     Igbo    → ig      (Android TTS supports if language pack installed)
     Pidgin  → en-NG   (no native Android TTS for Pidgin — falls back to English)
*/

'use strict';

/** Map our language names to BCP-47 locale codes used by both TTS engines. */
const LANG_TO_BCP47 = {
  English: 'en-NG',
  Hausa: 'ha',
  Yoruba: 'yo',
  Igbo: 'ig',
  Pidgin: 'en-NG', // no Pidgin TTS support — graceful English fallback
};

let audioManifest = null;
let currentAudio = null;

/* ─── Tier 1: Pre-generated Audio Library (HTML5 Audio) ───────────────────── */

async function loadManifest() {
  if (audioManifest !== null) return;
  try {
    const res = await fetch('assets/audio/MANIFEST.json');
    if (res.ok) {
      audioManifest = await res.json();
    } else {
      audioManifest = {};
    }
  } catch (err) {
    console.warn('[Voice] Could not load audio MANIFEST.json:', err);
    audioManifest = {};
  }
}

async function playPreGeneratedAudio(diseaseId, lang) {
  await loadManifest();
  if (!audioManifest[diseaseId] || !audioManifest[diseaseId][lang]) {
    return false; // No pre-generated clip available
  }

  return new Promise((resolve, reject) => {
    try {
      const audioPath = audioManifest[diseaseId][lang];
      if (currentAudio) {
        currentAudio.pause();
      }
      currentAudio = new Audio(audioPath);
      currentAudio.onended = () => resolve(true);
      currentAudio.onerror = () => {
        console.warn(`[Voice] Failed to play audio asset: ${audioPath}`);
        resolve(false);
      };
      currentAudio.play().catch(err => {
        console.warn(`[Voice] Playback prevented by browser policy:`, err);
        resolve(false);
      });
    } catch (e) {
      resolve(false);
    }
  });
}

/* ─── Capacitor TTS plugin helper ──────────────────────────────────────────── */

function getCapacitorTTS() {
  return window.Capacitor?.Plugins?.TextToSpeech ?? null;
}

/* ─── Tier 2a: Capacitor native TTS (Android) ─────────────────────────────── */

async function speakNative(text, lang) {
  const tts = getCapacitorTTS();
  if (!tts) return false;
  try {
    await tts.speak({
      text,
      lang: LANG_TO_BCP47[lang] ?? 'en-NG',
      rate: 0.9,   // slightly slower than default — clearer for field agents
      pitch: 1.0,
      volume: 1.0,
      category: 'ambient',
    });
    return true;
  } catch (err) {
    console.warn('[Voice] Native TTS failed, falling back to Web Speech:', err);
    return false;
  }
}

/* ─── Tier 2b: Web Speech API (browser / PWA fallback) ────────────────────── */

function speakWebSpeech(text, lang) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return false;

  // Cancel any speech already in progress
  window.speechSynthesis.cancel();

  const utter = new SpeechSynthesisUtterance(text);
  const bcp47 = LANG_TO_BCP47[lang] ?? 'en-NG';

  // Try to find a matching voice; fall back to whatever the browser has
  const voices = window.speechSynthesis.getVoices();
  const match = voices.find((v) => v.lang.startsWith(bcp47))
    ?? voices.find((v) => v.lang.startsWith('en'))
    ?? null;
  if (match) utter.voice = match;

  utter.lang = bcp47;
  utter.rate = 0.9;
  utter.pitch = 1.0;
  utter.volume = 1.0;

  window.speechSynthesis.speak(utter);
  return true;
}

/* ─── Public API ───────────────────────────────────────────────────────────── */

/**
 * Speak text in the given language.
 * Tries Tier 1 (Pre-generated Audio), then Tier 2a (Native TTS), then Tier 2b (Web Speech).
 * @param {string} text - The fallback text to speak
 * @param {string} lang - Language name: 'English'|'Hausa'|'Yoruba'|'Igbo'|'Pidgin'
 * @param {string} [diseaseId] - Disease ID to look up in the audio library
 * @returns {Promise<boolean>} true if speech was initiated
 */
export async function speak(text, lang = 'English', diseaseId = null) {
  if (!text || text === '—') return false;

  // Tier 1: Pre-generated Audio
  if (diseaseId) {
    const played = await playPreGeneratedAudio(diseaseId, lang);
    if (played) return true;
  }

  // Tier 2a: Capacitor native TTS (Android device)
  if (await speakNative(text, lang)) return true;

  // Tier 2b: Web Speech API (browser / dev preview)
  if (speakWebSpeech(text, lang)) return true;

  console.warn('[Voice] No TTS engine available. Text:', text);
  return false;
}

/**
 * Stop any speech currently playing.
 */
export async function stopSpeech() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
  }
  const tts = getCapacitorTTS();
  if (tts) {
    try { await tts.stop(); } catch (_) { /* ignore */ }
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Check if a language is natively supported by the TTS engine or pre-generated clips.
 * Returns true for English always (fallback).
 * @param {string} lang
 * @returns {Promise<boolean>}
 */
export async function isLanguageSupported(lang) {
  const tts = getCapacitorTTS();
  if (!tts) {
    // Web Speech: check voice list
    const voices = window.speechSynthesis?.getVoices() ?? [];
    const bcp47 = LANG_TO_BCP47[lang] ?? 'en-NG';
    return voices.some((v) => v.lang.startsWith(bcp47));
  }
  try {
    return true;
  } catch (_) {
    return false;
  }
}
