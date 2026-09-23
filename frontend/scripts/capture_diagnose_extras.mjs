// Standalone retry: just the diagnose -> calculator -> prescription-modal
// flow, reusing an existing account (signs up fresh, cheap) since the full
// capture_screenshots.mjs run already has the other pages covered.
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..', '..');
const OUT_DIR = path.join(ROOT, 'docs', 'screenshots');
const PDF_PATH = path.join(ROOT, 'backend', 'corpus', 'leafsense_test', '01_apple_diseases.pdf');
const LEAF_IMAGE = path.join(ROOT, 'backend', 'eval', 'module10', 'assets', 'synthetic_leaf_with_spots.jpg');

const BASE_URL = 'http://127.0.0.1:5174';
const EMAIL = `screenshots-diag-${Date.now()}@agrosense-demo.local`;
const PASSWORD = 'ScreenshotPass123!';

function log(...args) {
  console.error(new Date().toISOString(), ...args);
}

async function main() {
  log('launching browser');
  const browser = await chromium.launch({ headless: true });
  log('browser launched');
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  log('page created, navigating to signup');

  await page.goto(`${BASE_URL}/signup`, { waitUntil: 'domcontentloaded', timeout: 20000 });
  log('signup page navigated');
  try {
    await page.waitForSelector('#email', { timeout: 30000 });
  } catch (err) {
    await page.screenshot({ path: path.join(OUT_DIR, '_debug_signup_fail.png') });
    throw err;
  }
  log('email field found, filling form');
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.click('input[type="checkbox"]');
  await page.click('button[type="submit"]');
  log('submitted, waiting for /chat redirect');
  await page.waitForURL('**/chat', { timeout: 15000 });
  log('reached /chat');
  await sleep(500);

  // Upload a doc first so the "continue in chat" path has context (not
  // required for diagnose itself, but keeps behavior consistent).
  await page.goto(`${BASE_URL}/upload`, { waitUntil: 'domcontentloaded', timeout: 20000 });
  log('upload page navigated');
  await page.waitForSelector('input[type="file"]', { state: 'attached' });
  await page.setInputFiles('input[type="file"]', PDF_PATH);
  log('file set, waiting for processing to complete');
  await page.waitForSelector('text=Start chatting', { timeout: 60000 }).catch(() => null);
  log('upload processing done (or timed out waiting)');

  await page.goto(`${BASE_URL}/diagnose`, { waitUntil: 'domcontentloaded', timeout: 20000 });
  log('diagnose page navigated');
  await sleep(1000);
  const leafFileInput = page.locator('[data-testid="leaf-file-input"]');
  await leafFileInput.waitFor({ state: 'attached', timeout: 10000 });
  await leafFileInput.setInputFiles(LEAF_IMAGE);
  log('leaf image set');
  const analyzeBtn = page.getByRole('button', { name: /diagnose plant leaf/i }).first();
  await analyzeBtn.waitFor({ state: 'visible', timeout: 10000 });
  await analyzeBtn.click();
  log('clicked analyze, waiting for result tabs');

  const tabsAppeared = await page
    .getByRole('tablist', { name: 'Treatment plan tabs' })
    .waitFor({ timeout: 150000 })
    .then(() => true)
    .catch(() => false);

  if (!tabsAppeared) {
    console.error('Diagnose did not complete in time; aborting.');
    await browser.close();
    process.exit(1);
  }

  await sleep(1500);
  await page.screenshot({ path: path.join(OUT_DIR, 'diagnose-result.png') });

  const fieldSizeInput = page.locator('#field-size-input');
  const calcAppeared = await fieldSizeInput.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
  if (calcAppeared) {
    await fieldSizeInput.scrollIntoViewIfNeeded();
    await fieldSizeInput.fill('2.5');
    await sleep(800);
    await page.screenshot({ path: path.join(OUT_DIR, 'diagnose-calculator.png') });
  } else {
    console.error('Calculator field not found.');
  }

  const downloadRxBtn = page.locator('[data-testid="download-prescription-button"]');
  const rxAppeared = await downloadRxBtn.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
  if (rxAppeared) {
    await downloadRxBtn.scrollIntoViewIfNeeded();
    await sleep(300);
    await downloadRxBtn.click();
    log('clicked download-prescription-button, waiting for dialog');
    const modalAppeared = await page
      .getByRole('dialog')
      .waitFor({ state: 'visible', timeout: 15000 })
      .then(() => true)
      .catch(() => false);
    if (modalAppeared) {
      await sleep(1000);
      await page.screenshot({ path: path.join(OUT_DIR, 'prescription-work-order.png') });
      log('prescription modal screenshot saved');
    } else {
      log('Prescription modal did not appear; saving debug screenshot');
      await page.screenshot({ path: path.join(OUT_DIR, '_debug_prescription_fail.png') });
    }
  } else {
    log('Download prescription button not found; saving debug screenshot');
    await page.screenshot({ path: path.join(OUT_DIR, '_debug_prescription_fail.png') });
  }

  await browser.close();
  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
