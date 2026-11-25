"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "..", "piserver", "web", "static", "app.js"), "utf8");

const folders = (...names) => ({sessions: names.map(name => ({name, kind:"session", image_count:1}))});
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes,no) => {resolve=yes; reject=no;});
  return {promise,resolve,reject};
}
function fixture() {
  const state = {...folders("a","b"), selectedSession:"a", sessionListRevision:0};
  const reads=[], posts=[], messages=[];
  const postStarted=deferred();
  let renders=0, busy=false;
  const button={};
  const ctx=vm.createContext({
    state, document:{getElementById:()=>button},
    window:{PiDriveDestructive:{
      busy:()=>busy, confirm:async()=>{busy=true;return true;}, finish:()=>{busy=false;}
    }},
    fetchJson:(url,options)=>{
      const req=deferred();
      if(url==="/api/record/sessions") reads.push(req);
      else {assert.equal(url,"/api/record/delete");posts.push({...req,body:JSON.parse(options.body)});postStarted.resolve();}
      return req.promise;
    },
    updateSessionExportUi:()=>{renders++;},
    setBanner:(id,message)=>messages.push({id,message}),
    updateStatusUi:()=>{}
  });
  const start=source.indexOf("function findSelectedSession(");
  const end=source.indexOf("\nfunction formatDateTime(",start);
  const refresh=source.indexOf("async function refreshSessions(");
  const refreshEnd=source.indexOf("\nfunction updateSessionSelectionFromStatus(",refresh);
  const del=source.indexOf("async function deleteSelectedSession(");
  const delEnd=source.indexOf("\nasync function sendControlUpdate(",del);
  assert.ok(start>=0 && end>start && refresh>=0 && refreshEnd>refresh && del>=0 && delEnd>del);
  vm.runInContext(source.slice(start,end)+"\n"+source.slice(refresh,refreshEnd)+"\n"+source.slice(del,delEnd),ctx);
  return {ctx,state,reads,posts,messages,postStarted:postStarted.promise,renders:()=>renders,busy:()=>busy};
}

test("refresh retains a folder chosen while the read is pending",async()=>{
  const f=fixture();const p=f.ctx.refreshSessions();
  f.state.selectedSession="b";
  f.reads[0].resolve(folders("a","b","c"));await p;
  assert.equal(f.state.selectedSession,"b");assert.equal(f.renders(),1);
});
test("removed selection falls back to the first folder, including empty lists",async()=>{
  const f=fixture();let p=f.ctx.refreshSessions();
  f.state.selectedSession="b";f.reads[0].resolve(folders("a","c"));await p;
  assert.equal(f.state.selectedSession,"a");
  p=f.ctx.refreshSessions();f.reads[1].resolve(folders());await p;
  assert.equal(f.state.selectedSession,"");assert.equal(f.state.sessions.length,0);
});
test("startup reset does not overwrite a choice made while waiting",async()=>{
  const f=fixture();const p=f.ctx.refreshSessions(false);
  f.state.selectedSession="b";f.reads[0].resolve(folders("a","b"));await p;
  assert.equal(f.state.selectedSession,"b");
});
test("overlapping refresh ignores late success and does not repeat feedback",async()=>{
  const f=fixture();const older=f.ctx.refreshSessionsWithFeedback();
  const newer=f.ctx.refreshSessionsWithFeedback();
  f.reads[1].resolve(folders("b","c"));await newer;
  f.reads[0].resolve(folders("a"));await older;
  assert.equal(f.state.selectedSession,"b");
  assert.deepEqual(f.state.sessions.map(x=>x.name),["b","c"]);
  assert.equal(f.renders(),1);assert.equal(f.messages.length,1);
});
test("older failed read cannot replace newer success feedback",async()=>{
  const f=fixture();const older=f.ctx.refreshSessionsWithFeedback();
  const newer=f.ctx.refreshSessionsWithFeedback();
  f.reads[1].resolve(folders("b"));await newer;
  f.reads[0].reject(Error("stale failure"));await older;
  assert.deepEqual(f.messages,[{id:"sessionExportMessage",message:"Session list refreshed."}]);
});
test("latest failure retains list and displays failure; stale success cannot clear it",async()=>{
  const f=fixture();const older=f.ctx.refreshSessionsWithFeedback();
  const newer=f.ctx.refreshSessionsWithFeedback();
  f.reads[1].reject(Error("offline"));await newer;
  f.reads[0].resolve(folders("c"));await older;
  assert.equal(f.state.selectedSession,"a");assert.equal(f.renders(),0);
  assert.deepEqual(f.messages,[{id:"sessionExportMessage",message:"offline"}]);
});
for(const fail of [false,true]) {
  test("confirmed deletion supersedes pending folder "+(fail?"failure":"success"),async()=>{
    const f=fixture();const older=f.ctx.refreshSessionsWithFeedback();
    const deletion=f.ctx.deleteSelectedSession();await f.postStarted;
    assert.deepEqual(f.posts[0].body,{session:"a",confirm:true});
    f.state.selectedSession="b";
    f.posts[0].resolve({...folders("b"),message:"Deleted a."});await deletion;
    if(fail)f.reads[0].reject(Error("stale failure"));else f.reads[0].resolve(folders("a","b"));
    await older;
    assert.deepEqual(f.state.sessions.map(x=>x.name),["b"]);
    assert.equal(f.state.selectedSession,"b");
    assert.deepEqual(f.messages,[{id:"sessionExportMessage",message:"Deleted a."}]);
    assert.equal(f.busy(),false);
    const fresh=f.ctx.refreshSessions();f.reads[1].resolve(folders("b","c"));await fresh;
    assert.equal(f.state.sessions.length,2);
  });
}
test("rejected deletion does not invalidate a still-current read",async()=>{
  const f=fixture();const p=f.ctx.refreshSessions();
  const deletion=f.ctx.deleteSelectedSession();await f.postStarted;
  f.posts[0].reject(Error("rejected"));
  await assert.rejects(deletion,/rejected/);
  f.reads[0].resolve(folders("a","b","c"));await p;
  assert.equal(f.state.sessions.length,3);assert.equal(f.busy(),false);
});
