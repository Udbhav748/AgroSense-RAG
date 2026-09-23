// Captures real screenshots of the running app (frontend on :5173, backend
// on :8000) for README use -- a fresh signed-up account, real upload,
// real chat answer, real diagnose call. Not mockups.
//
// Usage: node scripts/capture_screenshots.mjs
// Requires: frontend dev server on http://localhost:5173, backend on :8000.

import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..', '..');
const OUT_DIR = path.join(ROOT, 'docs', 'screenshots');
const PDF_PATH = path.join(ROOT, 'backend', 'corpus', 'leafsense_test', '01_apple_diseases.pdf');
const LEAF_IMAGE = path.join(ROOT, 'backend', 'eval', 'module10', 'assets', 'synthetic_leaf_with_spots.jpg');

const BASE_URL = 'http://127.0.0.1:5174';
const EMAIL = `screenshots-${Date.now()}@agrosense-demo.local`;
const PASSWORD = 'ScreenshotPass123!';

fs.mkdirSync(OUT_DIR, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  await context.addInitScript(() => {
    window.localStorage.setItem('insightai-theme', 'light');
  });
  const page = await context.newPage();

  // ---- Signup ----
  await page.goto(`${BASE_URL}/signup`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#email');
  await page.screenshot({ path: path.join(OUT_DIR, 'signup.png') });
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.click('input[type="checkbox"]');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/chat', { timeout: 15000 });
  await sleep(1000);

  // ---- Home ----
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await page.screenshot({ path: path.join(OUT_DIR, 'home.png') });

  // ---- Upload ----
  await page.goto(`${BASE_URL}/upload`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('input[type="file"]', { state: 'attached' });
  await sleep(500);
  await page.screenshot({ path: path.join(OUT_DIR, 'upload.png') });
  await page.setInputFiles('input[type="file"]', PDF_PATH);
  await page.waitForSelector('text=Start chatting', { timeout: 60000 });
  await sleep(1000);
  await page.screenshot({ path: path.join(OUT_DIR, 'upload-complete.png') });

  // ---- Documents ----
  await page.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await page.screenshot({ path: path.join(OUT_DIR, 'documents.png') });

  // ---- Chat with grounded answer ----
  await page.goto(`${BASE_URL}/chat`, { waitUntil: 'domcontentloaded' });
  const chatInput = page.getByPlaceholder('Ask a question about your documents...');
  await chatInput.waitFor();
  await chatInput.fill('What apple diseases are covered in this document, and what are their symptoms?');
  await page.getByRole('button', { name: 'Send message' }).click();
  const goodResponseBtn = page.getByRole('button', { name: 'Good response' });
  await goodResponseBtn.first().waitFor({ timeout: 90000 });
  await sleep(1500);
  await page.screenshot({ path: path.join(OUT_DIR, 'chat.png') });

  // ---- Command palette (Cmd/Ctrl+K) ----
  await page.keyboard.press('Control+k');
  const paletteInput = page.getByPlaceholder(/type a command|search/i).first();
  const paletteAppeared = await paletteInput.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
  if (paletteAppeared) {
    await sleep(500);
    await page.screenshot({ path: path.join(OUT_DIR, 'command-palette.png') });
    await page.keyboard.press('Escape');
    await sleep(300);
  }

  // ---- Diagnose ----
  await page.goto(`${BASE_URL}/diagnose`, { waitUntil: 'domcontentloaded' });
  await sleep(1000);
  const leafFileInput = page.locator('[data-testid="leaf-file-input"]');
  await leafFileInput.waitFor({ state: 'attached', timeout: 10000 }).catch(() => null);
  if (await leafFileInput.count()) {
    // Prefer the Gemini engine explicitly since LeafSense (port 8001)
    // isn't running in this environment -- real diagnosis either way.
    const geminiBtn = page.getByRole('button', { name: /multimodal vision \(gemini\)/i });
    if (await geminiBtn.count()) {
      await geminiBtn.click();
      await sleep(500);
    }
    await leafFileInput.setInputFiles(LEAF_IMAGE);
    const analyzeBtn = page.getByRole('button', { name: /diagnose plant leaf/i }).first();
    const appeared = await analyzeBtn.waitFor({ state: 'visible', timeout: 10000 }).then(() => true).catch(() => false);
    if (appeared) {
      await page.screenshot({ path: path.join(OUT_DIR, 'diagnose-upload.png') });
      await analyzeBtn.click();
      const tabsAppeared = await page
        .getByRole('tablist', { name: 'Treatment plan tabs' })
        .waitFor({ timeout: 120000 })
        .then(() => true)
        .catch(() => false);
      if (tabsAppeared) {
        await sleep(1500);
        await page.screenshot({ path: path.join(OUT_DIR, 'diagnose-result.png') });
        // Scroll to the calculator for a second shot.
        const fieldSizeInput = page.locator('#field-size-input');
        const calcAppeared = await fieldSizeInput.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
        if (calcAppeared) {
          await fieldSizeInput.scrollIntoViewIfNeeded();
          await fieldSizeInput.fill('2.5');
          await sleep(800);
          await page.screenshot({ path: path.join(OUT_DIR, 'diagnose-calculator.png') });
        }

        // Prescription work order modal.
        const downloadRxBtn = page.locator('[data-testid="download-prescription-button"]');
        const rxAppeared = await downloadRxBtn.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
        if (rxAppeared) {
          await downloadRxBtn.scrollIntoViewIfNeeded();
          await downloadRxBtn.click();
          const modalAppeared = await page
            .getByRole('dialog')
            .waitFor({ state: 'visible', timeout: 8000 })
            .then(() => true)
            .catch(() => false);
          if (modalAppeared) {
            await sleep(800);
            await page.screenshot({ path: path.join(OUT_DIR, 'prescription-work-order.png') });
            await page.keyboard.press('Escape');
            await sleep(300);
          }
        }
      }
    }
  }

  // ---- History ----
  await page.goto(`${BASE_URL}/history`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await page.screenshot({ path: path.join(OUT_DIR, 'history.png') });

  // ---- Settings ----
  await page.goto(`${BASE_URL}/settings`, { waitUntil: 'domcontentloaded' });
  await sleep(1000);
  await page.screenshot({ path: path.join(OUT_DIR, 'settings.png') });

  // ---- Architecture ----
  await page.goto(`${BASE_URL}/architecture`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await page.screenshot({ path: path.join(OUT_DIR, 'architecture.png') });

  await context.close();
  await browser.close();
  console.log('Screenshots saved to', OUT_DIR);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
