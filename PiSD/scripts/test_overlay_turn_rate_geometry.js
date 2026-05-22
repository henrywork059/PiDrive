#!/usr/bin/env node
'use strict';

// Validate that the browser overlay geometry mirrors the PiSD 0.7.x turn-rate
// steering semantics without needing a real browser.
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
      turn_gain: 0.75,
      turn_curve: 1.5,
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

const lowGain = guide(1.0, { turn_gain: 0.35 });
const highGain = guide(1.0, { turn_gain: 1.35 });
line(highGain.end.x > lowGain.end.x && Math.abs(highGain.turnIntent) > Math.abs(lowGain.turnIntent), 'overlay.turn_rate.gain', 'higher Turn Gain produces a tighter visual curve', { lowEnd: lowGain.end, highEnd: highGain.end, lowTurn: lowGain.turnIntent, highTurn: highGain.turnIntent });

const gentleCurve = guide(0.45, { turn_curve: 2.4 });
const responsiveCurve = guide(0.45, { turn_curve: 0.7 });
line(responsiveCurve.end.x > gentleCurve.end.x && Math.abs(responsiveCurve.turnIntent) > Math.abs(gentleCurve.turnIntent), 'overlay.turn_rate.curve_exponent', 'lower Turn Curve exponent gives stronger small-input visual response', { gentleEnd: gentleCurve.end, responsiveEnd: responsiveCurve.end, gentleTurn: gentleCurve.turnIntent, responsiveTurn: responsiveCurve.turnIntent });

const arcade = guide(1.0, { steering_mode: 'arcade_mix', steer_mix: 1.0 });
line(arcade.steeringMode === 'arcade_mix' && Math.abs(arcade.turnIntent) > 0, 'overlay.arcade_mix.fallback', 'arcade_mix mode remains available for legacy visual comparison', { arcadeMode: arcade.steeringMode, arcadeEnd: arcade.end, arcadeTurn: arcade.turnIntent });

process.exit(ok ? 0 : 1);
