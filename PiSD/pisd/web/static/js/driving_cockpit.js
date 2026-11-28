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
  // This ratio is only a viewport-width hint; intrinsic image height owns
  // overlay alignment. Handle src replacement as well as a delayed load event.
  image.addEventListener("load", updateAspect);
  const sourceChanges = new MutationObserver(() => {
    updateAspect();
    if (typeof image.decode === "function") image.decode().then(updateAspect, () => {});
  });
  sourceChanges.observe(image, { attributes: true, attributeFilter: ["src", "srcset"] });
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
