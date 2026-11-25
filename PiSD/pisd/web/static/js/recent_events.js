/* R49 local sanitized events: GET-only, expanded-on-demand, no telemetry. */
(() => {
  "use strict";
  const panel = document.querySelector("[data-recent-events-root]");
  if (!panel) return;
  const refresh = panel.querySelector("[data-recent-refresh]");
  const copy = panel.querySelector("[data-recent-copy]");
  const output = panel.querySelector("[data-recent-output]");
  const message = panel.querySelector("[data-recent-status]");
  if (!refresh || !copy || !output || !message) return;
  let loading = false;

  async function loadEvents() {
    if (loading) return;
    loading = true;
    refresh.disabled = true;
    message.textContent = "Reading local sanitized events…";
    try {
      const controller = new AbortController();
      const deadline = setTimeout(() => controller.abort(), 3500);
      let data;
      try { const response = await fetch("/api/recent-events", {
        method: "GET", cache: "no-store", credentials: "same-origin", signal: controller.signal,
      });
      if (!response.ok) throw new Error("Event request unavailable");
      data = await response.json();
      } finally { clearTimeout(deadline); }
      if (data?.ok !== true || !Array.isArray(data.events)) {
        throw new Error("Invalid event data");
      }
      const events = data.events.slice(-80);
      // Never render arbitrary backend HTML. Data supplied by the server
      // consists only of static labels, timestamps, and outcomes.
      output.textContent = events.map((event) => {
        const at = String(event?.timestamp_utc || "");
        const label = String(event?.title || "Operator action");
        const outcome = String(event?.outcome || "observed");
        return at + " · " + label + " · " + outcome;
      }).join("\n") || "No recent operator events yet.";
      message.textContent = events.length +
        " sanitized events · oldest entries expire automatically.";
    } catch (_error) {
      message.textContent = "Events unavailable. Check server connection, then Refresh.";
      output.textContent = "Recent events unavailable.";
    } finally {
      loading = false;
      refresh.disabled = false;
    }
  }

  async function copyEvents() {
    const contents = output.textContent || "";
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(contents);
      } else {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(output);
        selection.removeAllRanges();
        selection.addRange(range);
        if (!document.execCommand("copy")) throw new Error("Clipboard not available");
        selection.removeAllRanges();
      }
      message.textContent = "Sanitized event history copied.";
    } catch (_error) {
      message.textContent = "Clipboard unavailable. Select the event text to copy manually.";
    }
  }

  panel.addEventListener("toggle", () => {
    if (panel.open) void loadEvents();
  });
  refresh.addEventListener("click", loadEvents);
  copy.addEventListener("click", copyEvents);
})();
