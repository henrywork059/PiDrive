"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,"..","piserver","web","static","app.js"),"utf8");
function harness({enabled=false, rejectPost=false, rejectRead=false}={}) {
  const start=source.indexOf("async function refreshRecordedFolders(");
  const end=source.indexOf("\nasync function setEstop(",start);
  assert.ok(start>=0 && end>start);
  const state={recordEnabled:enabled, recordPending:false};
  const messages={}, toggles=[];
  let polls=0, captures=0, pending=false, reads=0;
  const setRecordToggle=(enabled,pending=false)=>{
    state.recordEnabled=enabled; state.recordPending=pending;
    toggles.push([enabled,pending]);
  };
  const ctx=vm.createContext({state,setRecordToggle,
    fetchJson:async url=>{if(rejectPost)throw Error("POST rejected");return {recording:!enabled,state:{recording:url.endsWith("/toggle")?!enabled:enabled}};},
    refreshSessions:async()=>{reads++;if(rejectRead)throw Error("GET rejected");},
    updateStatusUi:data=>setRecordToggle(data.recording,false),
    setBanner:(id,message)=>{messages[id]=message;},
    pollStatus:async()=>{polls++;},
    setCapturePending:value=>{pending=value;},triggerSnapshotFlash:()=>{captures++;}
  });
  vm.runInContext(source.slice(start,end),ctx);
  return {ctx,state,messages,toggles,counts:()=>({polls,captures,pending,reads})};
}
for(const enabled of [false,true]) {
  test("acknowledged recording "+(enabled?"stop":"start")+" survives failed folder read",async()=>{
    const f=harness({enabled,rejectRead:true});await f.ctx.toggleRecording();
    assert.equal(f.state.recordEnabled,!enabled);
    assert.equal(f.state.recordPending,false);
    assert.equal(f.counts().polls,1);
    assert.match(f.messages.sessionExportMessage,/GET rejected/);
    assert.match(f.messages.statusBanner,/acknowledged; folder refresh failed/);
  });
}
test("rejected recording POST restores original indicator without reading folders",async()=>{
  const f=harness({rejectPost:true});
  await assert.rejects(f.ctx.toggleRecording(),/POST rejected/);
  assert.deepEqual(f.toggles,[[true,true],[false,false]]);
  assert.equal(f.counts().reads,0);
});
test("successful recording and folder read still poll status",async()=>{
  const f=harness();await f.ctx.toggleRecording();
  assert.equal(f.state.recordEnabled,true);assert.equal(f.counts().polls,1);
  assert.equal(f.counts().reads,1);assert.equal(f.messages.sessionExportMessage,undefined);
});
test("acknowledged snapshot survives failed folder read and clears pending",async()=>{
  const f=harness({rejectRead:true});const result=await f.ctx.captureOneShot();
  assert.ok(result);assert.equal(f.counts().captures,1);assert.equal(f.counts().pending,false);
  assert.match(f.messages.statusBanner,/Snapshot saved; folder refresh failed/);
});
test("rejected snapshot POST clears pending without false success",async()=>{
  const f=harness({rejectPost:true});await assert.rejects(f.ctx.captureOneShot(),/POST rejected/);
  assert.equal(f.counts().captures,0);assert.equal(f.counts().reads,0);assert.equal(f.counts().pending,false);
});
