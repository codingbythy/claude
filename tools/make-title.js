// Usage: node make-title.js <out.png> "<first line>" "<accent line>" "<subtitle>" [accent hex]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [out, l1, l2, sub, accent] = process.argv.slice(2);
  const q = new URLSearchParams({ l1, l2, sub, ...(accent ? { accent } : {}) });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + path.join(__dirname, 'title.html') + '?' + q); await p.waitForTimeout(2500);
  if (!(await p.evaluate(() => document.fonts.check('600 92px "Pixelify Sans"')))) throw new Error('Title font did not load');
  await p.screenshot({ path: out, omitBackground: true }); await b.close();
})();
