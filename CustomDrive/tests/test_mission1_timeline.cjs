'use strict';
const assert = require('node:assert/strict');
const { project } = require('../custom_drive/mission1_web/static/mission_timeline.js');
let count = 0;
function test(name, fn) { fn(); count++; process.stdout.write('PASS ' + name + '\n'); }
const make = () => ({mission_outcome:'running', mission_timeline:{
 schema_version:1, session_id:'run-1', outcome:'running',
 current_step:{id:'model', label:'Model loading', phase:'model_boot', state:'current'},
 last_completed_step:{id:'camera',label:'Camera startup',phase:'camera_boot',state:'completed'},
 last_failure:null,
 recent_steps:[{id:'route',label:'Route',phase:'start_route',state:'completed',cycle:0},
   {id:'camera',label:'Camera startup',phase:'camera_boot',state:'completed',cycle:0},
   {id:'model',label:'Model loading',phase:'model_boot',state:'current',cycle:0}],
 detail:'Loading selected model', arm_sequence:{state:'starting_position_loaded',note:'Pose settling'}
}});
test('without status does not invent progress', () => assert.equal(project(null).available,false));
test('old API does not infer completed stages', () => assert.equal(project({mission_state:'pickup_track'}).items.length,0));
test('missing timeline indicates wait', () => assert.equal(project({}).current,'Waiting for backend progress'));
test('render current backend model boot', () => assert.equal(project(make()).current,'Model loading'));
test('last completed from backend only', () => assert.equal(project(make()).lastCompleted,'Camera startup'));
test('history consists only of observed stages', () => assert.equal(project(make()).items.length,3));
test('transient camera boot is included', () => assert.equal(project(make()).items[1].label,'Camera startup'));
test('arm settle note visible', () => assert.equal(project(make()).arm,'Pose settling'));
test('server detail kept', () => assert.equal(project(make()).detail,'Loading selected model'));
test('session ID retained', () => assert.equal(project(make()).sessionId,'run-1'));
test('no failure shown as None', () => assert.equal(project(make()).failure,'None'));
test('failed current stage reported', () => {const s=make();s.mission_timeline.outcome='failed';s.mission_timeline.current_step.state='failed';assert.equal(project(s).current,'Failed during Model loading');});
test('failure stage reason retained', () => {const s=make();s.mission_timeline.last_failure={reason:'arm_unavailable',stage:'pickup_grip',message:'servo timeout'};assert.equal(project(s).failure,'arm_unavailable · pickup_grip');});
test('stopped stage is not marked complete', () => {const s=make();s.mission_timeline.outcome='stopped';s.mission_timeline.current_step.state='interrupted';assert.equal(project(s).current,'Stopped at Model loading');});
test('completed server run labeled Complete', () => {const s=make();s.mission_timeline.outcome='complete';assert.equal(project(s).current,'Complete');});
test('unknown state rows never shown as successful', () => {const s=make();s.mission_timeline.recent_steps.push({id:'fake',label:'Fake',state:'success'});assert.equal(project(s).items.length,3);});
test('cycle sequence preserved without inferred stages', () => {const s=make();s.mission_timeline.recent_steps=[{id:'release',label:'Release',state:'completed',cycle:1},{id:'pickup_search',label:'Search',state:'current',cycle:2}];assert.equal(project(s).items[1].cycle,2);});
test('long details are bounded', () => {const s=make();s.mission_timeline.detail='z'.repeat(1000);assert.equal(project(s).detail.length,220);});
test('recent stages capped at 12', () => {const s=make();s.mission_timeline.recent_steps=Array.from({length:30},(_,i)=>({id:'step'+i,label:'Step'+i,state:'completed'}));assert.equal(project(s).items.length,12);});
test('no implicit route search align release ladder', () => {const s=make();s.mission_timeline.recent_steps=[{id:'route',label:'Route',state:'completed'}];assert.equal(project(s).items.length,1);});
test('empty run has no completed milestone', () => {const s=make();s.mission_timeline.current_step=null;s.mission_timeline.last_completed_step=null;s.mission_timeline.recent_steps=[];assert.equal(project(s).lastCompleted,'None yet');});
test('failed stage text bounded', () => {const s=make();s.mission_timeline.last_failure={reason:'x'.repeat(800),stage:'y'.repeat(800)};assert.equal(project(s).failure.length<=445,true);});
console.log(count + '/22 Mission 1 timeline UI tests passed');
