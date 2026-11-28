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
  // Source replacement may decode before the load callback is delivered.
  // Invalidate old geometry immediately, then align only the current source.
  let sourceRevision = 0;
  function sourceChanged() {
    if (!active) return;
    const revision = ++sourceRevision;
    frame.dataset.cameraGeometry = "waiting";
    if (typeof image.decode === "function") {
      image.decode().then(() => {
        if (active && revision === sourceRevision) align();
      }, () => {});
    }
    // Cached or streaming images may be ready without a decode promise.
    if (image.complete && image.naturalWidth && image.naturalHeight) align();
  }
  const sourceObserver = new MutationObserver(sourceChanged);
  image.addEventListener("load", align);
  image.addEventListener("error", () => {
    if (active) frame.dataset.cameraGeometry = "waiting";
  });
  button.addEventListener("click", () => {
    active = !active;
    button.setAttribute("aria-pressed", String(active));
    button.textContent = active ? "Exit camera cockpit" : "Camera cockpit";
    if (active) {
      frame.dataset.cameraCockpit = "on";
      observer.observe(frame);
      sourceObserver.observe(image, {attributes:true, attributeFilter:["src","srcset"]});
      align();
    } else {
      observer.disconnect();
      sourceObserver.disconnect();
      ++sourceRevision;
      delete frame.dataset.cameraCockpit;
      delete frame.dataset.cameraGeometry;
      for (const key of ["x", "y", "width", "height"]) frame.style.removeProperty("--camera-cockpit-" + key);
    }
  });
})();
