# ui_base.py

BASE_HTML = """<!doctype html>
<html>
<head>
    <title>Pi Car Web UI</title>
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
    <style>
        :root {
            --cols: 30;
            --rows: 20;

            /* Responsive UI sizing (auto-adjusts with device screen size)
               - vmin follows the smaller screen dimension (good for phones/tablets)
               - clamp keeps sizes usable on both tiny and huge displays
            */
            /* IMPORTANT: on small screens we want text to stay readable.
               Use a higher minimum and avoid mobile browsers shrinking text.
            */
            --font-base: clamp(14px, 1.80vmin, 18px);
            --pad-panel-y: clamp(8px, 1.40vmin, 14px);
            --pad-panel-x: clamp(10px, 1.60vmin, 16px);
            --gap: clamp(6px, 1.00vmin, 10px);
            --pad-layout: clamp(8px, 1.20vmin, 14px);
            --radius: clamp(10px, 1.20vmin, 14px);
        }

        /* On phones: bump the base font a bit more.
           (We keep clamp so landscape / bigger phones don't get cartoonish.)
        */
        @media (max-width: 520px) {
            :root {
                --font-base: clamp(16px, 4.2vw, 18px);
            }
        }

        body {
            margin: 0;
            padding: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
            font-size: var(--font-base);
            line-height: 1.25;
            background: radial-gradient(circle at top, #20242c 0, #090b10 45%, #050608 100%);
            color: #f4f4f4;
            overflow: hidden;
            -webkit-text-size-adjust: 100%;
            text-size-adjust: 100%;
        }

        .layout {
            display: grid;
            grid-template-columns: repeat(var(--cols), 1fr);
            /* IMPORTANT:
               Using plain `1fr` tracks makes the min-size `auto` (min-content),
               which can cause a row to expand when a panel's content is tall.
               `minmax(0, 1fr)` forces rows to stay fixed and lets the panel
               scroll internally instead.
            */
            grid-template-rows: repeat(var(--rows), minmax(0, 1fr));
            grid-auto-rows: minmax(0, 1fr);
            width: 100vw;
            height: 100vh;
            box-sizing: border-box;
            gap: var(--gap);
            padding: var(--pad-layout);
        }

        .panel {
            min-height: 0;
            background: rgba(12, 16, 24, 0.96);
            border-radius: var(--radius);
            border: 1px solid rgba(120, 130, 160, 0.6);
            padding: var(--pad-panel-y) var(--pad-panel-x);
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            overflow: hidden; /* prevent content from forcing grid track growth */
        }
        .panel-body {
            flex: 1;
            min-height: 0;
            overflow: auto;
            -webkit-overflow-scrolling: touch;
            padding-right: 2px;
        }

        /* Viewer panel: keep content centered inside the scrollable body */
        .panel-viewer .panel-body {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }


        .panel-title {
            font-size: 0.95rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
            color: #9fb4ff;
            border-bottom: 1px solid rgba(120, 130, 160, 0.5);
            padding-bottom: 0.30rem;
        }

        .panel-statusbar {
            grid-column: 1 / span 20;
            grid-row: 1 / span 1;
        }

        /* Status bar: prioritize showing the full text on small screens.
           - remove the title to save vertical space (status bar is only 1 grid row)
           - keep the content on one line and allow horizontal swipe/scroll
        */
        .panel-statusbar .panel-title { display: none; }
        .panel-statusbar { padding: calc(var(--pad-panel-y) * 0.65) var(--pad-panel-x); }
        .panel-statusbar .panel-body {
            overflow-x: auto;
            overflow-y: hidden;
            -webkit-overflow-scrolling: touch;
        }
        .panel-statusbar #statusBarMain { white-space: nowrap; }

        .panel-viewer {
            grid-column: 1 / span 20;
            grid-row: 2 / span 19;
        }

        .panel-mode-select {
            grid-column: 21 / span 10;
            grid-row: 1 / span 5;
        }

        .panel-manual {
            grid-column: 21 / span 10;
            grid-row: 6 / span 12;
        }

        /* Manual drag pad: make it smaller (about 50%) and centered */
        .panel-manual #joystickArea {
            width: 50%;
            min-width: 160px;
            max-width: 360px;
            margin: 0 auto;
        }

        .panel-record {
            grid-column: 21 / span 10;
            grid-row: 18 / span 3;
        }

        #video {
            width: 90%;
            height: auto;
            max-height: 100%;
            border-radius: calc(var(--radius) - 2px);
            border: 1px solid rgba(120, 130, 160, 0.7);
            object-fit: contain;
            background: #000;
        }

        #joystickArea {
            position: relative;
            width: 100%;
            aspect-ratio: 1 / 1;
            background-color: #111320;
            background-image:
                linear-gradient(to right, rgba(120,130,160,0.25) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(120,130,160,0.25) 1px, transparent 1px);
            background-size: 10% 10%;
            border: 1px solid rgba(120, 130, 160, 0.8);
            border-radius: var(--radius);
            touch-action: none;
            overflow: hidden;
        }

        #joystickArea::before,
        #joystickArea::after {
            content: "";
            position: absolute;
            pointer-events: none;
        }

        #joystickArea::before {
            left: 50%;
            top: 0;
            width: 2px;
            height: 100%;
            margin-left: -1px;
            background-color: rgba(180, 195, 245, 0.9);
        }

        #joystickArea::after {
            top: 50%;
            left: 0;
            height: 2px;
            width: 100%;
            margin-top: -1px;
            background-color: rgba(180, 195, 245, 0.9);
        }

        #joystickDot {
            position: absolute;
            width: clamp(16px, 2.2vmin, 22px);
            height: clamp(16px, 2.2vmin, 22px);
            border-radius: 50%;
            background: #f6f7ff;
            border: 2px solid #5e8cff;
            left: 50%;
            top: 100%;
            transform: translate(-50%, -100%);
            pointer-events: none;
        }

        #joystickInfo {
            margin-top: 0.55rem;
            font-size: 0.85rem;
            color: #c8cce8;
        }

        /* Speed slider removed in 0_2_10 (manual control uses drag pad only). */

        .status-block {
            font-size: 0.9rem;
            margin-top: 0.30rem;
            color: #d4dafc;
        }

        .btn-row {
            margin-top: 0.7rem;
            display: flex;
            gap: 8px;
        }

        select {
            width: 100%;
            margin-top: 0.55rem;
            padding: clamp(6px, 1.0vmin, 10px) clamp(10px, 1.6vmin, 14px);
            border-radius: calc(var(--radius) - 2px);
            border: 1px solid rgba(126, 138, 184, 0.9);
            background: #0f1220;
            color: #e7e9ff;
            font-size: 0.80rem;
        }

        button {
            /* Reduce overall button size ~20% (padding + font-size) */
            padding: clamp(6px, 1.0vmin, 11px) clamp(10px, 1.6vmin, 14px);
            margin: 0;
            border-radius: 999px;
            border: 1px solid rgba(126, 138, 184, 0.9);
            background: #141827;
            color: #e7e9ff;
            cursor: pointer;
            font-size: 0.70rem;
            font-weight: 500;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            transition: background 0.15s ease, border-color 0.15s ease;
        }
        button:hover {
            background: #1c2235;
            border-color: rgba(160, 172, 220, 0.95);
        }
        button:active {
            background: #0d101b;
        }

        .btn-stop {
            border-color: #ff6b6b;
            color: #ffecec;
            background: #7a1010;
        }
        .btn-stop:hover {
            background: #951919;
            border-color: #ff8b8b;
        }

        .btn-record-on {
            border-color: #ffb347;
            color: #fff1df;
            background: #8f5a13;
        }
        .btn-record-off {
            border-color: #6bb8ff;
            color: #e8f3ff;
            background: #10406b;
        }

        .btn-danger {
            border-color: #ff6b6b;
            color: #ffecec;
            background: #5b1010;
        }
        .btn-danger:hover {
            background: #7a1414;
            border-color: #ff8b8b;
        }

        .record-status-text {
            margin-top: 0.45rem;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .rec-dot {
            display: inline-block;
            width: clamp(9px, 1.3vmin, 12px);
            height: clamp(9px, 1.3vmin, 12px);
            border-radius: 50%;
            box-shadow: 0 0 4px rgba(0, 0, 0, 0.4);
        }

        .rec-dot-on {
            background-color: #ff4d4d;
            box-shadow: 0 0 8px rgba(255, 77, 77, 0.8);
        }

        .rec-dot-off {
            background-color: #4b4f63;
        }
    </style>
</head>
<body>
<div class=\"layout\">
    {status_panel}
    {viewer_panel}
    {model_panel}
    {manual_panel}
    {record_panel}
</div>

<script>
{script}
</script>
</body>
</html>
"""