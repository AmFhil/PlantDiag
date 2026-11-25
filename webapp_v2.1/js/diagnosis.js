/* AgriNovva — diagnosis.js
   Offline crop-disease diagnosis pipeline.

   Runtime contract:
   - Preprocessing and postprocessing run in the WebView (pure JS, browser-testable).
   - Inference runs on the NATIVE layer via a Capacitor bridge. The WebView has
     no TFLite runtime: @tensorflow/tfjs-tflite (WASM) is not used. Native TFLite
     Java (TFLiteInterpreterPlugin.java) is the inference runtime.

   Model contract — PlantVillage-38 (plant_disease_model.tflite):
   - Architecture : ResNet18, Float32 (NCHW), trained on PlantVillage dataset.
   - Input        : Float32 [1, 3, 224, 224] — NCHW (channels-first, ResNet/PyTorch convention)
                    Normalized by ImageNet mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225].
                    JS sends Uint8Array(150528 raw RGB). Java bridge applies NCHW repack.
   - Output       : Float32 [1, 38] — raw logits (sum ≈ -600, large negative range).
   - Classes      : 38 PlantVillage classes (see models/classes.json)
                    Apple(4), Blueberry(1), Cherry(2), Corn(4), Grape(4),
                    Orange(1), Peach(2), Pepper(2), Potato(3), Raspberry(1),
                    Soybean(1), Squash(1), Strawberry(2), Tomato(10).
   - NOT IN SCOPE : Cassava, Yam, Rice, Cowpea, Sorghum — returning
                    'outside_scope' rejection for these rather than a wrong label.
   - Postprocess  : softmax(logits), top prediction must have prob >= 0.42,
                    normalized entropy must be < 0.78 for a result to be shown.

   Bridge protocol (Capacitor native plugin):
     window.NaijaHarvestDiagnosis.runInference(typedArray) -> Promise<Float32Array>
   The typed array is a Uint8Array of 1*224*224*3 = 150528 bytes in NHWC order
   (raw pixel values 0-255). Resolves with 30 dequantized float logits.
   In plain-browser development this bridge is absent; inferFromNative() falls
   back to inferFromBrowserPreview() so the UI degrades gracefully. */

'use strict';

const INPUT_SIZE = 224;
let NUM_CLASSES = 9;

// ── Validation gates ──────────────────────────────────────────────────────────
// CONFIDENCE_THRESHOLD: minimum top-class probability to accept a diagnosis.
// Safe threshold calibrated to 0.35 for the fine-tuned 9-class model.
const CONFIDENCE_THRESHOLD   = 0.35;

// ENTROPY_REJECT_THRESHOLD: normalized entropy above this = model is too uncertain.
const ENTROPY_REJECT_THRESHOLD = 0.82;

// MIN_FOLIAGE_PIXEL_RATIO: fraction of pixels that must be plant chlorophyll
const MIN_FOLIAGE_PIXEL_RATIO  = 0.04;

// SOFTMAX_TEMPERATURE: 1.0 for true probability distribution.
const SOFTMAX_TEMPERATURE    = 1.0;

/** Load and cache the class label list + disease reference DB. */
let classesCache = null;
let diseaseDbCache = null;

async function loadClasses() {
  if (!classesCache) {
    const res = await fetch('assets/model/classes.json?v=8');
    classesCache = await res.json();
    if (Array.isArray(classesCache) && classesCache.length > 0) {
      NUM_CLASSES = classesCache.length;
    }
  }
  return classesCache;
}

async function loadDiseaseDb() {
  if (!diseaseDbCache) {
    const res = await fetch('assets/model/disease_db.json?v=8');
    diseaseDbCache = await res.json();
  }
  return diseaseDbCache;
}

/** Parse "Crop___Disease" class names into displayable parts. */
function parseClassName(className) {
  const parts = className.split('___');
  if (parts.length === 2) {
    return {
      crop: parts[0].replace(/_/g, ' '),
      disease: parts[1].replace(/_/g, ' '),
      isHealthy: parts[1].toLowerCase() === 'healthy',
    };
  }
  return { crop: className.replace(/_/g, ' '), disease: '', isHealthy: false };
}

/**
 * Heuristic: does this image contain genuine plant foliage or crop leaf tissue?
 * 1. Color check: detects photosynthetic chlorophyll (green and chlorotic yellow-green).
 *    Rejects non-green surfaces (wood, furniture, skin, floors, beige walls).
 * 2. Texture & Gradient check: detects natural organic leaf cellular patterns and veins.
 *    Rejects synthetic flat green surfaces (painted green walls, green plastic, books, shirts)
 *    which have unnaturally low color variance and near-zero spatial gradients.
 * @param {Uint8ClampedArray} rgbaData — raw pixel data from getImageData()
 * @param {number} width
 * @param {number} height
 * @returns {{ isPlant: boolean, greenRatio: number, reason?: string }}
 */
