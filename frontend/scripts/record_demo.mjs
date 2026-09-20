// Records a real, working walkthrough of InsightAI-RAG using Playwright.
// Drives the actual running app (frontend on :5173, backend on :8000) with
// a fresh signed-up account and produces a .webm video via Playwright's
// built-in video recorder. No editing/compositing — just real screen capture
// of real actions against the live app.
//
// Usage: node scripts/record_demo.mjs
// Requires: frontend dev server on http://localhost:5173, backend on :8000.

import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..', '..');
const OUT_DIR = path.join(ROOT, 'docs', 'assets', 'demo-raw');
const PDF_PATH = path.join(ROOT, 'backend', 'corpus', 'leafsense_test', '01_apple_diseases.pdf');
const LEAF_IMAGE = path.join(ROOT, 'backend', 'eval', 'module10', 'assets', 'synthetic_leaf_with_spots.jpg');

const BASE_URL = 'http://localhost:5173';
const EMAIL = `demo-${Date.now()}@insightai-demo.local`;
const PASSWORD = 'DemoPassword123!';

async function expectCount(locator, n, timeout) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if ((await locator.count()) >= n) return;
    await sleep(300);
  }
  throw new Error(`Timed out waiting for locator count >= ${n}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: { dir: OUT_DIR, size: { width: 1920, height: 1080 } },
  });
  // Force light theme — dark mode's near-black backgrounds render as
  // near-blank frames on camera.
  await context.addInitScript(() => {
    window.localStorage.setItem('insightai-theme', 'light');
  });

  const page = await context.newPage();

  // ---- Scene 1: cold open on login/signup ----
  await page.goto(`${BASE_URL}/signup`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#email');
  await sleep(1500);

  // ---- Scene 2: signup (JWT auth) ----
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.click('input[type="checkbox"]');
  await sleep(500);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/chat', { timeout: 15000 });
  await sleep(1500);

  // ---- Scene 3: upload & ingestion ----
  await page.goto(`${BASE_URL}/upload`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('input[type="file"]', { state: 'attached' });
  await sleep(1000);
  await page.setInputFiles('input[type="file"]', PDF_PATH);
  // Wait for upload pipeline (extract -> chunk -> embed -> index) to finish.
  await page.waitForSelector('text=Start chatting', { timeout: 60000 });
  await sleep(2000);

  // ---- Scene 4: documents list ----
  await page.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await sleep(2500);

  // ---- Scene 5: chat with grounded answer + citations ----
  await page.goto(`${BASE_URL}/chat`, { waitUntil: 'domcontentloaded' });
  const chatInput = page.getByPlaceholder('Ask a question about your documents...');
  await chatInput.waitFor();
  await chatInput.fill('What apple diseases are covered in this document, and what are their symptoms?');
  await page.getByRole('button', { name: 'Send message' }).click();
  // Wait for the real answer to actually finish streaming (feedback buttons
  // only render on a completed assistant message) rather than guessing a
  // sleep duration for a real network/LLM call.
  const goodResponseBtn = page.getByRole('button', { name: 'Good response' });
  await goodResponseBtn.first().waitFor({ timeout: 90000 });
  await sleep(2500); // let the finished answer sit on screen briefly

  // Second turn: small-talk router path (should skip retrieval).
  await chatInput.fill('Thanks, that was helpful!');
  await page.getByRole('button', { name: 'Send message' }).click();
  await expectCount(goodResponseBtn, 2, 30000);
  await sleep(2000);

  // ---- Scene 6: multimodal diagnose ----
  await page.goto(`${BASE_URL}/diagnose`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  const fileInputs = page.locator('input[type="file"]');
  const count = await fileInputs.count();
  if (count > 0) {
    await fileInputs.first().setInputFiles(LEAF_IMAGE);
    await sleep(1500);
    const analyzeBtn = page.getByRole('button', { name: /diagnose plant leaf/i }).first();
    if (await analyzeBtn.count()) {
      await analyzeBtn.click();
      // Wait for the actual treatment plan (real diagnosis result) to render.
      await page.getByRole('tablist', { name: 'Treatment plan tabs' }).waitFor({ timeout: 90000 });
      // Force a couple of extra paints (scroll nudge) and hold well past the
      // tablist's own appearance — the video encoder can drop/blank frames
      // right at a heavy repaint (charts/gradients), so linger generously.
      await page.mouse.wheel(0, 50);
      await sleep(6000);
    }
  }
  await sleep(1500);

  // ---- Scene 7: history ----
  await page.goto(`${BASE_URL}/history`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await sleep(3000);

  // ---- Scene 8: outro on home ----
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);
  await sleep(3000);

  await context.close();
  await browser.close();
  console.log('Recording saved under', OUT_DIR);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
