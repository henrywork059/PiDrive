(() => {
  const themeClasses = ['theme-ops-flat'];
  const themes = {
    opsFlat: {
      className: 'theme-ops-flat',
      vars: {
        '--bg': '#101215',
        '--panel': '#171a1e',
        '--panel-alt': '#14171b',
        '--line': 'rgba(138, 144, 150, 0.18)',
        '--line-strong': 'rgba(176, 184, 190, 0.28)',
        '--text': '#e6e1d8',
        '--muted': '#a8a096',
        '--accent': '#8e7c67',
        '--danger': '#8f5c54',
        '--warn': '#8c7752',
        '--ok': '#667565',
        '--shadow': 'none',
        '--gap': '2px',
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
