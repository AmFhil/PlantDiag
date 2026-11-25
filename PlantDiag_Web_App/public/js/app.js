/**
 * PlantDiag Web Application JavaScript
 * Connects to Python TFLite server for dual-model AI diagnosis.
 */

'use strict';

let currentModel = 'v2.0';
let currentImageData = null;
let lastDiagnosisResult = null;

// DOM Elements
const btnModelV2 = document.getElementById('btnModelV2');
const btnModelV1 = document.getElementById('btnModelV1');
const activeModelHint = document.getElementById('activeModelHint');

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const dropPrompt = document.getElementById('dropPrompt');
const previewImg = document.getElementById('previewImg');
const sampleChips = document.querySelectorAll('.sample-chip');

const analyzeBtn = document.getElementById('analyzeBtn');
const analyzeSpinner = document.getElementById('analyzeSpinner');
const analyzeBtnText = document.getElementById('analyzeBtnText');

const langSelect = document.getElementById('langSelect');
const resultPlaceholder = document.getElementById('resultPlaceholder');
const resultContent = document.getElementById('resultContent');

const resCropName = document.getElementById('resCropName');
const resDiseaseName = document.getElementById('resDiseaseName');
const resSeverity = document.getElementById('resSeverity');
const resConfidenceVal = document.getElementById('resConfidenceVal');
const resConfidenceBar = document.getElementById('resConfidenceBar');
const resSymptoms = document.getElementById('resSymptoms');
const resTreatment = document.getElementById('resTreatment');
const resEngineTag = document.getElementById('resEngineTag');
const resTop3List = document.getElementById('resTop3List');
const speakBtn = document.getElementById('speakBtn');
const speakBtnText = document.getElementById('speakBtnText');

// 1. Model Selection
btnModelV2.addEventListener('click', () => setModel('v2.0'));
btnModelV1.addEventListener('click', () => setModel('v1.7'));

function setModel(ver) {
  currentModel = ver;
  if (ver === 'v2.0') {
    btnModelV2.classList.add('active');
    btnModelV1.classList.remove('active');
    activeModelHint.textContent = 'Targeting: Cassava & Rice (v2.0)';
  } else {
    btnModelV1.classList.add('active');
    btnModelV2.classList.remove('active');
    activeModelHint.textContent = 'Targeting: 38 Garden & Commercial Crops (v1.7)';
  }
  // Re-diagnose if image is already loaded
  if (currentImageData) {
    runDiagnosis();
  }
}

// 2. File Upload & Drag-and-Drop
browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files[0]) {
    loadImageFile(e.target.files[0]);
  }
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    loadImageFile(e.dataTransfer.files[0]);
  }
});

function loadImageFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    setImageData(e.target.result);
  };
  reader.readAsDataURL(file);
}

function setImageData(dataUrl) {
  currentImageData = dataUrl;
  previewImg.src = dataUrl;
  previewImg.hidden = false;
  dropPrompt.hidden = true;
  analyzeBtn.disabled = false;
  analyzeBtnText.textContent = 'Diagnose Leaf Now';
  runDiagnosis();
}

// 3. Quick Sample Chips
sampleChips.forEach((chip) => {
  chip.addEventListener('click', () => {
    const imgPath = chip.getAttribute('data-img');
    const prefModel = chip.getAttribute('data-preferred');

    if (prefModel && prefModel !== currentModel) {
      setModel(prefModel);
    }

    // Convert local sample to data URL
    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      setImageData(canvas.toDataURL('image/jpeg'));
    };
    img.src = imgPath;
  });
});

analyzeBtn.addEventListener('click', runDiagnosis);

// 4. API Inference Call
async function runDiagnosis() {
  if (!currentImageData) return;

  analyzeBtn.disabled = true;
  analyzeSpinner.hidden = false;
  analyzeBtnText.textContent = 'Analyzing Neural Features…';

  try {
    const res = await fetch('/api/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: currentImageData,
        model: currentModel
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned error ${res.status}`);
    }

    const data = await res.json();
    lastDiagnosisResult = data;
    renderDiagnosis(data);

  } catch (err) {
    alert('Diagnosis Error: ' + err.message + '\nMake sure server.py is running on port 8000.');
  } finally {
    analyzeBtn.disabled = false;
    analyzeSpinner.hidden = true;
    analyzeBtnText.textContent = 'Re-Diagnose Leaf';
  }
}

// 5. Render Diagnosis
function renderDiagnosis(data) {
  resultPlaceholder.hidden = true;
  resultContent.hidden = false;

  const top = data.top;
  const isHealthy = top.is_healthy;
  const details = top.details || {};

  resCropName.textContent = top.crop;
  resDiseaseName.textContent = top.disease;
  resConfidenceVal.textContent = top.percentage + '%';
  resConfidenceBar.style.width = top.percentage + '%';

  // Severity
  const sev = (details.severity || (isHealthy ? 'none' : 'moderate')).toLowerCase();
  resSeverity.className = 'severity-badge ' + (sev === 'none' ? 'healthy' : sev);
  resSeverity.textContent = sev === 'none' ? 'Healthy Tissue' : (sev.toUpperCase() + ' SEVERITY');

  // Symptoms
  resSymptoms.textContent = details.symptoms || 'Visual pathology consistent with ' + top.disease + '.';

  // Treatment by Language
  updateTreatmentLanguage();

  // Engine tag
  resEngineTag.textContent = `Engine: ${data.model_version === 'v2.0' ? 'Fine-Tuned MobileNetV3 (v2.0)' : 'PlantVillage ResNet18 (v1.7)'}`;

  // Top 3 list
  resTop3List.innerHTML = '';
  (data.top3 || []).forEach((item) => {
    const div = document.createElement('div');
    div.className = 'top3-item';
    div.innerHTML = `
      <span class="top3-name">${item.crop} — ${item.disease}</span>
      <span class="top3-pct">${item.percentage}%</span>
    `;
    resTop3List.appendChild(div);
  });
}

// 6. Language Updates
langSelect.addEventListener('change', updateTreatmentLanguage);

function updateTreatmentLanguage() {
  if (!lastDiagnosisResult || !lastDiagnosisResult.top) return;

  const details = lastDiagnosisResult.top.details || {};
  const lang = langSelect.value;

  let treatmentText = details.treatment || 'Consult local agricultural extension officer for customized chemical/organic treatment.';

  if (lang === 'ha' && details.treatment_ha) treatmentText = details.treatment_ha;
  if (lang === 'yo' && details.treatment_yo) treatmentText = details.treatment_yo;
  if (lang === 'ig' && details.treatment_ig) treatmentText = details.treatment_ig;
  if (lang === 'pcm' && details.treatment_pcm) treatmentText = details.treatment_pcm;

  resTreatment.textContent = treatmentText;
}

// 7. Speech Synthesis
speakBtn.addEventListener('click', () => {
  if (!lastDiagnosisResult || !lastDiagnosisResult.top) return;

  const top = lastDiagnosisResult.top;
  const treat = resTreatment.textContent;
  const textToSpeak = `${top.crop}, ${top.disease}. ${treat}`;

  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    speakBtnText.textContent = 'Speaking…';
    utterance.onend = () => { speakBtnText.textContent = 'Hear Advice Aloud'; };
    utterance.onerror = () => { speakBtnText.textContent = 'Hear Advice Aloud'; };

    window.speechSynthesis.speak(utterance);
  } else {
    alert('Speech synthesis is not supported on this browser.');
  }
});
