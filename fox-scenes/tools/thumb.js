// Makes the thumbnails for one type of a scene (lofi or ambience): three versions for YouTube's "Test & compare", each at
// 1280x720 with a 320x180 copy to judge it at feed size.
//   a  the whole scene with the scene name
//   b  closer on the foxes and the window, with the scene name
//   c  closer, no name: only the picture and the badges
// Usage: node thumb.js <scene> <lofi|ambience> <frame> <out-dir>
//   frame is a 1920x1080 frame of the scene (tools/still.js makes one), so the thumbnail shows the weather as the video does.
// Nothing on it is typed by hand: the hours come from "hours" in the scene's scene.json (the same value the long-video build
// uses) and the second badge and the accent colour come from the type.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const KINDS = { lofi: { kind: 'LO-FI', accent: '#ffcf70' }, ambience: { kind: 'NO MUSIC', accent: '#9fd0ee' } };
(async () => {
  const [scene, type, frame, outDir] = process.argv.slice(2);
  if (!KINDS[type]) throw new Error('type must be lofi or ambience');
  const C = JSON.parse(fs.readFileSync(path.join(__dirname, '..', scene, 'scene.json'), 'utf8')), T = C.thumbnail;
  const V = (C.variants || {})[type] || {};
  const close = V.thumbnail_close || T.close;      // a type with its own picture (no foxes) frames the closer versions its own way
  // what the words must never cover (the hot chocolate), in layout pixels in scene.json, in the 1920x1080 frame here
  const keep = (V.thumbnail_keep_clear || T.keep_clear || []).map(b => b.map(v => v * 1.5));
  const base = { bg: 'file://' + path.resolve(frame), keep, ...KINDS[type], badge: `${C.hours} HOUR${C.hours === 1 ? '' : 'S'}`, boost: T.boost || [1.12, 1.12, 1.04] };
  const versions = { a: { crop: [0, 0, 1920], lines: T.lines }, b: { crop: close, lines: T.lines }, c: { crop: close, lines: [] } };
  fs.mkdirSync(outDir, { recursive: true });
  const b = await chromium.launch();
  for (const [v, cfg] of Object.entries(versions)) {
    const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
    await p.goto('file://' + path.join(__dirname, 'thumb.html') + '#' + encodeURIComponent(JSON.stringify({ ...base, ...cfg })));
    await p.waitForFunction(() => document.body.dataset.ready === '1');
    if (!(await p.evaluate(() => document.fonts.check('62px "Anton"')))) throw new Error('Thumbnail font did not load');
    const blocked = await p.evaluate(() => document.body.dataset.blocked);
    if (blocked) throw new Error(`version ${v}: ${blocked} would cover something the thumbnail must keep clear (thumbnail_keep_clear in scene.json)`);
    await p.waitForTimeout(300);
    const big = path.join(outDir, `${scene}-${type}-thumbnail-${v}.jpg`), small = path.join(outDir, `${scene}-${type}-thumbnail-${v}-320.jpg`);
    await p.screenshot({ path: big, type: 'jpeg', quality: 93 });
    await p.setViewportSize({ width: 320, height: 180 });       // the same page scaled down, as the feed shows it
    await p.evaluate(() => { document.documentElement.style.cssText = 'transform:scale(.25);transform-origin:0 0;width:1280px;height:720px'; });
    await p.screenshot({ path: small, type: 'jpeg', quality: 90, clip: { x: 0, y: 0, width: 320, height: 180 } });
    console.log(big); await p.close();
  }
  await b.close();
})();
