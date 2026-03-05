# ui_model_panel.py

MODEL_PANEL = """<div class=\"panel panel-mode-select\">
    <div class=\"panel-title\">Mode Selection</div>

    
    <div class=\"panel-body\">
        <div class=\"model-select-row\">
        <label for=\"modeSelect\">Drive mode:</label>
        <select id=\"modeSelect\">
        <option value=\"manual\">Manual</option>
        <option value=\"auto_steer\">Auto steer</option>
        <option value=\"autopilot\">Self driving</option>
        </select>
    </div>

    <div id=\"modeInfo\">Current mode: <span id=\"currentModeText\">manual</span></div>

    <hr class=\"panel-separator\" />

    <div class=\"model-section-title\">TFLite model</div>

    <div class=\"model-upload-row\">
        <label for=\"modelFile\">Upload .tflite:</label>
        <input id=\"modelFile\" type=\"file\" accept=\".tflite\" />
        <button type=\"button\" class=\"btn-secondary\" onclick=\"uploadModel()\">Upload</button>
    </div>

    <div class=\"model-select-row\">
        <label for=\"modelSelect\">Available models:</label>
        <select id=\"modelSelect\">
            <option value=\"\">(none)</option>
        </select>
        <button type=\"button\" class=\"btn-secondary\" onclick=\"loadSelectedModel()\">Load</button>
    </div>

    <div id=\"modelStatus\">Current model: <span id=\"currentModelName\">none</span></div>
    <div id=\"modelMessage\" class=\"model-message\"></div>
    </div>
</div>
"""
