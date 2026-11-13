const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:720}});
await p.goto('file://'+process.argv[2]+'/thumb.html');await p.waitForTimeout(2500);
console.log('font',await p.evaluate(()=>document.fonts.check('700 118px "Pixelify Sans"')));
await p.screenshot({path:process.argv[2]+'/thumb.png'});await b.close();})();
