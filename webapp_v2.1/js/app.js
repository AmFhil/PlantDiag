/* AgriNovva — app.js
   Tab shell + camera + diagnosis flow. Works in browser (preview mode) and
   Capacitor (full diagnosis via native TFLite bridge).

   Phase 2 wiring:
   - initDB()       initialises SQLite on startup
   - loadSettings() restores language preference
   - saveDiagnosis() persists every inference result
   - saveFarmer()   persists farmer registration form
   - getRecentDiagnoses() populates Home + History lists
   - speak()        replaces the "audio coming later" alert on Speak button
*/

'use strict';

import { capturePhoto } from './camera.js';
import { diagnoseWithFallback, enrichWithDiseaseInfo, registerNativeBridge } from './diagnosis.js?v=2.1';
import { hashImage, storeCorrection, lookupCorrection } from './corrections.js?v=2.1';
import { initDB, saveFarmer, getFarmers, saveDiagnosis, getRecentDiagnoses, clearDatabase } from './database.js?v=2';
import { loadSettings, getLanguage, setLanguage, getOfflineMode, setOfflineMode } from './settings.js';
import { speak, stopSpeech } from './voice.js';
import { TRANSLATIONS } from './translations.js';

/* ─── Formatting helpers ───────────────────────────────────────────────────── */

