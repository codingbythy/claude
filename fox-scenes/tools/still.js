// Steps a scene forward offline and saves a frame at each of the given times. For checking that effects sit where they should.
// Usage: node still.js <page-url> <out-prefix> <seconds>[,<seconds>...] [--size 640x360]
//   -> <out-prefix>-<seconds>.jpg (or <out-prefix> itself for one .jpg). With --size, frames are PNG at that exact size.
const { chromium } = require('playwright');
(async () => {
  const av = process.argv.slice(2), size = av.includes('--size') ? av[av.indexOf('--size') + 1].split('x').map(Number) : null;
  const [url, out, list] = av.filter((a, i) => !a.startsWith('--') && av[i - 1] !== '--size'), times = list.split(',').map(Number).sort((a, b) => a - b);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: size ? { width: size[0], height: size[1] } : { width: 1920, height: 1080 } });
  let errs = 0;
  p.on('pageerror', e => { errs++; console.error('PAGEERR', String(e)); });
  p.on('console', m => { if (m.type() === 'error') { errs++; console.error('CONSOLE', m.text()); } });
  await p.addInitScript(T => {
    let a = 20261120;     // the renderer's seed, so a still matches the rendered video
    Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    window.__render = { t: 0, ac: new OfflineAudioContext(2, 48000 * Math.ceil(T + 5), 48000) };
  }, times[times.length - 1]);
  await p.goto(url);
  await p.waitForFunction(() => window.__render.frame && window.__render.ready(), null, { timeout: 15000 });
  await p.evaluate(() => { window.__render.start(); window.__i = 0; window.__next = 0; });
  for (const T of times) {
    await p.evaluate(T => { const R = window.__render; for (; window.__i <= Math.round(T * 30); window.__i++) { R.t = window.__i / 30; if (R.t >= window.__next) { R.tick(); window.__next += 0.45; } R.frame(); } }, T);
    const file = size ? `${out}-${T}.png` : times.length === 1 && out.endsWith('.jpg') ? out : `${out}-${T}.jpg`;
    await p.screenshot(size ? { path: file, type: 'png' } : { path: file, type: 'jpeg', quality: 90 }); console.log('saved', file);
  }
  console.log('page errors:', errs);
  await b.close();
})();
