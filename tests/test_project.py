import math

from spatialscene_maker.project import build_v3_project, expanded_vertical_fov_rad


def test_v3_project_contains_loader_fields():
    p = build_v3_project(1290, 2796, 45.0, (1.0, 3.5), (8.4, 8.401), scene_id="00000000-0000-0000-0000-000000000001")
    assert p["schemaVersion"] == 3
    assert p["renderer"] == "depth-field-v3"
    assert set(("camera", "id", "layers", "viewport")).issubset(p)

    assert p["viewport"] == {"height": 2796, "width": 1290, "x": 0, "y": 0}
    required = {
        "aspectRatio", "depthRange", "frame", "mesh",
        "modelToWorldColumnMajor", "role", "texture", "verticalFOV",
    }
    for layer in p["layers"]:
        assert required.issubset(layer)

    main = next(x for x in p["layers"] if x["role"] == "main")
    back = next(x for x in p["layers"] if x["role"] == "backfill")
    assert math.isclose(main["verticalFOV"], math.radians(45.0))
    assert math.isclose(back["verticalFOV"], expanded_vertical_fov_rad(45.0))
    assert math.isclose(back["frame"]["width"], 1290 * 1.16)
    assert math.isclose(back["frame"]["height"], 2796 * 1.16)
