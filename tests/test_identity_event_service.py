from backend.services.identity_event_service import IdentityEventService


def test_event_contains_identity_camera_and_time_metadata():
    event = IdentityEventService().create_event(
        animal_id="C00017",
        animal_type="Cow",
        tracking_id=42,
        confidence=0.93456,
        similarity=0.88123,
        camera_id="CAM-002",
        camera_location="Vadodara Dairy Farm - Gate 2",
        timestamp="2026-09-10T10:15:00+00:00",
    )

    assert event["animal_id"] == "C00017"
    assert event["camera_id"] == "CAM-002"
    assert event["camera_location"] == "Vadodara Dairy Farm - Gate 2"
    assert event["timestamp"] == "2026-09-10T10:15:00+00:00"
    assert event["confidence"] == 0.9346
    assert event["similarity_score"] == 0.8812


def test_event_rejects_missing_camera_metadata():
    service = IdentityEventService()
    try:
        service.create_event(
            animal_id="C00017",
            animal_type="Cow",
            tracking_id=1,
            confidence=0.9,
            similarity=0.9,
            camera_id="",
            camera_location="Gate 1",
        )
    except ValueError as exc:
        assert "camera_id" in str(exc)
    else:
        raise AssertionError("Expected missing camera_id to be rejected")
