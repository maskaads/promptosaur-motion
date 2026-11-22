#!/usr/bin/env node
// Frame-by-frame capture of an HTML or SVG page in headless Chrome.
//
// The page is rendered at exact times, one frame after another, so the same
// page gives the same video on every run. Frames go to a folder as PNG files.
// A stopped run resumes where it stopped: frames that exist are skipped.
//
// How time reaches the page:
//   1. If the page defines  window.renderFrame = async (frame, fps) => {...}
//      it is called for every frame. Seek your GSAP timeline, set your Three.js
//      clock, draw your canvas there.
//   2. Otherwise every CSS and Web Animation on the page is paused and set to
//      the frame time (works for CSS keyframes and animated SVG).
//   In both cases Date.now(), performance.now() and requestAnimationFrame
//   follow the frame clock, never the wall clock.
//
// Usage:
//   node capture.mjs index.html --duration 15 [--fps 30] [--width 1920 --height 1080]
//                    [--out frames] [--start 0] [--end N] [--jpg] [--require-gpu] [--exact]
//                    [--encode final.mp4 [--audio mix.wav]] [--chrome PATH]
//
// --exact draws 2D content on the processor so two runs match pixel for pixel
// (WebGL stays on the GPU). It also drops gradient dithering: bake large
// gradients into images, or add a little noise, when you use it.
// Text is always drawn with grayscale smoothing (--disable-lcd-text), so it
// does not flicker between frames.
//
// Needs: npm i puppeteer-core   (uses your installed Chrome)
//    or: npm i puppeteer        (downloads its own Chrome)

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const args = parseArgs(process.argv.slice(2));
if (!args._[0]) {
  console.error('usage: node capture.mjs <page.html|page.svg|url> --duration <s> [options]');
  process.exit(2);
}

const fps = Number(args.fps ?? 30);
const width = Number(args.width ?? 1920);
const height = Number(args.height ?? 1080);
const outDir = path.resolve(args.out ?? 'frames');
const ext = args.jpg ? 'jpg' : 'png';
const target = /^https?:/.test(args._[0]) ? args._[0] : pathToFileURL(path.resolve(args._[0])).href;

const puppeteer = await loadPuppeteer();
const executablePath = args.chrome ?? process.env.CHROME_PATH ?? findChrome();

// GPU flags per platform. Without them headless Chrome often falls back to
// SwiftShader, a software renderer: 3D then runs on the processor, many times slower.
const gpuFlags = {
  win32: ['--use-angle=d3d11'],
  darwin: ['--use-angle=metal'],
  linux: ['--use-angle=vulkan', '--enable-features=Vulkan', '--use-vulkan'],
}[process.platform] ?? [];

const browser = await puppeteer.launch({
  headless: true,
  executablePath,
  args: ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-webgpu',
         '--hide-scrollbars', '--mute-audio', '--disable-lcd-text', '--allow-file-access-from-files', '--force-color-profile=srgb', ...(args['exact'] ? ['--disable-gpu-rasterization'] : []), ...gpuFlags],
  defaultViewport: { width, height, deviceScaleFactor: 1 },
});

