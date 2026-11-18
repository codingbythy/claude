# Thumbnail template

`node shot.js <dir> out.png '<config JSON>'` renders `thumb.html` at 1280×720 from a 1920×1080 frame in `<dir>`.

Config used for each episode:

- Cartographer's Cottage: `{"bg":"thumbnail-bg.png","crop":[560,90,1360],"l1":"STORMY SEA","l2":"COTTAGE","sub":"rain · waves · distant thunder","accent":"#8fc3d6","bolt":[226,5,60,48]}`
- Botanist's Glasshouse: `{"bg":"thumbnail-bg.png","crop":[270,250,1440],"l1":"AUTUMN RAIN","l2":"GLASSHOUSE","sub":"shh... the fox is asleep","accent":"#f4bd4f","bolt":null,"shade":0.75}`

`crop` is x, y and width in the 1920×1080 frame (height follows 16:9). `bolt` draws a lightning bolt inside a
window pane, given as x, y, w, h on a 320×180 grid. `shade` (0–1) sets how dark the panel behind the text is.
