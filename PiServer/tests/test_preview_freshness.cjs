'use strict';
const assert = require('node:assert/strict');
const { createPreviewFreshness } = require('../piserver/web/static/preview_freshness.js');
let checks = 0;
function test(name, callback) { callback(); checks += 1; process.stdout.write('PASS ' + name + '\n'); }
let tick = 0;
const clock = () => tick;
test('fresh capture becomes Live', () => { const h=createPreviewFreshness(clock);h.setBackendLive(true);assert.equal(h.accept(1),true);assert.equal(h.snapshot().state,'Live'); });
test('frame age uses monotonic elapsed milliseconds', () => {tick=100;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(3);tick=510;assert.equal(h.snapshot().ageMs,410);});
test('delayed frame clearly marked',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(1);tick=1600;assert.equal(h.snapshot().state,'Delayed');});
test('stale frame becomes Disconnected',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(1);tick=6000;assert.equal(h.snapshot().state,'Disconnected');});
test('same JPEG sequence does not reset age',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(10);tick=6500;assert.equal(h.accept(10),false);assert.equal(h.snapshot().ageMs,6500);});
test('backend disconnection overrides recently received frame',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(2);h.setBackendLive(false);assert.equal(h.snapshot().state,'Disconnected');assert.equal(h.snapshot().hasFrame,true);});
test('failure reports Delayed without discarding last frame',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(2);h.fail();assert.equal(h.snapshot().state,'Delayed');assert.equal(h.snapshot().hasFrame,true);});
test('initial no-frame state is Disconnected',()=>{tick=0;assert.equal(createPreviewFreshness(clock).snapshot().state,'Disconnected');});
test('exponential reconnect delay is capped',()=>{tick=0;const h=createPreviewFreshness(clock);for(let i=0;i<20;i++) h.fail();assert.equal(h.retryDelay(160),4000);});
test('initial reconnect delay starts at 250 ms',()=>{tick=0;const h=createPreviewFreshness(clock);h.fail();assert.equal(h.retryDelay(160),250);h.fail();assert.equal(h.retryDelay(160),500);});
test('new frame automatically restores Live and resets retries',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(1);h.fail();h.setBackendLive(false);h.setBackendLive(true);tick=200;assert.equal(h.accept(2),true);assert.equal(h.snapshot().state,'Live');assert.equal(h.retryDelay(160),160);});
test('paused preview never claims Live',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);h.accept(1);h.setPaused(true);assert.equal(h.snapshot().state,'Paused');h.setPaused(false);assert.equal(h.snapshot().state,'Live');});
test('invalid sequence cannot establish freshness',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(true);assert.equal(h.accept(NaN),false);assert.equal(h.accept(-1),false);assert.equal(h.snapshot().hasFrame,false);});
test('offline backend rejects JPEG even with new sequence',()=>{tick=0;const h=createPreviewFreshness(clock);h.setBackendLive(false);assert.equal(h.accept(1),false);assert.equal(h.snapshot().state,'Disconnected');});
console.log(checks + '/14 deterministic preview tests passed');

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
test('unchanged preview health avoids repeated text/class writes; changes still render', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'piserver', 'web', 'static', 'app.js'), 'utf8');
  const start = src.indexOf('function renderPreviewHealth() {');
  const end = src.indexOf('\nfunction previewDelayMs()', start);
  assert.ok(start >= 0 && end > start);
  let writes = 0;
  const node = () => {
    let text = '', cls = '';
    return {get textContent(){return text;}, set textContent(v){text=v;writes++;},
      get className(){return cls;}, set className(v){cls=v;writes++;}};
  };
  const nodes = {previewHealth:node(), metricPreview:node(), cameraPreviewMeta:node()};
  let health = {state:'Paused', ageMs:null, hasFrame:false};
  const ctx = vm.createContext({previewHealth:{snapshot:()=>health},
    state:{latestStatus:{}}, document:{getElementById:id=>nodes[id],querySelector:()=>null}});
  vm.runInContext(src.slice(start,end),ctx);
  ctx.renderPreviewHealth();
  assert.equal(writes,4);
  ctx.renderPreviewHealth();
  assert.equal(writes,4);
  health = {state:'Live',ageMs:100,hasFrame:true};
  ctx.renderPreviewHealth();
  assert.equal(writes,8);
  assert.equal(nodes.previewHealth.textContent,'Live · 0.1s old');
});
