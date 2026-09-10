# Testing and Runtime Validation

## What CI verifies

GitHub Actions installs the backend dependency set and runs the repository regression suite with:

```bash
python -m pytest -q
```

The suite covers API smoke behavior, detector/species mapping, camera configuration, recognition logic, identity-event metadata, identity-pipeline behavior, and frontend/API contracts.

## Local validation

From the repository root:

```bash
python -m pip install -r backend/requirements.txt
python -m pytest -q
python scripts/validate_runtime.py
```

`validate_runtime.py` checks the core API/ML imports. If a YOLO weight file is available through `YOLO_MODEL_PATH` or `backend/yolov8n.pt`, it also loads the detector and performs one inference on a synthetic blank frame.

A missing model is reported as **NOT RUN**, not as a passing inference test. This prevents the project from claiming model validation when weights are not available.

## Real image/video validation

For meaningful model validation, provide a compatible detector weight and representative animal images or video. For example:

```powershell
$env:YOLO_MODEL_PATH = "C:\path\to\yolov8n.pt"
python scripts/validate_runtime.py
```

Then validate the application through the image/video endpoints or the live camera workflow. Record the model name, dataset/sample count, confidence threshold, and observed results when reporting performance.

## Accuracy evaluation

The current project is an end-to-end visual re-identification demonstration. It does **not** include a scientifically validated livestock biometric benchmark. Do not report an accuracy percentage unless it has been measured on a defined evaluation dataset.

For a future evaluation, keep separate samples for each animal and report at least:

- detection precision/recall or mAP for the detector
- identification/re-identification accuracy on a held-out set
- false-match and false-new-ID rates
- similarity threshold used
- results by species and camera when applicable

## Validation status

- Automated regression tests: validated in GitHub Actions.
- API smoke tests: validated in GitHub Actions.
- Real YOLO inference: environment/model dependent; only claim PASS when the runtime script or an equivalent real inference run succeeds.
- Real camera/video accuracy: not benchmarked in this repository yet.
- Production performance/security: not validated.
