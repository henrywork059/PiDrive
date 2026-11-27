"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.join(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const manual=read("pisd/web/static/js/manual_drive.js");
const ai=read("pisd/web/static/js/ai_mode.js");
const errors=read("pisd/core/errors.py");
const app=read("pisd/app.py");
const trace=read("pisd/core/request_trace.py");
test("Manual Drive and AI Mode scripts parse",()=>{
  assert.doesNotThrow(()=>new vm.Script(manual));
  assert.doesNotThrow(()=>new vm.Script(ai));
});
test("PiSD installs response hook without changing native error code registry",()=>{
  assert.match(app,/install_mutation_trace\(app\)/);
  assert.match(app,/PiSDErrorCodes\.API_SERVICE_EXCEPTION/);
  assert.match(trace,/secrets\.token_hex\(8\)/);
});
test("API error history export redacts paths and credentials",()=>{
  assert.match(errors,/safe_diagnostic_text\(self\.message\)/);
  assert.match(errors,/safe_diagnostic\(self\.context\)/);
  assert.match(errors,/traceback not exported/);
  assert.match(errors,/safe_diagnostic_text\(latest\.message\)/);
});
test("Manual Drive avoids full raw response serialization on failed calls",()=>{
  assert.match(manual,/const safeResponse = failed \?/);
  assert.match(manual,/correlation_id: payload\?\.correlation_id/);
  assert.match(manual,/response: safeResponse/);
});
test("Manual Drive expandable reference uses only validated trace ID",()=>{
  assert.match(manual,/function appendRequestTrace\(payload, status\)/);
  assert.match(manual,/\/\^\[0-9a-f\]\{16\}\$\/\.test\(id\)/);
  assert.match(manual,/summary\.textContent = 'Error details'/);
  assert.match(manual,/short\.parentNode\.insertBefore\(details, short\.nextSibling\)/);
});
test("failed PiSD camera Start never advertises running preview",()=>{
  assert.match(manual,/if \(payload\?\.ok === false\) return; \/\/ keep failed Start/);
  assert.match(manual,/if \(preview && !document\.hidden\) preview\.src/);
});
test("failed motor STOP and drive/recording commands never claim success",()=>{
  assert.match(manual,/if \(payload\?\.ok === false\) return; \/\/ STOP outcome is unconfirmed/);
  assert.match(manual,/if \(result\.payload\?\.ok === false\) return/);
  // The recording path now reports rejection visibly rather than silently returning.
  // Its exact production handler is exercised below for HTTP and payload outcomes.
});
test("AI failure hides raw error payload and retains correlation metadata",()=>{
  assert.match(ai,/const safePayload = traced/);
  assert.match(ai,/correlation_id: traceId/);
  assert.match(ai,/throw Object\.assign\(new Error\(message\), \{ payload: safePayload/);
  assert.match(ai,/summary\.textContent = 'Error details'/);
});
test("R43 hidden tab STOP and AI timer remain unchanged",()=>{
  assert.match(manual,/sendFailSafeStop\('visibility-hidden'\)/);
  assert.match(ai,/if \(document\.hidden \|\| statusPollInFlight\) return/);
  assert.match(ai,/stopFullManualDrive\('ai-manual-hidden'\)/);
});


test("actual Manual recording handler never reports success on HTTP or payload rejection", async()=>{
  require("../pisd/web/static/js/recording_reader.js");
  const start=manual.indexOf("  async function toggleRecording()");
  const end=manual.indexOf("  function sendFailSafeStop",start);
  assert.ok(start>=0 && end>start);
  for(const stopping of [false,true]) {
    for(const [httpOk,payload,success] of [
      [false,{ok:true,code:"PISD-OK-000"},false],
      [true,{ok:false,code:"PISD-REC-002"},false],
      [true,{},false],
      [true,{ok:true,code:"PISD-OK-000",recording:{running:!stopping}},true]
    ]) {
      const notices=[],requests=[],states=[],gate=globalThis.PiSDRecordingReader.createRecordingGate();
      let refresh=0, folders=0;
      const ctx=vm.createContext({
        recordingGate:gate, recordingRunning:stopping, DEFAULTS:{recording_fps:6},
        readRuntimeLocal:()=>({}), overlaySettingsForRecording:()=>({}),
        api:async(method,path)=>{requests.push([method,path]);return {response:{ok:httpOk},payload};},
        renderRecording:value=>states.push(value), isOk:code=>String(code).startsWith("PISD-OK"),
        showCaptureNotice:(message,code)=>notices.push({message,code}),
        writeLog:()=>{}, refreshStatus:async()=>{refresh++;}, refreshRecordingItems:async()=>{folders++;}
      });
      vm.runInContext(manual.slice(start,end),ctx);
      await Promise.all([ctx.toggleRecording(),ctx.toggleRecording()]);
      assert.deepEqual(requests,[["POST",stopping?"/api/recording/stop":"/api/recording/start"]]);
      assert.equal(notices.length,1);
      assert.equal(refresh,1);assert.equal(folders,1);
      if(success) {
        assert.match(notices[0].message,/acknowledged/);
        assert.equal(notices[0].code,"PISD-OK-000");
        assert.deepEqual(states,[{running:!stopping}]);
      } else {
        assert.match(notices[0].message,/not confirmed/);
        assert.equal(notices[0].code,"PISD-REC-002");
        assert.equal(states.length,0);
      }
    }
  }
});
test("AI recording actions require explicit successful acknowledgement",()=>{
  for(const endpoint of ["capture","start","stop"]) {
    const at=ai.indexOf("const data = await api('/api/recording/"+endpoint+"'");
    assert.ok(at>=0);
    assert.match(ai.slice(at,at+450),/if \(data\.ok !== true\) throw new Error\('Recording acknowledgement missing\.'\)/);
  }
});
