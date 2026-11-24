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
  assert.match(manual,/if \(payload\?\.ok === false\) return;\s*showCaptureNotice\(/);
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
