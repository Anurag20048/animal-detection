# Phase 3 — Persistent Animal Identity and Camera History

## Goal

Connect animal identity to an observation event so the system can answer:

- Which persistent animal ID was detected?
- When was it detected?
- Which camera saw it?
- Where is that camera located?
- What were the detection confidence and identity similarity scores?

## Implementation

### 1. Explicit camera metadata

`backend/utils/camera_registry.py` maps a video source to:

- `camera_id`
- `source`
- `location`

Location is configuration data. The system does not pretend to derive a physical location from a webcam or video stream.

Example configuration:

```json
[
  {"camera_id": "CAM-001", "source": "0", "location": "Vadodara Dairy Farm - Gate 1"},
  {"camera_id": "CAM-002", "source": "1", "location": "Vadodara Dairy Farm - Gate 2"}
]
```

Set this JSON in `CAMERA_CONFIGS`.

### 2. Normalized identity events

`backend/services/identity_event_service.py` creates a storage-neutral event containing:

- persistent `animal_id`
- animal type
- ByteTrack `tracking_id`
- timestamp
- camera ID and location
- detection confidence
- identity similarity score
- optional crop paths

This preserves the distinction between a short-lived tracking ID and a persistent animal identity.

### 3. Multi-camera history

Because camera metadata is stored on every event, the same persistent ID can appear across cameras:

```text
C00017
  ├── CAM-001 → 08:31
  ├── CAM-002 → 10:15
  └── CAM-003 → 12:48
```

## Validation

Unit tests cover camera-source resolution, safe unknown-camera fallback, event fields, numeric rounding, and required camera metadata.

Full webcam/video runtime validation is still a separate environment-dependent step because the ML stack and model execution are not verified in CI yet.
