// Makes the channel's corner mark: the words "Somewhere Sheltered" in the banner's typeface (Cormorant Garamond) and colour,
// on a transparent background, sized for a 2560x1440 video. The long-video build lays it over the bottom right-hand corner.
// Usage: node mark.js [out.png]      (default: ../../channel/somewhere-sheltered-mark.png)
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const out = process.argv[2] || path.join(__dirname, '..', '..', 'channel', 'somewhere-sheltered-mark.png');
  const font = 'data:font/woff2;base64,' + fs.readFileSync(path.join(__dirname, 'fonts', 'CormorantGaramond-SemiBold.woff2')).toString('base64');
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: 1200, height: 300 } });
  await p.setContent(`<!doctype html><style>
    @font-face { font-family: "Cormorant Garamond"; font-weight: 600; src: url("${font}") format("woff2"); }
    html, body { margin: 0; background: transparent; }
    #m { display: inline-block; padding: 14px 18px 16px; font: 600 60px/1 "Cormorant Garamond", Georgia, serif; letter-spacing: .02em; color: #f4e6cc; white-space: nowrap;
         opacity: .86; text-shadow: 0 2px 3px rgba(0, 0, 0, .75), 0 0 14px rgba(0, 0, 0, .6); }
  </style><span id="m">Somewhere Sheltered</span>`);
  await p.evaluate(() => document.fonts.ready);
  if (!(await p.evaluate(() => document.fonts.check('600 60px "Cormorant Garamond"')))) throw new Error('The mark\'s font did not load');
  await p.locator('#m').screenshot({ path: out, omitBackground: true });
  const box = await p.locator('#m').boundingBox();
  console.log(out, Math.round(box.width) + 'x' + Math.round(box.height));
  await b.close();
})();
