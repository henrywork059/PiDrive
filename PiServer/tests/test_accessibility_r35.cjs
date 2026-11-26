'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname,'../piserver/web');
const app = fs.readFileSync(path.join(root,'static/app.js'),'utf8');
const html = fs.readFileSync(path.join(root,'templates/index.html'),'utf8');
const css = fs.readFileSync(path.join(root,'static/styles.css'),'utf8');
let count=0;
function test(name,fn){fn();count++;process.stdout.write('PASS '+name+'\n');}
new Function(app);
const functions = app.slice(app.indexOf('function openStyleSettings() {'),app.indexOf('function resetStyleSettings() {'));
const modal = {attributes:{},classList:{classes:new Set(['hidden']),add(key){this.classes.add(key);},remove(key){this.classes.delete(key);}},setAttribute(k,v){this.attributes[k]=v;}};
const focus = {open:0,close:0};
const elements={styleSettingsModal:modal,openStyleSettingsBtn:{focus(){focus.open++;}},closeStyleSettingsBtn:{focus(){focus.close++;}}};
const document={getElementById(id){return elements[id];}};
const modalApi=new Function('document','syncStyleInputsFromCurrentVars','styleManager',functions+'\nreturn {openStyleSettings,closeStyleSettings};')(
  document,()=>{},()=>({applyTheme(){},getCurrentTheme(){return {};}}));
test('style modal opens and focuses keyboard close',()=>{modalApi.openStyleSettings();assert.equal(focus.close,1);assert.equal(modal.attributes['aria-hidden'],'false');});
test('style modal closes and restores opener focus',()=>{modalApi.closeStyleSettings();assert.equal(focus.open,1);assert.equal(modal.attributes['aria-hidden'],'true');});
test('modal has labelled accessible dialog',()=>assert.equal(html.includes('role="dialog" aria-modal="true" aria-labelledby="styleSettingsTitle" aria-describedby="styleSettingsHelp"'),true));
test('modal focus trap registered',()=>assert.equal(app.includes('event.shiftKey && document.activeElement === focusable[0]'),true));
test('keyboard page navigation is named',()=>assert.equal(html.includes('<nav class="page-tabs" id="pageTabs" aria-label="PiServer pages">'),true));
test('active page exposed as pressed',()=>assert.equal(app.includes('btn.setAttribute("aria-pressed"'),true));
test('manual drive pad keyboard focus and description',()=>assert.equal(html.includes('id="joystickArea" class="joystick-area" role="group" tabindex="0"')&&html.includes('id="joystickKeyboardHint"'),true));
test('motor keydown ignores native inputs and editable',()=>assert.equal(app.includes('event.target?.isContentEditable'),true));
test('focus visible for all controls',()=>assert.equal(css.includes('[tabindex="0"]):focus-visible')&&css.includes('outline: 3px solid #ffca65'),true));
test('reduced motion media query present',()=>assert.equal(css.includes('@media (prefers-reduced-motion: reduce)'),true));
test('no new control fetch endpoint introduced',()=>assert.equal(!functions.includes('fetch(')&&!functions.includes('sendControlUpdate('),true));
test('all eight visual preview controls are inert',()=>{
  const sample=html.slice(html.indexOf('<div class="style-preview-surface">'),html.indexOf('<div class="style-modal-foot">'));
  const controls=sample.match(/<(?:button|input)\b[^>]*>/g)||[];
  assert.equal(controls.length,8);
  assert.ok(controls.every(tag=>/\binert\b/.test(tag)));
  assert.ok(!html.match(/<(?:button|input)\s+inert\b[^>]*\bid="(?:saveStyleSettingsBtn|styleBg)"/));
});
test('dialog focus trap excludes inert sample controls',()=>assert.ok(app.includes('!el.closest("[inert]")')));
const keydownStart=app.indexOf('  window.addEventListener("keydown", (event) => {\n    if (!(pagePanels[state.page]');
const keyupStart=app.indexOf('  window.addEventListener("keyup", (event) => {',keydownStart);
const keyupEnd=app.indexOf('\n}',keyupStart);
assert.ok(keydownStart>=0 && keyupStart>keydownStart && keyupEnd>keyupStart);
const keyboardSource=app.slice(keydownStart,keyupEnd);
function simulateKeys(tag, blocked, keys) {
  const listeners={}, calls=[];
  const window={addEventListener(type,handler){listeners[type]=handler;}};
  new Function('window','pagePanels','state','setStepInput','setManualTargets',keyboardSource)(
    window,{manual:['manual']},{page:'manual'},(direction,pressed)=>calls.push([direction,pressed]),
    (steer,throttle)=>calls.push(['zero',steer,throttle]));
  const target={tagName:tag,closest(selector){return blocked && selector.includes(blocked)?this:null;}};
  let prevented=0;
  for(const [type,key] of keys) listeners[type]({target,key,preventDefault(){prevented++;}});
  return {calls,prevented};
}
test('native diagnostic disclosure Space is not a drive command',()=>{
  assert.deepEqual(simulateKeys('SUMMARY','summary',[['keydown',' ']]),{calls:[],prevented:0});
});
test('diagnostic log arrows and letters do not drive',()=>{
  assert.deepEqual(simulateKeys('PRE','[data-drive-keys-ignore]',[['keydown','ArrowDown'],['keydown','w']]),{calls:[],prevented:0});
});
test('body and drive-pad keys remain active; keyup after focus change releases',()=>{
  assert.deepEqual(simulateKeys('DIV',null,[['keydown','ArrowUp'],['keyup','ArrowUp'],['keydown',' ']]),
    {calls:[['up',true],['up',false],['zero',0,0]],prevented:2});
  assert.deepEqual(simulateKeys('SUMMARY','summary',[['keyup','ArrowUp']]),{calls:[['up',false]],prevented:0});
});
test('native disclosure focus and reduced motion styles',()=>{
  assert.equal((css.match(/:where\([^\n]*\bsummary\b[^\n]*\):focus-visible/g)||[]).length,2);
  assert.ok(css.includes('button:hover { transform: none !important; }'));
  assert.ok(html.includes('data-drive-keys-ignore aria-label="Recent operator event log"'));
});
test('active workspace has a non-color cue and decorative flash respects reduced motion',()=>{
  assert.match(css,/#pageTabs \.tab-btn\[aria-pressed="true"\]\s*\{\s*text-decoration: underline/);
  assert.match(css,/@media \(forced-colors: active\)[\s\S]*#pageTabs \.tab-btn\[aria-pressed="true"\] \{ border-color: Highlight !important; \}/);
  assert.match(css,/\.snapshot-flash\.active \{ animation: none !important; opacity: 0 !important; \}/);
});
console.log(count+'/18 PiServer R35 accessibility tests passed');
