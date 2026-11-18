const { chromium } = require('playwright');
(async () => {
  const [dir, out, cfg] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.goto('file://' + dir + '/thumb.html#' + encodeURIComponent(cfg)); await p.waitForTimeout(1500); await p.evaluate(() => Promise.all(['44px "Press Start 2P"', '700 104px "Pixelify Sans"'].map(f => document.fonts.load(f)))); await p.waitForTimeout(500);
  if (!(await p.evaluate(() => document.fonts.check('700 104px "Pixelify Sans"') && document.fonts.check('44px "Press Start 2P"')))) throw new Error('font');
  await p.screenshot({ path: dir + '/' + out }); await b.close();
})();
