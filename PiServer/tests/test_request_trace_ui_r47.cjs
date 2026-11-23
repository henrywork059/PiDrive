"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,"..");
const app=fs.readFileSync(path.join(root,"piserver/web/static/app.js"),"utf8");
const server=fs.readFileSync(path.join(root,"piserver/app.py"),"utf8");
const trace=fs.readFileSync(path.join(root,"piserver/core/request_trace.py"),"utf8");

function helpers(){
  const a=app.indexOf("function tracedRequestError(");
  const b=app.indexOf("async function fetchJson(",a);
  assert.ok(a>=0&&b>a);
  const elements=new Map();
  const make=tag=>({tag,children:[],textContent:"",appendChild(c){this.children.push(c)}});
  const document={getElementById:id=>elements.get(id),createElement:make};
  elements.set("banner",make("div"));
  const funcs=vm.runInNewContext(app.slice(a,b)+"\n({tracedRequestError,appendRequestTrace})",{document});
  return {...funcs,elements};
}
test("browser source parses",()=>assert.doesNotThrow(()=>new vm.Script(app)));
test("server R47 hook installed after access control, not replacing auth",()=>{
  assert.match(server,/install_access_control\(app\)\s+install_mutation_trace\(app\)/);
  assert.match(trace,/secrets\.token_hex\(8\)/);
});
test("traced motor Apply shows short and safe operator action",()=>{
  const f=helpers();
  const err=f.tracedRequestError({correlation_id:"0123456789abcdef",
    operation:"api_motor_apply",message:"password=secret /home/pi/private"},
    400,"/api/motor/apply","fallback");
  assert.match(err.message,/Motor Apply failed/);
  assert.doesNotMatch(err.message,/secret|private/);
  assert.equal(err.trace.id,"0123456789abcdef");
});
test("expandable details show only ID, operation, status and sanitized code",()=>{
  const f=helpers();
  const err=f.tracedRequestError({correlation_id:"0123456789abcdef",
    operation:"api_camera_apply",code:"PISD-API-002",message:"secret"},
    400,"/api/camera/apply","fallback");
  f.appendRequestTrace("banner",err);
  const details=f.elements.get("banner").children[0];
  assert.equal(details.tag,"details");
  assert.equal(details.children[0].textContent,"Error details");
  assert.match(details.children[1].textContent,/0123456789abcdef.*api_camera_apply.*HTTP 400.*PISD-API-002/);
  assert.doesNotMatch(JSON.stringify(details),/secret|\/home\//);
});
test("invalid attacker IDs never render as trace details",()=>{
  const f=helpers();
  const err=f.tracedRequestError({correlation_id:"../password",message:"Untraced error"},400,"/api/motor/apply","fallback");
  assert.equal(err.trace,undefined);
  f.appendRequestTrace("banner",err);
  assert.equal(f.elements.get("banner").children.length,0);
});
test("401/403 keep login/permission recovery while preserving security redirect",()=>{
  const f=helpers();
  const err=f.tracedRequestError({correlation_id:"0123456789abcdef"},403,"/api/motor/apply","Permission denied.");
  assert.equal(err.message,"Permission denied.");
  assert.match(app,/window\.location\.assign\("\/login"\)/);
});
test("both HTTP errors and ok:false/saved:false rejected",()=>{
  assert.match(app,/!response\.ok \|\| data\?\.ok === false \|\| data\?\.saved === false/);
});
test("camera and motor Apply catches append trace after setting the short banner",()=>{
  assert.match(app,/setBanner\("cameraMessage", error\.message[^;]*;\s*appendRequestTrace\("cameraMessage", error\)/);
  assert.match(app,/setBanner\("motorMessage", error\.message[^;]*;\s*appendRequestTrace\("motorMessage", error\)/);
});
test("R43 preview freshness and R31 saved readback remain",()=>{
  assert.match(app,/previewHealth\.isNew\(sequence\)/);
  assert.match(app,/confirmedConfig\('\/api\/motor\/config'/);
  assert.match(app,/confirmedConfig\('\/api\/camera\/config'/);
  assert.match(server,/APP_VERSION = "0_4_26"/);
});
