const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
await p.goto('file://'+process.argv[2]+'/title.html');await p.waitForTimeout(2500);
console.log('font ok:',await p.evaluate(()=>document.fonts.check('600 92px "Pixelify Sans"')));
await p.screenshot({path:process.argv[2]+'/title.png',omitBackground:true});await b.close();})();
