/* V17 shared shell. Reuse the original DOM and controller.
 * Navigation waits for the existing backend STOP acknowledgement.
 * No automatic arm, settings write, additional polling or new authority.
 */
(() => {
  "use strict";
  const mode = document.body.dataset.pisdV17;
  if (mode !== "manual" && mode !== "ai") return;
  const manual = mode === "manual";
  const byId = id => document.getElementById(id);
  const shell = byId(manual ? "manualDriveShell" : "aiModeShell");
  const panel = byId(manual ? "manualDriveCameraPanel" : "aiPreviewPanel");
  const frame = byId(manual ? "mdrvPreviewFrame" : "aiPreviewFrame");
  const image = frame?.querySelector("img");
  const header = document.querySelector(".mdrv-topbar");
  const reason = byId(manual ? "mdrvReadyReason" : "aiReadyReason")?.closest(".pisd-readiness-reason");
  if (!shell || !panel || !frame || !image || !header || !reason) return;

  // Move existing nodes before page-specific controllers bind. IDs, labels,
  // overlays, focusable controls and state readers remain the original nodes.
  shell.prepend(panel);
  panel.prepend(frame);
  const readiness = document.createElement("div");
  readiness.className = "v17-readiness";
  readiness.setAttribute("role", "status");
  readiness.setAttribute("aria-live", "polite");
  readiness.append(reason);
  panel.prepend(readiness);
  const classicToggle = byId("drivingCockpitToggle");
  if (classicToggle) classicToggle.hidden = true; // reversible via Classic layout
  const nav = byId("v17ModeNav");
  const arm = byId(manual ? "mdrvArm" : "aiEnableMotor");
  const feedback = document.createElement("span");
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  feedback.hidden = true;
  feedback.style.flexBasis = "100%";
  nav.append(feedback);
  const transition = window.PiSDV17TransitionFactory.create({
    fetchImpl: (...args) => window.fetch(...args),
    disarm: () => {
      if (arm) { arm.checked = false; arm.disabled = true; }
      document.body.dataset.pisdV17Transition = "locked";
    },
    status: (state, message) => {
      document.body.dataset.pisdV17Transition = state;
      nav.setAttribute("aria-busy", String(state === "pending"));
      feedback.hidden = false;
      feedback.textContent = message;
    },
    navigate: url => window.location.assign(url),
  });
  window.PiSDV17Transition = transition;
  for (const link of [...nav.querySelectorAll("a"), ...header.querySelectorAll("a.pisd-front-link")]) {
    link.addEventListener("click", event => {
      event.preventDefault();
      if (link.getAttribute("aria-current") === "page") return;
      void transition.switchTo(link.href);
    });
  }

  // The existing cockpit aspect observer continues to own decoded ratio.
  // Only the header measurement is new, so large text and narrow widths
  // do not push a nominally full-height camera underneath the sticky STOP.
  const measure = () => {
    document.body.style.setProperty("--v17-header-height", `${Math.ceil(header.getBoundingClientRect().height)}px`);
  };
  measure();
  const observer = new ResizeObserver(measure);
  observer.observe(header);
  window.addEventListener("pagehide", () => observer.disconnect());
  // BFCache restoration must reattach the presentation observer, not a
  // controller or a stream. Existing controllers own lifecycle/STOP.
  window.addEventListener("pageshow", event => {
    if (event.persisted) {
      observer.observe(header);
      measure();
    }
  });
  document.body.dataset.pisdV17Ready = "true";
})();