function validatePlantImage(rgbaData, width, height) {
  const total = width * height;
  let foliageCount = 0;
  let sumG = 0;
  let sumG2 = 0;

  for (let i = 0; i < total; i++) {
    const r = rgbaData[i * 4];
    const g = rgbaData[i * 4 + 1];
    const b = rgbaData[i * 4 + 2];
    // 1. Green leaf foliage: green clearly dominates red and blue
    const isGreen = g > r + 10 && g > b + 10 && g > 35;
    // 2. Chlorotic / yellow-green diseased tissue (mosaic virus, chlorosis)
    const isYellowGreen = g > b + 15 && r > b + 15 && g >= r - 15 && g > 40;

    if (isGreen || isYellowGreen) {
      foliageCount++;
      sumG += g;
      sumG2 += g * g;
    }
  }

  const foliageRatio = foliageCount / total;
  if (foliageRatio < MIN_FOLIAGE_PIXEL_RATIO) {
    return { isPlant: false, greenRatio: foliageRatio, reason: 'insufficient_chlorophyll' };
  }

  // ── Texture variance test across foliage pixels ───────────────────────────
  // Real leaves have organic cellular variation and lighting gradients (std >= 18).
  // Synthetic flat green objects (green plastic, green wall, green book) have std < 12.
  const meanG = sumG / foliageCount;
  const varianceG = (sumG2 / foliageCount) - (meanG * meanG);
  const stdG = Math.sqrt(Math.max(0, varianceG));

  // ── Spatial gradient test across the image ────────────────────────────────
  // Real leaves have leaf veins, edges, and surface contours (avg gradient >= 4.0).
  // Flat painted surfaces or plastics have avg gradient < 2.5.
  let totalGrad = 0;
  let gradSamples = 0;
  const step = 2;
  for (let y = 0; y < height - 1; y += step) {
    for (let x = 0; x < width - 1; x += step) {
      const idx = (y * width + x) * 4;
      const g0 = rgbaData[idx + 1];
      const gRight = rgbaData[idx + 4 + 1];
      const gDown = rgbaData[((y + 1) * width + x) * 4 + 1];
      totalGrad += Math.abs(g0 - gRight) + Math.abs(g0 - gDown);
      gradSamples += 2;
    }
  }
  const avgGrad = gradSamples > 0 ? (totalGrad / gradSamples) : 0;

  const hasOrganicTexture = stdG >= 18.0 && avgGrad >= 3.8;
  if (!hasOrganicTexture) {
    console.warn(`[Diagnosis] Rejected artificial green surface: stdG=${stdG.toFixed(1)} (min 18), avgGrad=${avgGrad.toFixed(1)} (min 3.8)`);
    return { isPlant: false, greenRatio: foliageRatio, reason: 'artificial_green_texture' };
  }

  return { isPlant: true, greenRatio: foliageRatio };
}

/**
 * Preprocess an image element into the model's input tensor.
 *
 * The NaijaStaples model is INT8 quantized. Its TFLite input tensor is:
 *   Uint8 [1, 224, 224, 3] — NHWC, raw pixel values 0-255 (150,528 bytes).
 * The TFLite runtime applies scale/zero_point internally. Sending Float32
 * would produce a 4× size mismatch (602,112 vs 150,528 bytes) and crash.
 *
 * Also returns the raw RGBA pixel data for the plant-image validation gate.
 * @param {HTMLImageElement|HTMLCanvasElement} image - source image (any size)
 * @returns {Promise<{ tensor: Uint8Array, rgbaData: Uint8ClampedArray, width: number, height: number }>}
 */
export async function preprocessImage(image) {
  const canvas = document.createElement('canvas');
  canvas.width  = INPUT_SIZE;
  canvas.height = INPUT_SIZE;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(image, 0, 0, INPUT_SIZE, INPUT_SIZE);

  const imageData = ctx.getImageData(0, 0, INPUT_SIZE, INPUT_SIZE);
  const { data } = imageData; // Uint8ClampedArray [R,G,B,A, R,G,B,A, ...]

  // Pack into NHWC Uint8 [224, 224, 3] — strip alpha, keep RGB order.
  // Do NOT normalize: the INT8 model's quantization params handle that.
  const planeSize = INPUT_SIZE * INPUT_SIZE;
  const out = new Uint8Array(planeSize * 3);
  for (let i = 0; i < planeSize; i++) {
    out[i * 3]     = data[i * 4];     // R
    out[i * 3 + 1] = data[i * 4 + 1]; // G
    out[i * 3 + 2] = data[i * 4 + 2]; // B
  }
  return { tensor: out, rgbaData: data, width: INPUT_SIZE, height: INPUT_SIZE };
}

