const fs = require('fs');

const checks = [];

// 1. index.html checks
const html = fs.readFileSync('src/index.html', 'utf8');
checks.push(['Header lang select exists',     html.includes('id="globalLangSelect"')]);
checks.push(['Hausa/Yoruba/Igbo options',     html.includes('Hausa') && html.includes('Yoruba') && html.includes('Igbo')]);
checks.push(['Offline badge exists',           html.includes('id="offlineBadge"')]);
checks.push(['History search bar',            html.includes('id="historySearch"')]);
checks.push(['Nigerian states dropdown',       html.includes('>Lagos<') && html.includes('>Kaduna<') && html.includes('>Kano<')]);
checks.push(['State is select not text input', !html.includes('type="text" id="farmerState"')]);
checks.push(['Sync Data button',              html.includes('id="syncDataBtn"')]);
checks.push(['Clear Data button',             html.includes('id="clearDataBtn"')]);
checks.push(['Phase 4 in About',              html.includes('Phase 4')]);
checks.push(['Old langSelect removed',        !html.includes('id="langSelect"')]);
checks.push(['Old appLangSelect removed',     !html.includes('id="appLangSelect"')]);

// 2. app.js checks
const app = fs.readFileSync('src/js/app.js', 'utf8');
checks.push(['globalLangSelect wired in app.js',  app.includes('globalLangSelect')]);
checks.push(['NIN 11-digit validation',            app.includes('11')]);
checks.push(['renderFilteredHistory function',    app.includes('renderFilteredHistory')]);
checks.push(['clearDatabase imported',            app.includes('clearDatabase')]);
checks.push(['syncDataBtn wired',                 app.includes('syncDataBtn')]);
checks.push(['clearDataBtn wired',                app.includes('clearDataBtn')]);

// 3. database.js checks
const db = fs.readFileSync('src/js/database.js', 'utf8');
checks.push(['clearDatabase exported',            db.includes('export async function clearDatabase')]);
checks.push(['Diagnoses table schema',            db.includes('CREATE TABLE IF NOT EXISTS diagnoses')]);
checks.push(['Farmers table schema',              db.includes('CREATE TABLE IF NOT EXISTS farmers')]);

// 4. voice.js checks
const voice = fs.readFileSync('src/js/voice.js', 'utf8');
checks.push(['speak() exported',                  voice.includes('export async function speak')]);
checks.push(['stopSpeech() exported',             voice.includes('export function stopSpeech')]);

// 5. Audio manifest
const manifestPath = 'src/assets/audio/MANIFEST.json';
const manifestExists = fs.existsSync(manifestPath);
checks.push(['Audio MANIFEST.json exists',        manifestExists]);
if (manifestExists) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const keys = Object.keys(manifest);
  checks.push(['Manifest has entries',            keys.length > 0]);
  checks.push(['Has English entries',             keys.some(k => k.includes('English'))]);
  checks.push(['Has Hausa entries',               keys.some(k => k.includes('Hausa'))]);
}

// 6. style.css checks
const css = fs.readFileSync('src/css/style.css', 'utf8');
checks.push(['header-lang-select styled',         css.includes('.header-lang-select')]);

// Print results
let passed = 0, failed = 0;
checks.forEach(([name, result]) => {
  const icon = result ? 'PASS' : 'FAIL';
  console.log('[' + icon + '] ' + name);
  result ? passed++ : failed++;
});
console.log('');
console.log('Results: ' + passed + ' passed, ' + failed + ' failed out of ' + checks.length + ' checks');
