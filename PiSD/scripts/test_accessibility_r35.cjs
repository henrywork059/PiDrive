'use strict';
/* R35: run with node PiSD/scripts/test_accessibility_r35.cjs */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/global_space_stop.js'), 'utf8');

function simulate(focusedTag, options = {}) {
  const body = {tagName:'BODY'};
  const root = {tagName:'HTML'};
  let focus = focusedTag === 'BODY' ? body : {
    tagName: focusedTag,
    type: options.type || '',
    isContentEditable: options.contentEditable || false,
    closest(selector) {
      if (options.ignore && selector.includes('data-space-stop-ignore')) return this;
      if (selector.includes('data-space-stop-ignore')) return null;
      if (options.roleTab && selector.includes('[role="tab"]')) return this;
      if (['BUTTON','A','INPUT'].includes(this.tagName) && selector.includes(this.tagName.toLowerCase())) return this;
      return null;
    }
  };
  let handler, prevented = false, dispatched = 0, posted = 0;
  const document = {
    body, documentElement:root, activeElement:focus,
    addEventListener(event, listener) { if(event === 'keydown') handler = listener; }
  };
  const window = {location:{pathname:'/manual-drive'},dispatchEvent(){dispatched++;}};
  const fakeFetch = () => {posted++;return Promise.resolve({ok:true});};
  const FakeCustomEvent = class {constructor(type, args){this.type=type;this.detail=args?.detail;}};
  const Clock = {now(){return 3000;}};
  new Function('document','window','fetch','CustomEvent','Date',source)(
    document,window,fakeFetch,FakeCustomEvent,Clock);
  const event = {
    key:' ',target:focus,repeat:false,
    preventDefault(){prevented=true;},
    stopImmediatePropagation(){this.stopped=true;}
  };
  handler(event);
  return {prevented,posted,dispatched,handler,window,document};
}
let n=0;
function test(name,fn){fn();n++;process.stdout.write('PASS '+name+'\n');}
test('body Space still sends STOP',()=>{const x=simulate('BODY');assert.equal(x.prevented,true);assert.equal(x.posted,1);});
test('focussed drive pad Space still sends STOP',()=>{const x=simulate('DIV');assert.equal(x.posted,1);assert.equal(x.prevented,true);});
test('focused button Space preserves native click',()=>{const x=simulate('BUTTON');assert.equal(x.posted,0);assert.equal(x.prevented,false);});
test('checkbox Space preserves native toggle',()=>{const x=simulate('INPUT',{type:'checkbox'});assert.equal(x.posted,0);assert.equal(x.prevented,false);});
test('text input Space does not STOP',()=>{const x=simulate('INPUT',{type:'text'});assert.equal(x.posted,0);});
test('focused select Space does not STOP',()=>{const x=simulate('SELECT');assert.equal(x.posted,0);});
test('focused textarea Space does not STOP',()=>{const x=simulate('TEXTAREA');assert.equal(x.posted,0);});
test('focused link Space does not STOP',()=>{const x=simulate('A');assert.equal(x.posted,0);});
test('accessible tab Space does not STOP',()=>{const x=simulate('DIV',{roleTab:true});assert.equal(x.posted,0);});
test('contenteditable does not STOP',()=>{const x=simulate('DIV',{contentEditable:true});assert.equal(x.posted,0);});
test('explicit ignore zone does not STOP',()=>{const x=simulate('DIV',{ignore:true});assert.equal(x.posted,0);});
const manual = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/manual_drive.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, '../pisd/web/templates/manual_drive.html'), 'utf8');
const start = manual.indexOf('  function keyboardControlBlocked() {');
const end = manual.indexOf('  function setKeyboardStatus(', start);
assert.ok(start >= 0 && end > start);
function blocked(active) {
  const body = {};
  const pad = {};
  const document = {body, documentElement: {}, activeElement: active === 'body' ? body : active === 'pad' ? pad : active};
  return new Function('document','pad','overlaySettingsPopup',manual.slice(start,end)+'\nreturn keyboardControlBlocked();')(document,pad,null);
}
test('manual log keyboard shortcut isolation preserves body and pad',()=>{
  assert.equal(blocked({closest: selector => selector.includes('data-space-stop-ignore')}),true);
  assert.equal(blocked('body'),false);
  assert.equal(blocked('pad'),false);
});
test('manual log disclosure and focus semantics',()=>{
  assert.match(html, /id="mdrvToggleLog"[^>]*aria-expanded="false"[^>]*aria-controls="manualDriveLogPanel"/);
  assert.match(html, /id="mdrvLog"[^>]*tabindex="0"[^>]*aria-label="Manual Drive action log"[^>]*data-space-stop-ignore="true"/);
  assert.ok(manual.includes("toggleLog.setAttribute('aria-expanded', String(Boolean(hidden)))"));
});
test('read-only log does not dispatch global Space STOP',()=>{
  const x=simulate('PRE',{ignore:true});
  assert.equal(x.posted,0);
  assert.equal(x.prevented,false);
});
const ai = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/ai_mode.js'), 'utf8');
const aiHtml = fs.readFileSync(path.join(__dirname, '../pisd/web/templates/ai_mode.html'), 'utf8');
const startAIKeyup = ai.indexOf("    document.addEventListener('keyup', (event) => {");
const endAIKeyup = ai.indexOf("    }, { passive: false });", startAIKeyup);
assert.ok(startAIKeyup >= 0 && endAIKeyup > startAIKeyup);
const keyupSource = ai.slice(startAIKeyup, endAIKeyup + "    }, { passive: false });".length);
function aiRelease(mode, blocked, held) {
  let handler, prevented = 0, loops = 0;
  const document = {addEventListener(type, fn) { assert.equal(type, 'keyup'); handler = fn; }};
  const script = new Function('document', 'shortcutBlocked', 'aiAssistPanelActive', 'manualDrivePanelActive', 'correctionPanelActive',
    'assistKeyboardLeftHeld', 'assistKeyboardRightHeld', 'manualDriveKeyboardLeftHeld', 'manualDriveKeyboardRightHeld',
    'correctionKeyboardLeftHeld', 'correctionKeyboardRightHeld', 'startAssistKeyboardLoop', 'startManualDriveKeyboardLoop',
    'startCorrectionKeyboardLoop', keyupSource);
  const loop = () => { loops++; };
  script(document, () => blocked, () => mode === 'assist', () => mode === 'manual', mode === 'correction',
    held, false, held, false, held, false, loop, loop, loop);
  handler({key:'ArrowLeft', preventDefault(){prevented++;}});
  return {prevented, loops};
}
test('AI native control keyup does not start steering release in any drive mode',()=>{
  for (const mode of ['assist','manual','correction']) {
    assert.deepEqual(aiRelease(mode,true,false),{prevented:0,loops:0});
    assert.deepEqual(aiRelease(mode,true,true),{prevented:1,loops:1});
    assert.deepEqual(aiRelease(mode,false,false),{prevented:1,loops:1});
  }
});
test('AI library controls named and actions initially locked',()=>{
  assert.match(aiHtml,/id="aiFileKind"[^>]*aria-label="Recording library type"/);
  assert.match(aiHtml,/id="aiFileSelect"[^>]*aria-label="Recording library folder"/);
  assert.match(aiHtml,/id="aiDownloadZip"[^>]*\bdisabled\b/);
  assert.match(aiHtml,/id="aiDeleteFolder"[^>]*\bdisabled\b/);
});
console.log(n+'/16 PiSD safety/input tests passed');
