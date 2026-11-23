"use strict";
// R45 component-local token contract: no browser automation or hardware.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const themeSrc = fs.readFileSync(path.join(root,"piserver","web","static","theme.js"),"utf8");
const css = fs.readFileSync(path.join(root,"piserver","web","static","styles.css"),"utf8");
const guide = fs.readFileSync(path.join(root,"UI_DESIGN_TOKENS.md"),"utf8");

function boot(store=new Map()) {
  const declarations = new Map();
  const classes = new Set();
  const document = { documentElement: {
    style: { setProperty(name, value) { declarations.set(name, String(value)); } },
    classList: {
      add(...values) { values.forEach(value=>classes.add(value)); },
      remove(...values) { values.forEach(value=>classes.delete(value)); },
    }
  } };
  const window = { localStorage: {
    getItem(key) { return store.has(key) ? store.get(key) : null; },
    setItem(key,value) { store.set(key,String(value)); },
    removeItem(key) { store.delete(key); },
  }};
  vm.runInNewContext(themeSrc,{window,document,JSON,Object,Number,String});
  return { api:window.PiServerStyle, declarations, classes, store };
}

test("R45 runtime token names stay semantic, no palette invention",()=>{
  const {api,declarations}=boot();
  const values=api.getResolvedVars();
  for(const key of ["--bg","--panel","--panel-alt","--text","--muted","--accent",
                    "--ok","--warn","--danger","--font-scale",
                    "--workspace-pad","--panel-pad","--card-gap","--field-gap",
                    "--control-radius","--card-radius"])
    assert.equal(declarations.get(key),values[key],key);
});
test("accepted operator theme status colors remain stable until reviewed",()=>{
  const v=boot().api.getResolvedVars();
  assert.equal(v["--ok"],"#8d9d61");
  assert.equal(v["--warn"],"#f4a31e");
  assert.equal(v["--danger"],"#ca655d");
  assert.equal(v["--muted"],"#9ea5b5");
  assert.equal(v["--accent"],"#f4a31e");
});
test("accepted compact sizing and dense operator spacing",()=>{
  const v=boot().api.getResolvedVars();
  assert.equal(v["--font-scale"],"80%");
  assert.equal(v["--font-scale-factor"],"0.8");
  assert.equal(v["--gap"],"4px");
  assert.equal(v["--workspace-pad"],"10px");
  assert.equal(v["--panel-pad"],"12px");
  assert.equal(v["--control-radius"],"12px");
});
test("custom overrides supersede theme without losing other tokens",()=>{
  const {api,declarations}=boot();
  api.saveCustomOverrides({"--accent":"#112233","--workspace-pad":"19px","--font-scale":"92%"});
  assert.equal(declarations.get("--accent"),"#112233");
  assert.equal(declarations.get("--workspace-pad"),"19px");
  assert.equal(declarations.get("--font-scale-factor"),"0.92");
  assert.equal(api.getResolvedVars()["--warn"],"#f4a31e");
});
test("applyTheme does not replace persisted custom visual preferences",()=>{
  const {api,store}=boot();
  api.saveCustomOverrides({"--panel-pad":"24px"});
  api.applyTheme("opsFlat");
  assert.equal(api.getResolvedVars()["--panel-pad"],"24px");
  assert.ok(store.has("PiServerStyleCustom:v0_3_5"));
});
test("user overrides survive full theme reload from localStorage",()=>{
  const store=new Map();
  boot(store).api.saveCustomOverrides({"--card-gap":"21px","--font-scale":"110%"});
  const next=boot(store);
  assert.equal(next.api.getResolvedVars()["--card-gap"],"21px");
  assert.equal(next.declarations.get("--font-scale-factor"),"1.1");
});
test("reset is explicit and restores defaults rather than erasing silently",()=>{
  const {api,store}=boot();
  api.saveCustomOverrides({"--card-gap":"42px"});
  api.resetCustomOverrides();
  assert.equal(api.getResolvedVars()["--card-gap"],"10px");
  assert.equal(store.has("PiServerStyleCustom:v0_3_5"),false);
});
test("invalid persisted data falls back without removing it",()=>{
  const store=new Map([["PiServerStyleCustom:v0_3_5","{corrupt"]]);
  const {api}=boot(store);
  assert.equal(api.getResolvedVars()["--font-scale"],"80%");
  assert.equal(store.size,1);
});
test("source retains stable public style API and storage key",()=>{
  for(const name of ["getCurrentTheme","getCustomOverrides","getResolvedVars",
                     "saveCustomOverrides","resetCustomOverrides","applyTheme"])
    assert.ok(themeSrc.includes(name),name);
  assert.match(themeSrc,/const customStyleKey = 'PiServerStyleCustom:v0_3_5'/);
});
test("CSS consumes semantic variables and has no hidden replacements",()=>{
  for(const variable of ["--bg","--panel","--text","--muted","--accent","--warn","--ok","--danger"])
    assert.ok(css.includes("var("+variable+")"),variable);
  assert.match(css,/\.badge\.on/);
  assert.match(css,/\.badge\.off/);
  assert.match(css,/:focus-visible/);
});
test("touch accessibility and operator controls remain in stylesheet",()=>{
  assert.match(css,/min-height:\s*44px/);
  assert.match(css,/\.status-banner/);
  assert.match(css,/\.theme-ops-flat/);
});
test("component guide explicitly covers icon sizing and safe saved values",()=>{
  for(const phrase of ["16px","18px","44px","saved panel layout",
                       "PiServerStyleCustom:v0_3_5","Do not","STOP"])
    assert.ok(guide.includes(phrase),phrase);
});
