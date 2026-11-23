// Renders a fox scene frame by frame with its sound, offline (not in real time).
// Usage: node render.js <page-url> <out-dir> <seconds> [--audio-only] [--size 640x360]
// Writes <out-dir>/raw.mp4 (30 fps, picture only) and <out-dir>/raw.f32 (48 kHz stereo, 32-bit float, interleaved).
// Without --size the picture is 1920x1080. With --size 640x360 a pixel-grid scene is captured at its own resolution, one
// screen pixel per scene pixel and without any compression loss, so it can later be scaled up by whole numbers (x3 = 1080p,
// x4 = 1440p) and stay perfectly sharp. It also renders several times faster.
// It also writes <out-dir>/events.json: the occasional sounds of this take and when they fall.
// Both start PRE seconds into the scene, once the snow, steam and wind have settled, so the first frame is already "mid-storm".
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const args = process.argv.slice(2), audioOnly = args.includes('--audio-only');
const size = args.includes('--size') ? args[args.indexOf('--size') + 1].split('x').map(Number) : null;
const [url, out, secs] = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--size');
const FPS = 30, PRE = 10, TOTAL = PRE + (+secs), SR = 48000;
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: size ? { width: size[0], height: size[1] } : { width: 1920, height: 1080 } });
  p.on('pageerror', e => console.error('PAGEERR', String(e)));
  p.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await p.addInitScript(({ TOTAL, SR }) => {
    let a = 20261120;     // fixed seed: the same scene always renders the same way
    Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    window.__render = { t: 0, ac: new OfflineAudioContext(2, Math.ceil(SR * TOTAL), SR) };
  }, { TOTAL, SR });
  await p.goto(url);
  await p.waitForFunction(() => window.__render.frame && window.__render.ready());
  await p.waitForTimeout(500);
  await p.evaluate(() => window.__render.start());
  const t0 = Date.now();
  if (audioOnly) {
    await p.evaluate(TOTAL => { const R = window.__render; for (let t = 0; t < TOTAL; t += 0.45) { R.t = t; R.tick(); } }, TOTAL);
  } else {
    const enc = size ? ['-c:v', 'png', '-i', '-', '-c:v', 'libx264rgb', '-preset', 'veryfast', '-crf', '0']                      // exact pixels in, lossless out
      : ['-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p'];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), ...enc, out + '/raw.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
    const N = Math.round(TOTAL * FPS); let nextTick = 0;
    for (let i = 0; i < N; i++) {
      const t = i / FPS, doTick = t >= nextTick; if (doTick) nextTick += 0.45;
      await p.evaluate(({ t, doTick }) => { const R = window.__render; R.t = t; if (doTick) R.tick(); R.frame(); }, { t, doTick });
      if (t >= PRE) { const buf = await p.screenshot(size ? { type: 'png' } : { type: 'jpeg', quality: 96 }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
      if (i % 600 === 0) console.log('frame', i, '/', N, ((Date.now() - t0) / 1000).toFixed(0) + 's');
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  // sound: render the whole timeline, drop the settling time, write left/right interleaved
  const len = await p.evaluate(async ({ PRE, SR }) => {
    const buf = await window.__render.ac.startRendering(), L = buf.getChannelData(0), Rr = buf.getChannelData(1), o = PRE * SR, n = L.length - o;
    const pcm = new Float32Array(2 * n); for (let i = 0; i < n; i++) { pcm[2 * i] = L[o + i]; pcm[2 * i + 1] = Rr[o + i]; }
    window.__pcm = pcm; return pcm.length;
  }, { PRE, SR });
  const fd = fs.openSync(out + '/raw.f32', 'w'), CH = 1 << 20;
  for (let o = 0; o < len; o += CH) {
    const b64 = await p.evaluate(({ o, CH }) => { const s = window.__pcm.subarray(o, o + CH), u = new Uint8Array(s.buffer, s.byteOffset, s.byteLength); let r = ''; for (let i = 0; i < u.length; i += 32768) r += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(r); }, { o, CH });
    fs.writeSync(fd, Buffer.from(b64, 'base64'));
  }
  fs.closeSync(fd);
  const log = await p.evaluate(() => window.__render.log || []);      // the occasional sounds of this take (gusts hitting the wall, the stove settling), in seconds from the start of the file
  fs.writeFileSync(out + '/events.json', JSON.stringify(log.map(([k, t]) => [k, +(t - PRE).toFixed(2)]).filter(e => e[1] >= 0)));
  console.log('done', len / 2 / SR, 's of sound', ((Date.now() - t0) / 1000).toFixed(0) + 's');
  await b.close();
})();
