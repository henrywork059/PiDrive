# CustomTrainer

## R42 — Exact operation results and artifact locations (0_2_16)

**Validation**, **Export** and **Export Validate** now show a compact, scrollable
**Last result** pane beside their existing Status message. The pane reports
**Running / Stopping / Succeeded / Failed / Cancelled**, local start/finish
timestamps, the exact input model name/path and dataset YAML or prediction
source captured **at launch**, output format where applicable, reported
validation metrics, and the exact output file or folder emitted by the worker.

- **Native-model Validation** and **Exported-model Validation** have separate
  labels so metrics are visibly linked to the specific model evaluated. The
  selected model path and dataset/source are frozen at the start; changing an
  input field while a task runs cannot relabel an old result.
- Export reads the existing `[export] <path>` CLI marker, ignoring the
  separate manifest marker. Validation and prediction read `[save-dir]`;
  validation metrics read `[metrics]`. A successful process exit is **not**
  by itself enough to confirm an output. Existing on-screen frame browsers,
  validation charts, logs and immutable YOLO dataset cache are unchanged.
- An output is confirmed only when the reported file exists and is nonempty,
  or a reported output directory contains actual nonempty result files.
  Prediction folders must contain an image. TFLite exports additionally
  require their existing U27 checksum-bound YOLO manifest to verify.
- **Open Location** opens the verified artifact's parent directory or the
  verified result directory using the OS file manager. The button is
  disabled for running/stopped/failed/unverified results, and validates the
  path **again** when clicked in case files were moved or deleted. A cancelled
  or failing subprocess can leave partial disk files; these are not reported
  as successfully completed artifacts.
- If the selected model path is unavailable (for example, an Ultralytics
  name that the backend resolves or downloads), the summary explicitly says
  **Not verified**, instead of claiming the entered path was confirmed.
  Missing metrics are **Unknown**, never fabricated as zero. The output path
  may be logged for troubleshooting when an operation fails, but it is
  visibly labelled **unconfirmed** and cannot be opened through the action.

This release does **not** alter PyTorch/Ultralytics training commands, split
or cache semantics, export formats, existing window splitter proportions,
Marking/Quick Deploy shortcuts, YOLO source labels or U27 metadata.

Regression check on the workstation:

```bash
cd CustomTrainer
python -m unittest discover -s tests -p 'test_task_result_r42.py' -v
python -m unittest discover -s tests -v
```

Check real successful/failed/stopped native validation, exported-model
validation, prediction and all supported exports, including exported TFLite
sidecars and Windows **Open Location** behavior. The optional offscreen Qt
smoke checks do not replace real Windows interaction testing.

## Marking annotation workflow (0_2_15, R41)

The Marking tab keeps the compact **280-pixel maximum right-side pane** and its
large central frame preview, Quick Deploy Selected / Current, and existing
auto-save on frame switch. New edit/navigation commands are scoped to Marking:

- **A / D** or **PageUp / PageDown**: previous / next image; existing
  unsaved-label auto-save policy still applies.
- **B / Shift+B**: select next / previous bounding box. Right-click still
  selects a box; right-drag moves the selected box.
- **W / S**: cycle classes; **1–9** chooses class ID 0–8 (only when that
  class exists) and applies it to the selected box, or sets the active class
  for newly drawn boxes. Existing class list and class storage are unchanged.
- **Arrow keys**: nudge selected box by one source-image pixel, **Shift+Arrows**
  by 10 pixels; movement remains inside the image.
- **Ctrl+Z**: undo; **Ctrl+Y / Ctrl+Shift+Z**: redo creation, deletion,
  movement, class changes, nudges, and replacement of the current canvas
  annotations from Quick Deploy. The last 50 committed edits are retained
  **for the current image only**. Switching or reloading the frame resets
  undo/redo; editing another frame cannot undo the previous frame's edits.
- **Ctrl+mouse-wheel**: zoom around the pointer (1×–8×); **middle-button drag**
  pans the zoomed image; **Ctrl+Plus / Ctrl+Minus / Ctrl+0** zooms or resets.
  Zoom/pan changes only the viewport, not YOLO label coordinates or images.
- **X**: delete selected frame(s) using the existing confirmation;
  **Delete**: remove selected bounding box; **Ctrl+S**: save labels;
  **F1**: full shortcut Help.

Marking letter/number/annotation shortcuts are disabled while a text editor,
path input, class combo box or numeric editor has keyboard focus, **before**
Qt can intercept typed keys. Shortcuts from the previous main-window scope
that duplicated Marking commands were consolidated onto the Marking page.

Undo and redo modify the **current unsaved annotations** only; they do not
restore a frame that was deleted from disk, undo already persisted edits to
another frame, or roll back Quick Deploy's batch writes to other frames.
The existing explicit Save Labels and save-before-switch behavior still
controls persistent YOLO label writes.

Regression checks: `cd CustomTrainer && python -m unittest discover -s
tests -p 'test_marking_efficiency_r41.py' -v`. The optional PySide6 tests
require a GUI-capable workstation; verify text entry, fast frame switching,
box coordinates after zoom/pan, class selection, undo across multiple
moves, and Quick Deploy before promoting this draft PR.

## YOLO model manifests and Pi preflight (0_2_14, U27)

