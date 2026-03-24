(() => {
  const api = window.CustomDriveGuiStyle;
  if (!api) return;

  const fieldMap = {
    fontScale: { cssVar: "--font-scale", unit: "%", type: "range", defaultValue: 80 },
    workspacePad: { cssVar: "--workspace-pad", unit: "px", type: "range", defaultValue: 10 },
    panelPad: { cssVar: "--panel-pad", unit: "px", type: "range", defaultValue: 12 },
    panelHeadPad: { cssVar: "--panel-head-pad-y", unit: "px", type: "range", defaultValue: 10 },
    cardGap: { cssVar: "--card-gap", unit: "px", type: "range", defaultValue: 10 },
    fieldGap: { cssVar: "--field-gap", unit: "px", type: "range", defaultValue: 10 },
    radius: { cssVar: "--radius", unit: "px", type: "range", defaultValue: 10 },
    bg: { cssVar: "--bg", type: "color", defaultValue: "#1b1d23" },
    panel: { cssVar: "--panel", type: "color", defaultValue: "#232630" },
    panelAlt: { cssVar: "--panel-alt", type: "color", defaultValue: "#2a2e39" },
    text: { cssVar: "--text", type: "color", defaultValue: "#f1f2f7" },
    muted: { cssVar: "--muted", type: "color", defaultValue: "#9ea5b5" },
    accent: { cssVar: "--accent", type: "color", defaultValue: "#f4a31e" },
    danger: { cssVar: "--danger", type: "color", defaultValue: "#ca655d" },
    ok: { cssVar: "--ok", type: "color", defaultValue: "#8d9d61" },
    line: { cssVar: "--line", type: "color", defaultValue: "#2c313d" },
    lineStrong: { cssVar: "--line-strong", type: "color", defaultValue: "#50586a" },
  };

  function message(text) {
    const element = document.getElementById("styleSettingsMessage");
    if (element) element.textContent = text;
  }

  function numericPart(value, fallback) {
    const match = String(value || "").match(/-?\d+(?:\.\d+)?/);
    return match ? Number(match[0]) : fallback;
  }

  function renderInputs() {
    const vars = api.getResolvedVars();
    Object.entries(fieldMap).forEach(([id, meta]) => {
      const input = document.getElementById(id);
      const valueEl = document.getElementById(`${id}Value`) || document.getElementById(`${id}Text`);
      if (!input) return;
      const raw = vars[meta.cssVar] ?? meta.defaultValue;
      if (meta.type === "range") {
        const value = numericPart(raw, meta.defaultValue);
        input.value = `${value}`;
        if (valueEl) valueEl.textContent = `${value}${meta.unit || ""}`;
      } else {
        input.value = String(raw).toLowerCase();
        if (valueEl) valueEl.textContent = String(raw).toLowerCase();
      }
    });
  }

  function collectOverrides() {
    const next = {};
    Object.entries(fieldMap).forEach(([id, meta]) => {
      const input = document.getElementById(id);
      if (!input) return;
      const value = meta.type === "range" ? `${input.value}${meta.unit || ""}` : String(input.value).toLowerCase();
      next[meta.cssVar] = value;
    });
    return next;
  }

  function preview() {
    api.saveCustomOverrides(collectOverrides());
    renderInputs();
  }

  document.getElementById("saveStyleBtn")?.addEventListener("click", () => {
    api.saveCustomOverrides(collectOverrides());
    message("Style saved to this browser for the new GUI control shell.");
  });

  document.getElementById("resetStyleBtn")?.addEventListener("click", () => {
    api.resetCustomOverrides();
    renderInputs();
    message("Style reset to the PiServer-like defaults.");
  });

  Object.entries(fieldMap).forEach(([id]) => {
    document.getElementById(id)?.addEventListener("input", preview);
  });

  renderInputs();
})();
