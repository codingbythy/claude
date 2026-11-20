const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + __dirname + '/thumb.html'); await p.waitForTimeout(1500); await p.evaluate(() => document.fonts.load('44px "Press Start 2P"')); await p.waitForTimeout(400);
  if (!(await p.evaluate(() => document.fonts.check('44px "Press Start 2P"')))) throw new Error('font');
  await p.screenshot({ path: __dirname + '/thumb.png' }); await b.close(); })();
