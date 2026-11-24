const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class El {
  constructor() { this.disabled=false; this.style={}; this.children=[]; this.events={}; }
  setAttribute() {}
  append(...items) { this.children.push(...items); }
  after(item) { this.panel=item; }
  addEventListener(name, fn) { this.events[name]=fn; }
  focus() {}
  remove() { this.removed=true; }
  click() { if (!this.disabled) this.events.click?.(); }
}
function fixture() {
  const ctx={document:{createElement:()=>new El()}};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/destructive_action.js'), 'utf8'),ctx);
  return {guard:ctx.PiDriveDestructive,button:new El(),stop:new El()};
}
test('confirmation names target, cancellation performs no action and STOP stays usable',async()=>{
  const {guard,button,stop}=fixture();
  let stopped=0; stop.addEventListener('click',()=>stopped++);
  const result=guard.confirm(button,'Delete only folder A? Cannot undo.');
  assert.match(button.panel.children[0].textContent,/folder A/);
  assert.equal(button.disabled,true);
  stop.click(); assert.equal(stopped,1);
  button.panel.children[2].click();
  assert.equal(await result,false);
  assert.equal(button.disabled,false);
  assert.equal(button.panel.removed,true);
});
test('confirmation and network work hold one guard until finally release',async()=>{
  const {guard,button}=fixture();
  const first=guard.confirm(button,'model A');
  assert.equal(await guard.confirm(button,'model B'),false);
  button.panel.children[1].click();
  assert.equal(await first,true);
  assert.equal(guard.busy(button),true);
  assert.equal(await guard.confirm(button,'model B'),false);
  guard.finish(button);
  assert.equal(button.disabled,false);
  const retry=guard.confirm(button,'model B'); button.panel.children[2].click();
  assert.equal(await retry,false);
});
