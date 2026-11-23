"use strict";
// R45 design contract for the real GUI theme and separate Mission 1 palette.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.join(__dirname,"..");
const gui=path.join(root,"custom_drive","gui_web","static");
const mission=path.join(root,"custom_drive","mission1_web","static");
const theme=fs.readFileSync(path.join(gui,"theme.js"),"utf8");
const css=fs.readFileSync(path.join(gui,"styles.css"),"utf8");
const missionCss=fs.readFileSync(path.join(mission,"styles.css"),"utf8");
const guide=fs.readFileSync(path.join(root,"UI_DESIGN_TOKENS.md"),"utf8");

function boot(store=new Map()) {
  const declarations=new Map(), classes=new Set();
  const document={documentElement:{
    style:{setProperty(k,v){declarations.set(k,String(v));}},
    classList:{add(...xs){xs.forEach(x=>classes.add(x));},
               remove(...xs){xs.forEach(x=>classes.delete(x));}},
  }};
  const window={localStorage:{
    getItem(k){return store.has(k)?store.get(k):null;},
    setItem(k,v){store.set(k,String(v));},
    removeItem(k){store.delete(k);},
  }};
  vm.runInNewContext(theme,{window,document,Number,String,JSON,Object});
  return {api:window.PiServerStyle,declarations,store,classes};
}

test("general GUI's own theme advertises expected semantic token names",()=>{
  const v=boot().api.getResolvedVars();
  for(const key of ["--bg","--panel","--panel-alt","--accent","--accent-rgb",
                    "--ok","--warn","--danger","--text","--muted",
                    "--font-scale","--font-scale-factor","--card-gap","--field-gap",
                    "--control-radius","--card-radius"])
    assert.equal(typeof v[key],"string",key);
});
test("general GUI accepted status roles are stable",()=>{
  const v=boot().api.getResolvedVars();
  assert.equal(v["--ok"],"#8d9d61");
  assert.equal(v["--warn"],"#f4a31e");
  assert.equal(v["--danger"],"#ca655d");
  assert.equal(v["--accent"],"#f4a31e");
  assert.equal(v["--muted"],"#9ea5b5");
});
test("accepted GUI compact density is unchanged",()=>{
  const v=boot().api.getResolvedVars();
  assert.equal(v["--font-scale"],"80%");
  assert.equal(v["--workspace-pad"],"10px");
  assert.equal(v["--panel-pad"],"12px");
  assert.equal(v["--gap"],"4px");
});
test("GUI reapply does not wipe custom styling",()=>{
  const {api,store}=boot();
  api.saveCustomOverrides({"--panel-pad":"26px","--accent":"#445566"});
  api.applyTheme("opsFlat");
  assert.equal(api.getResolvedVars()["--panel-pad"],"26px");
  assert.equal(api.getResolvedVars()["--accent"],"#445566");
  assert.ok(store.has("PiServerStyleCustom:v0_3_5"));
});
test("GUI saved theme persists after browser script reinitialization",()=>{
  const store=new Map();
  boot(store).api.saveCustomOverrides({"--font-scale":"125%","--card-gap":"16px"});
  const next=boot(store);
  assert.equal(next.api.getResolvedVars()["--font-scale-factor"],"1.25");
  assert.equal(next.declarations.get("--card-gap"),"16px");
});
test("only explicit reset erases GUI user-defined overrides",()=>{
  const {api,store}=boot();
  api.saveCustomOverrides({"--workspace-pad":"33px"});
  api.resetCustomOverrides();
  assert.equal(store.has("PiServerStyleCustom:v0_3_5"),false);
  assert.equal(api.getResolvedVars()["--workspace-pad"],"10px");
});
test("keep the historical GUI style API and storage key for compatibility",()=>{
  assert.match(theme,/PiServerStyleCustom:v0_3_5/);
  for(const method of ["getResolvedVars","saveCustomOverrides","resetCustomOverrides","applyTheme"])
    assert.ok(theme.includes(method),method);
});
test("GUI status CSS uses meaning-aware classes not accent alone",()=>{
  for(const cls of [".banner.muted",".banner.warn",".banner.good",".badge.estop",
                    ".preview-health.delayed",".preview-health.disconnected",
                    '.settings-apply-state[data-state="applied"]',
                    '.settings-apply-state[data-state="failed"]'])
    assert.ok(css.includes(cls),cls);
  assert.match(css,/:focus-visible/);
});
test("GUI CSS references central density/shape tokens",()=>{
  for(const key of ["--workspace-pad","--panel-pad","--card-gap","--field-gap",
                    "--control-radius","--card-radius"])
    assert.ok(css.includes("var("+key+")"),key);
  assert.match(css,/min-height:\s*44px/);
});
test("Mission 1 uses its own separate dark-blue and cyan palette",()=>{
  for(const [key,value] of [["--bg","#0b1220"],["--panel","#101827"],
                             ["--text","#e5edf9"],["--muted","#9fb0cc"],
                             ["--accent","#38bdf8"]])
    assert.ok(missionCss.includes(key+": "+value+";"),key);
});
test("Mission stage-state colors remain distinguishable by semantic role",()=>{
  for(const state of ["current","completed","failed","interrupted"])
    assert.ok(missionCss.includes('.mission-progress-step[data-step-state="'+state+'"]'),state);
  assert.match(missionCss,/data-step-state="current"[^\n]*#38bdf8/);
  assert.match(missionCss,/data-step-state="completed"[^\n]*#22c55e/);
  assert.match(missionCss,/data-step-state="failed"[^\n]*#f87171/);
  assert.match(missionCss,/data-step-state="interrupted"[^\n]*#fbbf24/);
});
test("R44 green Grip and amber Drop-off guide stays distinct",()=>{
  assert.match(missionCss,/\.overlay-guides \.overlay-trigger-pickup\s*\{[^}]*#4ade80/s);
  assert.match(missionCss,/\.overlay-guides \.overlay-trigger-dropoff\s*\{[^}]*#fbbf24/s);
  assert.ok(missionCss.includes(".trigger-guide-readout"));
  assert.ok(missionCss.includes(".overlay-frame-scale"));
});
test("Mission 1 layout, focus and mobile targets remain accessible",()=>{
  assert.match(missionCss,/aspect-ratio:\s*16\s*\/\s*9/);
  assert.match(missionCss,/:focus-visible/);
  assert.match(missionCss,/min-height:\s*44px/);
  assert.match(missionCss,/@media\s*\(max-width:\s*720px\)/);
});
test("component-specific policy and icon-size guidance are documented",()=>{
  for(const word of ["separately owned","Mission 1","100% top","50% middle",
                     "0% bottom","16px","18px","44px","R43","R44"])
    assert.ok(guide.includes(word),word);
});
