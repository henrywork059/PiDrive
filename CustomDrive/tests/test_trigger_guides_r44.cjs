"use strict";
// R44: deterministic tests execute the Mission 1 browser's actual guide helpers.
// Run: node --test CustomDrive/tests/test_trigger_guides_r44.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.join(__dirname, "..");
const script = fs.readFileSync(path.join(root, "custom_drive", "mission1_web", "static", "app.js"), "utf8");
const html = fs.readFileSync(path.join(root, "custom_drive", "mission1_web", "templates", "index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "custom_drive", "mission1_web", "static", "styles.css"), "utf8");
const server = fs.readFileSync(path.join(root, "custom_drive", "mission1_session_app.py"), "utf8");

function functionsBetween(start, end) {
  const a = script.indexOf("function " + start + "(");
  const b = script.indexOf("function " + end + "(", a);
  assert.ok(a >= 0 && b > a, "actual guide function source exists: " + start);
  return script.slice(a, b);
}
function sandbox() {
  const elements = {
    armGripYRatio: { value: "30" },
    armDropoffYRatio: { value: "70" },
    triggerGuideReadout: { dataset: {} },
    triggerGripValue: { textContent: "" },
    triggerDropoffValue: { textContent: "" },
    triggerGuideState: { textContent: "" },
    viewerOverlay: {
      attrs: {}, innerHTML: "", group: null,
      setAttribute(name, value) { this.attrs[name] = value; },
      appendChild(group) { this.group = group; }
    }
  };
  const document = {
    getElementById(id) { return elements[id] ?? null; },
    createElementNS() {
      return {
        attrs: {}, dataset: {}, innerHTML: "",
        setAttribute(name, value) { this.attrs[name] = value; }
      };
    }
  };
  const context = vm.createContext({ document, triggerPreviewEdited: false, Math, Number, String });
  vm.runInContext(functionsBetween("clampTriggerPercent", "collectArmConfig"), context);
  vm.runInContext(functionsBetween("triggerGuideY", "renderViewer"), context);
  const status = {
    config: { arm: { grip_trigger_y_ratio: 0.30, dropoff_trigger_y_ratio: 0.70 },
              drive: { target_x_deadband_ratio: 0.05 } },
    frame: { width: 640, height: 360 },
    detections: []
  };
  return { context, status, elements };
}

test("ruler maps 100% top / 50% center / 0% bottom without reversal", () => {
  const { context } = sandbox();
  assert.equal(context.triggerGuideY(1, 360), 0);
  assert.equal(context.triggerGuideY(.5, 360), 180);
  assert.equal(context.triggerGuideY(0, 360), 360);
  assert.equal(context.triggerGuidePercent(0), 0);
  assert.equal(context.triggerGuidePercent(1), 100);
});
test("invalid and over-range input is safely clamped, valid 0 retained", () => {
  const { context } = sandbox();
  assert.equal(context.clampTriggerPercent("0"), 0);
  assert.equal(context.clampTriggerPercent("50"), 50);
  assert.equal(context.clampTriggerPercent("100"), 100);
  assert.equal(context.clampTriggerPercent("-20"), 0);
  assert.equal(context.clampTriggerPercent("140"), 100);
  assert.equal(context.clampTriggerPercent(""), 30);
  assert.equal(context.clampTriggerPercent("bad"), 30);
});
test("saved independent grip/drop-off percentages reflect actual server config", () => {
  const { context, status } = sandbox();
  const g = context.triggerGuideValues(status);
  assert.equal(g.grip, 30); assert.equal(g.dropoff, 70);
  assert.equal(g.savedGrip, 30); assert.equal(g.savedDropoff, 70);
  assert.equal(g.preview, false);
});
test("editing grip changes grip guide but not drop-off or server values", () => {
  const { context, status, elements } = sandbox();
  context.triggerPreviewEdited = true;
  elements.armGripYRatio.value = "80";
  const g = context.triggerGuideValues(status);
  assert.equal(g.grip, 80); assert.equal(g.dropoff, 70);
  assert.equal(g.savedGrip, 30); assert.equal(g.savedDropoff, 70);
  assert.equal(g.preview, true);
});
test("editing drop-off changes drop-off guide without touching grip", () => {
  const { context, status, elements } = sandbox();
  context.triggerPreviewEdited = true;
  elements.armDropoffYRatio.value = "0";
  const g = context.triggerGuideValues(status);
  assert.equal(g.grip, 30); assert.equal(g.dropoff, 0);
  assert.equal(g.savedGrip, 30); assert.equal(g.savedDropoff, 70);
  assert.equal(g.preview, true);
});
test("reverting unsaved input to the server values exits preview mode", () => {
  const { context, status } = sandbox();
  context.triggerPreviewEdited = true;
  const g = context.triggerGuideValues(status);
  assert.equal(g.preview, false);
});
test("overlay draws distinct lines and 100/50/0 scale at correct Y coordinates", () => {
  const { context, status, elements } = sandbox();
  context.renderOverlay(status);
  const svg = elements.viewerOverlay;
  assert.equal(svg.attrs.viewBox, "0 0 640 360");
  const markup = svg.group.innerHTML;
  assert.match(markup, /y1="252" x2="640" y2="252" class="overlay-trigger overlay-trigger-pickup"/);
  assert.match(markup, /y1="108" x2="640" y2="108" class="overlay-trigger overlay-trigger-dropoff"/);
  assert.match(markup, />Grip 30%</);
  assert.match(markup, />Drop-off 70%</);
  for (const label of ["100%", "50%", "0%"]) assert.ok(markup.includes(">" + label + "</text>"));
  assert.equal(svg.group.dataset.guideMode, "saved");
});
test("separate 0 and 100 percent preview markers render at bottom and top", () => {
  const { context, status, elements } = sandbox();
  context.triggerPreviewEdited = true;
  elements.armGripYRatio.value = "0";
  elements.armDropoffYRatio.value = "100";
  context.renderOverlay(status);
  const markup = elements.viewerOverlay.group.innerHTML;
  assert.match(markup, /y1="360" x2="640" y2="360" class="overlay-trigger overlay-trigger-pickup"/);
  assert.match(markup, /y1="0" x2="640" y2="0" class="overlay-trigger overlay-trigger-dropoff"/);
  assert.equal(elements.viewerOverlay.group.dataset.guideMode, "preview");
});
test("readout clearly differentiates draft from server saved values", () => {
  const { context, status, elements } = sandbox();
  context.renderTriggerReadout(context.triggerGuideValues(status));
  assert.equal(elements.triggerGuideReadout.dataset.mode, "saved");
  assert.match(elements.triggerGuideState.textContent, /Saved on server/);
  context.triggerPreviewEdited = true;
  elements.armGripYRatio.value = "88";
  context.renderTriggerReadout(context.triggerGuideValues(status));
  assert.equal(elements.triggerGripValue.textContent, "Grip 88%");
  assert.equal(elements.triggerDropoffValue.textContent, "Drop-off 70%");
  assert.equal(elements.triggerGuideReadout.dataset.mode, "preview");
  assert.match(elements.triggerGuideState.textContent, /server still uses Grip 30%, Drop-off 70%/);
});
test("only a confirmed save clears draft state; failed save cannot start mission", () => {
  assert.match(script, /if \(data\.ok !== true \|\| !data\.config \|\| !data\.status\)/);
  assert.match(script, /triggerPreviewEdited = false; \/\/ only a server-confirmed save/);
  assert.match(script, /currentStatus = data\.status;\s*renderStatus\(data\.status\)/);
  assert.match(script, /if \(!await saveConfig\(\)\) return;/);
  assert.match(script, /triggerPreviewEdited = true;\s*if \(currentStatus\) renderViewer\(currentStatus\)/);
});
test("backend zero trigger is not replaced by 30% fallback", () => {
  assert.doesNotMatch(server, /grip_trigger_y_ratio', 0\.3\) or 0\.3/);
  assert.doesNotMatch(server, /dropoff_trigger_y_ratio'.*or 0\.3\)\)/);
  assert.match(server, /'grip_trigger_y_ratio': round\(_normalize_ratio_percent_or_fraction/);
  assert.match(server, /'dropoff_trigger_y_ratio': round\(_normalize_ratio_percent_or_fraction/);
  assert.match(server, /APP_VERSION = '0_5_25'/);
});
test("marker/readout DOM and responsive layout remain present", () => {
  for (const id of ["viewerOverlay", "triggerGripValue", "triggerDropoffValue", "triggerGuideState"]) {
    assert.match(html, new RegExp('id="' + id + '"'));
  }
  assert.match(css, /\.overlay-frame-scale \.overlay-scale-label/);
  assert.match(css, /\.trigger-guide-readout\s*\{[^}]*flex-wrap: wrap/s);
  assert.match(css, /\.viewer-stage\s*\{[^}]*aspect-ratio: 16 \/ 9/s);
});
test("R43 mission polling and stop routes are untouched", () => {
  assert.match(script, /const STATUS_REFRESH_MS = 600;/);
  assert.match(script, /const FRAME_REFRESH_MS = 250;/);
  assert.match(script, /scheduleFrameRefresh\(\); \/\/ one request at a time/);
  assert.match(server, /def rearm_safety\(/);
  assert.match(server, /def _target_close_enough\(/);
});
