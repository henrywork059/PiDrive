'use strict';
const assert = require('node:assert/strict');
const { createSettingsFeedback, matchesSubset } = require('../pisd/web/static/js/settings_feedback.js');
let count = 0;
function test(name, fn) { fn(); count++; process.stdout.write('PASS ' + name + '\n'); }
test('starts Unsaved, not falsely Applied',()=>assert.equal(createSettingsFeedback().snapshot().phase,'Unsaved'));
test('user edit is Unsaved',()=>{const x=createSettingsFeedback();x.edit();assert.equal(x.snapshot().phase,'Unsaved');});
test('begin is Applying',()=>{const x=createSettingsFeedback();x.begin();assert.equal(x.snapshot().phase,'Applying');});
test('duplicate apply is blocked',()=>{const x=createSettingsFeedback();x.begin();assert.equal(x.begin(),null);});
test('confirmed readback becomes Applied',()=>{const x=createSettingsFeedback(),r=x.begin();x.complete(r,true,'confirmed');assert.equal(x.snapshot().phase,'Applied');});
test('rejected readback is Failed',()=>{const x=createSettingsFeedback(),r=x.begin();x.complete(r,false,'mismatch');assert.equal(x.snapshot().phase,'Failed');});
test('network failure supports retry',()=>{const x=createSettingsFeedback(),r=x.begin();x.fail(r,'offline');assert.equal(x.snapshot().retry,true);});
test('retry succeeds after failure',()=>{const x=createSettingsFeedback();x.fail(x.begin(),'fail');const t=x.begin();x.complete(t,true);assert.equal(x.snapshot().phase,'Applied');});
test('edits during flight do not become Applied',()=>{const x=createSettingsFeedback(),r=x.begin();x.edit();x.complete(r,true);assert.equal(x.snapshot().phase,'Unsaved');});
test('save without runtime apply does not claim Applied',()=>{const x=createSettingsFeedback(),r=x.begin();x.complete(r,true,'Saved, not applied',false);assert.equal(x.snapshot().phase,'Unsaved');});
test('nested readback matches requested keys, ignoring extras',()=>assert.equal(matchesSubset({camera:{fps:20}},{camera:{fps:20,backend:'picamera2'},motor:{}}),true));
test('numeric drift is tolerated only within small precision',()=>{assert.equal(matchesSubset({v:0.30000001},{v:0.3}),true);assert.equal(matchesSubset({v:0.7},{v:0.6}),false);});
test('missing key fails backend comparison',()=>assert.equal(matchesSubset({foo:{bar:1}},{foo:{}}),false));
test('wrong types fail backend comparison',()=>assert.equal(matchesSubset({enabled:true},{enabled:1}),false));
test('arrays compare in order',()=>{assert.equal(matchesSubset({a:[1,2]},{a:[1,2]}),true);assert.equal(matchesSubset({a:[1,2]},{a:[2,1]}),false);});
test('read-specific pending state blocks concurrent mutation',()=>{const x=createSettingsFeedback();const r=x.begin({phase:'Loading',detail:'Reading'});assert.equal(x.snapshot().phase,'Loading');assert.equal(x.snapshot().detail,'Reading');assert.equal(x.begin(),null);x.complete(r,true,'Loaded, not applied',false);assert.equal(x.snapshot().phase,'Unsaved');assert.equal(x.snapshot().busy,false);});
test('failed read releases lock and permits load retry',()=>{const x=createSettingsFeedback();x.fail(x.begin({phase:'Loading'}),'timed out');assert.equal(x.snapshot().phase,'Failed');assert.equal(x.snapshot().retry,true);assert.notEqual(x.begin({phase:'Loading'}),null);});
test('edit during read prevents old read from confirming draft',()=>{const x=createSettingsFeedback();const r=x.begin({phase:'Loading'});x.edit();assert.equal(x.complete(r,true,'Loaded',false),false);assert.equal(x.snapshot().phase,'Unsaved');assert.equal(x.snapshot().busy,false);});
console.log(count + '/18 deterministic settings feedback tests passed');

// Registered settings regression: production multi-context presentation synchronization.
require('./test_panel_presentation_sync.cjs');
