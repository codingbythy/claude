const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:720}});
await p.goto('file://'+process.argv[2]+'/thumb.html');await p.waitForTimeout(1500); await p.evaluate(() => Promise.all(['44px "Press Start 2P"', '700 104px "Pixelify Sans"'].map(f => document.fonts.load(f)))); await p.waitForTimeout(500);
console.log('font',await p.evaluate(()=>document.fonts.check('700 118px "Pixelify Sans"') && document.fonts.check('44px "Press Start 2P"')));
await p.screenshot({path:process.argv[2]+'/thumb.png'});await b.close();})();