A successful TFLite export now writes `<model>.tflite.manifest.json`,
including the YOLO model family, RGB/NHWC input, image size, normalization,
output interpretation, class names, selected quantization mode and SHA-256
checksum. An unknown training seed remains null rather than being invented.
If manifest publication fails, the export reports a failure explicitly.

The **Pi Deploy** bundle includes a copy of the TFLite model, labels,
its checksum-verified YOLO sidecar, `model_config.json`, and a model-manifest
reader. A complete bundle is staged before replacing an existing bundle; an
invalid source sidecar or empty class list does not delete the previous bundle.
The standalone runtime validates the family, file checksum, image shape,
class names, and a zero-input inference **before opening the camera**.
Old sidecar-free YOLO models are still accepted with an explicit warning and
shape/inference checks. A steering-control model is not accepted as a YOLO
detector.

The sidecar documents intended semantics, not proof of training quality.
Check a physical Pi with a real TFLite interpreter before deployment.
Existing U18 session grouping, U25 immutable dataset generations, Marking,
Quick Deploy and all stored settings remain unchanged.

CustomTrainer is a PySide6 desktop workflow for object-detection data labeling, training, validation, export, and exported-model validation.

## Launch

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

## Current snapshot version marker

Window title/version is set in:
- `custom_trainer/ui/main_window.py`

Use that file as source of truth for documentation version text.

## Tabs and responsibilities

- **Marking**: session discovery, annotation, class management, quick deploy labeling support
- **Training**: run training jobs and inspect logs/plots
- **Validation**: run validation/prediction for trained models
- **Export**: export trained weights (TFLite/ONNX/OpenVINO/TorchScript)
- **Export Validate**: run inference/validation on exported models

## Dataset integrity and YOLO annotation validation (0_2_12)

The generated `dataset.yaml` uses session-aware train/validation partitions.
Whole capture sessions stay in one partition, including sessions connected
by identical image bytes. The approximate 10% validation target is secondary
to keeping independent capture sessions separate.

**At least two independent, non-duplicate sessions are required** for an
automatic validation holdout. If only one independent session exists, the
generated `val.txt` stays empty and Train, Validate and Export Validate
show a clear warning rather than reusing training images as validation.
You can label a second recording session and regenerate the dataset.

Before launching training or validation, the Run Log reports per-session
image counts, valid annotation counts, missing/empty labels, invalid box
counts and representative line-specific errors. The generated training
cache excludes invalid YOLO boxes (non-finite/out-of-range coordinates,
boxes extending beyond image bounds, invalid class IDs and zero-size
boxes). Source labels are **not rewritten**; fix problematic labels in
Marking and prepare the dataset again.

Session-grouped splitting reduces leakage but cannot detect visually
near-identical frames with different bytes. Capture in distinct runs,
conditions or locations for stronger validation. The existing Marking
quick-deploy and Export Validate interfaces are unchanged.

## Immutable YOLO dataset cache generations (0_2_13, U25)

Training, Validation, and Export Validate now run against **private, immutable
dataset snapshots** in `.customtrainer_yolo_cache/generations/gen_*/`.
Preparing another dataset no longer deletes files referenced by an active
training process. Each run receives its own generation-local `dataset.yaml`,
`train.txt`, `val.txt`, copied image files, and validated training labels.

Dataset preparation first builds in a private `.building/` directory, checks
the complete image lists and label counts, writes a `cache_manifest.json`,
then atomically promotes the generation. Only after successful publication
does the familiar root `dataset.yaml` pointer change (via atomic file
replacement). If a build fails, the previous public YAML and old generations
remain intact. The Marking, training split, labeling, and exported-model
workflows are otherwise unchanged. Original images are **copied**, not
hard-linked: an in-place source image edit cannot alter a running snapshot.

**Retention:** There is **no automatic deletion** of prior generations or
the old pre-U25 cache layout. This uses additional disk space; check free space
when preparing large image datasets. Inspect caches from the CustomTrainer
project directory:

```bash
python manage_dataset_cache.py /path/to/sessions_root
```

After confirming training, validation, and external YOLO readers are finished,
explicitly prune old known generations:

```bash
python manage_dataset_cache.py /path/to/sessions_root --prune --confirm-idle
```

Pruning preserves at least the two newest generations, the currently selected
dataset YAML, generations younger than 24 hours, and any generation protected
by an active CustomTrainer Ultralytics subprocess lease. Other directories or
unknown cache formats are never removed. Do **not** manually delete or edit an
active `gen_*` directory. Jobs launched outside CustomTrainer may not hold
its reader lock: the `--confirm-idle` acknowledgement is therefore
important even when the CLI shows no busy generation.

The root `dataset.yaml` remains for backwards compatibility, but it points
to the latest published snapshot and can change on a later preparation.
For reproducible manual `yolo` commands, use the **generation-local
`dataset.yaml`** shown in the Run Log. Cache cleanup and Windows file-lock
handover should be verified on the target workstation before widespread use.

## Requirements and environment

- Python **3.11** recommended
- Install from `requirements.txt`
- GPU acceleration depends on local torch/cuda environment

## Operational notes

- UI state (splitters, last path) is persisted locally.
- If layout is abnormal after upgrades, reset state or ensure width clamping logic is active in Marking page.
- For Pi deployment helpers, see `custom_trainer/assets/pi_runtime/README_PI.md`.

## Bug-prevention reference

For recurring UI and deployment pitfalls derived from historical patch notes, see:
- `../BUG_PREVENTION_NOTES.md`
