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
console.log(n+'/11 PiSD Space safety/input tests passed');
