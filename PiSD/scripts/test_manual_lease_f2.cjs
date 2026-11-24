const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const js = path.join(__dirname, '../pisd/web/static/js');
const src = fs.readFileSync(path.join(js, 'manual_lease.js'), 'utf8');
function fixture() {
  let active = true, lost = 0, requests = [], fail = false;
  const ctx = { setInterval: () => 1, clearInterval: () => {} };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  const lease = ctx.PiSDManualLease.create({
    active: () => active, onLost: () => lost++,
    fetchImpl: async (url, options) => { requests.push([url, JSON.parse(options.body)]); return {ok: !fail, json: async () => ({ok: !fail})}; }
  });
  return {lease, requests, lost: () => lost, fail: () => {fail = true;}, hide: () => {active = false;}};
}
test('renewal only sends lease ID; failure cannot replay', async () => {
  const f = fixture(); f.lease.finish(f.lease.begin(), {ok:true,manual_lease_id:'token'});
  await f.lease.tick(); assert.deepEqual(f.requests, [['/api/control/heartbeat',{lease_id:'token'}]]);
  f.fail(); await f.lease.tick(); await f.lease.tick(); assert.equal(f.lost(),1); assert.equal(f.requests.length,2);
});
test('stop invalidates late reply and hidden view never renews', async () => {
  const f = fixture(); const ticket=f.lease.begin(); f.lease.cancel();
  f.lease.finish(ticket,{ok:true,manual_lease_id:'late'}); await f.lease.tick(); assert.equal(f.requests.length,0);
  f.lease.finish(f.lease.begin(),{ok:true,manual_lease_id:'next'}); f.hide(); await f.lease.tick(); assert.equal(f.requests.length,0);
});
test('production pages parse and connect the lease to real stop paths', () => {
  for (const file of ['manual_drive.js','ai_mode.js']) {
    const s=fs.readFileSync(path.join(js,file),'utf8');
    new vm.Script(s);
    assert.match(s,/PiSDManualLease\.create/);
    assert.match(s,/manualLease\.cancel\(\)/);
    assert.match(s,/manualLease\.finish\(leaseTicket,/);
  }
});
