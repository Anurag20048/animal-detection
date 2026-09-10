# Phase 7 — Inference Validation

Phase 7 validates the detector's inference-result handling without making CI dependent on a camera, GPU, or model download.

## Validated in CI

- YOLO detection result parsing.
- Confidence-threshold filtering.
- Bounding-box conversion.
- Tracking-ID extraction.
- Animal-type mapping for Cow, Sheep, Buffalo, Other Animals, and unsupported classes.
- Identity-service behavior for new and returning detections using deterministic test doubles.

## Real inference requirements

Running YOLO inference requires the dependencies in `backend/requirements.txt` and an available YOLO weights file. A local camera/video source is optional for image-level inference.

The repository does **not** claim a measured detection or biometric accuracy in this phase. Standard pretrained YOLO weights may not contain every livestock class used by the application; buffalo detection requires compatible/custom weights when that class is not present in the selected model.

## Local validation

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m pytest -q
```

For an actual image inference run, start the backend and use the dashboard's image-upload flow. Record the model name, image/video source, hardware, and observed results before adding performance numbers to the README or resume.
