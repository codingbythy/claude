const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
// Usage: node render-scene.js <page-url> <out-dir> <loop-seconds> <crossfade-seconds>
const [url, out, Ls, Xs] = process.argv.slice(2);
const FPS = 30, PRE = 10, L = +Ls, X = +Xs, TOTAL = PRE + L + X, SR = 48000;
const STRIKES = [17, 61, 96, 141].filter(t => t < L - 15).map(t => t + PRE);
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  p.on('pageerror', e => console.error('PAGEERR', String(e)));
  await p.addInitScript(({ TOTAL, SR }) => {
    let a = 20261111;
    Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    window.__render = { t: 0, ac: new OfflineAudioContext(1, Math.ceil(SR * TOTAL), SR) };
  }, { TOTAL, SR });
  await p.goto(url);
  await p.waitForFunction(() => window.__render.frame && document.getElementById('base').complete && (!window.__render.ready || window.__render.ready()));
  await p.waitForTimeout(800);
  await p.evaluate(() => { const s = document.getElementById('strikes'); s.value = 'off'; s.dispatchEvent(new Event('change')); try { localStorage.clear(); } catch (e) {} window.__render.start(); });
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '10', '-pix_fmt', 'yuv420p', out + '/raw.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
  const N = Math.round(TOTAL * FPS); let nextTick = 0, si = 0; const t0 = Date.now();
  for (let i = 0; i < N; i++) {
    const t = i / FPS;
    const doTick = t >= nextTick; if (doTick) nextTick += 0.45;
    const st = (si < STRIKES.length && t >= STRIKES[si] - 0.5) ? STRIKES[si++] : 0;
    await p.evaluate(({ t, doTick, st }) => { const R = window.__render; R.t = t; if (st) R.strike(st); if (doTick) R.tick(); R.frame(); }, { t, doTick, st });
    if (t >= PRE) {
      const buf = await p.screenshot({ type: 'jpeg', quality: 96 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    if (i % 600 === 0) console.log('frame', i, '/', N, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  const len = await p.evaluate(async () => { const buf = await window.__render.ac.startRendering(); window.__pcm = buf.getChannelData(0); return window.__pcm.length; });
  const fd = fs.openSync(out + '/raw.f32', 'w'); const CH = 1 << 20;
  for (let o = 0; o < len; o += CH) {
    const b64 = await p.evaluate(({ o, CH }) => { const s = window.__pcm.subarray(o, o + CH); const u = new Uint8Array(s.buffer, s.byteOffset, s.byteLength); let r = ''; for (let i = 0; i < u.length; i += 32768) r += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(r); }, { o, CH });
    fs.writeSync(fd, Buffer.from(b64, 'base64'));
  }
  fs.closeSync(fd); console.log('done', len, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  await b.close();
})();
