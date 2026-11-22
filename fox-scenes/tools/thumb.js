// Makes a scene's thumbnails: three versions for YouTube's "Test & compare", each at 1280x720 with a 320x180 copy to judge it at
// feed size.
//   a  the whole scene with the scene name
//   b  closer on the foxes and the window, with the scene name
//   c  closer, no name: only the picture and the duration badge
// Usage: node thumb.js <scene> <frame> <out-dir>
//   frame is a 1920x1080 frame of the scene (tools/still.js makes one), so the thumbnail shows the weather as the video does.
// The badge is not typed anywhere: it is the "hours" value in the scene's scene.json, the same value the long-video build uses.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [scene, frame, outDir] = process.argv.slice(2);
  const C = JSON.parse(fs.readFileSync(path.join(__dirname, '..', scene, 'scene.json'), 'utf8')), T = C.thumbnail;
  const base = { bg: 'file://' + path.resolve(frame), accent: T.accent, badge: `${C.hours} HOUR${C.hours === 1 ? '' : 'S'}`, boost: T.boost || [1.12, 1.12, 1.04] };
  const versions = { a: { crop: [0, 0, 1920], lines: T.lines }, b: { crop: T.close, lines: T.lines }, c: { crop: T.close, lines: [] } };
  fs.mkdirSync(outDir, { recursive: true });
  const b = await chromium.launch();
  for (const [v, cfg] of Object.entries(versions)) {
    const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
    await p.goto('file://' + path.join(__dirname, 'thumb.html') + '#' + encodeURIComponent(JSON.stringify({ ...base, ...cfg })));
    await p.waitForFunction(() => document.body.dataset.ready === '1');
    if (!(await p.evaluate(() => document.fonts.check('62px "Anton"')))) throw new Error('Thumbnail font did not load');
    await p.waitForTimeout(300);
    const big = path.join(outDir, `${scene}-thumbnail-${v}.jpg`), small = path.join(outDir, `${scene}-thumbnail-${v}-320.jpg`);
    await p.screenshot({ path: big, type: 'jpeg', quality: 93 });
    await p.setViewportSize({ width: 320, height: 180 });       // the same page scaled down, as the feed shows it
    await p.evaluate(() => { document.documentElement.style.cssText = 'transform:scale(.25);transform-origin:0 0;width:1280px;height:720px'; });
    await p.screenshot({ path: small, type: 'jpeg', quality: 90, clip: { x: 0, y: 0, width: 320, height: 180 } });
    console.log(big); await p.close();
  }
  await b.close();
})();
