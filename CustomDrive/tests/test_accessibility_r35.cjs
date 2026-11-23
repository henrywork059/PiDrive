'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const web = path.join(__dirname, '../custom_drive/gui_web');
const gui = fs.readFileSync(path.join(web,'static/app.js'),'utf8');
const html = fs.readFileSync(path.join(web,'templates/index.html'),'utf8');
const css = fs.readFileSync(path.join(web,'static/styles.css'),'utf8');
const mission = fs.readFileSync(path.join(__dirname,'../custom_drive/mission1_web/static/app.js'),'utf8');
const missionHtml = fs.readFileSync(path.join(__dirname,'../custom_drive/mission1_web/templates/index.html'),'utf8');
const missionCss = fs.readFileSync(path.join(__dirname,'../custom_drive/mission1_web/static/styles.css'),'utf8');
let count=0;
function test(name,fn){fn();count++;process.stdout.write('PASS '+name+'\n');}
function makeEvent(key, extra={}) {return {key,repeat:false,preventDefault(){this.prevented=true;},...extra};}
const startIdx=gui.indexOf('function bindHoldAction(');
const endIdx=gui.indexOf('\nfunction bindClickAction(',startIdx);
assert.equal(startIdx>=0&&endIdx>startIdx,true);
const holdSource=gui.slice(startIdx,endIdx);
function setupHold(postJson) {
 const handlers={};
 const button={addEventListener(name,handler){(handlers[name] ||= []).push(handler);},
   releasePointerCapture(){},hasPointerCapture(){return false;},setPointerCapture(){}};
 const document={getElementById(){return button;},addEventListener(){}};
 const window={addEventListener(){}};
 const bind=new Function('document','window','postJson','pollStatus','setBanner',
    holdSource+'\nreturn bindHoldAction;')(document,window,postJson,async()=>{},()=>{});
 bind('armOpenBtn','start_open','stop_grip');
 return {button,emit(name,event=makeEvent(' ')){for(const f of handlers[name]||[])f(event);return event;}};
}
async function flush(){for(let i=0;i<12;i++)await Promise.resolve();}
(async()=>{
test('GUI parses',()=>new Function(gui));
test('Mission 1 script parses',()=>new Function(mission));
test('Keyboard Hold buttons have native names',()=>assert.equal(html.includes('id="servo0PlusBtn"')&&html.includes('id="armOpenBtn"'),true));
test('Dialogs are named and modal',()=>assert.equal((html.match(/role="dialog" aria-modal="true"/g)||[]).length,3));
test('Dialogs return focus and trap Tab',()=>assert.equal(gui.includes('modalFocusIds')&&gui.includes("event.key !== 'Tab'")&&gui.includes("event.key === 'Escape'"),true));
test('Manual pad has keyboard STOP alternative',()=>assert.equal(html.includes('id="manualStopBtn"')&&gui.includes("addEventListener('click', releaseDrivePad)"),true));
test('Pointer and keyboard arm controls share existing endpoint',()=>assert.equal(holdSource.includes("postJson('/api/arm/action'")&&!holdSource.includes('/api/arm/new'),true));
test('Reduced motion shared by GUI and Mission 1',()=>assert.equal(css.includes('prefers-reduced-motion: reduce')&&missionCss.includes('prefers-reduced-motion: reduce'),true));
test('Mission 1 dedicated live region is persistent',()=>assert.equal(missionHtml.includes('id="missionTimelineAnnouncement"')&&mission.includes("announcer.dataset.lastStage"),true));
let commands=[];
let demo=setupHold(async (_url,body)=>{commands.push(body.action);return {ok:true};});
demo.emit('keydown',makeEvent(' '));demo.emit('keyup',makeEvent(' '));await flush();
test('Space keydown starts then keyup stops',()=>assert.equal(commands.join(','),'start_open,stop_grip'));
commands=[];demo=setupHold(async (_url,body)=>{commands.push(body.action);return {ok:true};});
demo.emit('keydown',makeEvent('Enter'));demo.emit('keyup',makeEvent('Enter'));await flush();
test('Enter keydown starts then keyup stops',()=>assert.equal(commands.join(','),'start_open,stop_grip'));
commands=[];demo=setupHold(async (_url,body)=>{commands.push(body.action);return {ok:true};});
demo.emit('keydown',makeEvent(' ',{repeat:false}));demo.emit('keydown',makeEvent(' ',{repeat:true}));demo.emit('blur',makeEvent(' '));await flush();
test('Repeat key does not duplicate start and focus loss stops',()=>assert.equal(commands.join(','),'start_open,stop_grip'));
let releaseStart;commands=[];demo=setupHold((_url,body)=>{
 commands.push(body.action);
 return body.action==='start_open' ? new Promise(resolve=>releaseStart=resolve) : Promise.resolve({ok:true});
});
demo.emit('keydown',makeEvent(' '));
demo.emit('keyup',makeEvent(' '));
test('Early keyup does not overtake pending start',()=>assert.equal(commands.join(','),'start_open'));
releaseStart({ok:true});await flush();
test('Early keyup posts STOP after start settles',()=>assert.equal(commands.join(','),'start_open,stop_grip'));
console.log(count+'/14 CustomDrive R35 keyboard accessibility tests passed');
})().catch(err=>{console.error(err);process.exitCode=1;});
