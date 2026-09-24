# Layered gravity demo

This is the preferred demo for the recessed / gravity-wallpaper effect.

It keeps the known-loadable V3 top-level structure (`main` + `backfill`), while the
`main` layer is internally split into **nine independent texture-array slices** and
nine independent quads.

## Why this version exists

The earlier single-image depth mesh could expose the original source image around
the viewport during tilt. The layered version avoids that failure mode:

- eight rounded-rectangle rings + one center disc are separate RGBA images;
- every layer image canvas is larger than the screen;
- every quad uses a matching overscan factor, so artwork aligns at rest but has
  hidden pixels around the viewport;
- overscan grows toward the center (`1.04` -> `1.31`);
- a separate dark-teal backfill uses `1.38x` overscan;
- the outer rim is tuned to move very little, while inner stages move
  progressively more.

### Motion profile

The last point is intentionally an **illusion-oriented** mapping. Camera-space Z is
used as a parallax control: a larger value moves less, and a smaller value moves
more. Therefore the outer rim uses a large value and the center uses a much smaller
one. This is chosen to match the requested "stationary rim / active recessed bottom"
look rather than literal physical Z ordering.

## Build

```powershell
git pull
python -m pip install -e .

python examples/gravity/make_layered_assets.py

python examples/gravity/build_layered_bundle.py `
  examples/gravity/layered_assets `
  -o GravityLayered.spatialscene `
  --fov 45 `
  --astcenc "C:\Tools\astcenc\astcenc-avx2.exe"
```

The output is:

```text
GravityLayered.spatialscene/
├── project.json
└── assets/
    ├── main.ssmesh
    ├── main.sstexture      # arrayLength = 9
    ├── backfill.ssmesh
    └── backfill.sstexture  # arrayLength = 1
```

Import the `.spatialscene` folder itself into SpatialScene.

## Tunable constants

The visual/motion behavior is intentionally easy to tune:

- `OVERSCANS` in `make_layered_assets.py`: hidden border per visible layer.
- `BACKGROUND_OVERSCAN`: hidden border for the full-screen backfill.
- `PARALLAX_DEPTHS` in `build_layered_bundle.py`: larger value = less motion.
- `camera.motionRange` in the generated project: global motion amplitude.

The defaults bias toward avoiding exposed edges first. Once loading and compositing
are confirmed on-device, motion can be increased gradually.
