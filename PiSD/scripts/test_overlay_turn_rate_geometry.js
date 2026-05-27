#!/usr/bin/env node
'use strict';

// Validate that the browser overlay geometry keeps PiSD 0.8.2 visual overlay
// tuning separate from motor turn-rate settings without needing a real browser.
global.window = global;
require('../pisd/web/static/js/overlay_geometry.js');

const geom = global.PiSDOverlayGeometry;
let ok = true;

function line(condition, label, message, details = undefined) {
  const pass = Boolean(condition);
  ok = ok && pass;
  console.log(`${pass ? 'OK  ' : 'FAIL'} ${label} - ${message}`);
  if (details !== undefined) console.log(JSON.stringify(details, null, 2));
}

function guide(steering, motorSettings = {}, overlaySettings = {}) {
  return geom.roadGuideGeometry({
    throttle: 0.42,
    steering,
    settings: {
      path_length_scale: 1.0,
      curve_strength: 3.35,
      path_width_scale: 0.34,
      opacity: 0.94,
      turn_rate_visual_scale: 2.2,
      ...overlaySettings,
    },
    defaults: {},
    motorSettings: {
      steering_mode: 'turn_rate',
      ...motorSettings,
    },
  });
}

if (!geom || typeof geom.roadGuideGeometry !== 'function') {
  line(false, 'overlay.geometry.exports', 'shared overlay geometry helper is exported');
  process.exit(1);
}

const straight = guide(0.0);
const right = guide(1.0);
const left = guide(-1.0);
line(Math.abs(straight.turnIntent) < 1e-9 && straight.steeringMode === 'turn_rate', 'overlay.turn_rate.straight', 'straight command has zero turn intent', { end: straight.end, turnIntent: straight.turnIntent, steeringMode: straight.steeringMode });
line(right.turnIntent > 0 && right.end.x > straight.end.x, 'overlay.turn_rate.right_curve', 'positive steering bends the path right on screen', { straightEnd: straight.end, rightEnd: right.end, rightTurnIntent: right.turnIntent });
line(left.turnIntent < 0 && left.end.x < straight.end.x, 'overlay.turn_rate.left_curve', 'negative steering bends the path left on screen', { straightEnd: straight.end, leftEnd: left.end, leftTurnIntent: left.turnIntent });

const lowVisualScale = guide(1.0, {}, { turn_rate_visual_scale: 1.1 });
const highVisualScale = guide(1.0, {}, { turn_rate_visual_scale: 3.4 });
line(highVisualScale.end.x > lowVisualScale.end.x && Math.abs(highVisualScale.curve) > Math.abs(lowVisualScale.curve), 'overlay.visual_scale', 'higher visual scale produces a tighter overlay curve without motor turn_gain', { lowEnd: lowVisualScale.end, highEnd: highVisualScale.end, lowCurve: lowVisualScale.curve, highCurve: highVisualScale.curve });

const gentleCurve = guide(0.45, { turn_curve: 0.7 }, { curve_response: 2.4 });
const responsiveCurve = guide(0.45, { turn_curve: 2.4 }, { curve_response: 0.7 });
line(responsiveCurve.end.x > gentleCurve.end.x && Math.abs(responsiveCurve.turnIntent) > Math.abs(gentleCurve.turnIntent), 'overlay.visual_curve_response', 'overlay curve_response controls small-input visual response while legacy motor turn_curve is ignored', { gentleEnd: gentleCurve.end, responsiveEnd: responsiveCurve.end, gentleTurn: gentleCurve.turnIntent, responsiveTurn: responsiveCurve.turnIntent });

const arcade = guide(1.0, { steering_mode: 'arcade_mix', steer_mix: 1.0 });
line(arcade.steeringMode === 'arcade_mix' && Math.abs(arcade.turnIntent) > 0, 'overlay.arcade_mix.fallback', 'arcade_mix mode remains available for legacy visual comparison', { arcadeMode: arcade.steeringMode, arcadeEnd: arcade.end, arcadeTurn: arcade.turnIntent });

process.exit(ok ? 0 : 1);
