"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const css=fs.readFileSync(path.join(__dirname,"../pisd/web/static/css/pisd_design_system.css"),"utf8");
const ratio=(a,b)=>{const l=h=>h.match(/[0-9a-f]{2}/gi).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);return (Math.max(l(a),l(b))+.05)/(Math.min(l(a),l(b))+.05)};
for (const mode of ["dark","light"]) {
 const match=css.match(new RegExp('body\\[data-pisd-theme="'+mode+'"\\]\\s*\\{([^}]+)\\}'));
 assert.ok(match,mode);
 const p=Object.fromEntries([...match[1].matchAll(/--vd-([a-zA-Z]+):\s*(#[0-9a-f]{6})/gi)].map(m=>[m[1],m[2]]));
 for(const [fg,bg] of [["text","bg"],["muted","surface"],["accent","surface"],["on","accent"],["good","goodBg"],["warn","warnBg"],["error","errorBg"],["capture","captureBg"]]) assert.ok(ratio(p[fg],p[bg])>=4.5,mode+" "+fg+"/"+bg);
 assert.ok(ratio(p.outline,p.surface)>=3,mode+" boundary");
}
assert.ok(css.includes('forced-colors: none'));
assert.ok(css.includes('background: #B91C2C !important'));
console.log("VD palette token contrast verified; rendered coverage is separate");
