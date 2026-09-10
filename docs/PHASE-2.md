# Phase 2 — YOLO Animal Detection

## Goal
Establish the computer-vision detection layer that converts camera, image, or video frames into animal detections with bounding boxes, confidence scores, species/type labels, and optional ByteTrack IDs.

## Implemented
- YOLO detector service integrated under `backend/models/detector.py`.
- Separate `predict_frame()` for image/frame inference.
- `track_frame()` for persistent video tracking with ByteTrack.
- Confidence threshold filtering.
- Bounding-box parsing and normalized animal-type mapping.
- Support for Cow, Buffalo, Sheep, and selected COCO animal classes.
- ByteTrack-to-persistent-animal mapping foundation in `backend/models/tracker.py`.
- Unit coverage for species alias mapping in `tests/test_detector_mapping.py`.

## Detection flow

```text
Image / Video / Camera
        |
        v
      YOLO
        |
        +--> Bounding Box
        +--> Confidence
        +--> Species / Animal Type
        |
        v
    ByteTrack
        |
        v
 Tracking ID
```

## Important limitation
The repository currently uses the supplied YOLO weights. Standard COCO weights do not guarantee every requested livestock class, especially buffalo. A custom livestock-trained model should be introduced and evaluated before claiming reliable buffalo detection.

## Phase 2 exit criteria
- Detector module is version-controlled in the repository.
- Animal class mapping has automated tests.
- Runtime camera/image/video validation is still required before production claims.

## Next phase
Phase 3 will connect visual embeddings and similarity matching to the tracking layer so the system can assign or recover persistent animal identities.