/**
 * Run inference through the native Capacitor bridge.
 * @param {Uint8Array} inputTensor - NHWC uint8 input (150528 bytes, 0-255 pixels)
 * @returns {Promise<Float32Array>} 30 dequantized logits
 */
function inferFromBrowserPreview(rgbaData) {
  // Browser preview only — returns a plausible-looking dummy result.
  // Uses class index 8 (Corn Healthy) or 4 (Cassava Healthy) depending on
  // dominant green pixel ratio. Never claims the native model ran.
  const previewLogits = new Float32Array(NUM_CLASSES).fill(-5);
  let greenPixels = 0;

  for (let i = 0; i < rgbaData.length; i += 4) {
    const r = rgbaData[i], g = rgbaData[i + 1], b = rgbaData[i + 2];
    if (g > r + 15 && g > b + 10 && g > 45) greenPixels++;
  }

  // class 4 = Cassava___Healthy, class 8 = Corn_(maize)___Healthy
  const ratio = greenPixels / (rgbaData.length / 4);
  previewLogits[ratio > 0.3 ? 4 : 8] = 10;
  return previewLogits;
}

async function inferFromNative(inputTensor, rgbaData) {
  const bridge = window.NaijaHarvestDiagnosis;
  if (!bridge || typeof bridge.runInference !== 'function') {
    return inferFromBrowserPreview(rgbaData);
  }
  const result = await bridge.runInference(inputTensor);
  if (!(result instanceof Float32Array) || result.length === 0) {
    throw new Error(
      `Native inference returned invalid result: expected Float32Array, ` +
      `got ${result instanceof Float32Array ? result.length : typeof result}.`
    );
  }
  if (result.length !== NUM_CLASSES) {
    console.warn(`[Diagnosis] Native output dimension (${result.length}) != NUM_CLASSES (${NUM_CLASSES}), updating.`);
    NUM_CLASSES = result.length;
  }
  return result;
}

/**
 * Encode a Uint8Array (raw pixel bytes) to base64 for the native bridge.
 * Renamed from float32ToBase64: the INT8 model takes raw uint8 pixels, not floats.
 * @param {Uint8Array} uint8Array
 * @returns {string} base64 string
 */
function uint8ToBase64(uint8Array) {
  let binary = '';
  const CHUNK = 0x8000;
  for (let i = 0; i < uint8Array.length; i += CHUNK) {
    binary += String.fromCharCode.apply(null, uint8Array.subarray(i, i + CHUNK));
  }
  return btoa(binary);
}

/**
 * Register the Capacitor native TFLite plugin as window.NaijaHarvestDiagnosis.
 * No-op in plain-browser preview or when the native plugin is absent.
 */
export async function registerNativeBridge() {
  const cap = window.Capacitor;
  const plugin = cap && cap.Plugins && cap.Plugins.NaijaHarvestDiagnosis;
  if (!plugin || window.NaijaHarvestDiagnosis) return;
  window.NaijaHarvestDiagnosis = {
    async runInference(inputTensor) {
      // inputTensor is Uint8Array (150,528 bytes). Encode as base64 for the
      // Capacitor bridge; Java decodes and passes directly to TFLite.
      const result = await plugin.runInference({ input: uint8ToBase64(inputTensor) });
      return Float32Array.from(result.logits);
    }
  };
}

/** Softmax with optional temperature. */
function softmax(logits, temperature = 1.0) {
  const scaled = Array.from(logits, (l) => l / temperature);
  const maxLogit = Math.max(...scaled);
  const exps = scaled.map((x) => Math.exp(x - maxLogit));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((x) => x / sum);
}

/**
 * Map a /api/diagnose server response into the exact shape diagnose()
 * returns, so existing render/speak/persist code works unchanged.
 */
