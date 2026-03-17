# PATCH NOTES — PiServer 0_2_9

## Summary
This patch fixes the Motor tab UI so your selected values do not immediately snap back to the previous saved settings before you can press **Apply motor settings**.

It also forces a new web-app version string so the browser loads the updated JavaScript instead of keeping an older cached script.

---

## Problem reported
You reported that after changing a motor setting in the web UI, the value immediately fell back to the default/old value. Because of that, the new setting never stayed long enough to be applied, so the car behavior looked unchanged.

---

## Root cause
The Motor tab was being refreshed continuously from `/api/status` every ~800 ms.

That status sync was writing the currently applied motor values back into the form even while you were editing it. So the flow looked like this:

1. you changed a dropdown or slider
2. the background status poll ran
3. the form was overwritten with the old live values
4. your new choice disappeared before Apply could use it

A second issue was browser caching: if the JavaScript file did not refresh, the old overwrite behavior could continue even after copying in a new `app.js`.

---

## What changed

### 1) Added a motor-form dirty state in the frontend
When you edit any Motor tab control, the page now marks the motor form as **unsaved/dirty**.

### 2) Stopped background status polling from overwriting the Motor form while you are editing
If the Motor page has unsaved changes, `/api/status` no longer pushes the old motor values back into those inputs.

### 3) Clear the dirty state only after a real refresh/apply
The Motor form is reset to a clean state only when:
- saved motor config is explicitly loaded
- motor settings are successfully applied

### 4) Bumped the web app version to 0_2_9
This changes the cache-busting version on the script URL so the browser requests the new `app.js` instead of reusing an older cached copy.

---

## Files changed
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_9.md`

---

## Verification
I checked the updated logic to confirm:
- changing any Motor tab input sets the form to unsaved
- background status sync no longer overwrites Motor tab inputs while unsaved changes exist
- loading saved motor config still fills the form normally
- applying motor settings fills the form with the saved/applied values and clears the unsaved state
- app version now reports `0_2_9` for browser cache refresh

---

## How to apply
1. copy these patched files into your existing `PiServer` folder
2. restart PiServer
3. hard-refresh the browser once after restart
4. open the Motor tab
5. change the setting you want
6. click **Apply motor settings**

If your car turns right when you steer left, set:
- **Steering direction = Reverse**

---

## Expected result after this patch
The selected value should now stay where you set it until you press **Apply motor settings**, and then the applied value should remain visible afterward.
