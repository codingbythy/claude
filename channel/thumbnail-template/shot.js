const { chromium } = require('playwright');
(async () => {
  const [dir, out, cfg] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.goto('file://' + dir + '/thumb.html#' + encodeURIComponent(cfg)); await p.waitForTimeout(2500);
  if (!(await p.evaluate(() => document.fonts.check('700 104px "Pixelify Sans"')))) throw new Error('font');
  await p.screenshot({ path: dir + '/' + out }); await b.close();
})();
