"use strict";
const test=require("node:test"), assert=require("node:assert/strict");
const fs=require("node:fs"), path=require("node:path"), vm=require("node:vm");
const gui=fs.readFileSync(path.join(__dirname,"..","custom_drive","gui_web","static","app.js"),"utf8");
const mission=fs.readFileSync(path.join(__dirname,"..","custom_drive","mission1_web","static","app.js"),"utf8");
function extract(source,start,end) {
  const i=source.indexOf("function "+start+"(");
  const j=source.indexOf("\nfunction "+end+"(",i);
  assert.ok(i>=0&&j>i,"expected live scheduling policy function");
  return source.slice(i,j);
}
function guiDelay(state,hidden) {
  const ctx=vm.createContext({document:{hidden},state,Math,Boolean});
  return vm.runInContext(extract(gui,"statusPollDelayMs","scheduleStatusPoll")+";statusPollDelayMs()",ctx);
}
function missionDelay(status,hidden,failures=0) {
  const ctx=vm.createContext({document:{hidden},currentStatus:status,statusFailures:failures,STATUS_REFRESH_MS:600,Math,Boolean,String});
  return vm.runInContext(extract(mission,"statusRefreshDelay","frameRefreshDelay")+";statusRefreshDelay()",ctx);
}
function frameDelay(status,hidden,failures=0) {
  const ctx=vm.createContext({document:{hidden},currentStatus:status,frameFailures:failures,FRAME_REFRESH_MS:250,Math,Boolean,
    shouldShowLiveFrame:(s)=>Boolean(s?.camera?.running)&&String(s?.phase||"").startsWith("ai")});
  return vm.runInContext(extract(mission,"frameRefreshDelay","scheduleRefresh")+";frameRefreshDelay()",ctx);
}

test("GUI active 1.5s / idle 4s / hidden skipped",()=>{
  const state={manualSteering:0,manualThrottle:0,latestStatus:{camera_preview_live:false},controlInFlight:false,pendingControl:false,statusFailures:0};
  assert.equal(guiDelay(state,false),4000);
  assert.equal(guiDelay({...state,manualThrottle:0.5},false),1500);
  assert.equal(guiDelay({...state,latestStatus:{camera_preview_live:true}},false),1500);
  assert.equal(guiDelay(state,true),5000);
  assert.match(gui,/if \(document.hidden\) \{\s*scheduleStatusPoll\(\);\s*return;/);
});
test("GUI retry bounded and focus return immediate",()=>{
  const s={manualSteering:0,manualThrottle:0,latestStatus:{},controlInFlight:false,pendingControl:false,statusFailures:99};
  assert.equal(guiDelay(s,false),10000);
  assert.match(gui,/scheduleStatusPoll\(0\); \/\/ return to tab/);
});
test("Mission status 600 active, 2500 idle, 5000 hidden",()=>{
  assert.equal(missionDelay({running:true},false),600);
  assert.equal(missionDelay({running:false,phase:"idle"},false),2500);
  assert.equal(missionDelay({running:false,phase:"idle"},true),5000);
  assert.match(mission,/if \(document.hidden\) \{\s*scheduleRefresh\(\);/);
});
test("Mission status bounded retry",()=>{
  assert.equal(missionDelay({running:true},false,2),2400);
  assert.equal(missionDelay({running:false,phase:"idle"},false,99),8000);
});
test("Mission frame polls 250ms active, 2000ms idle, 0 HTTP hidden",()=>{
  assert.equal(frameDelay({phase:"ai_track",camera:{running:true}},false),250);
  assert.equal(frameDelay({phase:"route",camera:{running:true}},false),2000);
  assert.equal(frameDelay({phase:"ai_track",camera:{running:true}},true),5000);
  assert.match(mission,/if \(document.hidden\) \{\s*scheduleFrameRefresh\(\);\s*return;/);
});
test("Mission frame failure backs off; one in flight until completion or abort",()=>{
  assert.equal(frameDelay({phase:"ai_track",camera:{running:true}},false,99),4000);
  assert.match(mission,/if \(frameRequestInFlight\) \{/);
  assert.match(mission,/scheduleFrameRefresh\(\); \/\/ one request at a time/);
  assert.match(mission,/video\.removeAttribute\('src'\)/);
});
test("browser status is server timestamped and safety operation remains separate",()=>{
  assert.match(gui,/Number\(data\.server_status_at_ms\)/);
  assert.match(mission,/Number\(status\.server_status_at_ms\)/);
  assert.match(gui,/releaseDrivePad\(\)/);
  assert.match(mission,/setMessage\('configMessage'/);
});
test("modeled one-tab requests/min: GUI 40→15, Mission idle 100→24",()=>{
  assert.equal(60000/1500,40);
  assert.equal(60000/guiDelay({manualSteering:0,manualThrottle:0,latestStatus:{},controlInFlight:false,pendingControl:false,statusFailures:0},false),15);
  assert.equal(60000/600,100);
  assert.equal(60000/missionDelay({running:false,phase:"idle"},false),24);
});
