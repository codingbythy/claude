// Steps a scene forward to a given time, offline, and saves one frame. For checking that effects sit where they should.
// Usage: node still.js <page-url> <out.jpg> <seconds>
const { chromium } = require('playwright');
(async () => {
  const [url, out, T] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  let errs = 0;
  p.on('pageerror', e => { errs++; console.error('PAGEERR', String(e)); });
  p.on('console', m => { if (m.type() === 'error') { errs++; console.error('CONSOLE', m.text()); } });
  await p.addInitScript(() => { window.__render = { t: 0, ac: new OfflineAudioContext(2, 48000 * 30, 48000) }; });
  await p.goto(url);
  await p.waitForFunction(() => window.__render.frame && window.__render.ready(), null, { timeout: 15000 });
  await p.evaluate(T => {
    const R = window.__render; R.start(); let next = 0;
    for (let i = 0; i <= T * 30; i++) { R.t = i / 30; if (R.t >= next) { R.tick(); next += 0.45; } R.frame(); }
  }, +T);
  await p.screenshot({ path: out, type: 'jpeg', quality: 88 });
  console.log('saved', out, '- page errors:', errs);
  await b.close();
})();
