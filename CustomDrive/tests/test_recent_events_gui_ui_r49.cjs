"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.join(__dirname, "..");
const js = fs.readFileSync(path.join(root, "custom_drive/gui_web/static/recent_events.js"), "utf8");
const html = fs.readFileSync(path.join(root, "custom_drive/gui_web/templates/index.html"), "utf8");

function element(tag="div") {
  return {tag, textContent:"", open:false, disabled:false, listeners:{},
    addEventListener(name,fn){this.listeners[name]=fn;}};
}
function start({offline=false}={}){
  const nodes = {
    "[data-recent-refresh]": element("button"),
    "[data-recent-copy]": element("button"),
    "[data-recent-output]": element("pre"),
    "[data-recent-status]": element("p"),
  };
  const panel=element("details");
  panel.querySelector=key=>nodes[key]||null;
  const calls=[],writes=[];
  const document={querySelector:key=>key==="[data-recent-events-root]"?panel:null};
  const navigator={clipboard:{writeText:async value=>{writes.push(value)}}};
  const fetch=async(url,opts)=>{
    calls.push({url,opts});
    if(offline) throw new Error("offline");
    return {ok:true,json:async()=>({ok:true,capacity:128,events:[
      {timestamp_utc:"2026-11-24T00:00:00+00:00",operation:"safety_stop",
       category:"safety",title:"Emergency STOP requested",outcome:"succeeded"},
      {timestamp_utc:"2026-11-24T00:00:10+00:00",operation:"model_load",
       category:"model",title:"Model load",outcome:"failed"},
    ]})};
  };
  vm.runInNewContext(js,{document,navigator,fetch,window:{}},{timeout:1000});
  return {panel,nodes,calls,writes};
}
async function settle(){await new Promise(resolve=>setImmediate(resolve));}

test("R49 script parses",()=>assert.doesNotThrow(()=>new vm.Script(js)));
test("collapsed operator panel includes Copy and Refresh without replacing preflight",()=>{
  assert.match(html,/data-recent-events-root/);
  assert.match(html,/data-recent-output/);
  assert.match(html,/data-recent-refresh/);
  assert.match(html,/data-recent-copy/);
  assert.match(html,/data-preflight-root/);
});
test("opening collapsed panel makes exactly one GET, not on page load",async()=>{
  const s=start();
  assert.equal(s.calls.length,0);
  s.panel.open=true;
  s.panel.listeners.toggle();
  await settle();
  assert.equal(s.calls.length,1);
  assert.equal(s.calls[0].url,"/api/recent-events");
  assert.equal(s.calls[0].opts.method,"GET");
  assert.equal(s.calls[0].opts.cache,"no-store");
});
test("safe text output highlights emergency STOP and failure outcomes",async()=>{
  const s=start();
  s.panel.open=true;s.panel.listeners.toggle();await settle();
  assert.match(s.nodes["[data-recent-output]"].textContent,/Emergency STOP requested · succeeded/);
  assert.match(s.nodes["[data-recent-output]"].textContent,/Model load · failed/);
  assert.match(s.nodes["[data-recent-status]"].textContent,/2 sanitized events/);
  assert.doesNotMatch(js,/\.innerHTML\s*=/);
});
test("Refresh retrieves another GET without drive/motor/config changes",async()=>{
  const s=start();
  s.panel.open=true;s.panel.listeners.toggle();await settle();
  await s.nodes["[data-recent-refresh]"].listeners.click();await settle();
  assert.equal(s.calls.length,2);
  assert.ok(s.calls.every(x=>x.opts.method==="GET"));
});
test("Copy puts only the visible sanitized text on clipboard",async()=>{
  const s=start();
  s.panel.open=true;s.panel.listeners.toggle();await settle();
  await s.nodes["[data-recent-copy]"].listeners.click();
  assert.equal(s.writes.length,1);
  assert.equal(s.writes[0],s.nodes["[data-recent-output]"].textContent);
  assert.doesNotMatch(s.writes[0],/password|secret|\/home\//i);
});
test("offline request reports unavailable and never marks success",async()=>{
  const s=start({offline:true});
  s.panel.open=true;s.panel.listeners.toggle();await settle();
  assert.match(s.nodes["[data-recent-status]"].textContent,/unavailable/);
  assert.match(s.nodes["[data-recent-output]"].textContent,/unavailable/);
});
test("R49 never sends POST nor touches localStorage/telemetry",()=>{
  assert.doesNotMatch(js,/method:\s*["']POST["']/);
  assert.doesNotMatch(js,/localStorage|WebSocket|navigator\.sendBeacon|motor_service/);
});
