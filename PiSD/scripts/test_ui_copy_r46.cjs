"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
const manual=read("pisd/web/static/js/manual_drive.js");
const ai=read("pisd/web/static/js/ai_mode.js");
const version=read("pisd/__init__.py");
const readerSource=read("pisd/web/static/js/recording_reader.js");
test("Manual and AI browser JS both parse",()=>{
 assert.doesNotThrow(()=>new vm.Script(manual));
 assert.doesNotThrow(()=>new vm.Script(ai));
});
test("no recording folders has a Record next step",()=>{
 assert.match(manual,/No recordings yet\. Start live, then Record/);
 assert.match(manual,/No recordings — start a recording/);
});
test("no snapshots has a capture next step",()=>{
 assert.match(manual,/No snapshots yet\. Start live and capture a frame/);
 assert.match(manual,/No snapshots — capture a frame/);
});
test("empty folders are not mislabeled as loaded after refreshing",()=>{
 assert.match(manual,/const selectedKind = fileKind\?\.value === 'snapshot'/);
 assert.match(manual,/if \(visibleItems\.length\)/);
});
test("offline folder refresh says what to do without losing diagnostics",()=>{
 assert.match(manual,/Could not load saved folders\. Check the Pi connection, then Refresh/);
 assert.match(manual,/writeLog\('recording items failed'/);
});
test("empty models and camera error include actionable next step",()=>{
 assert.match(ai,/No models on Pi — upload \.keras or \.tflite/);
 assert.match(ai,/No AI models on Pi\. Upload a \.keras or \.tflite file/);
 assert.match(ai,/Camera preview unavailable\. Check camera, then Start live again/);
});
test("preserve safety stop, streaming, AI ownership and version",()=>{
 assert.match(manual,/sendFailSafeStop\('visibility-hidden'\)/);
 assert.match(ai,/stopFullManualDrive\('ai-manual-hidden'\)/);
 assert.match(ai,/stopAssistDrive\('ai-assist-hidden'\)/);
 assert.match(ai,/if \(document\.hidden \|\| statusPollInFlight\) return/);
 const m=version.match(/__version__\s*=\s*"0\.11\.(\d+)"/);assert.ok(m&&Number(m[1])>=19);
});

/* Execute the actual shared browser reader with controlled network completion.
   No physical backend, real clock or mutation requests. */
function readerHarness(){
 const requests=[],timers=new Map();let id=0;
 const ctx={AbortController,fetch:(url,options)=>new Promise((resolve,reject)=>{
   requests.push({url,options,resolve,reject});
 }),setTimeout:(fn,ms)=>{assert.equal(ms,3500);timers.set(++id,fn);return id;},
 clearTimeout:id=>timers.delete(id)};
 vm.createContext(ctx);new vm.Script(readerSource).runInContext(ctx);
 return {reader:ctx.PiSDRecordingReader.createReader(),requests,timers};
}
const good=(name="a")=>({ok:true,collections:{recordings:[{id:name}],snapshots:[]}});
function reply(req,data,status=200){req.resolve({ok:status===200,status,json:async()=>data});}
test("newer folder read cannot be overwritten by stale success or rejection",async()=>{
 const {reader,requests,timers}=readerHarness();
 const first=reader.read(),second=reader.read();
 assert.equal(requests[0].options.signal.aborted,true);
 assert.equal(requests[1].url,"/api/recording/items");
 assert.equal(reader.loading(),true);
 reply(requests[1],good("new"));
 const newer=await second;
 assert.equal(newer.payload.collections.recordings[0].id,"new");
 reply(requests[0],good("old"));
 assert.equal(await first,null);
 assert.equal(reader.verified(),true);
 assert.equal(reader.isCurrent(newer.token),true);
 const third=reader.read(),fourth=reader.read();
 reply(requests[3],good("latest"));
 await fourth;
 requests[2].reject(new Error("old failure"));
 assert.equal(await third,null);
 assert.equal(reader.verified(),true);
 assert.equal(timers.size,0);
});
test("deadline during JSON body cannot verify even if transport returns late",{timeout:2000},async()=>{
 const {reader,requests,timers}=readerHarness();
 const pending=reader.read();
 let signalBodyStarted;
 const bodyStarted=new Promise(resolve=>{signalBodyStarted=resolve;});
 requests[0].resolve({ok:true,status:200,json:()=>new Promise(resolve=>{
   signalBodyStarted(resolve);
 })});
 const finishBody=await bodyStarted;
 assert.equal(typeof finishBody,"function");
 assert.equal(reader.loading(),true);
 assert.equal(timers.size,1);
 [...timers.values()][0]();
 assert.equal(requests[0].options.signal.aborted,true);
 finishBody(good());
 const result=await pending;
 assert.match(result.error,/timed out/);
 assert.equal(reader.verified(),false);
 assert.equal(reader.loading(),false);
 assert.equal(timers.size,0);
});
test("rejected and malformed folder lists stay unverified; retry succeeds",async()=>{
 const {reader,requests}=readerHarness();
 let pending=reader.read();
 reply(requests[0],{ok:false,message:"offline"},503);
 assert.match((await pending).error,/offline/);
 assert.equal(reader.verified(),false);
 pending=reader.read();
 reply(requests[1],{ok:true,collections:{recordings:[]}});
 assert.match((await pending).error,/not confirmed/);
 assert.equal(reader.verified(),false);
 pending=reader.read();
 reply(requests[2],good());
 await pending;
 assert.equal(reader.verified(),true);
 reader.invalidate();
 assert.equal(reader.verified(),false);
});
