"use strict";
const assert = require("node:assert/strict");
const {create, neutralAck} = require("../pisd/web/static/js/v17_transition.js");
const ok = {ok:true, motor:{manual_lease_active:false,last_intended_left:0,last_intended_right:0,last_left:0,last_right:0},ai:{running:false,drive_output_enabled:false}};
const response = data => ({ok:true,json:async()=>data});
const deferred = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
async function main() {
  assert(neutralAck(ok));
  for (const data of [{ok:true}, {...ok,motor:{...ok.motor,last_left:0.1}}, {...ok,motor:{...ok.motor,last_left:null}}, {...ok,ai:{...ok.ai,running:true}}, {...ok,motor:{...ok.motor,manual_lease_active:true}}]) assert(!neutralAck(data));
  let log=[], motion=deferred(), firstStop=deferred(), stopCount=0;
  const controller=create({
    fetchImpl(path){log.push(path);if(path==="/api/control/manual") return motion.promise; if(path==="/api/control/stop") return ++stopCount===1?firstStop.promise:Promise.resolve(response(ok));throw Error(path);},
    disarm:()=>log.push("disarm"), status:(s)=>log.push(s), navigate:(u)=>log.push(u),
  });
  const sent=controller.request("/api/control/manual",{method:"POST"});
  await Promise.resolve();
  const moving=controller.switchTo("/drive?mode=ai");
  await assert.rejects(controller.request("/api/control/manual",{method:"POST"}),/locked/);
  await assert.rejects(controller.request("/api/ai/start",{method:"POST"}),/locked/);
  assert.equal(await controller.switchTo("/"),false);
  firstStop.resolve(response(ok));
  await Promise.resolve();await Promise.resolve();
  assert(!log.includes("/drive?mode=ai"));
  motion.resolve(response(ok));await sent;
  assert.equal(await moving,true);
  assert.deepEqual(log,["/api/control/manual","disarm","pending","/api/control/stop","/api/control/stop","confirmed","/drive?mode=ai"]);
  log=[]; let fail=true;
  const retry=create({fetchImpl:async()=>fail?{ok:false,json:async()=>({ok:false})}:response(ok),disarm:()=>{},status:s=>log.push(s),navigate:u=>log.push(u)});
  assert.equal(await retry.switchTo("/"),false);
  assert.deepEqual(log,["pending","failed"]);
  await assert.rejects(retry.request("/api/ai/start",{method:"POST"}),/locked/);
  fail=false;assert.equal(await retry.switchTo("/"),true);
  assert.deepEqual(log,["pending","failed","pending","confirmed","/"]);
  const unknown=create({fetchImpl:async path=>{if(path==="/api/control/manual")throw Error("network");return response(ok);},disarm:()=>{},status:()=>{},navigate:()=>{throw Error("must not navigate");}});
  await assert.rejects(unknown.request("/api/control/manual",{method:"POST"}),/network/);
  assert.equal(await unknown.switchTo("/"),false);
  console.log("V17 transition: acknowledgement, pending drain, duplicate navigation, refusal, retry and unknown-outcome checks passed");
}
main().catch(error=>{console.error(error);process.exitCode=1;});
