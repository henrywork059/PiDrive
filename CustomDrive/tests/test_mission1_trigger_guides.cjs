'use strict';

// Run from CustomDrive/: node tests/test_mission1_trigger_guides.cjs
// Exercises the real browser overlay functions with fake SVG elements.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const project = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(project, 'custom_drive', 'mission1_web', 'static', 'app.js'), 'utf8');
const first = source.indexOf('function triggerGuideY(');
const last = source.indexOf('function renderViewer(');
assert.ok(first >= 0 && last > first, 'overlay functions must exist');

const children = [];
const svg = {
  innerHTML: '',
  attrs: {},
  setAttribute(name, value) { this.attrs[name] = value; },
  appendChild(element) { children.push(element); },
};
const document = {
  getElementById(name) {
    assert.equal(name, 'viewerOverlay');
    return svg;
  },
  createElementNS(_ns, tag) {
    assert.equal(tag, 'g');
    return { innerHTML: '', attrs: {}, setAttribute(name, value) { this.attrs[name] = value; } };
  },
};
const context = vm.createContext({ document, Number, Math });
vm.runInContext(source.slice(first, last), context);

assert.equal(context.triggerGuideY(1, 360), 0, '100% must draw at the top');
assert.equal(context.triggerGuideY(0.5, 360), 180, '50% must draw in the middle');
assert.equal(context.triggerGuideY(0, 360), 360, '0% must draw at the bottom');
assert.equal(context.triggerGuideY(1.3, 360), 0, 'upper bound must be clamped');
assert.equal(context.triggerGuideY(-0.4, 360), 360, 'lower bound must be clamped');
assert.equal(context.triggerGuideY(NaN, 360), 252, 'invalid ratio must use documented default');

context.renderOverlay({
  frame: { width: 640, height: 360 },
  config: { drive: { target_x_deadband_ratio: 0.05 }, arm: { grip_trigger_y_ratio: 0.3, dropoff_trigger_y_ratio: 0.7 } },
  detections: [],
});
assert.equal(svg.attrs.viewBox, '0 0 640 360');
assert.equal(children.length, 1);
const markup = children[0].innerHTML;
assert.match(markup, /y1="252" x2="640" y2="252" class="overlay-trigger overlay-trigger-pickup"/);
assert.match(markup, /y1="108" x2="640" y2="108" class="overlay-trigger overlay-trigger-dropoff"/);
assert.match(markup, /Grip 30%/);
assert.match(markup, /Drop-off 70%/);

// Independent labels must remain readable even when both lines coincide.
children.length = 0;
context.renderOverlay({ frame: { width: 320, height: 180 }, config: { arm: { grip_trigger_y_ratio: 0.3, dropoff_trigger_y_ratio: 0.3 } }, detections: [] });
assert.match(children[0].innerHTML, /x="6"[^>]*>Grip 30%/);
assert.match(children[0].innerHTML, /x="314"[^>]*text-anchor="end"[^>]*>Drop-off 30%/);

children.length = 0;
context.renderOverlay({
  frame: { width: 320, height: 180 }, config: {},
  detections: [{ is_target_class: true, center: { x_raw: 120, y_raw: 80 } }],
});
assert.equal(children.length, 2, 'existing target dot overlay remains');
assert.match(children[1].innerHTML, /cx="120" cy="80"/);

console.log('Mission 1 trigger guide tests passed.');
