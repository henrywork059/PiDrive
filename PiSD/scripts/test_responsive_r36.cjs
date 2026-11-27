'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const css = fs.readFileSync(path.join(__dirname,'../pisd/web/static/css/pisd_layout_system.css'),'utf8');
const design = fs.readFileSync(path.join(__dirname,'../pisd/web/static/css/pisd_design_system.css'),'utf8');
const manual = fs.readFileSync(path.join(__dirname,'../pisd/web/templates/manual_drive.html'),'utf8');
const ai = fs.readFileSync(path.join(__dirname,'../pisd/web/templates/ai_mode.html'),'utf8');
const version = fs.readFileSync(path.join(__dirname,'../pisd/__init__.py'),'utf8');
let n=0;function test(name,fn){fn();n++;process.stdout.write('PASS '+name+'\n');}
test('manual pad remains square',()=>assert.equal(design.includes('body.manual-drive-page .mdrv-drag-pad')&&manual.includes('id="mdrvDragPad"'),true));
test('manual live preview remains aspect-aware',()=>assert.equal(css.includes('aspect-ratio: var(--pisd-ui-preview-aspect, 16 / 9)'),true));
test('small layout retains status preview drive stop files log ordering',()=>assert.equal(css.includes('"status"')&&css.includes('"preview"')&&css.includes('"files"')&&css.includes('"stop"'),true));
test('emergency stop remains in actual manual DOM',()=>assert.equal(manual.includes('id="mdrvStopBig"')&&manual.includes('id="mdrvStopTop"'),true));
test('R36 emergency labels wrap on 390 px',()=>assert.equal(css.includes('#mdrvStopTop, #mdrvStopBig, #mdrvStopPad')&&css.includes('overflow-wrap: anywhere !important'),true));
test('AI stop retained on narrow screens',()=>assert.equal(ai.includes('id="aiStopAll"')&&css.includes('#aiStopAll, #aiStop, #aiManualDriveStop, #aiAssistStop'),true));
test('manual preview aspect ratio has no forced square override',()=>assert.equal(!css.includes('.mdrv-preview-frame { aspect-ratio: 1 / 1'),true));
test('settings popup is constrained to dynamic viewport height',()=>assert.equal(css.includes('max-height: calc(100dvh - 16px) !important'),true));
test('settings action row wraps',()=>assert.equal(css.includes('.mdrv-overlay-settings-actions')&&css.includes('flex-wrap: wrap !important'),true));
test('R35 focus styles are kept',()=>assert.equal(design.includes('prefers-reduced-motion: reduce')&&design.includes('focus-visible'),true));
test('version is 0.11.17 or later in the patch line',()=>{const m=version.match(/__version__\s*=\s*"0\.11\.(\d+)"/);assert.ok(m&&Number(m[1])>=17);});
test('narrow STOP geometry does not inherit presentation transform',()=>{
  const rule=css.match(/:is\(#fpStopAll, #mdrvStopTop, #mdrvStopPad, #mdrvStopBig, #aiStopAll, #aiStop, #aiManualDriveStop, #aiAssistStop, #stStopAll\)\s*\{([^}]+)\}/);
  assert.ok(rule);
  assert.match(rule[1],/min-height:\s*44px !important/);
  assert.match(rule[1],/min-width:\s*44px !important/);
  assert.match(rule[1],/transform:\s*none !important/);
});
test('recording toolbar projects only confirmed backend count and session',()=>{
  require('../pisd/web/static/js/recording_reader.js');
  const describe=globalThis.PiSDRecordingReader.describeRecording;
  assert.deepEqual(describe({running:true,frame_count:7,active_session:{session_id:'sample',session_dir:'/private/path'}}),{countText:'7',sessionText:'Session: sample'});
  assert.deepEqual(describe({running:true}),{countText:'unknown',sessionText:'Session: unknown'});
  assert.deepEqual(describe({running:false,frame_count:0,active_session:{session_id:'old'}}),{countText:'0',sessionText:'No active session'});
  assert.deepEqual(describe({frame_count:NaN}),{countText:'unknown',sessionText:'Session: unknown'});
});
test('calibration reset is draft-only and scoped',()=>{
  const js=fs.readFileSync(path.join(__dirname,'../pisd/web/static/js/manual_drive.js'),'utf8');
  const start=js.indexOf('  function resetOverlayDraft(keys)');
  const end=js.indexOf('  function readOverlayCalibrationFromControls()',start);
  assert.ok(start>=0&&end>start);
  const a={value:'5'},b={value:'6'};
  const reset=new Function('OVERLAY_CONTROL_BINDINGS','DEFAULTS','setOverlaySettingsStatus',js.slice(start,end)+';return resetOverlayDraft;')(
    [['a',a],['b',b]],{overlay:{a:1,b:2}},()=>{});
  reset(['a']);assert.deepEqual([a.value,b.value],['1','6']);
  reset(['a','b']);assert.deepEqual([a.value,b.value],['1','2']);
  assert.match(js,/resetOverlayDraft\(OVERLAY_CONTROL_BINDINGS\.map\(\(\[key\]\) => key\)\)/);
});
test('missing recording status cannot clear a confirmed active session',()=>{
  const js=fs.readFileSync(path.join(__dirname,'../pisd/web/static/js/ai_mode.js'),'utf8');
  const start=js.indexOf('  function renderRecording(');
  const end=js.indexOf('  async function refreshStatus()',start);
  assert.ok(start>=0&&end>start);
  const session={},state={dataset:{}},button={classList:{toggle(){}}};
  const run=new Function('window','document','els','let recordingRunning=false,confirmedRecording=null;'+js.slice(start,end)+';return renderRecording;')(
    {PiSDRecordingReader:globalThis.PiSDRecordingReader},{getElementById:()=>session},{aiRecordingState:state,aiRecordToggle:button});
  run({running:true,frame_count:7,active_session:{session_id:'test'}});
  run({});assert.equal(state.textContent,'REC on · Frames: 7');assert.equal(session.textContent,'Session: test');
  run({running:false});assert.equal(state.textContent,'REC off');
});
test('shared recording projection retains confirmed state only for incomplete responses',()=>{
  const retain=globalThis.PiSDRecordingReader.retainConfirmedRecording;
  const active={running:true,frame_count:8,active_session:{session_id:'fixture'}};
  assert.deepEqual(retain(null,undefined),{});
  assert.equal(retain(active,{frame_count:0}),active);
  assert.equal(retain(active,{running:'false'}),active);
  assert.deepEqual(retain(active,{running:false}),{running:false});
});
test('recording gate rejects duplicate commands and stale or out-of-order reads',()=>{
  const gate=globalThis.PiSDRecordingReader.createRecordingGate();
  const before=gate.read();
  assert.equal(gate.begin(),true);
  assert.equal(gate.begin(),false);
  assert.equal(gate.accept(before),false);
  const during=gate.read();
  gate.finish();
  assert.equal(gate.accept(during),false);
  assert.equal(gate.accept(before),false);
  const older=gate.read(), newer=gate.read();
  assert.equal(gate.accept(newer),true);
  assert.equal(gate.accept(older),false);
  assert.equal(gate.begin(),true);
  gate.finish();
  assert.equal(gate.accept(newer),false);
  assert.equal(gate.accept(gate.read()),true);
});
console.log(n+'/17 PiSD R36 responsive checks passed');