/** Format a Unix timestamp (seconds) as a readable date string. */
function formatDate(sec) {
  if (!sec) return '—';
  const d = new Date(sec * 1000);
  return d.toLocaleDateString('en-NG', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** Round a 0–1 probability to "XX%" */
function fmtPct(v) {
  return Math.round((v ?? 0) * 100) + '%';
}

/* ─── History rendering ────────────────────────────────────────────────────── */

/**
 * Render a list of diagnosis rows into a container element.
 * @param {HTMLElement} container
 * @param {Array} rows — from getRecentDiagnoses()
 * @param {boolean} compact — true for the Home "Recent" strip (shorter cards)
 */
function renderDiagnosisList(container, rows, compact = false) {
  if (!container) return;

  if (!rows || rows.length === 0) {
    const langKey = (getLanguage() || 'English').toLowerCase();
    const dict = TRANSLATIONS[langKey] || TRANSLATIONS.english;
    container.innerHTML = compact
      ? `<p class="empty-state">${dict.empty_recent || 'No diagnoses yet — capture a crop photo to get started.'}</p>`
      : `<div class="empty-state"><p>${dict.empty_history || 'No diagnoses yet'}</p><p class="empty-sub">${dict.empty_history_sub || 'Your past diagnoses will appear here.'}</p></div>`;
    return;
  }

  container.innerHTML = rows.map((row) => {
    const isHealthy = (row.disease_name || '').toLowerCase().includes('healthy');
    const confPct = fmtPct(row.confidence);
    const chipClass = isHealthy ? 'chip chip-healthy'
      : row.confidence >= 0.7 ? 'chip chip-high'
        : row.confidence >= 0.4 ? 'chip chip-medium'
          : 'chip chip-low';
    return `
      <div class="history-card">
        <div class="history-card-header">
          <span class="history-crop">${row.crop_name || 'Unknown crop'}</span>
          <span class="${chipClass}">${confPct}</span>
        </div>
        <p class="history-disease">${row.disease_name || '—'}</p>
        ${!compact ? `<p class="history-treatment">${row.treatment || ''}</p>` : ''}
        <div class="history-meta">
          <span>${formatDate(row.created_at)}</span>
          ${row.farmer_name ? `<span>· ${row.farmer_name}</span>` : ''}
        </div>
      </div>`;
  }).join('');
}

/* ─── App bootstrap ────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {
  // Initialise native bridge and database concurrently
  registerNativeBridge();
  await initDB();
  await loadSettings();

  /* ── Navigation ─────────────────────────────────────────────────────────── */
  const pages = Array.from(document.querySelectorAll('.page'));
  const navItems = Array.from(document.querySelectorAll('.nav-item'));

  function showPage(pageName) {
    pages.forEach((p) => p.classList.toggle('active', p.dataset.page === pageName));
    navItems.forEach((n) => n.classList.toggle('active', (n.dataset.page || n.dataset.target) === pageName));
    window.scrollTo({ top: 0, behavior: 'auto' });
    // Reload history list whenever the History tab is activated
    if (pageName === 'history') loadHistory();
    // Reload home recent list whenever Home is activated
    if (pageName === 'home') loadRecentDiagnoses();
    // Refresh farmer dropdown whenever Diagnose tab is activated
    if (pageName === 'diagnose') loadFarmersDropdown();
  }

  navItems.forEach((item) => {
    item.addEventListener('click', () => showPage(item.dataset.page || item.dataset.target));
  });

  document.getElementById('homeDiagnoseBtn')?.addEventListener('click', () => showPage('diagnose'));

  /* ── Language state ─────────────────────────────────────────────────────── */
  const globalLangSelect = document.getElementById('globalLangSelect');

  /** Sync global language selector and apply translations. */
  function syncLang(value) {
    if (globalLangSelect) globalLangSelect.value = value;
    applyTranslations(value);
  }

  function applyTranslations(langName) {
    const langKey = (langName || 'English').toLowerCase();
    const dict = TRANSLATIONS[langKey] || TRANSLATIONS.english;

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        el.textContent = dict[key];
      }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) {
        el.setAttribute('placeholder', dict[key]);
      }
    });
  }

  // Apply saved preference
  syncLang(getLanguage());

  globalLangSelect?.addEventListener('change', async () => {
    const lang = globalLangSelect.value;
    syncLang(lang);
    await setLanguage(lang);
    // Re-render result in new language if a diagnosis is on screen
    if (lastDiagnosis) await renderResult(lastDiagnosis.diag);
    loadRecentDiagnoses();
  });

  /* ── Offline toggle ─────────────────────────────────────────────────────── */
  const offlineBadge = document.getElementById('offlineBadge');
  const offlineToggle = document.getElementById('offlineToggle');

  // Restore saved offline state
  const isOffline = getOfflineMode();
  if (offlineToggle) offlineToggle.checked = isOffline;
  if (offlineBadge) offlineBadge.textContent = isOffline ? '● Offline Ready' : '● Online';

  if (offlineToggle && offlineBadge) {
    offlineToggle.addEventListener('change', async () => {
      const on = offlineToggle.checked;
      offlineBadge.textContent = on ? '● Offline Ready' : '● Online';
      await setOfflineMode(on);
    });
  }

  /* ── Farmers selection in Diagnose tab ──────────────────────────────────── */
  const diagFarmerSelect = document.getElementById('diagFarmerSelect');

  async function loadFarmersDropdown() {
    if (!diagFarmerSelect) return;
    try {
      const farmers = await getFarmers();
      const currentVal = diagFarmerSelect.value;
      diagFarmerSelect.innerHTML = '<option value="">-- No farmer linked --</option>' +
        farmers.map(f => `<option value="${f.id}">${f.name}${f.village ? ` (${f.village})` : ''}</option>`).join('');
      if (currentVal) diagFarmerSelect.value = currentVal;
    } catch (err) {
      console.warn('[App] Could not populate farmers dropdown:', err);
    }
  }

  await loadFarmersDropdown();

  /* ── Home — recent diagnoses ────────────────────────────────────────────── */
  const recentListEl = document.getElementById('recentList');

  async function loadRecentDiagnoses() {
    try {
      const rows = await getRecentDiagnoses(5);
      renderDiagnosisList(recentListEl, rows, true);
    } catch (err) {
      if (recentListEl) recentListEl.innerHTML = '<p class="empty-state">No diagnoses yet — capture a crop photo to get started.</p>';
    }
  }

  await loadRecentDiagnoses();

  /* ── History page ───────────────────────────────────────────────────────── */
  const historyListEl = document.getElementById('historyList');
  const historySearch = document.getElementById('historySearch');
  let allHistoryRows = [];

  async function loadHistory() {
    try {
      allHistoryRows = await getRecentDiagnoses(50);
      renderFilteredHistory();
    } catch (err) {
      if (historyListEl) historyListEl.innerHTML = '<div class="empty-state"><p>Could not load history.</p></div>';
    }
  }

  function renderFilteredHistory() {
    if (!historySearch) return;
    const query = historySearch.value.toLowerCase();
    const filtered = allHistoryRows.filter(row =>
      (row.crop_name || '').toLowerCase().includes(query) ||
      (row.disease_name || '').toLowerCase().includes(query)
    );
    renderDiagnosisList(historyListEl, filtered, false);
  }

  if (historySearch) {
    historySearch.addEventListener('input', renderFilteredHistory);
  }

  /* ── Diagnose page ──────────────────────────────────────────────────────── */
  const captureBtn = document.getElementById('captureBtn');
  const galleryBtn = document.getElementById('galleryBtn');
  const retakeBtn = document.getElementById('retakeBtn');
  const previewImg = document.getElementById('previewImg');
  const cameraIcon = document.getElementById('cameraIcon');
  const cameraHint = document.getElementById('cameraHint');
  const resultCard = document.getElementById('resultCard');
  const resultDisease = document.getElementById('resultDisease');
  const resultConfidence = document.getElementById('resultConfidence');
  const resultTreatment = document.getElementById('resultTreatment');
  const analyzeStatus = document.getElementById('analyzeStatus');
  const speakBtn = document.getElementById('speakBtn');
  let minConfidence = 0.55;

  let lastDiagnosis = null; // { diag, info }

  function showPreview(dataUrl) {
    previewImg.src = dataUrl;
    previewImg.hidden = false;
    cameraIcon.hidden = true;
    cameraHint.textContent = 'Photo captured — analysing…';
    captureBtn.hidden = true;
    galleryBtn.hidden = true;
    retakeBtn.hidden = false;
  }

  function resetPreview() {
    previewImg.src = '';
    previewImg.hidden = true;
    cameraIcon.hidden = false;
    resultCard.hidden = true;
    lastDiagnosis = null;
    captureBtn.hidden = false;
    galleryBtn.hidden = false;
    retakeBtn.hidden = true;
    cameraHint.textContent = 'Point your camera at the damaged leaf or crop';
    stopSpeech();
  }

  async function renderResult(diag) {
    const lang = getLanguage();
    const info = await enrichWithDiseaseInfo(diag.top, lang.toLowerCase());
    lastDiagnosis = { diag, info };

    // Handle rejection from validation gates
    if (diag.rejected) {
      const msgs = {
        english: {
          no_plant: { title: 'Not a plant image', hint: 'Please capture a clear photo of a crop leaf or stem.' },
          uncertain: { title: 'Plant outside database', hint: 'This plant species is not in the model\'s training set. Supported crops: Corn, Tomato, Potato, Pepper, Apple, Grape, and more. Retrain with local crops for Cassava, Yam, Rice.' },
          low_confidence: { title: 'Plant not recognized', hint: 'This plant is not in the current 38-crop database. Try a clearer photo or check the supported crop list.' },
          outside_scope: { title: 'Crop not in database', hint: 'This crop (e.g. Cassava, Yam, Rice) is not in the 38-species model. Supported: Corn, Tomato, Potato, Pepper, Apple, Grape, and 8 more.' },
        },
        hausa: {
          no_plant: { title: 'Ba hoton shuka ba ne', hint: 'Don Allah a ɗauki kyakkyawan hoton ganyen shuka ko jikin shuka.' },
          uncertain: { title: 'Shuka ba ta cikin bayanan', hint: 'Wannan shuka ba a horar da ita a cikin samfurin. Shukar da aka horar: Masara, Tumatir, Dankali da ƙari.' },
          low_confidence: { title: 'Ba a gane shukar ba', hint: 'Gwada kyakkyawan hoto na ganye ɗaya mai cuta kusa-kusa.' },
          outside_scope: { title: 'Shuka ba ta cikin bayanan', hint: 'Wannan shuka (misali Rogo, Doya) ba ta cikin samfurin 38. Shukar da aka horar: Masara, Tumatir, Dankali.' },
        },
        yoruba: {
          no_plant: { title: 'Kì í ṣe àwòrán ewéko', hint: 'Jọ̀wọ́ ya àwòrán tó mọ́ gárágárá fún ewé tàbí igi ọ̀gbìn.' },
          uncertain: { title: 'Ọ̀gbìn kò wà nínú àkójọ', hint: 'Irú ọ̀gbìn yìí kò sí nínú ìkọ́ àwòrán. Àwọn tí a mọ: Àgbàdo, Tòmátì, Ọdùn-kikan, ati bẹ́ẹ̀ bẹ́ẹ̀ lọ.' },
          low_confidence: { title: 'Kò mọ irú ọ̀gbìn yìí', hint: 'Gbìyànjú àwòrán tó mọ́ gárágárá fún ewé kan tó ní àrùn.' },
          outside_scope: { title: 'Ọ̀gbìn kò wà nínú àkójọ', hint: 'Ọ̀gbìn yìí (bí Kàsáfà, Iyán) kò wà nínú àwọn 38 irú ọ̀gbìn tí a mọ.' },
        },
        igbo: {
          no_plant: { title: 'Ọ bụghị foto ihe ọkụkụ', hint: 'Biko see ezigbo foto akwụkwọ ihe ọkụkụ.' },
          uncertain: { title: 'Ihe ọkụkụ adịghị na ndekọ', hint: 'Ụdị ihe ọkụkụ a adịghị na ndekọ ọzụzụ. Ihe ọkụkụ ama ama: Ọka, Tomato, Ji Oyibo, Ose.' },
          low_confidence: { title: 'Amaghị ihe ọkụkụ a', hint: 'Nwaa see ezigbo foto akwụkwọ ahụ butere ọrịa.' },
          outside_scope: { title: 'Ihe ọkụkụ adịghị na ndekọ', hint: 'Ihe ọkụkụ a (dị ka Akpu, Ji) adịghị na ndekọ 38 a mụrụ ya.' },
        },
        pidgin: {
          no_plant: { title: 'Dis no be plant picture', hint: 'Abeg snap clear photo of leaf.' },
          uncertain: { title: 'Dis plant no dey our list', hint: 'Dis crop no dey our 38-crop database. Crops wey dey: Corn, Tomato, Potato, Pepper and more. Cassava, Yam no dey yet.' },
          low_confidence: { title: 'We no know dis crop', hint: 'Snap one leaf clear well well.' },
          outside_scope: { title: 'Dis crop no dey database', hint: 'Cassava, Yam, Rice no dey our 38-crop model yet. Try Corn, Tomato, Potato or Pepper leaf instead.' },
        }
      };

      const langKey = lang.toLowerCase();
      const localeMsgs = msgs[langKey] || msgs.english;
      const { title, hint } = localeMsgs[diag.rejectReason] || localeMsgs.low_confidence;

      resultDisease.textContent = title;
      resultConfidence.textContent = hint;
      resultTreatment.textContent = '';
      resultCard.dataset.severity = 'low';
      analyzeStatus.hidden = true;
      resultCard.hidden = false;
      return;
    }

    if (!diag.top) {
      resultDisease.textContent = 'Could not identify with enough confidence.';
      resultConfidence.textContent = 'Try a clearer photo of a single leaf.';
      resultTreatment.textContent = '';
      analyzeStatus.hidden = true;
      resultCard.hidden = false;
      return;
    }

    const pct = Math.round(diag.top.prob * 100);
    const cropLabel = info?.crop || diag.top.crop;
    const diseaseLabel = info?.disease || diag.top.disease;
    const isHealthy = info?.isHealthy ?? diag.top.isHealthy ?? false;
    const severity = info?.severity || null;

    const treatment = info?.treatment
      ?? (isHealthy ? 'Crop looks healthy — no treatment needed.' : 'Treatment advice not available.');
    const symptoms = info?.symptoms || '';

    // Disease + crop heading
    resultDisease.textContent = cropLabel + ' — ' + diseaseLabel;

    // Confidence + severity badge on same line
    const severityLabel = isHealthy ? 'Healthy' : severity
      ? severity.charAt(0).toUpperCase() + severity.slice(1)
      : null;
    const MODEL_LABELS = { naija: 'NaijaStaples', 'v1.7': 'PlantVillage-38' };
    const modelLabel = diag.modelVersion ? MODEL_LABELS[diag.modelVersion] || diag.modelVersion : null;
    resultConfidence.textContent = 'Confidence: ' + pct + '%'
      + (severityLabel ? '  ·  Severity: ' + severityLabel : '')
      + (modelLabel ? '  ·  Model: ' + modelLabel : '')
      + (diag.browserPreview ? '  ·  Web preview' : '');

    // Symptoms then treatment
    resultTreatment.innerHTML = '';
    if (symptoms && !isHealthy) {
      const sympEl = document.createElement('p');
      sympEl.style.cssText = 'font-size:0.82rem;color:var(--text-muted);margin-bottom:8px;font-style:italic;';
      sympEl.textContent = '⚠️ ' + symptoms;
      resultTreatment.appendChild(sympEl);
    }
    const treatEl = document.createElement('p');
    treatEl.textContent = (diag.browserPreview
      ? 'Web preview estimate only. Use the Android app for full disease diagnosis. '
      : '') + treatment;
    resultTreatment.appendChild(treatEl);

    analyzeStatus.hidden = true;
    resultCard.hidden = false;

    // Border colour: use DB severity if available, else fall back to confidence bands
    const dbSeverity = isHealthy ? 'healthy'
      : severity === 'severe' ? 'high'
        : severity === 'moderate' ? 'medium'
          : severity === 'mild' ? 'low'
            : pct >= 70 ? 'high'
              : pct >= 40 ? 'medium'
                : 'low';
    resultCard.dataset.severity = dbSeverity;
  }

  let currentImageDataUrl = null;
  let currentImageEl = null;
  let currentImageHash = null;

  const cropModal = document.getElementById('crop-select-modal');
  const aiGuessEl = document.getElementById('ai-guess');
  const cropChoice = document.getElementById('crop-choice');
  const cropSaveBtn = document.getElementById('crop-save');
  const cropCancelBtn = document.getElementById('crop-cancel');

  let classesList = [];
  async function loadClassList() {
    if (classesList.length) return classesList;
    const urls = ['assets/model/classes.json', 'assets/model/v1_7/classes.json'];
    const settled = await Promise.allSettled(urls.map((u) => fetch(u).then((r) => r.json())));
    const merged = [];
    settled.forEach((s) => {
      if (s.status === 'fulfilled' && Array.isArray(s.value)) merged.push(...s.value);
    });
    if (!merged.length) console.warn('[App] Could not load classes.json from either model.');
    classesList = merged;
    return classesList;
  }

  function uniqueCrops(classNames) {
    const seen = new Map();
    classNames.forEach((c) => {
      const crop = c.split('___')[0].replace(/_/g, ' ').trim();
      if (crop && !seen.has(crop.toLowerCase())) seen.set(crop.toLowerCase(), crop);
    });
    return Array.from(seen.values());
  }

  function showCropSelector(aiCrop) {
    if (!cropModal || !cropChoice) return;
    if (aiGuessEl) aiGuessEl.textContent = aiCrop;
    loadClassList().then((classes) => {
      const crops = uniqueCrops(classes);
      cropChoice.innerHTML = '';
      crops.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        cropChoice.appendChild(opt);
      });
      if (crops.some((c) => c.toLowerCase() === String(aiCrop).toLowerCase())) {
        cropChoice.value = crops.find((c) => c.toLowerCase() === String(aiCrop).toLowerCase());
      }
      cropModal.classList.remove('hidden');
    });
  }

  function hideCropSelector() {
    cropModal?.classList.add('hidden');
  }

  function setCorrectionNote(text) {
    let note = document.getElementById('correctionNote');
    if (!text) { note?.remove(); return; }
    if (!note && resultCard) {
      note = document.createElement('p');
      note.id = 'correctionNote';
      note.style.cssText = 'font-size:0.82rem;margin-bottom:8px;font-weight:600;';
      resultCard.insertBefore(note, resultTreatment);
    }
    if (note) {
      note.textContent = text;
      note.style.color = 'var(--primary-green)';
    }
  }

  async function persistResult(diag) {
    if (!diag.top) return;
    const info = lastDiagnosis?.info;
    const farmerId = diagFarmerSelect?.value || null;
    try {
      await saveDiagnosis({
        farmerId,
        diseaseName: (info?.disease) || diag.top.disease,
        confidence: diag.top.prob,
        cropName: (info?.crop) || diag.top.crop,
        treatment: info?.treatment_en || info?.treatment || '',
        treatment_ha: info?.treatment_ha || '',
        treatment_yo: info?.treatment_yo || '',
        treatment_ig: info?.treatment_ig || '',
        treatment_pcm: info?.treatment_pcm || '',
      });
      loadRecentDiagnoses();
    } catch (dbErr) {
      console.warn('[App] Could not persist diagnosis (DB unavailable in preview):', dbErr.message);
    }
  }

  async function runDiagnosis(dataUrl) {
    analyzeStatus.hidden = false;
    analyzeStatus.textContent = 'Analysing leaf…';
    resultCard.hidden = true;
    setCorrectionNote(null);

    try {
      const img = new Image();
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = () => reject(new Error('Could not load captured image.'));
        img.src = dataUrl;
      });

      currentImageDataUrl = dataUrl;
      currentImageEl = img;
      currentImageHash = await hashImage(dataUrl);

      const prior = await lookupCorrection(currentImageHash);

      let diag;
      if (prior) {
        diag = await diagnoseWithFallback(img, { dataUrl, crop: prior.crop });
        await renderResult(diag);
        setCorrectionNote('♻ Correction applied from a previous visit (' + prior.crop + ')');
      } else {
        diag = await diagnoseWithFallback(img, { dataUrl });
        await renderResult(diag);
      }

      await persistResult(diag);

      if (diag.top && !prior) {
        showCropSelector(diag.top.crop);
      }
    } catch (err) {
      analyzeStatus.hidden = true;
      resultDisease.textContent = 'Diagnosis unavailable';
      resultConfidence.textContent = err?.message ?? 'Unknown error.';
      resultTreatment.textContent = '';
      resultCard.hidden = false;
    }
  }

  cropSaveBtn?.addEventListener('click', async () => {
    const chosen = cropChoice?.value;
    if (!chosen || !currentImageHash) { hideCropSelector(); return; }
    cropSaveBtn.disabled = true;
    try {
      const aiCrop = aiGuessEl?.textContent || '';
      const topNow = lastDiagnosis?.diag?.top;
      await storeCorrection(currentImageHash, {
        crop: chosen,
        disease: (lastDiagnosis?.info?.disease) || topNow?.disease || null,
        modelClassId: topNow?.idx ?? null,
        sourceAiCrop: aiCrop,
      });
      if (currentImageEl && currentImageDataUrl) {
        analyzeStatus.hidden = false;
        analyzeStatus.textContent = 'Re-analysing with ' + chosen + '…';
        const diag = await diagnoseWithFallback(currentImageEl, { dataUrl: currentImageDataUrl, crop: chosen });
        await renderResult(diag);
        await persistResult(diag);
        setCorrectionNote('✓ Crop manually set to ' + chosen);
      }
    } catch (err) {
      console.warn('[App] Could not apply crop correction:', err.message);
    } finally {
      cropSaveBtn.disabled = false;
      hideCropSelector();
      analyzeStatus.hidden = true;
    }
  });

  cropCancelBtn?.addEventListener('click', () => hideCropSelector());

  async function handleCapture(fromGallery) {
    try {
      const dataUrl = await capturePhoto(fromGallery);
      if (dataUrl) {
        showPreview(dataUrl);
        await runDiagnosis(dataUrl);
      }
    } catch (err) {
      if (err?.message !== 'cancelled') {
        alert('Could not open camera: ' + err.message);
      }
    }
  }

  captureBtn?.addEventListener('click', () => handleCapture(false));
  galleryBtn?.addEventListener('click', () => handleCapture(true));
  retakeBtn?.addEventListener('click', () => { resetPreview(); handleCapture(false); });

  document.getElementById('btn-photo')?.addEventListener('click', () => {
    window.location.href = 'app.html?camera=1';
  });
  document.getElementById('btn-live')?.addEventListener('click', () => {
    window.open('live.html', '_blank');
  });

  if (new URLSearchParams(location.search).get('camera') === '1') {
    showPage('diagnose');
    handleCapture(false).catch((err) => {
      if (err?.message !== 'cancelled') console.warn('[App] Auto camera open failed:', err.message);
    });
  }

  /* ─── Speak button ───────────────────────────────────────────────────────── */
  speakBtn?.addEventListener('click', async () => {
    if (!lastDiagnosis) return;
    const { info, diag } = lastDiagnosis;
    const lang = getLanguage();

    if (diag.rejected) {
      // Rejection branch
      const textToSpeak = resultDisease.textContent + '. ' + resultConfidence.textContent;
      await speak(textToSpeak, lang, null);
      return;
    }

    const disease = (info?.disease) || diag.top?.disease || 'Unknown';
    const crop = (info?.crop) || diag.top?.crop || '';
    const treat = info?.treatment || '';
    const isHealthy = info?.isHealthy ?? false;

    const text = isHealthy
      ? `${crop} - ${treat || 'Healthy'}`
      : `${crop} ${disease}. ${treat}`;

    // Pass info?.id so voice.js can fetch the pre-generated Tier 1 audio clip
    await speak(text, lang, info?.id);
  });

  /* ── Farmer registration form ──────────────────────────────────────────── */
  const farmerForm = document.getElementById('farmerForm');
  if (farmerForm) {
    farmerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('farmerName')?.value.trim();
      const nin = document.getElementById('farmerNin')?.value.trim();
      const village = document.getElementById('farmerVillage')?.value.trim();
      const state = document.getElementById('farmerState')?.value.trim();
      const phone = document.getElementById('farmerPhone')?.value.trim();
      const lang = document.getElementById('farmerLang')?.value || 'English';

      if (!name) {
        alert('Please enter the farmer\'s name.');
        return;
      }

      if (nin && !/^\d{11}$/.test(nin)) {
        alert('NIN must be exactly 11 digits.');
        return;
      }

      const submitBtn = farmerForm.querySelector('[type="submit"]');
      const origText = submitBtn?.textContent;
      if (submitBtn) { submitBtn.textContent = 'Saving…'; submitBtn.disabled = true; }

      try {
        await saveFarmer({ name, nin, village, state, phone, language: lang });
        farmerForm.reset();
        showSaveConfirmation(farmerForm);
        // Increment pending sync counter ONLY on successful save
        const c = getSyncCounts();
        localStorage.setItem('agrinovva_pending', String(c.pending + 1));
        renderSync();
        // Refresh farmer dropdown in Diagnose tab
        await loadFarmersDropdown();
      } catch (err) {
        alert('Could not save farmer: ' + (err.message || 'Database not available in browser preview.'));
      } finally {
        if (submitBtn) { submitBtn.textContent = origText; submitBtn.disabled = false; }
      }
    });
  }

  function showSaveConfirmation(form) {
    let msg = form.querySelector('.save-confirmation');
    if (!msg) {
      msg = document.createElement('p');
      msg.className = 'save-confirmation';
      form.appendChild(msg);
    }
    msg.textContent = '✅ Farmer saved offline!';
    msg.style.opacity = '1';
    setTimeout(() => { msg.style.opacity = '0'; }, 3000);
  }

  /* ── Data Management ─────────────────────────────────────────────────────── */
  const clearDataBtn = document.getElementById('clearDataBtn');
  const syncDataBtn = document.getElementById('syncDataBtn');

  if (clearDataBtn) {
    clearDataBtn.addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear all local farmer and diagnosis data? This cannot be undone.')) {
        try {
          await clearDatabase();
          alert('Local data cleared successfully.');
          await loadRecentDiagnoses();
          await loadFarmersDropdown();
          allHistoryRows = [];
          renderFilteredHistory();
        } catch (err) {
          alert('Could not clear data: ' + err.message);
        }
      }
    });
  }

  if (syncDataBtn) {
    syncDataBtn.addEventListener('click', () => {
      alert('Cloud Sync will be available in Phase 6.');
    });
  }

  const pendingEl = document.getElementById('pendingCount');
  const syncedEl = document.getElementById('syncedCount');
  const badgeEl = document.getElementById('syncBadge');
  const lastSyncEl = document.getElementById('lastSyncText');
  const fakeSyncBtn = document.getElementById('fakeSyncBtn');

  function getSyncCounts() {
    try {
      const p = parseInt(localStorage.getItem('agrinovva_pending') || '0', 10);
      const s = parseInt(localStorage.getItem('agrinovva_synced') || '0', 10);
      return { pending: isNaN(p) ? 0 : p, synced: isNaN(s) ? 0 : s };
    } catch { return { pending: 0, synced: 0 }; }
  }

  function renderSync() {
    const { pending, synced } = getSyncCounts();
    if (pendingEl) pendingEl.textContent = String(pending);
    if (syncedEl) syncedEl.textContent = String(synced);
    if (badgeEl) {
      if (pending > 0) {
        badgeEl.textContent = '● Pending Sync';
        badgeEl.style.background = '#FFF7ED';
        badgeEl.style.color = '#9A3412';
        badgeEl.style.borderColor = '#FDBA74';
      } else {
        badgeEl.textContent = '● Synced';
        badgeEl.style.background = '#ECFDF5';
        badgeEl.style.color = '#065F46';
        badgeEl.style.borderColor = '#6EE7B7';
      }
    }
    const last = localStorage.getItem('agrinovva_lastSync');
    if (lastSyncEl) lastSyncEl.textContent = last ? 'Last sync: ' + last : 'Last sync: never';
  }

  if (fakeSyncBtn) {
    fakeSyncBtn.addEventListener('click', () => {
      const c = getSyncCounts();
      if (c.pending === 0) { alert('No pending farmers — all synced!'); return; }
      fakeSyncBtn.textContent = 'Syncing…';
      fakeSyncBtn.disabled = true;
      setTimeout(() => {
        const now = new Date().toLocaleString('en-NG');
        localStorage.setItem('agrinovva_synced', String(c.synced + c.pending));
        localStorage.setItem('agrinovva_pending', '0');
        localStorage.setItem('agrinovva_lastSync', now);
        renderSync();
        fakeSyncBtn.textContent = 'Sync Now (offline-first queue)';
        fakeSyncBtn.disabled = false;
        alert('Sync complete — ' + (c.synced + c.pending) + ' records synced.');
      }, 1200);
    });
  }

  renderSync();

  const agentSaveBtn = document.getElementById('agentCheckSaveBtn');
  const agentResetBtn = document.getElementById('agentCheckResetBtn');
  const agentHint = document.getElementById('agentCheckHint');
  const agentPhotoBtn = document.getElementById('agentPhotoBtn');
  const agentGalleryBtn = document.getElementById('agentGalleryBtn');
  const agentPreview = document.getElementById('agentPhotoPreview');
  const agentPreviewImg = document.getElementById('agentPreviewImg');
  const agentMeta = document.getElementById('agentPhotoMeta');

  function getChecks() { return Array.from(document.querySelectorAll('.agent-check')); }

  if (agentSaveBtn) {
    agentSaveBtn.addEventListener('click', () => {
      const checks = getChecks();
      const done = checks.filter(c => c.checked).length;
      const total = checks.length;
      const payload = { at: new Date().toISOString(), done, total, checks: checks.map(c => c.checked) };
      try { localStorage.setItem('agrinovva_agent_report', JSON.stringify(payload)); } catch {}
      if (agentHint) {
        agentHint.textContent = done === total ? '✅ Field report saved offline — ' + done + '/' + total + ' checks done.' : '⚠️ Saved offline — ' + done + '/' + total + ' checks (complete all for 100%).';
        agentHint.style.color = done === total ? '#065F46' : '#9A3412';
      }
    });
  }

  if (agentResetBtn) {
    agentResetBtn.addEventListener('click', () => {
      getChecks().forEach(c => c.checked = false);
      if (agentHint) agentHint.textContent = '';
    });
  }

  async function handleAgentPhoto(fromGallery) {
    try {
      const dataUrl = await capturePhoto(fromGallery);
      if (dataUrl && agentPreviewImg && agentPreview) {
        agentPreviewImg.src = dataUrl;
        agentPreview.style.display = 'block';
        if (agentMeta) agentMeta.textContent = 'Evidence captured — ' + new Date().toLocaleString('en-NG') + ' · geo-tagged (demo) · stored locally';
        try { localStorage.setItem('agrinovva_agent_photo', dataUrl); } catch (e) {
          console.warn('[Agent] Could not cache full photo in localStorage:', e);
        }
      }
    } catch (err) {
      if (err?.message !== 'cancelled') alert('Could not open camera: ' + err.message);
    }
  }

  if (agentPhotoBtn) agentPhotoBtn.addEventListener('click', () => handleAgentPhoto(false));
  if (agentGalleryBtn) agentGalleryBtn.addEventListener('click', () => handleAgentPhoto(true));
});