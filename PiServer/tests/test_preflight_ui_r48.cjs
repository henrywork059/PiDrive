"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.join(__dirname,"..");
const script=fs.readFileSync(path.join(root, "piserver/web/static/preflight.js"),"utf8");
const html=fs.readFileSync(path.join(root, "piserver/web/templates/index.html"),"utf8");

function node(tag="div") {
  return {
    tagName:tag, textContent:"", dataset:{}, disabled:false, children:[],
    callbacks:{},
    appendChild(value){this.children.push(value);},
    replaceChildren(...values){this.children=[...values];},
    addEventListener(type,fn){this.callbacks[type]=fn;},
  };
}
function setup({response,fail=false}={}) {
  const elements={
    '[data-preflight-list]':node("ul"),
    '[data-preflight-status]':node("p"),
    'summary':node("summary"),
    '[data-preflight-refresh]':node("button"),
  };
  const calls=[];
  const panel={querySelector(key){return elements[key]||null}};
  const document={
    querySelector(key){return key==='[data-preflight-root]'?panel:null},
    createElement(tag){return node(tag)},
    createDocumentFragment(){return node("fragment")},
  };
  async function fetch(url,opts) {
    calls.push({url,opts});
    if(fail) throw new Error("connection down");
    return {ok:true,json:async()=>response||{
      ok:true,read_only:true,
      checks:[
        {key:"mode",title:"Service mode",state:"simulation",
         detail:"No GPIO adapter",next_step:"Inspect the Pi"},
        {key:"model",title:"AI model",state:"attention",
         detail:"No model",next_step:"Upload a model"},
      ],
    }};
  }
  vm.runInNewContext(script,{document,fetch},{timeout:1000});
  return {elements,calls};
}
async function settle(){await new Promise(resolve=>setImmediate(resolve));}

test("preflight browser JS parses",()=>assert.doesNotThrow(()=>new vm.Script(script)));
test("read-only panel and refresh are present without removing primary controls",()=>{
  assert.match(html,/data-preflight-root/);
  assert.match(html,/data-preflight-refresh/);
  assert.match(html,/data-preflight-list/);
  assert.match(html,/role="status"/);
  assert.match(html,/Startup preflight \(read-only\)/);
});
test("initial load calls only GET /api/preflight",async()=>{
  const x=setup(); await settle();
  assert.equal(x.calls.length,1);
  assert.equal(x.calls[0].url,"/api/preflight");
  assert.equal(x.calls[0].opts.method,"GET");
  assert.equal(x.calls[0].opts.cache,"no-store");
  assert.equal(x.calls[0].opts.credentials,"same-origin");
});
test("renders explicit simulation and missing model without HTML injection",async()=>{
  const x=setup(); await settle();
  const rows=x.elements['[data-preflight-list]'].children[0].children;
  assert.equal(rows.length,2);
  assert.match(rows[0].children[0].textContent,/Service mode — Simulation/);
  assert.match(rows[1].children[0].textContent,/AI model — Needs attention/);
  assert.match(x.elements['[data-preflight-status]'].textContent,/No hardware actions performed/);
  assert.doesNotMatch(script,/\.innerHTML\s*=/);
});
test("refresh requests a new read-only GET and never a POST",async()=>{
  const x=setup();await settle();
  await x.elements['[data-preflight-refresh]'].callbacks.click();
  await settle();
  assert.equal(x.calls.length,2);
  assert.ok(x.calls.every(c=>c.opts.method==="GET"&&c.url==="/api/preflight"));
});
test("unavailable server is honestly marked unavailable",async()=>{
  const x=setup({fail:true});await settle();
  assert.match(x.elements.summary.textContent,/unavailable/);
  assert.match(x.elements['[data-preflight-status]'].textContent,/Check the Pi connection/);
  assert.equal(x.elements['[data-preflight-list]'].children.length,0);
});
test("source does not call hardware/camera/settings mutation routes",()=>{
  assert.doesNotMatch(script,/fetch\([^)]*\/api\/(?:motor|camera\/start|session\/start|settings\/apply)/);
  assert.doesNotMatch(script,/method:\s*['"]POST['"]/);
});