try {
  const page = await browser.newPage();
  page.on('pageerror', e => console.error('[page error]', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('[page console]', m.text()); });

  // Frame clock, installed before any page script runs.
  await page.evaluateOnNewDocument(() => {
    let t = 0;
    const rafQueue = [];
    window.__setClock = ms => { t = ms; };
    window.__flushRaf = () => {
      const q = rafQueue.splice(0);
      for (const cb of q) { try { cb(t); } catch (e) { console.error(e); } }
    };
    const start = 1767225600000; // fixed date, so Date.now() is the same on every run
    performance.now = () => t;
    Date.now = () => start + t;
    window.requestAnimationFrame = cb => { rafQueue.push(cb); return rafQueue.length; };
    window.cancelAnimationFrame = () => {};
  });

  await page.goto(target, { waitUntil: 'networkidle0', timeout: 120000 });

  const gpu = await page.evaluate(() => {
    try {
      const c = document.createElement('canvas');
      const gl = c.getContext('webgl2') || c.getContext('webgl');
      if (!gl) return 'no WebGL';
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      return dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    } catch (e) { return 'unknown: ' + e.message; }
  });
  const software = /swiftshader|llvmpipe|software|no webgl/i.test(gpu);
  console.log(`renderer: ${gpu}${software ? '   <-- SOFTWARE, frames are drawn on the processor' : ''}`);
  if (software && args['require-gpu']) {
    console.error('stopped: --require-gpu is set and Chrome has no GPU. Check drivers and the flags above.');
    process.exit(3);
  }

  await page.evaluate(() => document.fonts && document.fonts.ready);
  const hasRender = await page.evaluate(() => typeof window.renderFrame === 'function');
  const duration = Number(args.duration ?? await page.evaluate(() => window.DURATION ?? 0));
  if (!duration) { console.error('set --duration or window.DURATION on the page'); process.exit(2); }

  const total = Math.round(duration * fps);
  const first = Number(args.start ?? 0);
  const last = Math.min(Number(args.end ?? total), total);
  fs.mkdirSync(outDir, { recursive: true });
  console.log(`${total} frames at ${fps} fps, ${width}x${height}, mode: ${hasRender ? 'renderFrame()' : 'CSS / Web Animations'}`);

  const t0 = process.hrtime.bigint();
  let done = 0;
  for (let f = first; f < last; f++) {
    const file = path.join(outDir, `${String(f).padStart(6, '0')}.${ext}`);
    if (fs.existsSync(file) && fs.statSync(file).size > 0) continue;
    const ms = (f / fps) * 1000;
    await page.evaluate(async (f, fps, ms, hasRender) => {
      window.__setClock(ms);
      if (hasRender) {
        await window.renderFrame(f, fps);
      } else {
        for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
      }
      window.__flushRaf(); // one tick for libraries that draw in requestAnimationFrame
    }, f, fps, ms, hasRender);
    const tmp = file + '.part';
    await page.screenshot({ path: tmp, type: ext === 'jpg' ? 'jpeg' : 'png', quality: ext === 'jpg' ? 95 : undefined, captureBeyondViewport: false });
    fs.renameSync(tmp, file); // a frame file exists only when it is complete
    done++;
    if (done === 1) {
      const msPerFrame = Number(process.hrtime.bigint() - t0) / 1e6;
      console.log(`first frame: ${msPerFrame.toFixed(0)} ms, estimate for this run: ${((msPerFrame * (last - f)) / 60000).toFixed(1)} min`);
    }
    if (f % fps === 0) process.stdout.write(`frame ${f}/${total}\r`);
  }
  console.log(`\ncaptured ${done} new frames into ${outDir}`);

  if (args.encode) encode(outDir, ext, fps, args.encode, args.audio);
} finally {
  await browser.close();
}

function encode(dir, ext, fps, out, audio) {
  const a = ['-y', '-v', 'error', '-framerate', String(fps), '-i', path.join(dir, `%06d.${ext}`)];
  if (audio) a.push('-i', audio);
  a.push('-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart');
  if (audio) a.push('-c:a', 'aac', '-b:a', '192k', '-shortest');
  a.push(out);
  const r = spawnSync('ffmpeg', a, { stdio: 'inherit', windowsHide: true });
  if (r.status !== 0) { console.error('ffmpeg failed'); process.exit(r.status ?? 1); }
  console.log(`encoded ${out}`);
}

async function loadPuppeteer() {
  for (const name of ['puppeteer-core', 'puppeteer']) {
    try { return (await import(name)).default; } catch {}
  }
  console.error('install puppeteer-core (uses your Chrome) or puppeteer: npm i puppeteer-core');
  process.exit(2);
}

function findChrome() {
  const c = {
    win32: [
      `${process.env['PROGRAMFILES']}\\Google\\Chrome\\Application\\chrome.exe`,
      `${process.env['PROGRAMFILES(X86)']}\\Google\\Chrome\\Application\\chrome.exe`,
      `${process.env['LOCALAPPDATA']}\\Google\\Chrome\\Application\\chrome.exe`,
      `${process.env['PROGRAMFILES(X86)']}\\Microsoft\\Edge\\Application\\msedge.exe`,
    ],
    darwin: ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
             '/Applications/Chromium.app/Contents/MacOS/Chromium'],
    linux: ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser'],
  }[process.platform] ?? [];
  return c.find(p => p && fs.existsSync(p)); // undefined: puppeteer uses its own Chrome
}

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      const v = argv[i + 1];
      if (v === undefined || v.startsWith('--')) o[k] = true; else { o[k] = v; i++; }
    } else o._.push(a);
  }
  return o;
}
