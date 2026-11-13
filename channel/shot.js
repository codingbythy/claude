const { chromium } = require('playwright');
(async () => {
  const [dir, page, w, h, out, hash] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +w, height: +h } });
  await p.goto('file://' + dir + '/' + page + (hash || '')); await p.waitForTimeout(2500);
  console.log('fonts', await p.evaluate(() => document.fonts.check('600 150px "Cormorant Garamond"')));
  await p.screenshot({ path: dir + '/' + out }); await b.close();
})();
