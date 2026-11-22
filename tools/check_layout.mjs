#!/usr/bin/env node
// Layout check on rendered frames of an HTML or SVG page.
//
// Mark the elements in your page:
//   data-text            a block of text (a title, a label, a line of a caption)
//   data-solid           a shape that text must not cover
//   data-on="<id>"       on a text: it sits on its own panel, the element with that id
// Every sampled frame is rendered (window.renderFrame or CSS animations, like
// capture.mjs) and every visible marked element is measured. Reported:
//   - text closer than --margin px (default 100) to an edge of the frame;
//   - text over other text;
//   - text over a solid shape that is not its own panel.
// Elements with an effective opacity under 5% are skipped.
//
// Usage:
//   node check_layout.mjs index.html --duration 10 [--fps 30] [--step 2]
//                         [--width 1920 --height 1080] [--margin 100] [--chrome PATH]
// Exit code 1 when anything is reported.

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = parseArgs(process.argv.slice(2));
if (!args._[0]) { console.error('usage: node check_layout.mjs <page> --duration <s>'); process.exit(2); }
const fps = Number(args.fps ?? 30), width = Number(args.width ?? 1920), height = Number(args.height ?? 1080);
const step = Number(args.step ?? 2), M = Number(args.margin ?? 100);
const target = /^https?:/.test(args._[0]) ? args._[0] : pathToFileURL(path.resolve(args._[0])).href;

let puppeteer;
for (const n of ['puppeteer-core', 'puppeteer']) { try { puppeteer = (await import(n)).default; break; } catch {} }
if (!puppeteer) { console.error('npm i puppeteer-core'); process.exit(2); }
const exe = args.chrome ?? process.env.CHROME_PATH ?? [
  `${process.env.PROGRAMFILES}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium',
].find(p => p && fs.existsSync(p));

const browser = await puppeteer.launch({ headless: true, executablePath: exe,
  args: ['--allow-file-access-from-files', '--hide-scrollbars', '--disable-lcd-text'],
  defaultViewport: { width, height, deviceScaleFactor: 1 } });
const found = new Map();
try {
  const page = await browser.newPage();
  await page.goto(target, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  const duration = Number(args.duration ?? await page.evaluate(() => window.DURATION ?? 0));
  if (!duration) { console.error('set --duration'); process.exit(2); }
  const total = Math.round(duration * fps);
  let marked = 0;
  for (let f = 0; f < total; f += step) {
    const boxes = await page.evaluate(async (f, fps) => {
      const ms = f / fps * 1000;
      if (typeof window.renderFrame === 'function') await window.renderFrame(f, fps);
      else for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
      const vis = el => {
        let o = 1;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
          o *= Number(cs.opacity);
        }
        return o;
      };
      return [...document.querySelectorAll('[data-text],[data-solid]')].map((el, k) => {
        const r = el.getBoundingClientRect();
        return { id: el.id || `${el.tagName.toLowerCase()}#${k}`, text: el.hasAttribute('data-text'),
                 on: el.getAttribute('data-on'), o: vis(el), x0: r.left, y0: r.top, x1: r.right, y1: r.bottom };
      }).filter(b => b.o >= 0.05 && b.x1 - b.x0 > 0.5 && b.y1 - b.y0 > 0.5);
    }, f, fps);
    marked = Math.max(marked, boxes.length);
    const hit = (a, b) => a.x0 < b.x1 - 1 && b.x0 < a.x1 - 1 && a.y0 < b.y1 - 1 && b.y0 < a.y1 - 1;
    const texts = boxes.filter(b => b.text), solids = boxes.filter(b => !b.text);
    const add = (key, msg) => { const v = found.get(key); if (v) v.last = f; else found.set(key, { first: f, last: f, msg }); };
    for (const t of texts) {
      if (t.x0 < M || t.y0 < M || t.x1 > width - M || t.y1 > height - M)
        add(`margin ${t.id}`, `text ${t.id} is inside the ${M} px edge margin`);
      for (const u of texts) if (t.id < u.id && hit(t, u)) add(`tt ${t.id} ${u.id}`, `text ${t.id} overlaps text ${u.id}`);
      for (const s of solids) if (s.id !== t.on && hit(t, s)) add(`ts ${t.id} ${s.id}`, `text ${t.id} overlaps shape ${s.id}`);
    }
  }
  if (!marked) console.log('no element has data-text or data-solid; mark them so they can be checked');
  for (const { first, last, msg } of found.values())
    console.log(`ERROR  frames ${first}-${last}  ${msg}`);
  console.log(`${found.size} layout problems (${marked} marked elements, every ${step} frames)`);
} finally {
  await browser.close();
}
process.exit(found.size ? 1 : 0);

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { const v = argv[i + 1]; if (v === undefined || v.startsWith('--')) o[a.slice(2)] = true; else { o[a.slice(2)] = v; i++; } }
    else o._.push(a);
  }
  return o;
}