function mapServerResponse(json, cropOverride) {
  const mapEntry = (e) => ({
    prob: e.probability,
    idx: e.idx,
    crop: e.crop,
    disease: e.disease,
    isHealthy: e.is_healthy,
    class_name: e.class_name,
    details: e.details || null,
  });
  const top = json.top ? mapEntry(json.top) : null;
  return {
    top,
    top3: (json.top3 || []).map(mapEntry),
    entropy: json.entropy ?? 1,
    certainty: 1 - (json.entropy ?? 1),
    rejected: !top,
    rejectReason: top ? null : 'low_confidence',
    serverPrediction: true,
    sourceCrop: cropOverride || null,
    modelVersion: json.model_version || null,
    modelRouting: json.model_routing || null,
    bothModels: json.both_models || null,
    warning: json.warning || null,
  };
}

/**
 * Real inference via the local Python TFLite server (POST /api/diagnose).
 * @param {string} dataUrl - JPEG/PNG data URL of the captured leaf
 * @param {string|null} cropOverride - farmer-chosen crop to bias the ranking
 * @returns {Promise<Object>} diagnose()-shaped result
 */
export async function diagnoseOnServer(dataUrl, cropOverride = null) {
  const payload = { image: dataUrl };
  if (cropOverride) payload.crop = cropOverride;

  const res = await fetch('/api/diagnose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = 'HTTP ' + res.status;
    try {
      const err = await res.json();
      if (err.error) detail = err.error;
    } catch (_) { /* non-JSON error body — keep HTTP status */ }
    throw new Error('Server diagnosis failed: ' + detail);
  }
  const json = await res.json();
  if (json.error) throw new Error('Server diagnosis failed: ' + json.error);
  return mapServerResponse(json, cropOverride);
}

/**
 * v2.1 entry point: real server inference when running in a plain browser
 * over http(s); falls back to the existing local pipeline (Capacitor bridge
 * or browser preview) when the server is unreachable.
 * @param {HTMLImageElement} imageElement - loaded image for the local path
 * @param {{dataUrl: string, crop?: string|null}} opts
 */
export async function diagnoseWithFallback(imageElement, opts = {}) {
  const canUseServer =
    typeof location !== 'undefined' &&
    /^https?:$/.test(location.protocol) &&
    !window.Capacitor?.Plugins;

  if (canUseServer && opts.dataUrl) {
    try {
      return await diagnoseOnServer(opts.dataUrl, opts.crop || null);
    } catch (err) {
      console.warn('[Diagnosis] Server unavailable, falling back to local pipeline:', err.message);
    }
  }
  const local = await diagnose(imageElement);
  if (opts.crop && local.top && !opts._cropApplied) {
    console.info('[Diagnosis] Crop override "' + opts.crop + '" not applied — local pipeline has no server bias.');
  }
  return local;
}

/** Normalized entropy in [0,1] — higher means the model is more uncertain. */
function calcEntropy(probabilities) {
  const entropy = -probabilities.reduce((sum, p) => sum + (p > 1e-10 ? p * Math.log(p) : 0), 0);
  return entropy / Math.log(NUM_CLASSES);
}

/**
 * Full diagnosis: preprocess → validate → infer → postprocess.
 * Returns a structured result including a rejection reason when the image
 * is not a plant leaf.
 * @param {HTMLImageElement|HTMLCanvasElement} image
 * @returns {Promise<Object>} { top, top3, entropy, certainty, rejected, rejectReason }
 */
