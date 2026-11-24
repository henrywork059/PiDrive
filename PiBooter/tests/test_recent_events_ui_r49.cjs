"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const source=fs.readFileSync(path.join(__dirname,"..","pibooter/app.py"),"utf8");
const shell=source.match(/HTML_SHELL = """([\s\S]*?)"""/)?.[1]||"";
const embedded=shell.match(/<script>([\s\S]*?)<\/script>/)?.[1]||"";
const script=embedded.replace(/\{\{/g,"{").replace(/\}\}/g,"}")
  .replace(/\{status_timer\}/g,"");
function make(id){return{
  id,open:false,textContent:"",dataset:{},className:"",listeners:{},
  addEventListener(name,fn){this.listeners[name]=fn;}
};}
function setup(){
  const nodes={};
  for(const name of ["recent-events-panel","recent-events-output",
  "recent-events-status","refresh-recent-events","copy-recent-events"])nodes[name]=make(name);
  const calls=[],copies=[];
  const document={
    getElementById:id=>nodes[id]||null,
    querySelector:key=>null,
  };
  const navigator={clipboard:{writeText:async value=>{copies.push(value)}}};
  const fetch=async url=>{
    calls.push(url);
    return {ok:true,json:async()=>url==="/api/recent-events"?
      {ok:true,events:[{timestamp_utc:"2026-11-24T00:00:00+00:00",
      operation:"wifi_connect",title:"Wi-Fi connection",outcome:"failed"}]}:
      {onboarding:{state:"ready",headline:"Ready",summary:"ready",next_action:"connect"}}};
  };
  vm.runInNewContext(script,{document,fetch,navigator,window:{}},{timeout:1000});
  return {nodes,calls,copies};
}
async function settle(){await new Promise(r=>setImmediate(r));}

test("Python-embedded page JS braces normalize to syntactically valid JS",()=>{
  assert.ok(shell.length>1000);assert.doesNotThrow(()=>new vm.Script(script));
});
test("safe copyable event panel exists in existing Wi-Fi setup page",()=>{
  assert.match(source,/id="recent-events-panel"/);
  assert.match(source,/id="recent-events-output"/);
  assert.match(source,/Copy events/);
  assert.match(source,/Sanitized recent operator events|Recent operator events \(sanitized\)/);
});
test("collapsed view never performs background recent-events polling",async()=>{
  const s=setup();await settle();
  assert.equal(s.calls.filter(x=>x==="/api/recent-events").length,0);
});
test("opening event panel uses GET of bounded sanitized endpoint",async()=>{
  const s=setup();s.nodes["recent-events-panel"].open=true;
  s.nodes["recent-events-panel"].listeners.toggle();await settle();
  assert.equal(s.calls.filter(x=>x==="/api/recent-events").length,1);
  assert.match(s.nodes["recent-events-output"].textContent,/Wi-Fi connection · failed/);
});
test("Copy contains only displayed generic event outcome",async()=>{
  const s=setup();s.nodes["recent-events-panel"].open=true;
  s.nodes["recent-events-panel"].listeners.toggle();await settle();
  await s.nodes["copy-recent-events"].listeners.click();await settle();
  assert.equal(s.copies.length,1);
  assert.equal(s.copies[0],s.nodes["recent-events-output"].textContent);
  assert.doesNotMatch(s.copies[0],/ssid|password|token|\/root\//i);
});
test("refresh button retrieves only the safe recent-events GET",async()=>{
  const s=setup();s.nodes["recent-events-panel"].open=true;
  s.nodes["recent-events-panel"].listeners.toggle();await settle();
  await s.nodes["refresh-recent-events"].listeners.click();await settle();
  assert.equal(s.calls.filter(x=>x==="/api/recent-events").length,2);
});
test("new GET route never bypasses existing setup POST origin/CSRF controls",()=>{
  assert.match(source,/if path == "\/api\/recent-events":/);
  assert.match(source,/authorized_setup_client\(/);
  assert.match(source,/trusted_post_origin\(/);
  assert.match(source,/request_token_matches\(/);
});
test("raw messages are projected before the browser event export",()=>{
  assert.match(source,/safe_events = project_recent_events/);
  assert.match(source,/events": project_recent_events/);
  assert.doesNotMatch(source,/id="recent-events-output"[^>]*>\{html\.escape\(self\.render_logs/);
});
