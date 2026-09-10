import numpy as np

from backend.models.detector import YOLOAnimalDetector


def _detector_without_model():
    detector = YOLOAnimalDetector.__new__(YOLOAnimalDetector)
    detector.names = {0: "cow", 1: "sheep", 2: "dog", 3: "buffalo"}
    return detector


class _Tensor:
    def __init__(self, value):
        self.value = np.asarray(value)

    def cpu(self):
        return self

    def numpy(self):
        return self.value


class _Boxes:
    def __init__(self):
        self.xyxy = _Tensor([[10.2, 20.8, 110.9, 120.1], [5, 5, 50, 50]])
        self.conf = _Tensor([0.91, 0.25])
        self.cls = _Tensor([0, 2])
        self.id = _Tensor([17, 18])

    def __len__(self):
        return 2


class _Result:
    boxes = _Boxes()


def test_inference_result_parser_keeps_valid_animal_detection():
    detector = _detector_without_model()
    detections = detector._parse_results([_Result()], confidence_threshold=0.35)

    assert len(detections) == 1
    detection = detections[0]
    assert detection.animal_type == "Cow"
    assert detection.class_name == "cow"
    assert detection.confidence == 0.91
    assert detection.tracking_id == 17
    assert detection.bbox == (10, 20, 110, 120)


def test_inference_result_parser_maps_supported_animal_types():
    detector = _detector_without_model()
    assert detector._map_animal_type("cow") == "Cow"
    assert detector._map_animal_type("sheep") == "Sheep"
    assert detector._map_animal_type("buffalo") == "Buffalo"
    assert detector._map_animal_type("dog") == "Other Animals"
    assert detector._map_animal_type("car") is None
