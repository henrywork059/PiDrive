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
 const m=server.match(/APP_VERSION\s*=\s*"(0_4|1_0)_(\d+)"/);assert.ok(m&&(m[1]==='1_0'||Number(m[2])>=25));
});

test("UI2 offline status invalidates server observations without mutating local target or STOP authority",()=>{
 const start=app.indexOf("function markStatusUnverified(error) {"), end=app.indexOf("\nfunction updateStatusUi(data)",start);
 assert.ok(start>=0&&end>start);
 const ids=["metricDriveState","metricApplied","metricWheels","metricCamera","metricModel","metricAlgorithm","metricMaxThrottle","metricSteerMix","metricSteerBias","metricFps","metricBackend","metricError","metricManual","metricLastSave"];
 const nodes=Object.fromEntries(ids.map(id=>[id,{textContent:"last value",title:""}]));
 let banner="";
 const ctx=vm.createContext({state:{statusVerified:true},document:{getElementById:id=>nodes[id],querySelector:()=>null},setBanner:(_id,value)=>{banner=value;}});
 vm.runInContext(app.slice(start,end),ctx);
 ctx.markStatusUnverified(new Error("Disconnected"));
 assert.equal(ctx.state.statusVerified,false);
 for(const id of ids.slice(0,-2))assert.equal(nodes[id].textContent,"Unverified",id);
 assert.equal(nodes.metricManual.textContent,"last value");
 assert.equal(nodes.metricLastSave.textContent,"last value");
 assert.match(nodes.metricLastSave.title,/Last confirmed/);
 assert.match(banner,/STOP can be requested/);
});
test("UI2 initial dashboard does not imply verified motor status",()=>{
 assert.match(html,/id="metricDriveState">Unverified/);
 assert.match(html,/id="estopToggle"[^>]*aria-pressed="mixed"/);
 assert.match(html,/E-STOP STATUS UNKNOWN/);
});