export async function diagnose(image) {
  const [classes, preprocessed] = await Promise.all([
    loadClasses(),
    preprocessImage(image),
  ]);

  // ── Gate 1: Green-pixel heuristic ──────────────────────────────────────────
  const { isPlant, greenRatio } = validatePlantImage(
    preprocessed.rgbaData,
    preprocessed.width,
    preprocessed.height,
  );
  if (!isPlant) {
    console.warn(`[Diagnosis] Rejected: foliage pixel ratio ${(greenRatio * 100).toFixed(1)}% < ${(MIN_FOLIAGE_PIXEL_RATIO * 100).toFixed(1)}% threshold.`);
    return {
      top: null, top3: [], entropy: 1, certainty: 0,
      rejected: true,
      rejectReason: 'no_plant',
    };
  }

  const rawOutput = await inferFromNative(preprocessed.tensor, preprocessed.rgbaData);
  
  // The INT8 quantized model produces UINT8 outputs scaled by 0.00390625 (~1/256)
  // in Java, which already represent DIRECT SOFTMAX PROBABILITIES in [0, 1] summing to ~1.0.
  // In plain-browser preview mode, inferFromBrowserPreview returns unnormalized dummy logits.
  // We detect whether rawOutput is already a normalized probability distribution.
  // Applying softmax to an existing probability distribution flattens it (entropy -> 0.998),
  // which was falsely rejecting valid plant images!
  const sum = rawOutput.reduce((a, b) => a + b, 0);
  const isProbabilityDistribution = sum >= 0.7 && sum <= 1.3 && rawOutput.every((v) => v >= 0 && v <= 1.0);

  const probabilities = isProbabilityDistribution
    ? Array.from(rawOutput, (p) => p / sum)
    : softmax(rawOutput, SOFTMAX_TEMPERATURE);

  const entropy = calcEntropy(probabilities);

  // ── Gate 2: Entropy gate ───────────────────────────────────────────────────
  if (entropy > ENTROPY_REJECT_THRESHOLD) {
    console.warn(`[Diagnosis] Rejected: entropy ${entropy.toFixed(3)} > ${ENTROPY_REJECT_THRESHOLD} threshold.`);
    return {
      top: null, top3: [], entropy, certainty: 1 - entropy,
      rejected: true,
      rejectReason: 'uncertain',
    };
  }

  const ranked = probabilities
    .map((prob, idx) => ({ prob, idx, ...parseClassName(classes[idx]) }))
    .sort((a, b) => b.prob - a.prob)
    .slice(0, 3)
    .filter((p) => p.prob >= CONFIDENCE_THRESHOLD);

  const top = ranked.length > 0 ? ranked[0] : null;

  // ── Gate 3: Confidence threshold (already applied via filter above) ─────────
  if (!top) {
    return {
      top: null, top3: ranked, entropy, certainty: 1 - entropy,
      rejected: true,
      rejectReason: 'low_confidence',
    };
  }

  return {
    top,
    top3: ranked,
    entropy,
    certainty: 1 - entropy,
    rejected: false,
    browserPreview: !window.NaijaHarvestDiagnosis,
  };
}

/**
 * Maps our internal language names to the treatment column suffix in disease_db.json.
 * getLanguage() returns 'English'|'Hausa'|'Yoruba'|'Igbo'|'Pidgin'.
 * After .toLowerCase() these become 'english','hausa','yoruba','igbo','pidgin'.
 * The DB columns are: treatment (English), treatment_ha, treatment_yo,
 * treatment_ig, treatment_pcm.
 */
const LANG_TO_TREATMENT_KEY = {
  english: 'treatment',
  hausa:   'treatment_ha',
  yoruba:  'treatment_yo',
  igbo:    'treatment_ig',
  pidgin:  'treatment_pcm',
  // BCP-47 short codes (legacy fallback)
  en:  'treatment',
  ha:  'treatment_ha',
  yo:  'treatment_yo',
  ig:  'treatment_ig',
  pcm: 'treatment_pcm',
};

/**
 * Map a diagnosis result onto the disease reference DB (localized).
 * @param {Object|null} topPrediction - top result from diagnose()
 * @param {string} lang - language name (e.g. 'English', 'Hausa') or BCP-47 code
 * @returns {Promise<Object|null>}
 */
export async function enrichWithDiseaseInfo(topPrediction, lang = 'english') {
  if (!topPrediction) return null;

  // Server predictions carry the matched entry from the CORRECT per-model
  // disease DB in top.details — trusting the local 9-class DB here would
  // corrupt v1.7 (38-class) results, whose model_class_id indexes overlap.
  let entry = topPrediction.details || null;

  if (!entry) {
    const db = await loadDiseaseDb();
    const local = db.diseases.find((d) => d.model_class_id === topPrediction.idx);
    if (!local) {
      return {
        id:        null,
        crop:      topPrediction.crop,
        disease:   topPrediction.disease,
        isHealthy: topPrediction.isHealthy,
        treatment: null,
        symptoms:  null,
        severity:  null,
      };
    }
    entry = local;
  }

  const langKey   = LANG_TO_TREATMENT_KEY[lang.toLowerCase()] ?? 'treatment';
  const treatment = entry[langKey] || entry.treatment;

  console.log(`[Diagnosis] lang='${lang}' → key='${langKey}' → treatment snippet: '${(treatment || '').slice(0, 60)}...'`);

  return {
    id:            entry.id,
    crop:          entry.crop,
    disease:       entry.disease_name,
    isHealthy:     entry.is_healthy,
    severity:      entry.severity,
    symptoms:      entry.symptoms,
    treatment,
    treatment_en:  entry.treatment || '',
    treatment_ha:  entry.treatment_ha || '',
    treatment_yo:  entry.treatment_yo || '',
    treatment_ig:  entry.treatment_ig || '',
    treatment_pcm: entry.treatment_pcm || '',
  };
}