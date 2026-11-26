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
test('model actions retain their visible verbs and expose distinct accessible names',()=>{
  for (const [id,name] of Object.entries({uploadModelBtn:'Upload model',refreshModelsBtn:'Refresh models',loadModelBtn:'Load selected model',deleteModelBtn:'Delete selected model'})) {
    const tag=html.match(new RegExp('<button id="'+id+'"[^>]*>[^<]+</button>'))?.[0];
    assert.ok(tag && tag.includes('aria-label="'+name+'"'));
    assert.ok(name.startsWith(tag.split('>')[1].split('<')[0]));
  }
  for (const id of ['modelFile','modelManifestFile','modelSelect']) assert.ok(html.includes('for="'+id+'"'));
});
test('camera safe setup retains labels and apply/retry expose existing confirmation detail',()=>{
  for (const id of ['cameraResolutionPreset','cameraWidth','cameraHeight','cameraFps','cameraStreamQuality','cameraPreviewFps','cameraPreviewQuality','cameraFormat','cameraExposureUs','cameraAnalogueGain','cameraExposureComp','cameraBrightness','cameraContrast','cameraSaturation','cameraSharpness']) assert.ok(html.includes('for="'+id+'"'),id);
  for (const id of ['cameraAutoExposure','cameraAwb']) assert.match(html,new RegExp('<label[^>]*><input id="'+id+'" type="checkbox"[^>]*>[^<]+</label>'));
  for (const id of ['cameraApplyBtn','cameraRetryApply']) assert.match(html,new RegExp('<button id="'+id+'"[^>]*aria-describedby="cameraApplyDetail"'));
  assert.match(html,/<select id="cameraResolutionPreset" aria-label="Preset resolution">/);
  assert.match(html,/id="cameraApplyState"[^>]*role="status"[^>]*aria-live="polite"/);
});
test('global Escape closes only an open style dialog and respects handled cancellation',()=>{
  const start=app.indexOf('  window.addEventListener("keydown", (event) => {\n    const modal = document.getElementById("styleSettingsModal");');
  const end=app.indexOf('\n  });',start);
  assert.ok(start>=0 && end>start);
  let handler, closed=0, hidden=true, present=true;
  const fakeWindow={addEventListener(type,fn){assert.equal(type,'keydown');handler=fn;}};
  const fakeDocument={getElementById(id){assert.equal(id,'styleSettingsModal');return present?{classList:{contains(name){assert.equal(name,'hidden');return hidden;}}}:null;}};
  new Function('window','document','closeStyleSettings',app.slice(start,end+6))(fakeWindow,fakeDocument,()=>closed++);
  handler({key:'Escape',defaultPrevented:false});assert.equal(closed,0);
  hidden=false;
  handler({key:'Escape',defaultPrevented:true});assert.equal(closed,0);
  handler({key:'Tab',defaultPrevented:false});assert.equal(closed,0);
  handler({key:'Escape',defaultPrevented:false});assert.equal(closed,1);
  present=false;
  handler({key:'Escape',defaultPrevented:false});assert.equal(closed,1);
});
test('Training export actions expose distinct names and retain native folder selector',()=>{
  for(const [id,name] of Object.entries({refreshSessionsBtn:'Refresh saved folders',downloadSessionBtn:'Download selected folder',deleteSessionBtn:'Delete selected folder'})){
    const tag=html.match(new RegExp('<button id="'+id+'"[^>]*>[^<]+</button>'))?.[0];
    assert.ok(tag && tag.includes('aria-label="'+name+'"'));
    assert.ok(name.startsWith(tag.split('>')[1].split('<')[0]));
  }
  assert.match(html,/<label for="sessionSelect">Folder<\/label>\s*<select id="sessionSelect"/);
  assert.match(html,/id="sessionExportMessage"[^>]*role="status"[^>]*aria-live="polite"/);
});
test('Training native selector keys cannot drive; release remains unconditional',()=>{
  assert.deepEqual(simulateKeys('SELECT',null,[['keydown','ArrowDown'],['keydown','ArrowUp'],['keydown',' ']]),{calls:[],prevented:0});
  assert.deepEqual(simulateKeys('BUTTON',null,[['keydown',' '],['keydown','ArrowDown'],['keyup','ArrowDown']]),{calls:[['down',false]],prevented:0});
});
test('all eleven active style sliders retain native labels and visible readouts',()=>{
  const tags=html.match(/<input id="style[^"]+" type="range"[^>]*>/g)||[];
  assert.equal(tags.length,11);
  for(const tag of tags){
    const id=tag.match(/id="([^"]+)"/)[1];
    assert.ok(html.includes('for="'+id+'"'),id);
    assert.ok(html.includes('id="'+id+'Value"'),id);
    assert.match(tag,/data-style-unit="(?:%|px)"/);
  }
});
test('style slider accessible units and visible readout follow actual clamped native value',()=>{
  const start=app.indexOf('function updateStyleRangeReadout(');
  const end=app.indexOf('function previewStyleOverridesFromInputs(',start);
  assert.ok(start>=0 && end>start);
  const fields=[
    {id:'font',cssVar:'--font-scale',type:'range',unit:'%',fallback:80},
    {id:'gap',cssVar:'--gap',type:'range',unit:'px',fallback:4}
  ];
  function range(min,max,initial){
    let value=String(initial);
    return {min:String(min),attributes:{},get value(){return value;},
      set value(next){value=String(Math.max(min,Math.min(max,Number(next))));},
      setAttribute(name,v){this.attributes[name]=v;}};
  }
  const values={font:range(70,115,80),gap:range(0,20,4),fontValue:{},gapValue:{}};
  const resolved={'--font-scale':'130%','--gap':'-2px'};
  const api=new Function('document','styleSettingsFields','readResolvedStyleVars','parseNumericStyleValue',
    app.slice(start,end)+'\nreturn {syncStyleInputsFromCurrentVars,syncStyleValueLabelsFromInputs};')(
    {getElementById:id=>values[id]},fields,()=>resolved,(raw,fallback)=>parseFloat(raw)||fallback);
  api.syncStyleInputsFromCurrentVars();
  assert.equal(values.font.value,'115');
  assert.equal(values.fontValue.textContent,'115%');
  assert.equal(values.font.attributes['aria-valuetext'],'115 percent');
  assert.equal(values.gap.value,'0');
  assert.equal(values.gapValue.textContent,'0px');
  assert.equal(values.gap.attributes['aria-valuetext'],'0 pixels');
  values.font.value='91'; values.gap.value='7';
  api.syncStyleValueLabelsFromInputs();
  assert.equal(values.fontValue.textContent,'91%');
  assert.equal(values.font.attributes['aria-valuetext'],'91 percent');
  assert.equal(values.gapValue.textContent,'7px');
  assert.equal(values.gap.attributes['aria-valuetext'],'7 pixels');
  assert.deepEqual(resolved,{'--font-scale':'130%','--gap':'-2px'});
});
test('recording and snapshot expose stable action names with existing state descriptions',()=>{
  assert.match(html,/<button id="captureOnceBtn"[^>]*aria-label="Snapshot" aria-describedby="captureOnceHelp">/);
  assert.match(html,/<span id="captureOnceHelp" class="capture-once-subtitle">Save one frame<\/span>/);
  assert.match(html,/<button id="recordToggleBtn"[^>]*aria-pressed="false" aria-label="Record" aria-describedby="recordToggleHelp">/);
  assert.match(html,/<span id="recordToggleHelp" class="record-toggle-subtitle">Tap to start capture<\/span>/);
});
test('existing recording and snapshot setters retain names while updating descriptions and native disabled states',()=>{
  const state={};
  function button(name,help,prefix){
    const title={textContent:''},subtitle={textContent:''};
    return {title,subtitle,disabled:false,attributes:{'aria-label':name,'aria-describedby':help},
      classList:{toggle(){}},setAttribute(k,v){this.attributes[k]=v;},
      querySelector(selector){
        if(selector==='.'+prefix+'-title')return title;
        if(selector==='.'+prefix+'-subtitle')return subtitle;
        throw Error(selector);
      }};
  }
  const record=button('Record','recordToggleHelp','record-toggle');
  const snapshot=button('Snapshot','captureOnceHelp','capture-once');
  const els={recordToggleBtn:record,captureOnceBtn:snapshot};
  const recStart=app.indexOf('function setRecordToggle('),recEnd=app.indexOf('function setOverlayMode(',recStart);
  const capStart=app.indexOf('function setCapturePending('),capEnd=app.indexOf('function findSelectedSession(',capStart);
  assert.ok(recStart>=0 && recEnd>recStart && capStart>=0 && capEnd>capStart);
  const api=new Function('document','state',app.slice(recStart,recEnd)+app.slice(capStart,capEnd)+'\nreturn {setRecordToggle,setCapturePending};')({getElementById:id=>els[id]},state);
  for(const [on,pending,desc] of [[false,false,'Tap to start capture'],[true,true,'Starting capture…'],[true,false,'Tap to stop capture'],[false,true,'Stopping capture…'],[false,false,'Tap to start capture']]){
    api.setRecordToggle(on,pending);
    assert.equal(record.attributes['aria-label'],'Record');
    assert.equal(record.attributes['aria-describedby'],'recordToggleHelp');
    assert.equal(record.attributes['aria-pressed'],String(on));
    assert.equal(record.disabled,pending);
    assert.equal(record.subtitle.textContent,desc);
    assert.equal(record.title.textContent,on?'RECORD ON':'RECORD OFF');
    assert.equal(state.recordEnabled,on);
    assert.equal(state.recordPending,pending);
  }
  for(const [pending,desc] of [[false,'Save one frame'],[true,'Saving current frame'],[false,'Save one frame']]){
    api.setCapturePending(pending);
    assert.equal(snapshot.attributes['aria-label'],'Snapshot');
    assert.equal(snapshot.attributes['aria-describedby'],'captureOnceHelp');
    assert.equal(snapshot.disabled,pending);
    assert.equal(snapshot.subtitle.textContent,desc);
    assert.equal(snapshot.title.textContent,pending?'SNAPPING…':'SNAPSHOT');
    assert.equal(state.capturePending,pending);
  }
});
test('native model and manifest file inputs have distinct names and matching-sidecar guidance',()=>{
  assert.match(html,/<label for="modelFile">Upload model<\/label>\s*<input id="modelFile" type="file" accept="\.tflite" aria-label="Upload model file"/);
  assert.match(html,/<label for="modelManifestFile">Optional matching \.manifest\.json<\/label>\s*<input id="modelManifestFile" type="file" accept="\.json" aria-description="Use the model filename followed by \.manifest\.json\."/);
  assert.match(html,/<button id="uploadModelBtn" aria-label="Upload model" data-action-role="device">Upload<\/button>/);
  assert.match(html,/id="modelMessage"[^>]*role="status"[^>]*aria-live="polite"/);
});
test('native file controls leave drive keydown isolated and held-key release intact',()=>{
  assert.deepEqual(simulateKeys('INPUT',null,[['keydown',' '],['keydown','Enter'],['keydown','ArrowDown'],['keyup','ArrowDown']]),{calls:[['down',false]],prevented:0});
});
test('overlay has stable name and exposes current mode and note',()=>{
  assert.match(html,/<button id="overlayToggleBtn"[^>]*aria-pressed="false" aria-label="Overlay" aria-describedby="overlayModeValue overlayModeHelp">/);
  assert.match(html,/<strong id="overlayModeValue" class="metric-card-action-value">OFF<\/strong>/);
  assert.match(html,/<span id="overlayModeHelp" class="metric-card-action-note">Cycle view<\/span>/);
});
test('actual overlay setter preserves name and synchronizes pressed, mode and frame class',()=>{
  const value={textContent:''},note={textContent:''};
  function classes(){const values=new Set();return {values,remove(...names){names.forEach(n=>values.delete(n));},add(name){values.add(name);}};}
  const btn={attributes:{'aria-label':'Overlay','aria-describedby':'overlayModeValue overlayModeHelp'},classList:classes(),
    setAttribute(k,v){this.attributes[k]=v;},querySelector(s){if(s==='.metric-card-action-value')return value;if(s==='.metric-card-action-note')return note;throw Error(s);}};
  const frame={classList:classes()},state={};
  const start=app.indexOf('function setOverlayMode('),end=app.indexOf('function updateOverlayVisuals(',start);
  assert.ok(start>=0 && end>start);
  let updates=0;
  const setMode=new Function('document','state','updateOverlayVisuals',app.slice(start,end)+'\nreturn setOverlayMode;')(
    {getElementById:id=>({overlayToggleBtn:btn,frameOverlay:frame}[id])},state,()=>updates++);
  for(const [mode,normalized,label,description] of [[0,0,'OFF','Cycle view'],[1,1,'OVL 1','Throttle + steer'],[2,2,'OVL 2','Arc path'],[3,0,'OFF','Cycle view']]){
    setMode(mode);
    assert.equal(state.overlayMode,normalized);
    assert.equal(btn.attributes['aria-label'],'Overlay');
    assert.equal(btn.attributes['aria-describedby'],'overlayModeValue overlayModeHelp');
    assert.equal(btn.attributes['aria-pressed'],String(normalized!==0));
    assert.equal(value.textContent,label);
    assert.equal(note.textContent,description);
    assert.deepEqual([...btn.classList.values],[normalized===0?'off':'mode-'+normalized]);
    assert.deepEqual([...frame.classList.values],['overlay-mode-'+normalized]);
  }
  assert.equal(updates,4);
});
test('layout actions reference existing preview status',()=>{
  for(const id of ['previewLayoutBtn','cancelLayoutPreviewBtn','saveLayoutBtn','resetLayoutBtn']){
    assert.ok(html.includes('id="'+id+'" aria-describedby="layoutPreviewMessage"'));
  }
  assert.match(html,/id="layoutPreviewMessage" role="status"/);
});
test('actual layout preview and cancel transfer focus only from the disappearing active action',()=>{
  const state={page:'manual',layoutPreview:null},draft={page:'manual',candidate:{a:2},original:{a:1}},boxes=[];
  const doc={activeElement:null,getElementById:id=>els[id]};
  function control(){return {disabled:false,hidden:false,focus(){doc.activeElement=this;}};}
  const preview=control(),cancel=control(),reset=control(),nav=control(),feedback={};
  const els={previewLayoutBtn:preview,cancelLayoutPreviewBtn:cancel,resetLayoutBtn:reset,layoutPreviewMessage:feedback};
  const start=app.indexOf('function updateLayoutPreviewControls('),end=app.indexOf('function workspaceMetrics(',start);
  assert.ok(start>=0 && end>start);
  const api=new Function('document','state','window','currentLayout','applyLayoutBoxes','updateManualPadSizing',app.slice(start,end)+'\nreturn {previewWorkspaceLayout,cancelWorkspaceLayout};')(
    doc,state,{PiServerLayout:{preset:()=>({name:'Driving'}),begin:()=>draft},requestAnimationFrame(){}},()=>draft.original,b=>boxes.push(b),()=>{});
  preview.focus();api.previewWorkspaceLayout();
  assert.equal(doc.activeElement,cancel);assert.equal(preview.disabled,true);assert.equal(cancel.hidden,false);assert.equal(reset.disabled,true);
  assert.equal(feedback.textContent,'Unsaved preview — Save layout to keep, or Cancel.');
  api.cancelWorkspaceLayout();
  assert.equal(doc.activeElement,preview);assert.equal(preview.disabled,false);assert.equal(cancel.hidden,true);assert.equal(reset.disabled,false);
  assert.deepEqual(boxes,[draft.candidate,draft.original]);
  nav.focus();api.previewWorkspaceLayout();assert.equal(doc.activeElement,nav);
  api.cancelWorkspaceLayout();assert.equal(doc.activeElement,nav);
  preview.focus();state.dragging=true;api.previewWorkspaceLayout();assert.equal(state.layoutPreview,null);assert.equal(doc.activeElement,preview);
});
test('normalized tuning range readouts and contextual settings feedback',()=>{
  const fields = ['maxThrottle','steerMix','steerBias','steerCurve','throttleCurve','steerRate','throttleRate','leftMaxSpeed','rightMaxSpeed'];
  const names = ['Max throttle','Steering mix','Steering bias','Steer curve','Throttle curve','Steer rate','Throttle rate','Left max speed','Right max speed'];
  fields.forEach((id,i)=>assert.ok(html.includes('id="'+id+'" type="range" aria-label="'+names[i]+'" aria-valuetext='),id));
  assert.match(html,/id="runtimeMessage"[^>]*role="status"/);
  assert.match(html,/id="saveRuntimeBtn"[^>]*aria-describedby="runtimeMessage"/);
  assert.match(html,/id="motorApplyBtn"[^>]*aria-label="Apply motor settings"[^>]*aria-describedby="motorApplyDetail"/);
  assert.match(html,/id="motorRetryApply"[^>]*aria-label="Retry apply motor settings"[^>]*aria-describedby="motorApplyDetail"/);
  const values={maxThrottle:.43,steerMix:.5,steerBias:-.12,steerCurve:1.45,throttleCurve:1.55,steerRate:.07,throttleRate:.08};
  const elements={};
  fields.forEach(id=>{
    elements[id]={value:'63',attributes:{},setAttribute(k,v){this.attributes[k]=v;}};
    elements[id+'Value']={textContent:''};
  });
  const doc={getElementById:id=>elements[id]};
  const manual=app.slice(app.indexOf('function updateManualFeelUi()'),app.indexOf('function saveManualFeel()'));
  const range=app.slice(app.indexOf('function updateRangeText()'),app.indexOf('function updateToolbarBadge('));
  const update=new Function('document','state',manual+range+'\nreturn updateRangeText;')(doc,values);
  update();
  assert.deepEqual(fields.map(id=>elements[id].attributes['aria-valuetext']),['0.43','0.50','-0.12','1.45 times','1.55 times','0.07','0.08','0.63','0.63']);
  values.steerCurve=2;elements.leftMaxSpeed.value='50';update();
  assert.equal(elements.steerCurve.attributes['aria-valuetext'],'2.00 times');
  assert.equal(elements.leftMaxSpeed.attributes['aria-valuetext'],'0.50');
});
console.log(count+'/34 PiServer R35 accessibility tests passed');
test('R36 docking follows live viewport and cancels interrupted gestures without saving',()=>{
  const events={},headerEvents={},handleEvents={},mediaEvents={},saved=[],classes=new Set();
  const media={matches:true,addEventListener(k,f){mediaEvents[k]=f;}};
  const win={PiServerLayout:require("../piserver/web/static/layout_presets.js"),matchMedia(){return media;},addEventListener(k,f){events[k]=f;}};
  const header={addEventListener(k,f){headerEvents[k]=f;},setPointerCapture(){}};
  const handle={addEventListener(k,f){handleEvents[k]=f;},setPointerCapture(){}};
  let box={c:1,r:1,w:8,h:5};
  const panel={querySelector(s){return s==='.panel-head'?header:handle;},classList:{add(c){classes.add(c);},remove(c){classes.delete(c);}}};
  const state={page:'manual',dragging:null,resizing:null};
  const source=app.slice(app.indexOf('function setupDocking()'),app.indexOf('function renderActivePage('));
  const setup=new Function('window','state','panelEls','workspaceMetrics','readPanelBox','setPanelBox','saveLayout','currentLayout','clamp','gridCols','gridRows',source+'\nreturn setupDocking;')(
    win,state,()=>[panel],()=>({rect:{left:0,top:0},cellW:10,cellH:10}),()=>({...box}),(_p,b)=>{box={...b};},(p,b)=>saved.push([p,b]),()=>({...box}),(v,a,b)=>Math.max(a,Math.min(b,v)),45,25);
  setup();
  const start={clientX:0,clientY:0,pointerId:1,target:{closest(){return null;}},stopPropagation(){}};
  headerEvents.pointerdown(start);assert.equal(state.dragging,null);
  media.matches=false;mediaEvents.change();headerEvents.pointerdown(start);
  events.pointermove({clientX:30,clientY:10});assert.equal(box.c,4);
  media.matches=true;mediaEvents.change();assert.equal(box.c,1);assert.equal(state.dragging,null);assert.equal(saved.length,0);
  events.pointerup();assert.equal(saved.length,0);
  media.matches=false;mediaEvents.change();handleEvents.pointerdown(start);
  events.pointermove({clientX:20,clientY:10});assert.equal(box.w,10);
  events.pointercancel();assert.equal(box.w,8);assert.equal(state.resizing,null);assert.equal(saved.length,0);
  headerEvents.pointerdown(start);events.pointermove({clientX:20,clientY:0});events.pointerup();
  assert.equal(saved.length,1);assert.equal(box.c,3);assert.equal(classes.size,0);
});
console.log('1/1 PiServer R36 responsive docking contracts passed');
