from types import SimpleNamespace

from backend.utils.camera_registry import CameraRegistry


def test_registry_resolves_camera_by_source():
    settings = SimpleNamespace(
        camera_configs='[{"camera_id":"CAM-001","source":"0","location":"Vadodara Dairy Farm - Gate 1"}]',
        default_camera_id="CAM-001",
        default_camera_location="Unknown",
        default_camera_source="0",
        parse_source=lambda value: int(value) if str(value).isdigit() else value,
    )
    registry = CameraRegistry.from_settings(settings)
    assert registry.resolve(0) == ("CAM-001", "Vadodara Dairy Farm - Gate 1")


def test_registry_has_safe_unknown_fallback():
    registry = CameraRegistry([])
    assert registry.resolve("rtsp://unknown") == ("CAM-UNKNOWN", "Unknown")
