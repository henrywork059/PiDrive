/* M02 first slice: same-document quiescence and acknowledged STOP before
 * navigation. Not a server-issued authority token or a cross-client fence.
 * Never auto-arm, rearm, replay input, or infer physical motor feedback.
 */
(function(root) {
  "use strict";
  const motion = new Set(["/api/control/manual", "/api/ai/start", "/api/ai/manual-correction"]);
  function neutralAck(data) {
    const motor = data?.motor, ai = data?.ai;
    return data?.ok === true && motor?.manual_lease_active === false &&
      ["last_intended_left", "last_intended_right", "last_left", "last_right"].every(k =>
        typeof motor[k] === "number" && Number.isFinite(motor[k]) && Math.abs(motor[k]) <= 1e-6) &&
      ai?.running === false && ai?.drive_output_enabled === false;
  }
  function create({fetchImpl, disarm, status, navigate}) {
    let locked = false, switching = false, uncertain = false;
    const pending = new Set();
    function request(path, options = {}) {
      const tracked = String(options.method || "GET").toUpperCase() === "POST" && motion.has(path);
      if (!tracked) return fetchImpl(path, options);
      if (locked) return Promise.reject(new Error("Driving locked for neutral transition; fresh authorization required."));
      const task = Promise.resolve().then(() => fetchImpl(path, options));
      pending.add(task);
      task.then(() => pending.delete(task), () => { pending.delete(task); uncertain = true; });
      return task;
    }
    async function stop() {
      const response = await fetchImpl("/api/control/stop", {
        method: "POST", headers: {"Content-Type": "application/json"}, cache: "no-store",
        body: JSON.stringify({reason: "v17-navigation", keep_ai_preview: false}),
      });
      const data = await response.json();
      if (!response.ok || !neutralAck(data)) throw new Error("Backend did not confirm neutral output and idle AI.");
    }
    async function switchTo(url) {
      if (switching) return false;
      switching = locked = true;
      disarm();
      status("pending", "Stopping — waiting for backend confirmation.");
      try {
        const outstanding = [...pending];
        // Request STOP immediately, even if an earlier motion fetch is pending.
        // If any were outstanding, require another STOP after they settle.
        await stop();
        if (outstanding.length) {
          await Promise.allSettled(outstanding);
          await stop();
        }
        if (uncertain) throw new Error("Earlier motion request outcome is unknown. Verify STOP and recover explicitly.");
        status("confirmed", "Neutral output confirmed by backend.");
        navigate(url);
        return true;
      } catch (error) {
        status("failed", "Transition blocked: " + String(error?.message || error));
        return false;
      } finally {
        switching = false;
      }
    }
    return {request, switchTo};
  }
  const exported = {create, neutralAck};
  if (typeof module !== "undefined" && module.exports) module.exports = exported;
  else root.PiSDV17TransitionFactory = exported;
})(typeof window !== "undefined" ? window : globalThis);
