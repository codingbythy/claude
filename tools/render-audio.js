// Renders only a scene's sound (no picture) into <out-dir>/raw.f32, the same timeline as render-scene.js.
// Much faster than a full render; use it when only the ambience changed, then make-loop.sh.
// Usage: node render-audio.js <page-url> <out-dir> <loop-seconds> <crossfade-seconds>
const { chromium } = require('playwright');
const fs = require('fs');
const [url, out, Ls, Xs] = process.argv.slice(2);
const PRE = 10, TOTAL = PRE + (+Ls) + (+Xs), SR = 48000;
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage();
  p.on('pageerror', e => console.error('PAGEERR', String(e)));
  await p.addInitScript(({ TOTAL, SR }) => {
    let a = 20261111;
    Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    window.__render = { t: 0, ac: new OfflineAudioContext(1, Math.ceil(SR * TOTAL), SR) };
  }, { TOTAL, SR });
  await p.goto(url);
  await p.waitForFunction(() => window.__render.frame && (!window.__render.ready || window.__render.ready()));
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} window.__render.start(); });
  await p.evaluate(TOTAL => { const R = window.__render; for (let t = 0; t < TOTAL; t += 0.45) { R.t = t; R.tick(); } }, TOTAL);
  const len = await p.evaluate(async () => { const buf = await window.__render.ac.startRendering(); window.__pcm = buf.getChannelData(0); return window.__pcm.length; });
  const fd = fs.openSync(out + '/raw.f32', 'w'); const CH = 1 << 20;
  for (let o = 0; o < len; o += CH) {
    const b64 = await p.evaluate(({ o, CH }) => { const s = window.__pcm.subarray(o, o + CH); const u = new Uint8Array(s.buffer, s.byteOffset, s.byteLength); let r = ''; for (let i = 0; i < u.length; i += 32768) r += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(r); }, { o, CH });
    fs.writeSync(fd, Buffer.from(b64, 'base64'));
  }
  fs.closeSync(fd); console.log('done', len); await b.close();
})();
