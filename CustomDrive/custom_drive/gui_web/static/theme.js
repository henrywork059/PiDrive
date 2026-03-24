(() => {
  const themeClasses = ["theme-ops-flat"];
  const customStyleKey = "CustomDriveGuiStyle:v0_1_10";
  const baseStyleVars = {
    "--font-scale": "80%",
    "--font-scale-factor": "0.8",
    "--workspace-pad": "10px",
    "--panel-pad": "12px",
    "--panel-head-pad-y": "10px",
    "--panel-head-pad-x": "12px",
    "--control-radius": "12px",
    "--card-radius": "14px",
    "--card-gap": "10px",
    "--field-gap": "10px",
  };

  const themes = {
    opsFlat: {
      className: "theme-ops-flat",
      vars: {
        "--bg": "#1b1d23",
        "--panel": "#232630",
        "--panel-alt": "#2a2e39",
        "--line": "rgba(255, 176, 44, 0.18)",
        "--line-strong": "rgba(255, 176, 44, 0.34)",
        "--text": "#f1f2f7",
        "--muted": "#9ea5b5",
        "--accent": "#f4a31e",
        "--accent-rgb": "244, 163, 30",
        "--danger": "#ca655d",
        "--warn": "#f4a31e",
        "--ok": "#8d9d61",
        "--shadow": "none",
        "--gap": "4px",
        "--radius": "10px",
        "--card-gap": "10px",
        "--field-gap": "10px",
      },
    },
  };

  function withDerivedVars(vars = {}) {
    const next = { ...vars };
    const fontScale = String(next["--font-scale"] || "").match(/-?\d+(?:\.\d+)?/);
    if (fontScale) next["--font-scale-factor"] = String(Number(fontScale[0]) / 100);
    return next;
  }

  function loadCustomOverrides() {
    try {
      const raw = window.localStorage.getItem(customStyleKey);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  let currentTheme = "opsFlat";
  let customOverrides = withDerivedVars(loadCustomOverrides());

  function setVars(vars) {
    const root = document.documentElement;
    Object.entries(vars || {}).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function getResolvedVars(themeName = currentTheme) {
    const theme = themes[themeName] || themes.opsFlat;
    return { ...baseStyleVars, ...(theme.vars || {}), ...(customOverrides || {}) };
  }

  function applyTheme(name = "opsFlat") {
    const theme = themes[name] || themes.opsFlat;
    currentTheme = name in themes ? name : "opsFlat";
    setVars(baseStyleVars);
    setVars(theme.vars);
    setVars(withDerivedVars(customOverrides));
    document.documentElement.classList.remove(...themeClasses);
    if (theme.className) document.documentElement.classList.add(theme.className);
    return currentTheme;
  }

  function saveCustomOverrides(vars = {}) {
    customOverrides = withDerivedVars(vars);
    try {
      if (Object.keys(customOverrides).length) {
        window.localStorage.setItem(customStyleKey, JSON.stringify(customOverrides));
      } else {
        window.localStorage.removeItem(customStyleKey);
      }
    } catch {}
    applyTheme(currentTheme);
    return getResolvedVars();
  }

  window.CustomDriveGuiStyle = {
    themes,
    applyTheme,
    getCurrentTheme: () => currentTheme,
    getCustomOverrides: () => ({ ...(customOverrides || {}) }),
    getResolvedVars: () => getResolvedVars(),
    saveCustomOverrides,
    resetCustomOverrides: () => saveCustomOverrides({}),
  };

  applyTheme("opsFlat");
})();
