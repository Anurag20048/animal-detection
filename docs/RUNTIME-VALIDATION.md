# Runtime Validation Matrix

This document separates deterministic software validation from hardware/model-dependent validation.

| Area | Status | Evidence / requirement |
|---|---|---|
| Python syntax | Validated | Repository Python sources compile successfully in the development audit. |
| API routing | Validated | FastAPI smoke tests exercise health, animals, authentication protection, and missing-animal handling. |
| Frontend contract | Validated | Regression tests check dashboard assets, supported API routes, and absence of a shipped default password. |
| YOLO result parsing | Validated | Tests cover confidence filtering, boxes, tracking IDs, and animal-type mapping. |
| Identity service | Validated with deterministic fakes | Tests cover new-ID creation, tracking-ID reuse, similarity comparison, and persistence calls. |
| Real YOLO inference | Environment-dependent | Requires `ultralytics` and compatible weights. Must be run with a real image/video source. |
| ByteTrack on real frames | Environment-dependent | Requires a successful YOLO runtime and tracker configuration. |
| ResNet embedding on real crops | Environment-dependent | Requires PyTorch/torchvision weights to be available. |
| End-to-end image → ID | Environment-dependent | Requires all ML dependencies, model weights, writable runtime storage, and a representative image. |
| Buffalo detection | Not validated by generic COCO weights | Use a model trained with a buffalo class before claiming buffalo detection support. |
| Biometric accuracy | Not claimed | No animal-specific benchmark dataset or validation study is included. |

## Local runtime check

From `backend/`:

```powershell
pip install -r requirements.txt
uvicorn app:app --reload
```

Then use the dashboard or call the image-detection endpoint with a representative animal image.

## What counts as a real inference validation

A real validation run should record:

1. model file used and its SHA-256 hash;
2. Python and package versions;
3. input image/video source;
4. detected class, confidence and bounding box;
5. tracking ID when tracking is enabled;
6. generated animal ID and similarity score;
7. persistence result in the configured storage layer;
8. any model-specific limitations.

Do not convert a unit-test pass into an accuracy claim. The project should only report measurements that were actually produced by a reproducible runtime experiment.
