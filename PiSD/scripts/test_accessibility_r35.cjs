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
const tester = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/testing_server.js'), 'utf8');
const testerHtml = fs.readFileSync(path.join(__dirname, '../pisd/web/templates/testing_server.html'), 'utf8');
const lab = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/panel_testing.js'), 'utf8');
test('testing endpoint shortcut is native draft-only button',()=>{
  const start = tester.indexOf('function buildManifest()');
  const end = tester.indexOf('function smokeLine(',start);
  const elements = {};
  const make = tag => ({tag, children:[], append(...children){this.children.push(...children);},appendChild(child){this.children.push(child);},setAttribute(key,value){this[key]=value;},addEventListener(type,fn){this[type]=fn;}});
  const document = {getElementById(id){return elements[id] ||= make(id);},createElement:make};
  new Function('document','manifest',tester.slice(start,end)+'\nreturn buildManifest();')(document,{endpoints:[{method:'GET',path:'/api/status',purpose:'Read status'}]});
  const chip = elements.manifestList.children[0];
  assert.equal(chip.tag,'button');
  assert.equal(chip.type,'button');
  assert.equal(chip['aria-label'],'Prepare GET /api/status');
  chip.click();
  assert.equal(elements.customMethod.value,'GET');
  assert.equal(elements.customPath.value,'/api/status');
});
test('testing read-only outputs preserve native Space and are named',()=>{
  for (const id of ['fpsTestPanel','smokeTestPanel','lastResponse','statusPanel']) {
    const tag = testerHtml.match(new RegExp('<pre id="'+id+'"[^>]*>'))[0];
    assert.match(tag,/tabindex="0"/);
    assert.match(tag,/aria-label="[^"]+"/);
    assert.match(tag,/data-space-stop-ignore="true"/);
  }
});
test('panel size state tracks actual selected preset',()=>{
  const start=lab.indexOf('  function setPanelSize('),end=lab.indexOf('  function applyPanelSizePreset(',start);
  assert.ok(start>=0 && end>start);
  const buttons=['compact','standard','large'].map(panelSize=>({dataset:{panelSize},setAttribute(k,v){this[k]=v;}}));
  const panel={dataset:{},querySelectorAll(){return buttons;}};
  const setSize=new Function(lab.slice(start,end)+'\nreturn setPanelSize;')();
  setSize(panel,'large');
  assert.deepEqual(buttons.map(b=>b['aria-pressed']),['false','false','true']);
  setSize(panel,'wide');
  assert.deepEqual(buttons.map(b=>b['aria-pressed']),['false','false','false']);
});
const presentation = fs.readFileSync(path.join(__dirname, '../pisd/web/templates/panel_presentation.html'), 'utf8');
const presentationJS = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/panel_presentation.js'), 'utf8');
test('presentation mock controls are inert and console is named and locally focusable',()=>{
  assert.match(presentation, /class="pp-button-row" inert><span[^>]*>Run<\/span><span[^>]*>STOP<\/span>/);
  assert.match(presentation, /<pre class="pp-console" inert>OK/);
  assert.match(presentation, /id="ppOutput"[^>]*tabindex="0"[^>]*aria-label="[^"]+"[^>]*data-space-stop-ignore="true"/);
  assert.match(presentation, /id="ppFeedback" role="status"/);
  assert.equal(simulate('PRE',{ignore:true}).posted,0);
});
test('presentation every range has a visible value and actual readout updates',()=>{
  const ids = [...presentation.matchAll(/id="(pp[^"]+)" type="range"/g)].map(m=>m[1]);
  assert.equal(ids.length,19);
  for (const id of ids) assert.ok(presentation.includes('data-range-value-for="'+id+'"'));
  const start=presentationJS.indexOf('  function updateRangeReadouts()'), end=presentationJS.indexOf('  function log(',start);
  assert.ok(start>=0 && end>start);
  const field={id:'ppFontScale',value:'1.2',dataset:{valueUnit:'times'},attributes:{},setAttribute(k,v){this.attributes[k]=v;}}, readout={};
  const form={querySelectorAll(){return [field];},querySelector(selector){assert.ok(selector.includes(field.id));return readout;}};
  const update=new Function('form',presentationJS.slice(start,end)+'\nreturn updateRangeReadouts;')(form);
  update();
  assert.equal(readout.textContent,'1.2');
  assert.equal(field.attributes['aria-valuetext'],'1.2 times');
  field.value='0.9';update();assert.equal(readout.textContent,'0.9');
  assert.equal(field.attributes['aria-valuetext'],'0.9 times');
});
test('presentation dependency and page scripts both defer in document order',()=>{
  const scripts = [...presentation.matchAll(/<script\s+src="[^"]*js\/(panel_presentation(?:_global)?\.js)[^"]*"([^>]*)>/g)];
  assert.deepEqual(scripts.map(m=>m[1]),['panel_presentation_global.js','panel_presentation.js']);
  for (const script of scripts) assert.match(script[2],/\bdefer\b/);
});
test('Panel Lab mock bodies are inert while actual header test actions remain available',()=>{
  const start=lab.indexOf('  function bodyHtml('), end=lab.indexOf('  function renderPanels(',start);
  assert.ok(start>=0 && end>start);
  const render=new Function('field','lastStatus','manifest',lab.slice(start,end)+'\nreturn renderedBody;')(()=>'',{}, {});
  for (const body of ['cameraPreview','cameraSettings','motorSettings','motorChannel','manualDrive','apiInspector','validation']) {
    const html=render({body});
    assert.match(html,/Visual example only/);
    assert.match(html,/<div class="pt-mock-body" inert>/);
    assert.doesNotMatch(html,/<button\b/);
  }
  assert.doesNotMatch(render({body:'status'}),/pt-mock-body/);
  assert.match(lab, /data-panel-test="\$\{escapeText\(panel.id\)\}"/);
  assert.match(lab, /runPanelApiTest\(testId\)/);
});
test('Panel Lab selected size has a non-color cue and motion preference',()=>{
  const css=fs.readFileSync(path.join(__dirname,'../pisd/web/static/css/panel_testing.css'),'utf8');
  assert.match(css,/\[aria-pressed="true"\]\s*\{\s*text-decoration: underline/);
  assert.match(css,/@media \(forced-colors: active\)/);
  assert.match(css,/\.pt-button:hover, \.pt-link-button:hover \{ transform: none !important; \}/);
});
const settingsHtml = fs.readFileSync(path.join(__dirname, '../pisd/web/templates/settings_tab.html'), 'utf8');
const settingsJs = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/settings_tab.js'), 'utf8');
test('Settings response console is named and locally focusable without intercepting native Space',()=>{
  assert.match(settingsHtml, /id="stActionLog"[^>]*tabindex="0"[^>]*aria-label="Settings last response"[^>]*data-space-stop-ignore="true"/);
  assert.equal(simulate('PRE',{ignore:true}).posted,0);
  assert.equal(simulate('BODY').posted,1);
  assert.equal(simulate('DIV').posted,1);
});
test('Settings ranges keep stable labels and visible readouts',()=>{
  const fields = [...settingsHtml.matchAll(/<label>([^<]+)<input[^>]*type="range"[^>]*><output aria-hidden="true"><\/output><\/label>/g)];
  assert.equal(fields.length,20);
  assert.ok(fields.every(m=>m[1].trim()));
  const start=settingsJs.indexOf('function updateOutputs('),end=settingsJs.indexOf('\n',start);
  assert.ok(start>=0 && end>start);
  const output={}, input={value:'0.43',dataset:{valueUnit:'of full speed'},attributes:{},setAttribute(k,v){this.attributes[k]=v;},parentElement:{querySelector(){return output;}}};
  const update=new Function(settingsJs.slice(start,end)+'\nreturn updateOutputs;')();
  const root={querySelectorAll(){return [input];}};
  update(root); assert.equal(output.textContent,'0.43');
  assert.equal(input.attributes['aria-valuetext'],'0.43 of full speed');
  input.value='0.52'; update(root); assert.equal(output.textContent,'0.52');
  assert.equal(input.attributes['aria-valuetext'],'0.52 of full speed');
  assert.match(settingsHtml,/id="stImportSettings"[^>]*aria-label="Import settings JSON file"/);
});
test('Settings Import stays native, focusable and isolated from global Space STOP',()=>{
  const css=fs.readFileSync(path.join(__dirname,'../pisd/web/static/css/settings_tab.css'),'utf8');
  assert.match(settingsHtml,/id="stImportSettings"[^>]*type="file"[^>]*aria-label="Import settings JSON file"/);
  const rule=css.match(/\.st-import input\s*\{([^}]+)\}/);
  assert.ok(rule);
  assert.doesNotMatch(rule[1],/display\s*:\s*none|visibility\s*:\s*hidden/);
  assert.match(rule[1],/opacity:\s*0/);
  assert.match(css,/\.st-import:focus-within\s*\{\s*outline:\s*3px solid/);
  assert.equal(simulate('INPUT',{type:'file'}).posted,0);
  assert.equal(simulate('BODY').posted,1);
});
test('all settings and presentation ranges specify units; actions reference existing feedback',()=>{
  for(const [source,count] of [[settingsHtml,20],[presentation,19]]){
    const fields=[...source.matchAll(/<input[^>]*type="range"[^>]*>/g)];
    assert.equal(fields.length,count);
    assert.ok(fields.every(m=>/data-value-unit="[^"]+"/.test(m[0])));
  }
  for(const id of ['stLoadSettings','stSaveSettings','stApplySettings','stRetryApply','stResetSettings'])
    assert.ok(settingsHtml.includes('id="'+id+'" aria-describedby="stApplyDetail"'));
  for(const id of ['ppApply','ppSave','ppReset'])
    assert.ok(presentation.includes('id="'+id+'" aria-describedby="ppFeedback"'));
});
console.log(n+'/28 PiSD safety/input tests passed');
