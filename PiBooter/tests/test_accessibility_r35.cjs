'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const src = fs.readFileSync(path.join(__dirname,'../pibooter/app.py'),'utf8');
const found = src.match(/HTML_SHELL = """([\s\S]*?)"""/);
if(!found)throw Error('PiBooter HTML shell missing');
const raw=found[1];
const left='\u0001',right='\u0002';
let html=raw.replaceAll('{{',left).replaceAll('}}',right);
const placeholders=[...html.matchAll(/\{([^{}]*)\}/g)].map(x=>x[1]);
const allowed=new Set(['title','subtitle','notice','body','status_timer']);
if(placeholders.some(x=>!allowed.has(x)))throw Error('Bad HTML_SHELL format braces: '+placeholders.join(','));
const values={title:'PiBooter',subtitle:'Setup',notice:'',body:'Content',status_timer:''};
html=html.replace(/\{(title|subtitle|notice|body|status_timer)\}/g,(m,key)=>values[key]);
html=html.replaceAll(left,'{').replaceAll(right,'}');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
if(!script)throw Error('No inline browser script');
let count=0;
function test(name,fn){fn();count++;process.stdout.write('PASS '+name+'\n');}
test('HTML shell placeholders remain valid',()=>assert.equal(placeholders.length,6));
test('Browser JavaScript parses',()=>new Function(script));
test('Skip setup link targets actual main landmark',()=>assert.equal(html.includes('href="#setup-content"')&&html.includes('<main id="setup-content" tabindex="-1">'),true));
test('Skip link appears on keyboard focus',()=>assert.equal(html.includes('.skip-link:focus-visible'),true));
test('Native buttons/fields show keyboard outlines',()=>assert.equal(html.includes('button:focus-visible, input:focus-visible'),true));
test('Reduced motion is supported',()=>assert.equal(html.includes('prefers-reduced-motion: reduce'),true));
test('Progress update retains live next-action',()=>assert.equal(html.includes('data.onboarding?.next_action'),true));
test('Saved-network forget actions have unique name',()=>assert.equal(src.includes('aria-label=\'Forget saved Wi-Fi'),true));
test('Scan result buttons say which network they choose',()=>assert.equal(src.includes('aria-label="Use Wi-Fi network'),true));
test('Hotspot credential not interpolated in page',()=>assert.equal(!raw.includes('hotspot_password'),true));
test('Original CSRF and origin rules remain',()=>assert.equal(src.includes('request_token_matches')&&src.includes('trusted_post_origin'),true));
test('Original short startup window preserved',()=>assert.equal(src.includes('if now - self._started_at >= startup_wait_s'),true));
function simulateMotion(reduced) {
 const ssid={value:''},password={focus(){this.focused=true;}};
 let scrollValue=null;
 const document={body:{scrollHeight:1200},getElementById:id=>id==='ssid'?ssid:id==='password'?password:null,querySelector:()=>null};
 const window={matchMedia:()=>({matches:reduced}),scrollTo:arg=>scrollValue=arg};
 const fetch=async()=>({ok:false});
 const funcs=new Function('document','window','fetch','setInterval',script+'\nreturn {fillSsid};')(
   document,window,fetch,()=>null);
 funcs.fillSsid('Home network');
 return {ssid: ssid.value,focused:password.focused,scrollValue};
}
test('Reduced motion disables smooth scroll',()=>{const r=simulateMotion(true);assert.equal(r.scrollValue.behavior,'auto');assert.equal(r.focused,true);});
test('Normal motion retains smooth scroll',()=>{const r=simulateMotion(false);assert.equal(r.scrollValue.behavior,'smooth');assert.equal(r.ssid,'Home network');});
console.log(count+'/14 PiBooter R35 keyboard accessibility tests passed');
