"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
const app=read("piserver/web/static/app.js"),html=read("piserver/web/templates/index.html"),server=read("piserver/app.py");
test("updated browser JS parses",()=>assert.doesNotThrow(()=>new vm.Script(app)));
test("model selector offers upload action when empty",()=>{
 assert.match(app,/No \.tflite models — upload a model/);
 assert.match(app,/No models on Pi\. Upload a \.tflite model first\./);
 assert.match(app,/if \(!\(data\.models \|\| \[\]\)\.length\)/);
});
test("model action names distinguish upload, load and deletion",()=>{
 assert.match(app,/No model selected\. Upload a \.tflite file or choose a listed model/);
 assert.match(app,/No model selected\. Choose a listed model to delete/);
 assert.match(html,/No model loaded\. Upload a \.tflite model/);
});
test("empty recording list and missing selection supply one next step",()=>{
 assert.match(app,/No saved folders — record or capture a frame/);
 assert.match(app,/Record or capture a frame, then Refresh folders/);
 assert.match(html,/Record a session if none exists/);
});
test("permission, expired login and server unavailable have different recovery",()=>{
 assert.match(app,/response\.status === 403 \? "Permission denied/);
 assert.match(app,/response\.status === 401 \? "Session expired/);
 assert.match(app,/response\.status >= 500 \? "PiServer unavailable/);
 assert.match(app,/window\.location\.assign\("\/login"\)/);
});
test("does not interfere with STOP, camera freshness or R43 scheduling",()=>{
 assert.match(app,/const STEP_INTERVAL_MS = 60;/);
 assert.match(app,/previewHealth\.isNew\(sequence\)/);
 assert.match(app,/function scheduleStatusPoll/);
 assert.match(app,/setRecordToggle/);
});
test("status action labels and version retain hardware semantics",()=>{
 assert.match(html,/Apply \+ restart/);
 assert.match(html,/id="cameraApplyBtn"/);
 assert.match(html,/id="motorApplyBtn"/);
 assert.match(server,/APP_VERSION = "0_4_25"/);
});
