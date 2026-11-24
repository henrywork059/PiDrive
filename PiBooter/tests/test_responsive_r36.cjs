'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const app = fs.readFileSync(path.join(__dirname, '../pibooter/app.py'), 'utf8');
let n=0;
function test(name,fn){fn();n++;process.stdout.write('PASS '+name+'\n');}
test('phone mobile rules are scoped to device and scan channel',()=>assert.equal(
  app.includes('.device-table th:nth-child(4)')&&app.includes('.scan-network-table th:nth-child(4)'),true));
test('scan action fifth column is no longer hidden',()=>assert.equal(
  !app.includes('th:nth-child(5), td:nth-child(5) {{ display: none; }}'),true));
test('responsive scan table has horizontal scroll region',()=>assert.equal(
  app.includes('network-table-wrap')&&app.includes('horizontally scrollable'),true));
test('scan action column is pinned at mobile widths',()=>assert.equal(
  app.includes('.scan-network-table th:last-child, .scan-network-table td:last-child'),true));
test('visible scan action survives markup changes',()=>assert.equal(
  app.includes('Use this network</button>')&&app.includes('Use Wi-Fi network'),true));
test('saved profile Forget action remains',()=>assert.equal(
  app.includes('Forget saved Wi-Fi')&&app.includes('saved-profile-table'),true));
test('CSRF token checks preserved',()=>assert.equal(
  app.includes('request_token_matches')&&app.includes('trusted_post_origin'),true));
test('five-second first client auto-exit preserved',()=>assert.equal(
  app.includes('if now - self._started_at >= startup_wait_s'),true));
test('private hotspot credential not embedded in HTML shell',()=>{
  const shell=app.split('HTML_SHELL = """')[1].split('"""')[0];
  assert.equal(shell.includes('hotspot_password'),false);
});
test('consistent mobile button target height',()=>assert.equal(
  app.includes('min-height: 44px')&&app.includes('.btn-row button'),true));
test('version increment remains on PiBooter patch scheme',()=>{
  const m=app.match(/server_version\s*=\s*"PiBooter\/0\.1\.(\d+)"/);
  assert.ok(m&&Number(m[1])>=6);
});
test('existing R34 projected onboarding retained',()=>assert.equal(
  app.includes('"onboarding": project_onboarding(snapshot)'),true));
console.log(n+'/12 PiBooter R36 responsive checks passed');
