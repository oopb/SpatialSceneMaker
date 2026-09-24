# Layered gravity demo

This is the preferred demo for the recessed / gravity-wallpaper effect.

The current revision deliberately uses **six visible stages**:

- five rounded-rectangle rings;
- one center disc.

The previous nine-stage version was visually too busy.

## Recessed compositing

There are two separate requirements:

1. the upper / outer stages should move less;
2. the lower / inner stages should visually sit *behind* the upper stages.

The motion profile still uses larger camera-space depth for the outer rim and smaller
values toward the center, because that gives the requested increasing motion:

```text
outer/top    55.0   -> smallest motion
             28.0
             15.0
              8.5
              5.2
center/bottom 3.7   -> largest motion
```

That parallax mapping is intentionally non-physical. To stop it from reading as an
outward stack, the mesh is now emitted in **inner-to-outer painter order**, so the
outer rings are composited last and visually cover lower stages when motion causes
overlap. The artwork also has a darkened inner lip on every ring to reinforce the
cavity cue.

## Overscan

Every texture slice is generated on a canvas larger than the screen. Hidden border
still increases toward the lower stages:

```text
1.035, 1.055, 1.085, 1.12, 1.17, 1.24
```

The full-screen backfill uses `1.32x` overscan.

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

The asset generator removes stale `slice_*.png` files first, so switching from the
old nine-layer layout to the new six-layer layout will not leave extra slices behind.

## Current bundle structure

```text
GravityLayered.spatialscene/
├── project.json
└── assets/
    ├── main.ssmesh
    ├── main.sstexture      # arrayLength = 6
    ├── backfill.ssmesh
    └── backfill.sstexture  # arrayLength = 1
```

Import the `.spatialscene` folder itself into SpatialScene.
