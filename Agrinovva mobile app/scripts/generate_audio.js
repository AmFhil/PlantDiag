import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as googleTTS from 'google-tts-api';
import { mkdirp } from 'mkdirp';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const APP_ROOT = path.resolve(__dirname, '..');
const DB_PATH = path.join(APP_ROOT, 'models', 'disease_db.json');
const AUDIO_OUT_DIR = path.join(APP_ROOT, 'src', 'assets', 'audio');

/**
 * Mapping Naija Harvest languages to TTS supported locales.
 *
 * NOTE ON TIER 1 PRE-GENERATED AUDIO PIPELINE CONSTRAINTS:
 * 1. Google Translate TTS endpoint used by `google-tts-api` supports 'en' and 'ha',
 *    but does NOT reliably support 'yo' (Yoruba) or 'ig' (Igbo), and has no Pidgin.
 *    For development/scaffolding, 'yo', 'ig', and 'pcm' fall back to 'en'.
 * 2. Production Build Requirement:
 *    To generate authentic offline Nigerian language audio clips (~1,875 clips for 38 diseases):
 *    - Cloud Providers: Use Orinode (https://maraba.ai/products/orinode-tts) or Azure Speech Services
 *      which support yo-NG (Yoruba - Nigeria), ig-NG (Igbo - Nigeria), ha-NG (Hausa - Nigeria),
 *      and en-NG (Nigerian English / Pidgin-toned).
 * 3. On-Device Native Fallback (Tier 2):
 *    Android device Text-to-Speech engines (Google Speech Services) require the user/agent
 *    to download Nigerian language packs via Android Settings -> System -> Languages & Input -> TTS.
 *    If language packs are absent, Capacitor TTS safely catches the error and degrades gracefully.
 */
const TTS_LANG_MAP = {
  English: 'en',
  Hausa: 'ha',
  Yoruba: 'en', // Production: replace with Azure 'yo-NG' or Orinode
  Igbo: 'en',   // Production: replace with Azure 'ig-NG' or Orinode
  Pidgin: 'en', // Production: replace with Azure 'en-NG' (Nigerian accented)
};

async function generateClip(text, langCode, outPath) {
  try {
    // google-tts-api handles >200 chars by splitting into chunks if we use getAllAudioBase64
    const results = await googleTTS.getAllAudioBase64(text, {
      lang: langCode,
      slow: false,
      host: 'https://translate.google.com',
      timeout: 10000,
    });

    // Combine base64 strings into a single buffer
    const buffers = results.map(res => Buffer.from(res.base64, 'base64'));
    const finalBuffer = Buffer.concat(buffers);

    await fs.promises.writeFile(outPath, finalBuffer);
  } catch (err) {
    console.error(`Error generating TTS for text: "${text.substring(0, 30)}..."`, err);
    throw err;
  }
}

async function main() {
  console.log('Starting Tier 1 Audio Generation Pipeline...');

  // 1. Read Disease DB
  const rawData = await fs.promises.readFile(DB_PATH, 'utf-8');
  const db = JSON.parse(rawData);
  const diseases = db.diseases || [];

  const manifest = {};

  // 2. Iterate diseases and languages
  for (const disease of diseases) {
    manifest[disease.id] = {};
    const crop = disease.crop || '';
    const diseaseName = disease.disease_name || 'Unknown';
    const isHealthy = disease.is_healthy;

    for (const [langName, ttsCode] of Object.entries(TTS_LANG_MAP)) {
      // Build the folder structure: src/assets/audio/{langName}/
      const langDir = path.join(AUDIO_OUT_DIR, langName);
      await mkdirp(langDir);

      const fileName = `${disease.id}.mp3`;
      const outPath = path.join(langDir, fileName);

      // Determine the treatment text to read based on language
      let treatText = '';
      if (langName === 'English' || langName === 'Pidgin') {
        treatText = disease.treatment || '';
      } else if (langName === 'Hausa') {
        treatText = disease.treatment_ha || '';
      } else if (langName === 'Yoruba') {
        treatText = disease.treatment_yo || '';
      } else if (langName === 'Igbo') {
        treatText = disease.treatment_ig || '';
      }

      if (!treatText) {
        // Fallback to English treatment if translation is missing
        treatText = disease.treatment || '';
      }

      // Construct phrase: "Apple Scab. Treatment..."
      let phrase = '';
      if (isHealthy) {
        phrase = langName === 'English' || langName === 'Pidgin'
          ? `${crop} looks healthy. No treatment needed.`
          : `${crop} ${diseaseName}. ${treatText}`;
      } else {
        phrase = langName === 'English' || langName === 'Pidgin'
          ? `This is ${crop} ${diseaseName}. ${treatText}`
          : `${crop} ${diseaseName}. ${treatText}`; // Just say disease name then treatment for local langs
      }

      console.log(`Generating [${langName}] ${disease.id}...`);
      await generateClip(phrase, ttsCode, outPath);

      // We only store the relative path in the manifest
      manifest[disease.id][langName] = `assets/audio/${langName}/${fileName}`;

      // Sleep a bit to avoid Google TTS rate limits
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  // 3. Write MANIFEST.json
  const manifestPath = path.join(AUDIO_OUT_DIR, 'MANIFEST.json');
  await fs.promises.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`\n✅ Generated ${diseases.length * 5} audio clips successfully.`);
  console.log(`✅ MANIFEST.json saved to ${manifestPath}`);
}

main().catch(console.error);
