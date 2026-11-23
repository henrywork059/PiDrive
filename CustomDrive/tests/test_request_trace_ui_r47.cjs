"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const gui=read("custom_drive/gui_web/static/app.js");
const mission=read("custom_drive/mission1_web/static/app.js");
const guiServer=read("custom_drive/gui_control_app.py");
const missionServer=read("custom_drive/mission1_session_app.py");
const trace=read("custom_drive/request_trace.py");

function helpers(src,mode){
  const a=src.indexOf("function tracedRequestError(");
  const b=src.indexOf(mode==="mission"?"async function fetchJSON(":"async function fetchJson(",a);
  assert.ok(a>=0&&b>a);
  const nodes=new Map();
  const create=tag=>({tag,children:[],textContent:"",appendChild(n){this.children.push(n)}});
  nodes.set("target",create("div"));
  const document={getElementById:id=>nodes.get(id),createElement:create};
  const result=vm.runInNewContext(src.slice(a,b)+"\n({tracedRequestError,appendRequestTrace})",{document});
  return {...result,nodes};
}
test("two browser files parse as JavaScript",()=>{
  assert.doesNotThrow(()=>new vm.Script(gui));
  assert.doesNotThrow(()=>new vm.Script(mission));
});
test("both web backends install same server-only failure trace helper",()=>{
  assert.match(guiServer,/install_mutation_trace\(app\)/);
  assert.match(missionServer,/install_mutation_trace\(app\)/);
  assert.match(trace,/secrets\.token_hex\(8\)/);
});
test("GUI Deploy failed returns short safe message and correlation",()=>{
  const f=helpers(gui,"gui");
  const err=f.tracedRequestError({correlation_id:"0123456789abcdef",operation:"api_ai_deploy",
    message:"password=secret /home/pi/mypath"},400,"/api/ai/deploy","fallback");
  assert.match(err.message,/Deploy to Pi failed/);
  assert.doesNotMatch(err.message,/secret|mypath/);
  assert.equal(err.trace.operation,"api_ai_deploy");
});
test("Mission 1 Start failure mentions safety/readiness rather than claiming started",()=>{
  const f=helpers(mission,"mission");
  const err=f.tracedRequestError({correlation_id:"0123456789abcdef",operation:"api_session_start"},
    409,"/api/session/start","fallback");
  assert.match(err.message,/Mission 1 Start failed/);
  assert.match(err.message,/readiness/);
});
test("error details contain bounded reference, never backend exception message",()=>{
  for(const [src,mode] of [[gui,"gui"],[mission,"mission"]]){
    const f=helpers(src,mode);
    const error=f.tracedRequestError({correlation_id:"0123456789abcdef",operation:"api_motor_apply",
      code:"PISD-API-001",message:"Token=superSecret C:\\Users\\private"},
      400,"/api/motor/apply","fallback");
    f.appendRequestTrace("target",error);
    const details=f.nodes.get("target").children[0];
    assert.equal(details.tag,"details");
    assert.match(details.children[1].textContent,/0123456789abcdef.*HTTP 400/);
    assert.doesNotMatch(JSON.stringify(details),/superSecret|Users|private/);
  }
});
test("attacker IDs and operation names are rejected or constrained",()=>{
  const f=helpers(gui,"gui");
  const bad=f.tracedRequestError({correlation_id:"bad",message:"No trace"},400,"/api/ai/deploy","fallback");
  assert.equal(bad.trace,undefined);
  const other=f.tracedRequestError({correlation_id:"0123456789abcdef",
    operation:"../?password=secret"},400,"/api/ai/deploy","fallback");
  assert.equal(other.trace.operation,"unknown");
});
test("GUI runtime save checks both HTTP failure and body failure",()=>{
  assert.match(gui,/!response\.ok \|\| data\?\.ok === false/);
  assert.match(gui,/data\?\.saved === false && !\['GET', 'HEAD'\]/);
  assert.match(gui,/appendRequestTrace\('driveSettingsMessage', error\)/);
  assert.match(gui,/appendRequestTrace\('aiSettingsMessage', error\)/);
});
test("Mission1 cannot Start or move arm after failed settings readback",()=>{
  assert.match(mission,/if \(!await saveConfig\(\)\) return; \/\/ never start a mission/);
  assert.match(mission,/if \(!await saveConfig\(\)\) return; \/\/ never move a servo/);
  assert.match(mission,/Math\.abs\(saved - effective\) > 0\.0001/);
});
test("Mission1 short errors and details render only in error branches",()=>{
  assert.match(mission,/if \(isError\) appendRequestTrace\(id, error\)/);
  assert.match(mission,/setMessage\('configMessage', err\.message[^;]*true, err\)/);
  assert.match(mission,/setMessage\('modelMessage', err\.message[^;]*true, err\)/);
  assert.match(mission,/setMessage\('armMessage', err\.message[^;]*true, err\)/);
});
test("R43 polling, R44 guides, motor guards and 0 percent mapping unchanged",()=>{
  assert.match(mission,/const STATUS_REFRESH_MS = 600/);
  assert.match(mission,/const FRAME_REFRESH_MS = 250/);
  assert.match(mission,/function triggerGuideValues/);
  assert.match(missionServer,/get\('grip_trigger_y_ratio', 0\.3\)\)\)/);
  assert.match(guiServer,/APP_VERSION = '0_3_18'/);
  assert.match(missionServer,/APP_VERSION = '0_5_28'/);
});
