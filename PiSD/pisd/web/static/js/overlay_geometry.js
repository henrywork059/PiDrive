(() => {
  'use strict';

  const DEFAULT_OVERLAY = {
    path_length_scale: 1.0,
    curve_strength: 3.35,
    opacity: 0.94,
    path_width_scale: 0.34,
    sample_count: 56,
    wheelbase: 0.32,
    max_steer_rad: 0.62,
    curve_response: 1.05,
    curvature_scale: 0.52,
    curvature_limit: 2.25,
    entry_blend_start: 0.76,
    road_half_width: 0.41,
    base_y: 96,
    horizon_y: 31,
    camera_forward_offset: 0.26,
    near_clip: 0.19,
    perspective_scale: 64,
    perspective_depth: 0.92,
    turn_compression: 0.075,
    turn_width_taper: 0.08,
    // PiSD_0_8_1: visual-only manual scaling. Motor turn_gain was removed and
    // motor Turn Curve no longer drives the overlay; the user calibrates this
    // number against the real camera view and real car motion.
    turn_rate_visual_scale: 2.2,
  };

  const DEFAULT_MOTOR = {
    steering_mode: 'turn_rate',
    steer_mix: 1.0,
    turn_curve: 1.5,
    min_inside_speed: 0.0,
    allow_pivot_turn: false,
  };

  function clamp(value, min, max, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
  }

  function finiteOr(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function numberSetting(settings, defaults, key) {
    const fromSettings = settings && Object.prototype.hasOwnProperty.call(settings, key) ? Number(settings[key]) : NaN;
    if (Number.isFinite(fromSettings)) return fromSettings;
    const fromDefaults = defaults && Object.prototype.hasOwnProperty.call(defaults, key) ? Number(defaults[key]) : NaN;
    if (Number.isFinite(fromDefaults)) return fromDefaults;
    return DEFAULT_OVERLAY[key];
  }

  function motorNumberSetting(motorSettings, key, fallback) {
    const value = motorSettings && Object.prototype.hasOwnProperty.call(motorSettings, key) ? Number(motorSettings[key]) : NaN;
    return Number.isFinite(value) ? value : fallback;
  }

  function motorBoolSetting(motorSettings, key, fallback = false) {
    if (!motorSettings || !Object.prototype.hasOwnProperty.call(motorSettings, key)) return Boolean(fallback);
    const value = motorSettings[key];
    if (typeof value === 'string') return ['true', '1', 'yes', 'on'].includes(value.trim().toLowerCase());
    return Boolean(value);
  }

  function normaliseMotorSettings(motorSettings = {}) {
    const mode = String(motorSettings.steering_mode || DEFAULT_MOTOR.steering_mode).trim().toLowerCase();
    return {
      steering_mode: mode === 'arcade_mix' ? 'arcade_mix' : 'turn_rate',
      steer_mix: clamp(motorNumberSetting(motorSettings, 'steer_mix', DEFAULT_MOTOR.steer_mix), 0, 2, DEFAULT_MOTOR.steer_mix),
      turn_curve: clamp(motorNumberSetting(motorSettings, 'turn_curve', DEFAULT_MOTOR.turn_curve), 0.05, 8, DEFAULT_MOTOR.turn_curve),
      min_inside_speed: clamp(motorNumberSetting(motorSettings, 'min_inside_speed', DEFAULT_MOTOR.min_inside_speed), 0, 0.99, DEFAULT_MOTOR.min_inside_speed),
      allow_pivot_turn: motorBoolSetting(motorSettings, 'allow_pivot_turn', DEFAULT_MOTOR.allow_pivot_turn),
    };
  }

  function visualTurnIntent(steering, settings = {}, defaults = DEFAULT_OVERLAY) {
    const safeSteering = clamp(steering, -1, 1, 0);
    if (Math.abs(safeSteering) <= 1e-6) return 0;
    const response = clamp(numberSetting(settings, defaults, 'curve_response'), 0.2, 4.0, DEFAULT_OVERLAY.curve_response);
    const shaped = Math.pow(Math.abs(safeSteering), response);
    return clamp(Math.sign(safeSteering) * shaped, -1, 1, 0);
  }

  function appendCurveSegments(points, commands) {
    if (!Array.isArray(points) || points.length < 2) return;
    if (points.length < 3) {
      for (let i = 1; i < points.length; i += 1) {
        commands.push(`L ${points[i].x.toFixed(2)} ${points[i].y.toFixed(2)}`);
      }
      return;
    }
    for (let i = 1; i < points.length - 2; i += 1) {
      const current = points[i];
      const next = points[i + 1];
      const midX = (current.x + next.x) / 2;
      const midY = (current.y + next.y) / 2;
      commands.push(`Q ${current.x.toFixed(2)} ${current.y.toFixed(2)} ${midX.toFixed(2)} ${midY.toFixed(2)}`);
    }
    const penultimate = points[points.length - 2];
    const last = points[points.length - 1];
    commands.push(`Q ${penultimate.x.toFixed(2)} ${penultimate.y.toFixed(2)} ${last.x.toFixed(2)} ${last.y.toFixed(2)}`);
  }

  function pointsToPath(points) {
    if (!Array.isArray(points) || !points.length) return '';
    const commands = [`M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`];
    appendCurveSegments(points, commands);
    return commands.join(' ');
  }

  function pointsToPolygonPath(leftPoints, rightPoints) {
    if (!Array.isArray(leftPoints) || !leftPoints.length || !Array.isArray(rightPoints) || !rightPoints.length) return '';
    const commands = [`M ${leftPoints[0].x.toFixed(2)} ${leftPoints[0].y.toFixed(2)}`];
    appendCurveSegments(leftPoints, commands);
    commands.push(`L ${rightPoints[rightPoints.length - 1].x.toFixed(2)} ${rightPoints[rightPoints.length - 1].y.toFixed(2)}`);
    appendCurveSegments(rightPoints.slice().reverse(), commands);
    commands.push('Z');
    return commands.join(' ');
  }

  function roadBoundaryPath(points) {
    return pointsToPath(points);
  }

  function roadGuideGeometry(options = {}) {
    const safeThrottle = clamp(options.throttle, -1, 1, 0);
    const safeSteering = clamp(options.steering, -1, 1, 0);
    const settings = options.settings || {};
    const defaults = options.defaults || DEFAULT_OVERLAY;
    const speed = Math.max(0, safeThrottle);
    const movingReverse = safeThrottle < -0.02;

    // PiSD_0_6_4: shared road-guide geometry for Manual Drive and AI Mode.
    // The centre path is predicted on a ground plane with a kinematic bicycle
    // curvature command, integrated with a midpoint/RK-lite step. Road edges
    // are offset from local tangent normals before projection, and X/Y screen
    // projection now uses the same hyperbolic depth basis to avoid turn warping.
    // v0.6.4 intentionally flips the visual steering sign after hardware/UI
    // feedback showed the previous left/right overlay direction was inverted.
    const curveStrength = numberSetting(settings, defaults, 'curve_strength');
    const lengthScale = numberSetting(settings, defaults, 'path_length_scale');
    const widthCalibration = numberSetting(settings, defaults, 'path_width_scale');
    const visualWidthScale = Math.max(0.03, 0.82 + widthCalibration * 0.32);
    const baseY = clamp(numberSetting(settings, defaults, 'base_y'), -40, 160, DEFAULT_OVERLAY.base_y);
    const baseHorizonY = finiteOr(numberSetting(settings, defaults, 'horizon_y'), DEFAULT_OVERLAY.horizon_y);
    const lookahead = clamp(1.65 + speed * 0.85 + (lengthScale - 1.0) * 0.75, 0.25, 8.5, 1.65);
    const horizonY = clamp(baseHorizonY - speed * 8.5 - (lengthScale - 1.0) * 14, -60, 120, DEFAULT_OVERLAY.horizon_y);
    const samples = Math.round(clamp(numberSetting(settings, defaults, 'sample_count'), 8, 220, DEFAULT_OVERLAY.sample_count));
    const wheelbase = Math.max(0.01, Math.abs(numberSetting(settings, defaults, 'wheelbase')) || DEFAULT_OVERLAY.wheelbase);
    const maxSteerRad = Math.max(0.01, Math.abs(numberSetting(settings, defaults, 'max_steer_rad')) || DEFAULT_OVERLAY.max_steer_rad);
    const curveResponse = clamp(numberSetting(settings, defaults, 'curve_response'), 0.2, 4.0, DEFAULT_OVERLAY.curve_response);
    const curvatureScale = finiteOr(numberSetting(settings, defaults, 'curvature_scale'), DEFAULT_OVERLAY.curvature_scale);
    const curvatureLimit = Math.max(0.05, Math.abs(numberSetting(settings, defaults, 'curvature_limit')) || DEFAULT_OVERLAY.curvature_limit);
    const entryBlendStart = clamp(numberSetting(settings, defaults, 'entry_blend_start'), -1.5, 2.0, DEFAULT_OVERLAY.entry_blend_start);
    const roadHalfWidthBase = Math.max(0.01, Math.abs(numberSetting(settings, defaults, 'road_half_width')) || DEFAULT_OVERLAY.road_half_width);
    const cameraForwardOffset = Math.max(0.01, Math.abs(numberSetting(settings, defaults, 'camera_forward_offset')) || DEFAULT_OVERLAY.camera_forward_offset);
    const nearClip = Math.max(0.01, Math.abs(numberSetting(settings, defaults, 'near_clip')) || DEFAULT_OVERLAY.near_clip);
    const perspectiveBase = Math.max(1, Math.abs(numberSetting(settings, defaults, 'perspective_scale')) || DEFAULT_OVERLAY.perspective_scale);
    const perspectiveDepth = Math.max(0.05, Math.abs(numberSetting(settings, defaults, 'perspective_depth')) || DEFAULT_OVERLAY.perspective_depth);
    const turnCompressionSetting = finiteOr(numberSetting(settings, defaults, 'turn_compression'), DEFAULT_OVERLAY.turn_compression);
    const turnWidthTaperSetting = finiteOr(numberSetting(settings, defaults, 'turn_width_taper'), DEFAULT_OVERLAY.turn_width_taper);
    const turnRateVisualScale = Math.max(0.01, Math.abs(numberSetting(settings, defaults, 'turn_rate_visual_scale')) || DEFAULT_OVERLAY.turn_rate_visual_scale);
    const motor = normaliseMotorSettings(options.motorSettings || {});
    const visualSteering = safeSteering;
    const curvatureGain = (Number.isFinite(curveStrength) && DEFAULT_OVERLAY.curve_strength !== 0) ? curveStrength / DEFAULT_OVERLAY.curve_strength : 1.0;
    const turnIntent = visualTurnIntent(visualSteering, settings, defaults);
    let curvature = 0;
    if (motor.steering_mode === 'turn_rate') {
      // PiSD_0_8_1: overlay tuning is separated from motor tuning. Motor
      // turn_curve changes real wheel mixing only; the overlay path is calibrated
      // manually with visual-only curve_response and turn_rate_visual_scale.
      curvature = turnIntent * curvatureScale * curvatureGain * turnRateVisualScale;
    } else {
      // Fallback for the old arcade mixer. This preserves the previous visual
      // behaviour when users deliberately switch motor steering_mode back.
      const shapedSteering = Math.sign(visualSteering) * Math.pow(Math.abs(visualSteering), curveResponse);
      const steerRad = shapedSteering * maxSteerRad;
      curvature = (Math.tan(steerRad) / wheelbase) * curvatureScale * curvatureGain * motor.steer_mix;
    }
    curvature = clamp(curvature, -curvatureLimit, curvatureLimit, 0);
    const roadHalfWidth = roadHalfWidthBase * visualWidthScale;
    const centerWorld = [];
    let x = 0;
    let z = 0;
    let heading = 0;
    const ds = lookahead / (samples - 1);

    for (let i = 0; i < samples; i += 1) {
      centerWorld.push({ x, z, heading });
      if (i < samples - 1) {
        const progress = i / Math.max(1, samples - 1);
        const entryBlend = entryBlendStart + (1 - entryBlendStart) * Math.sin(progress * Math.PI * 0.5);
        const localCurvature = curvature * entryBlend;
        const midHeading = heading + localCurvature * ds * 0.5;
        x += Math.sin(midHeading) * ds;
        z += Math.cos(midHeading) * ds;
        heading += localCurvature * ds;
      }
    }

    function projectGroundPoint(point) {
      const projectedZ = Math.max(nearClip, point.z + cameraForwardOffset);
      const maxProjectedZ = lookahead + cameraForwardOffset;
      const perspectiveScale = perspectiveBase / (projectedZ + perspectiveDepth);
      const nearPerspectiveZ = Math.max(nearClip, cameraForwardOffset);
      const scaleAtNear = perspectiveBase / (nearPerspectiveZ + perspectiveDepth);
      const scaleAtFar = perspectiveBase / (maxProjectedZ + perspectiveDepth);
      const depthRatio = clamp((perspectiveScale - scaleAtFar) / Math.max(0.01, scaleAtNear - scaleAtFar), 0, 1, 0);
      const y = horizonY + (baseY - horizonY) * depthRatio;
      const t = clamp((projectedZ - nearClip) / Math.max(0.1, maxProjectedZ - nearClip), 0, 1, 0);
      const turnCompression = Math.abs(curvature) > 0.45 ? Math.max(0.05, 1 - turnCompressionSetting * t) : 1;
      const edgeGuard = 2.6 + t * 2.8;
      return {
        x: clamp(50 + point.x * perspectiveScale * turnCompression, edgeGuard, 100 - edgeGuard, 50),
        y: clamp(y, 7, 99, y),
      };
    }

    const leftPoints = [];
    const rightPoints = [];
    const centerPoints = [];
    for (let i = 0; i < centerWorld.length; i += 1) {
      const previous = centerWorld[Math.max(0, i - 2)];
      const next = centerWorld[Math.min(centerWorld.length - 1, i + 2)];
      const point = centerWorld[i];
      const dx = next.x - previous.x;
      const dz = next.z - previous.z;
      const tangentLength = Math.hypot(dx, dz) || 1;
      const normal = { x: -dz / tangentLength, z: dx / tangentLength };
      const progress = i / Math.max(1, centerWorld.length - 1);
      const turnWidthTaper = Math.max(0.05, 1 - Math.abs(curvature) * turnWidthTaperSetting * progress);
      const localHalfWidth = roadHalfWidth * turnWidthTaper;
      leftPoints.push(projectGroundPoint({ x: point.x + normal.x * localHalfWidth, z: point.z + normal.z * localHalfWidth }));
      rightPoints.push(projectGroundPoint({ x: point.x - normal.x * localHalfWidth, z: point.z - normal.z * localHalfWidth }));
      centerPoints.push(projectGroundPoint(point));
    }

    return {
      leftPath: roadBoundaryPath(leftPoints),
      rightPath: roadBoundaryPath(rightPoints),
      centerPath: pointsToPath(centerPoints),
      surfacePath: pointsToPolygonPath(leftPoints, rightPoints),
      start: centerPoints[0] || { x: 50, y: baseY },
      end: centerPoints[centerPoints.length - 1] || { x: 50, y: horizonY },
      curve: curvature * curveStrength,
      turnIntent,
      steeringMode: motor.steering_mode,
      overlayCurveResponse: curveResponse,
      motorTurnCurve: motor.turn_curve,
      movingReverse,
      speed,
    };
  }

  window.PiSDOverlayGeometry = {
    appendCurveSegments,
    pointsToPath,
    pointsToPolygonPath,
    roadBoundaryPath,
    roadGuideGeometry,
    normaliseMotorSettings,
    visualTurnIntent,
    turnRateIntent: visualTurnIntent,
  };
})();
