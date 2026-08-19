from sldforge.symbol_dataset import CLASS_ORDER, render_symbol_scene


def test_symbol_scene_is_deterministic_and_complete(tmp_path) -> None:
    image, objects = render_symbol_scene(123, "style_a", tmp_path / "scene.png")
    assert image.size == (1200, 820)
    assert len(objects) == len(CLASS_ORDER) == 10
    assert {item.class_name for item in objects} == {item.value for item in CLASS_ORDER}
    assert all(0 <= value <= 1 for item in objects for value in item.bbox)
