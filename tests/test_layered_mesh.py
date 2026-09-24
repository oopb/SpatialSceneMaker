from spatialscene_maker.mesh import build_full_frame_quad, merge_meshes


def test_full_frame_quad_preserves_texture_slice_and_overscan():
    vertices, indices = build_full_frame_quad(
        4.0,
        1290 / 2796,
        45.0,
        texture_slice=8,
        overscan=1.31,
    )
    assert len(vertices) == 4
    assert indices == [0, 2, 1, 1, 2, 3]
    assert {v.texture_slice for v in vertices} == {8}
    assert {round(v.z, 6) for v in vertices} == {-4.0}


def test_merge_meshes_rebases_indices():
    a = build_full_frame_quad(10.0, 0.5, 45.0, texture_slice=0)
    b = build_full_frame_quad(5.0, 0.5, 45.0, texture_slice=1)
    vertices, indices = merge_meshes([a, b])
    assert len(vertices) == 8
    assert indices[:6] == [0, 2, 1, 1, 2, 3]
    assert indices[6:] == [4, 6, 5, 5, 6, 7]
    assert {v.texture_slice for v in vertices[:4]} == {0}
    assert {v.texture_slice for v in vertices[4:]} == {1}
