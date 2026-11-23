"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
const manual=read("pisd/web/static/js/manual_drive.js");
const ai=read("pisd/web/static/js/ai_mode.js");
const version=read("pisd/__init__.py");
test("Manual and AI browser JS both parse",()=>{
 assert.doesNotThrow(()=>new vm.Script(manual));
 assert.doesNotThrow(()=>new vm.Script(ai));
});
test("no recording folders has a Record next step",()=>{
 assert.match(manual,/No recordings yet\. Start live, then Record/);
 assert.match(manual,/No recordings — start a recording/);
});
test("no snapshots has a capture next step",()=>{
 assert.match(manual,/No snapshots yet\. Start live and capture a frame/);
 assert.match(manual,/No snapshots — capture a frame/);
});
test("empty folders are not mislabeled as loaded after refreshing",()=>{
 assert.match(manual,/if \(recordingCollections\.recordings\.length \|\| recordingCollections\.snapshots\.length\)/);
});
test("offline folder refresh says what to do without losing diagnostics",()=>{
 assert.match(manual,/Could not load saved folders\. Check the Pi connection, then Refresh/);
 assert.match(manual,/writeLog\('recording items failed'/);
});
test("empty models and camera error include actionable next step",()=>{
 assert.match(ai,/No models on Pi — upload \.keras or \.tflite/);
 assert.match(ai,/No AI models on Pi\. Upload a \.keras or \.tflite file/);
 assert.match(ai,/Camera preview unavailable\. Check camera, then Start live again/);
});
test("preserve safety stop, streaming, AI ownership and version",()=>{
 assert.match(manual,/sendFailSafeStop\('visibility-hidden'\)/);
 assert.match(ai,/stopFullManualDrive\('ai-manual-hidden'\)/);
 assert.match(ai,/stopAssistDrive\('ai-assist-hidden'\)/);
 assert.match(ai,/if \(document\.hidden \|\| statusPollInFlight\) return/);
 assert.match(version,/0\.11\.19/);
});
