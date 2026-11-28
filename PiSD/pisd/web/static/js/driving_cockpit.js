/* VD1N: presentation only; no storage, camera, AI, or motor APIs. */
(() => {
  "use strict";
  const toggle = document.getElementById("drivingCockpitToggle");
  const frame = document.getElementById(toggle?.getAttribute("aria-controls") || "");
  const image = frame?.querySelector("img");
  if (!toggle || !frame || !image) return;
  function updateAspect() {
    if (image.naturalWidth > 0 && image.naturalHeight > 0) {
      frame.style.setProperty("--cockpit-camera-ratio", String(image.naturalWidth / image.naturalHeight));
    }
  }
  image.addEventListener("load", updateAspect);
  toggle.addEventListener("click", () => {
    const enabled = toggle.getAttribute("aria-pressed") !== "true";
    updateAspect();
    if (enabled) document.body.dataset.pisdCockpit = "immersive";
    else delete document.body.dataset.pisdCockpit;
    toggle.setAttribute("aria-pressed", String(enabled));
    toggle.textContent = enabled ? "Exit cockpit view" : "Cockpit view";
  });
  updateAspect();
})();
