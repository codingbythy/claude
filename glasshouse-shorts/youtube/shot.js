const { chromium } = require('playwright');
// Usage: node shot.js out.png ['<config JSON>']
(async () => { const [out, cfg] = process.argv.slice(2); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + __dirname + '/thumb.html' + (cfg ? '#' + encodeURIComponent(cfg) : '')); await p.waitForTimeout(1500); await p.evaluate(() => document.fonts.load('44px "Press Start 2P"')); await p.waitForTimeout(400);
  if (!(await p.evaluate(() => document.fonts.check('44px "Press Start 2P"')))) throw new Error('font');
  await p.screenshot({ path: out }); await b.close(); })();
