'use strict';
const assert = require('node:assert/strict');
const { projectReadiness } = require('../pisd/web/static/js/operating_readiness.js');
let count = 0;
function test(name, fn) { fn(); count++; process.stdout.write('PASS ' + name + '\n'); }
const make = () => ({
  camera: { running: true, frame_seq: 9 },
  ai_mode: { running: false, mode: 'idle', drive_output_enabled: false,
    model_id: 'steer.tflite', model_ready: true, manual_correction: {enabled: false, active: false} },
  motor: { hardware_enabled: true, last_intended_left: 0, last_intended_right: 0,
    last_command: {control_source:'stopped'} },
  safety: { latched: false, reason:'' }
});
test('offline never claims ready', () => assert.equal(projectReadiness(null).isVerified, false));
test('offline explicit failure never claims owner', () => assert.equal(projectReadiness(make(),{offline:true}).source.text,'Unconfirmed'));
test('backend rejected state never claims ready', () => assert.equal(projectReadiness({ok:false}).isVerified,false));
test('camera running with frame is ready', () => assert.equal(projectReadiness(make()).camera.tone,'good'));
test('camera stopped shows stop reason for AI', () => { const s=make();s.camera.running=false;assert.equal(projectReadiness(s).reason.text,'Start the camera for AI mode.'); });
test('camera starting without frames visible', () => {const s=make();s.camera.frame_seq=0;assert.equal(projectReadiness(s).camera.tone,'warning');});
test('selected model is not loaded model', () => {const s=make();s.ai_mode.model_ready=false;assert.equal(projectReadiness(s,{selectedModel:'other.tflite'}).model.text,'Selected only · other.tflite');});
test('ready backend model is named', () => assert.equal(projectReadiness(make()).model.text,'Ready · steer.tflite'));
test('different selected model does not claim it loaded', () => assert.equal(projectReadiness(make(),{selectedModel:'other.tflite'}).model.text.includes('other selected'),true));
test('no model displays missing', () => {const s=make();s.ai_mode.model_id='';s.ai_mode.model_ready=false;assert.equal(projectReadiness(s).model.text,'Not loaded');});
test('AI drive identifies motor owner', () => {const s=make();s.ai_mode.running=true;s.ai_mode.mode='drive';s.ai_mode.drive_output_enabled=true;assert.equal(projectReadiness(s,{confirmed:true}).source.text,'AI drive');});
test('active correction identifies combined owner', () => {const s=make();Object.assign(s.ai_mode,{running:true,mode:'drive',drive_output_enabled:true,manual_correction:{enabled:true,active:true}});assert.equal(projectReadiness(s).source.text,'AI + correction');});
test('enabled but inactive correction does not claim active', () => {const s=make();Object.assign(s.ai_mode,{running:true,mode:'drive',drive_output_enabled:true,manual_correction:{enabled:true,active:false}});assert.equal(projectReadiness(s).source.text,'AI drive');});
test('preview is never called motor owner', () => {const s=make();s.ai_mode.running=true;s.ai_mode.mode='preview';assert.equal(projectReadiness(s).source.text,'AI preview · no drive');});
test('manual source only when nonzero output intent', () => {const s=make();s.motor.last_intended_left=0.4;s.motor.last_command.control_source='manual';assert.equal(projectReadiness(s,{screen:'manual',confirmed:true}).source.text,'Manual input');});
test('assist source is distinct from model autonomous drive', () => {const s=make();s.motor.last_intended_right=0.2;s.motor.last_command.control_source='manual_assist';assert.equal(projectReadiness(s).source.text,'Manual + AI assist');});
test('unknown input not mislabeled manual', () => {const s=make();s.motor.last_intended_left=.3;s.motor.last_command.control_source='other';assert.equal(projectReadiness(s).source.text,'Other / unverified input');});
test('stopped manual input shows idle selected', () => {const s=make();s.motor.last_command.control_source='manual';assert.equal(projectReadiness(s,{screen:'manual'}).source.text,'Idle · Manual selected');});
test('manual mode can be selected without AI model', () => {const s=make();s.ai_mode.model_ready=false;assert.equal(projectReadiness(s,{screen:'manual'}).reason.text,'Check the single motor safety confirmation before driving.');});
test('manual camera off does not prevent manual confirmation', () => {const s=make();s.camera.running=false;assert.equal(projectReadiness(s,{screen:'manual',confirmed:true}).reason.text,'No active motor command.');});
test('unchecked checkbox is not authorization', () => assert.equal(projectReadiness(make(),{screen:'manual'}).motor.text,'Locked · confirmation unchecked'));
test('checkbox checked does not claim AI drive already running', () => assert.equal(projectReadiness(make(),{confirmed:true}).motor.text,'Confirmed · drive not started'));
test('AI drive flag is backend authority', () => {const s=make();s.ai_mode.running=true;s.ai_mode.mode='drive';s.ai_mode.drive_output_enabled=true;assert.equal(projectReadiness(s).motor.text,'AI drive authorized');});
test('simulation not mistaken for hardware', () => {const s=make();s.motor.hardware_enabled=false;assert.equal(projectReadiness(s,{confirmed:true}).motor.text,'Simulation · no physical output');});
test('safety latch overrides active AI', () => {const s=make();Object.assign(s.ai_mode,{running:true,mode:'drive',drive_output_enabled:true});s.safety.latched=true;s.safety.reason='Camera fault latch';assert.equal(projectReadiness(s).source.text,'Safety stopped');});
test('safety reason is preserved', () => {const s=make();s.safety.latched=true;s.safety.reason='Rearm required';assert.equal(projectReadiness(s).reason.text,'Rearm required');});
test('AI frame fault overrides missing safety object', () => {const s=make();delete s.safety;s.ai_mode.camera_frame_fault_latched=true;assert.equal(projectReadiness(s).motor.tone,'danger');});
test('AI preview explains why motor disabled', () => {const s=make();s.ai_mode.running=true;s.ai_mode.mode='preview';assert.equal(projectReadiness(s,{confirmed:true}).reason.text,'AI preview only; drive output is disabled.');});
test('manual output fault visible', () => {const s=make();s.motor.last_intended_left=.3;s.motor.last_command.control_source='manual';s.motor.last_error='GPIO failure';assert.equal(projectReadiness(s,{screen:'manual',confirmed:true}).reason.text,'Motor error: GPIO failure');});
test('idle selected panel is not conflated with active correction', () => assert.equal(projectReadiness(make(),{selectedPanel:'correction'}).source.text,'Idle · Correction selected'));
test('reason trims long backend error', () => {const s=make();s.safety.latched=true;s.safety.reason='x'.repeat(600);assert.equal(projectReadiness(s).reason.text.length,170);});
test('explicit stale camera warning for AI drive', () => {const s=make();Object.assign(s.ai_mode,{running:true,mode:'drive',drive_output_enabled:true,camera_frame_stale:true});assert.equal(projectReadiness(s).reason.text.includes('stale'),true);});
console.log(count + '/32 readiness tests passed');
