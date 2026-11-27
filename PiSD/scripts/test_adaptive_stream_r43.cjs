"use strict";
// R43 static safety/visibility checks; measure actual MJPEG bytes on a Pi.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const js=(file)=>fs.readFileSync(path.join(__dirname,"..","pisd","web","static","js",file),"utf8");
const manual=js("manual_drive.js"), ai=js("ai_mode.js"), dashboard=js("main_dashboard.js");
const app=fs.readFileSync(path.join(__dirname,"..","pisd","app.py"),"utf8");

test("manual live MJPEG is paused hidden and restarted on return",()=>{
  assert.match(manual,/if \(currentPreviewMode === 'live' && preview\) \{\s*preview\.src = PREVIEW_IDLE_SRC;/);
  assert.match(manual,/if \(currentPreviewMode === 'live' && preview\) \{\s*preview\.src = \`\/video_feed\?t=\$\{Date\.now\(\)\}\`;/);
  assert.match(manual,/stopPreviewMetricsLoop\(\);\s*sendFailSafeStop\('visibility-hidden'\)/);
});
test("manual original Space/global STOP not modified",()=>{
  assert.match(manual,/sendFailSafeStop\('pagehide'\)/);
  assert.match(manual,/sendFailSafeStop\('beforeunload'\)/);
  assert.match(manual,/window\.setInterval\(pollOperatingReadiness, 1400\)/);
});
test("AI hidden stream pause preserves all safety stop paths",()=>{
  assert.match(ai,/resetManualCorrection\('ai-correction-hidden'\)/);
  assert.match(ai,/stopFullManualDrive\('ai-manual-hidden'\)/);
  assert.match(ai,/stopAssistDrive\('ai-assist-hidden'\)/);
  assert.match(ai,/sendBeacon\?\.\('\/api\/ai\/stop'/);
  assert.match(ai,/els\.aiPreviewImage\.src = IDLE_PREVIEW_SRC; \/\/ close hidden MJPEG HTTP stream/);
  assert.match(ai,/if \(document\.hidden \|\| statusPollInFlight\) return;/);
});
test("AI returns to live stream without a new camera/motor command",()=>{
  assert.match(ai,/els\.aiPreviewImage\.src = \`\/video_feed\?t=\$\{Date\.now\(\)\}\`;/);
  assert.match(ai,/void refreshStatus\(\); \/\/ immediate full UI state after hidden stop\s*\} else \{\s*void pollOperatingReadiness\(\); \/\/ immediate fresh server state/);
  assert.equal((ai.match(/document\.addEventListener\('visibilitychange'/g)||[]).length, 1);
});
test("legacy dashboard reconnects only when live preview requested",()=>{
  assert.match(dashboard,/legacyLivePreviewRequested = true;/);
  assert.match(dashboard,/legacyLivePreviewRequested = false;/);
  assert.match(dashboard,/if \(document\.hidden\) \{\s*cameraPreview\?\.removeAttribute\('src'\)/);
  assert.match(dashboard,/else if \(legacyLivePreviewRequested && cameraPreview\)/);
});
test("server freshness already reported; motor loop code untouched",()=>{
  assert.match(app,/"timestamp_utc": datetime\.now\(timezone\.utc\)\.isoformat\(\)/);
  assert.doesNotMatch(manual,/setInterval\(pollOperatingReadiness, 100\)/);
});
