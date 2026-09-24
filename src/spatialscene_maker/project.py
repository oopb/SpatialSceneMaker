from __future__ import annotations

import math
import uuid


IDENTITY_4X4_COLUMN_MAJOR = [
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
]


def expanded_vertical_fov_rad(vertical_fov_deg: float, scale: float = 1.16) -> float:
    base = math.radians(vertical_fov_deg)
    return 2.0 * math.atan(scale * math.tan(base * 0.5))


def build_v3_project(
    width: int,
    height: int,
    vertical_fov_deg: float,
    main_depth_range: tuple[float, float],
    backfill_depth_range: tuple[float, float],
    *,
    scene_id: str | None = None,
    backfill_scale: float = 1.16,
) -> dict:
    if width <= 0 or height <= 0:
        raise ValueError("invalid image dimensions")
    aspect = width / height
    main_fov = math.radians(vertical_fov_deg)
    backfill_fov = expanded_vertical_fov_rad(vertical_fov_deg, backfill_scale)

    pad_x = (backfill_scale - 1.0) * width * 0.5
    pad_y = (backfill_scale - 1.0) * height * 0.5
    main_frame = {"height": height, "width": width, "x": 0, "y": 0}
    backfill_frame = {
        "height": height * backfill_scale,
        "width": width * backfill_scale,
        "x": -pad_x,
        "y": -pad_y,
    }

    return {
        "camera": {
            "motionRange": 0.035,
            "overscan": 0.015,
        },
        "generator": {
            "cameraModel": "pinhole-custom-depth-v1",
            "experimental": True,
            "framing": {"mode": "full"},
            "framingGeometry": "padded-frames",
            "input": {
                "orientedHeight": height,
                "orientedWidth": width,
            },
            "name": "SpatialSceneMaker",
            "strategy": "Full-image custom depth; 1.16 backfill projection expansion.",
        },
        "id": scene_id or str(uuid.uuid4()),
        "layers": [
            {
                "aspectRatio": aspect,
                "depthRange": [float(backfill_depth_range[0]), float(backfill_depth_range[1])],
                "frame": backfill_frame,
                "mesh": "assets/backfill.ssmesh",
                "modelToWorldColumnMajor": IDENTITY_4X4_COLUMN_MAJOR,
                "role": "backfill",
                "texture": "assets/backfill.sstexture",
                "verticalFOV": backfill_fov,
            },
            {
                "aspectRatio": aspect,
                "depthRange": [float(main_depth_range[0]), float(main_depth_range[1])],
                "frame": main_frame,
                "mesh": "assets/main.ssmesh",
                "modelToWorldColumnMajor": IDENTITY_4X4_COLUMN_MAJOR,
                "role": "main",
                "texture": "assets/main.sstexture",
                "verticalFOV": main_fov,
            },
        ],
        "renderer": "depth-field-v3",
        "schemaVersion": 3,
        "viewport": main_frame,
    }
