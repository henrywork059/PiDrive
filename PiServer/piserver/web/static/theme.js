(() => {
  const themeClasses = ['theme-ops-flat'];
  const themes = {
    opsFlat: {
      className: 'theme-ops-flat',
      vars: {
        '--bg': '#0b1012',
        '--panel': '#12181b',
        '--panel-alt': '#182127',
        '--line': 'rgba(116, 137, 145, 0.28)',
        '--line-strong': 'rgba(152, 178, 186, 0.44)',
        '--text': '#edf3f6',
        '--muted': '#92a1a8',
        '--accent': '#6eaeb6',
        '--accent-rgb': '110, 174, 182',
        '--danger': '#b35f58',
        '--warn': '#b79e63',
        '--ok': '#5f8576',
        '--shadow': 'none',
        '--gap': '4px',
        '--radius': '10px'
      }
    }
  };

  let currentTheme = 'opsFlat';

  function setVars(vars) {
    const root = document.documentElement;
    Object.entries(vars || {}).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function applyTheme(name = 'opsFlat') {
    const theme = themes[name] || themes.opsFlat;
    currentTheme = name in themes ? name : 'opsFlat';
    setVars(theme.vars);
    document.documentElement.classList.remove(...themeClasses);
    if (theme.className) document.documentElement.classList.add(theme.className);
    return currentTheme;
  }

  window.PiServerStyle = {
    themes,
    applyTheme,
    getCurrentTheme: () => currentTheme,
  };

  applyTheme('opsFlat');
})();
