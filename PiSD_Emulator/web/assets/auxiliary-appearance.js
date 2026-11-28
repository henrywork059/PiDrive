// Match the existing outer workspace's temporary per-page appearance.
// No storage writes, runtime calls, iframe effects or new polling.
(() => {
  const select = document.getElementById("auxiliaryTheme");
  if (!select) return;
  select.addEventListener("change", () => {
    document.documentElement.dataset.emulatorTheme = select.value === "light" ? "light" : "dark";
    document.dispatchEvent(new Event("emulator-appearance-changed"));
  });
})();
