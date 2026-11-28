/* VD24: align existing overlays with the contained camera image inside the
   existing dock. No requests, storage, layout mutations or safety commands. */
(() => {
  "use strict";
  const button = document.getElementById("cameraCockpitToggle");
  const image = document.getElementById("videoFeed");
  const frame = image?.closest(".viewer-frame");
  if (!button || !frame) return;
  let active = false;
  function align() {
    if (!active) return;
    const w = frame.clientWidth, h = frame.clientHeight;
    const iw = image.naturalWidth, ih = image.naturalHeight;
    if (!w || !h || !iw || !ih) {
      frame.dataset.cameraGeometry = "waiting";
      return;
    }
    const scale = Math.min(w / iw, h / ih);
    const width = iw * scale, height = ih * scale;
    for (const [key, value] of Object.entries({
      x: (w - width) / 2, y: (h - height) / 2, width, height
    })) frame.style.setProperty("--camera-cockpit-" + key, value + "px");
    frame.dataset.cameraGeometry = "aligned";
  }
  const observer = new ResizeObserver(align);
  image.addEventListener("load", align);
  image.addEventListener("error", align);
  button.addEventListener("click", () => {
    active = !active;
    button.setAttribute("aria-pressed", String(active));
    button.textContent = active ? "Exit camera cockpit" : "Camera cockpit";
    if (active) {
      frame.dataset.cameraCockpit = "on";
      observer.observe(frame);
      align();
    } else {
      observer.disconnect();
      delete frame.dataset.cameraCockpit;
      delete frame.dataset.cameraGeometry;
      for (const key of ["x", "y", "width", "height"]) frame.style.removeProperty("--camera-cockpit-" + key);
    }
  });
})();
