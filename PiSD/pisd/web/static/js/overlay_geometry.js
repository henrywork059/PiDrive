(() => {
  'use strict';

  const DEFAULT_OVERLAY = {
    path_length_scale: 1.0,
    curve_strength: 3.35,
    opacity: 0.94,
    path_width_scale: 0.34,
  };

  function clamp(value, min, max, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
  }

  function numberSetting(settings, defaults, key) {
    const fromSettings = settings && Object.prototype.hasOwnProperty.call(settings, key) ? Number(settings[key]) : NaN;
    if (Number.isFinite(fromSettings)) return fromSettings;
    const fromDefaults = defaults && Object.prototype.hasOwnProperty.call(defaults, key) ? Number(defaults[key]) : NaN;
    if (Number.isFinite(fromDefaults)) return fromDefaults;
    return DEFAULT_OVERLAY[key];
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

    // PiSD_0_6_3: shared road-guide geometry for Manual Drive and AI Mode.
    // The centre path is predicted on a ground plane with a kinematic bicycle
    // curvature command, integrated with a midpoint/RK-lite step.  Road edges
    // are offset from local tangent normals before projection, and X/Y screen
    // projection now uses the same hyperbolic depth basis to avoid turn warping.
    const curveStrength = numberSetting(settings, defaults, 'curve_strength');
    const lengthScale = numberSetting(settings, defaults, 'path_length_scale');
    const widthCalibration = numberSetting(settings, defaults, 'path_width_scale');
    const visualWidthScale = clamp(0.82 + widthCalibration * 0.32, 0.78, 1.36, 0.93);
    const baseY = 96;
    const lookahead = clamp(1.65 + speed * 0.85 + ((lengthScale || 1.0) - 1.0) * 0.75, 1.2, 3.1, 1.65);
    const horizonY = clamp(31 - speed * 8.5 - ((lengthScale || 1.0) - 1.0) * 14, 16, 44, 31);
    const samples = 56;
    const wheelbase = 0.32;
    const maxSteerRad = 0.62;
    const visualSteering = -safeSteering;
    const shapedSteering = Math.sign(visualSteering) * Math.pow(Math.abs(visualSteering), 1.05);
    const steerRad = shapedSteering * maxSteerRad;
    const curvatureGain = clamp((curveStrength || DEFAULT_OVERLAY.curve_strength) / DEFAULT_OVERLAY.curve_strength, 0.2, 1.65, 1.0);
    const curvatureLimit = clamp(1.15 + curvatureGain * 0.65, 1.15, 2.25, 1.65);
    const curvature = clamp((Math.tan(steerRad) / wheelbase) * 0.52 * curvatureGain, -curvatureLimit, curvatureLimit, 0);
    const roadHalfWidth = 0.41 * visualWidthScale;
    const cameraForwardOffset = 0.26;
    const nearClip = 0.19;
    const centerWorld = [];
    let x = 0;
    let z = 0;
    let heading = 0;
    const ds = lookahead / (samples - 1);

    for (let i = 0; i < samples; i += 1) {
      centerWorld.push({ x, z, heading });
      if (i < samples - 1) {
        const progress = i / Math.max(1, samples - 1);
        const entryBlend = 0.76 + 0.24 * Math.sin(progress * Math.PI * 0.5);
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
      const perspectiveScale = 64 / (projectedZ + 0.92);
      const nearPerspectiveZ = Math.max(nearClip, cameraForwardOffset);
      const scaleAtNear = 64 / (nearPerspectiveZ + 0.92);
      const scaleAtFar = 64 / (maxProjectedZ + 0.92);
      const depthRatio = clamp((perspectiveScale - scaleAtFar) / Math.max(0.01, scaleAtNear - scaleAtFar), 0, 1, 0);
      const y = horizonY + (baseY - horizonY) * depthRatio;
      const t = clamp((projectedZ - nearClip) / Math.max(0.1, maxProjectedZ - nearClip), 0, 1, 0);
      const turnCompression = Math.abs(curvature) > 0.45 ? 1 - 0.075 * t : 1;
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
      const turnWidthTaper = 1 - Math.min(0.18, Math.abs(curvature) * 0.08 * progress);
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
  };
})();
