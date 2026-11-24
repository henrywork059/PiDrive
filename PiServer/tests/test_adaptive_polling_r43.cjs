"use strict";
// R43 modeled request-rate policy checks; does not simulate network/robot timing.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "piserver", "web", "static", "app.js"), "utf8");
function policy(state, hidden) {
  const start = source.indexOf("function statusPollDelayMs() {");
  const end = source.indexOf("\nfunction scheduleStatusPoll(", start);
  assert.ok(start >= 0 && end > start, "actual status policy function found");
  const context = vm.createContext({state, document: {hidden}, Math, Object});
  const script = new vm.Script("("+source.slice(start, end).trim()+")()");
  return script.runInContext(context);
}
function freshState(overrides={}) {
  return {latestStatus:{camera_preview_live:false, recording:false}, statusFailures:0,
    manualThrottle:0,manualSteering:0,pointerControl:{active:false},
    stepInputs:{up:false,down:false,left:false,right:false},...overrides};
}

test("idle PiServer status interval becomes 2.5s", () => {
  assert.equal(policy(freshState(), false), 2500);
});
test("moving/recording/camera activity retains previous 800 ms interval", () => {
  for(const active of [
    {manualThrottle:0.5}, {pointerControl:{active:true}},
    {latestStatus:{recording:true}}, {latestStatus:{camera_preview_live:true}},
    {stepInputs:{up:true}}
  ]) assert.equal(policy(freshState(active),false),800);
});
test("hidden tabs do not execute status requests", () => {
  assert.equal(policy(freshState(), true), 5000);
  assert.match(source,/if \(document\.hidden\) \{\s*scheduleStatusPoll\(\);\s*return;/);
});
test("concurrent status in flight remains guarded", () => {
  assert.match(source,/if \(state\.statusInFlight\) return;/);
  assert.match(source,/state\.statusInFlight = true;/);
});
test("retry is bounded; returning to visible tab is immediate", () => {
  assert.equal(policy(freshState({statusFailures:1}),false),5000);
  assert.equal(policy(freshState({statusFailures:99}),false),8000);
  assert.match(source,/scheduleStatusPoll\(0\); \/\/ refresh immediately on return/);
});
test("motor tick and existing JPEG freshness guard are not changed", () => {
  assert.match(source,/const STEP_INTERVAL_MS = 60;/);
  assert.match(source,/setInterval\(controlLoopTick, STEP_INTERVAL_MS\)/);
  assert.match(source,/if \(state\.previewInFlight\)/);
  assert.match(source,/previewHealth\.retryDelay\(previewDelayMs\(\)\)/);
});
test("modeled one-tab idle status rate declines 75 to 24 requests/minute", () => {
  const previous = 60000/800, current = 60000/policy(freshState(),false);
  assert.equal(previous,75);
  assert.equal(current,24);
  assert.equal((1-current/previous)*100,68);
});


// Execute the real polling function with a controllable delayed response.
function delayedPoll() {
  const start = source.indexOf("async function pollStatus() {");
  const end = source.indexOf("\nasync function refreshModels()", start);
  assert.ok(start >= 0 && end > start);
  const state = {statusInFlight:false, statusRevision:0, statusFailures:0};
  let resolve, reject, updates=0, errors=0, syncs=0, scheduled=0;
  const deferred = new Promise((ok, fail) => { resolve=ok; reject=fail; });
  const ctx = vm.createContext({state, document:{hidden:false}, Math,
    fetchJson:()=>deferred,
    updateStatusUi:()=>{updates++;state.statusRevision++;},
    syncControlsFromStatus:()=>{syncs++;},
    markStatusUnverified:()=>{errors++;},
    scheduleStatusPoll:()=>{scheduled++;}});
  vm.runInContext(source.slice(start,end),ctx);
  return {state, resolve, reject, poll:()=>ctx.pollStatus(),
    counts:()=>({updates,errors,syncs,scheduled})};
}
test("a slow successful status read is applied when no newer snapshot exists", async () => {
  const f=delayedPoll();const pending=f.poll();
  f.resolve({safety_stop:false});await pending;
  assert.deepEqual(f.counts(),{updates:1,errors:0,syncs:1,scheduled:1});
  assert.equal(f.state.statusInFlight,false);
});
test("a delayed old success cannot overwrite a newer confirmed snapshot", async () => {
  const f=delayedPoll();const pending=f.poll();
  f.state.statusRevision++;f.resolve({safety_stop:false});await pending;
  assert.deepEqual(f.counts(),{updates:0,errors:0,syncs:0,scheduled:1});
  assert.equal(f.state.statusInFlight,false);
});
test("a delayed old failure cannot mark a newer confirmed snapshot unverified", async () => {
  const f=delayedPoll();const pending=f.poll();
  f.state.statusRevision++;f.reject(new Error("old timeout"));await pending;
  assert.deepEqual(f.counts(),{updates:0,errors:0,syncs:0,scheduled:1});
  assert.equal(f.state.statusInFlight,false);
});
