from backend.models.detector import YOLOAnimalDetector


def detector_without_model():
    return YOLOAnimalDetector.__new__(YOLOAnimalDetector)


def test_cow_aliases_map_to_cow():
    detector = detector_without_model()
    assert detector._map_animal_type("cow") == "Cow"
    assert detector._map_animal_type("bull") == "Cow"
    assert detector._map_animal_type("calf") == "Cow"


def test_buffalo_aliases_map_to_buffalo():
    detector = detector_without_model()
    assert detector._map_animal_type("buffalo") == "Buffalo"
    assert detector._map_animal_type("water_buffalo") == "Buffalo"


def test_sheep_aliases_map_to_sheep():
    detector = detector_without_model()
    assert detector._map_animal_type("sheep") == "Sheep"
    assert detector._map_animal_type("lamb") == "Sheep"


def test_non_animal_class_is_ignored():
    detector = detector_without_model()
    assert detector._map_animal_type("car") is None
