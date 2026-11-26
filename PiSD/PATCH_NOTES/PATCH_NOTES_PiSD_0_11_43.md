# PiSD 0.11.43 — Batch 4 / R35 Settings safe input and console audit

Exact parent ef7c1ee verified Linux 45755617247 4/4 and Windows 45755617236 1/1; PiSD Node 24/24, standard 63/63 and Chromium 32/32, PiServer Node 18/18 and Chromium 4/4, package dry runs all passed. Reviewed real PiSD.py, settings template/handlers, global Space STOP, current browser and Node tests, canonical R35 and latest notes 0.11.42/41/40/39. Also inventoried native controls in PiSD Front and PiServer dashboard template; broader audit remains open.

## Changes
- settings_tab.html: twenty existing numeric range readouts excluded from accessible name calculation (native range still exposes value, readouts remain visible); explicit import name; named, focusable read-only last-response console uses existing local Space exemption.
- scripts/test_accessibility_r35.cjs: two cases for stable labels, actual readout update and console local Space isolation with retained body/pad STOP.
- tools/check_browser_ui.py: existing failed/recovered read, slow load and save-rejection fixture at all four widths now uses native Enter and narrow-screen touch for read/retry, range arrow keys/readout, named focusable console and native reverse/forward Tab, no mutations during draft/console inspection. Retain actual rejected save and explicit STOP assertions.
- version and shared audit evidence.

## Verification and limits
Guarded forward edits and JS syntax preflight only; exact CI pending. No settings payload, save/load/reset logic, config values, global STOP handler, motor or authorization change. Existing body/pad Space STOP and explicit STOP unchanged. No local browser or hardware execution. R35 remains partial; native mobile file chooser, contrast, additional active controls and full safe journeys not certified. No merge, stable promotion or deployment.


## Revision B — relative Settings readout locator

Initial exact a475aad Linux 45756448004 failed only PiSD native Chromium (28/32; Settings at 390/768/1024/1440); Node safety/input 26/26 and standard validation 63/63 passed. Windows 45756448063 passed, combined 4/5. Logs show the correctly named Speed slider at 0.43, but the form-qualified inner locator was searched relative to each label and found no output. Use a label-relative input[name="speed"] locator and reuse its output for both exact 0.43 and 0.44 text assertions. All native input, readout, console isolation, no-mutation, rejected Save and STOP assertions retained. Guarded source comparison confirms only the locator expressions changed; no runtime, version, motor, config or other component changes. Exact corrected combined CI and package dry runs required; no local browser or hardware execution claimed. R35 remains partial.


## Revision C — native Settings Import accessibility

Exact Revision B 8873d22 Linux 45764849325 failed only PiSD Chromium Settings at 390/768/1024/1440 (28/32). The slider name, value and corrected readout assertions now pass; the next assertion finds the file input but its accessible name is empty. settings_tab.css sets its display to none, removing the native picker from focus and accessibility. PiSD Node 26/26 and standard 63/63 passed; PiServer Node 18/18 and Chromium 4/4 passed; manifest 7/7, package 11/11, all three actual forward dry runs passed. Windows 45764849409 passed (native Qt accessibility 15/15); combined 4/5, Chromium 32/36.

Retain the existing labelled file input, label appearance and import change handler; use a transparent positioned native picker over the label rather than display:none. Give the visible label a focus-within outline and forced-colors outline color. Extend registered Node suite with native-input/Space isolation and CSS contract; existing four-width browser cases retain the accessible-name assertion and add native Tab/reverse Tab, normal/forced-colors focus, Enter/Space chooser events and narrow touch chooser event, with no selected file and zero mutations. No import payload, config, motor, authorization, global STOP handler, other runtime or version changes.

Local isolated Chromium probe of the existing picker markup plus proposed CSS passed 390/768/1024/1440, including normal/forced-colors focus, Enter/Space chooser and narrow touch. This is not the full Flask fixture or full CSS cascade; actual OS chooser selection and physical hardware are not tested. Exact corrected combined CI pending; R35 remains partial. No PiServer 0.4.45 until the complete gate passes.
