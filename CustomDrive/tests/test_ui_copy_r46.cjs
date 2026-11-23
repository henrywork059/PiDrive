"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
const gui=read("custom_drive/gui_web/static/app.js");
const guiHtml=read("custom_drive/gui_web/templates/index.html");
const mission=read("custom_drive/mission1_web/static/app.js");
const missionHtml=read("custom_drive/mission1_web/templates/index.html");
const guiPy=read("custom_drive/gui_control_app.py");
const missionPy=read("custom_drive/mission1_session_app.py");
test("both UI scripts parse",()=>{assert.doesNotThrow(()=>new vm.Script(gui));assert.doesNotThrow(()=>new vm.Script(mission));});
test("GUI distinguishes deploy-to-Pi from preview toggle",()=>{
 assert.match(guiHtml,/Deploy Model to Pi/);
 assert.match(guiHtml,/Start \/ Stop Camera Preview/);
 assert.match(guiHtml,/Save Drive Settings/);
});
test("GUI missing model is actionable, not fake successful deployment",()=>{
 assert.match(gui,/No models — upload a \.tflite file/);
 assert.match(gui,/Upload a \.tflite model, then Deploy/);
 assert.match(gui,/Deploy failed\. Check model files, then retry Deploy/);
 assert.match(gui,/Model, labels, and input size changes take effect after Deploy/);
});
test("GUI permission and offline status have distinct next steps",()=>{
 assert.match(gui,/response\.status === 403 \? 'Permission denied/);
 assert.match(gui,/response\.status >= 500 \? 'Pi service unavailable/);
});
test("Mission 1 model picker points to upload on Pi",()=>{
 assert.match(mission,/No models on Pi — upload a \.tflite model/);
 assert.match(mission,/No model selected\. Upload a \.tflite model, then choose it/);
 assert.match(missionHtml,/Upload Model to Pi \+ Select/);
});
test("Mission 1 distinguishes permission, connection and actual apply state",()=>{
 assert.match(mission,/res\.status === 403 \? 'Permission denied/);
 assert.match(mission,/res\.status >= 500 \? 'Mission 1 service unavailable/);
 assert.match(mission,/if \(!await saveConfig\(\)\) return/);
 assert.match(mission,/server still uses Grip/);
});
test("R43/R44 and safety controls unchanged in source",()=>{
 assert.match(mission,/const STATUS_REFRESH_MS = 600;/);
 assert.match(mission,/const FRAME_REFRESH_MS = 250;/);
 assert.match(mission,/function triggerGuideValues/);
 assert.match(guiHtml,/STOP manual output/);
 assert.match(guiPy,/APP_VERSION = '0_3_17'/);
 assert.match(missionPy,/APP_VERSION = '0_5_27'/);
});
