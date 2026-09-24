# Layered gravity demo

This is the preferred demo for the recessed / gravity-wallpaper effect.

The current revision uses **six visible stages** built as **large plates with cut-out openings**:

- four upper plates with progressively smaller rounded-rectangle openings;
- one lower plate with a circular opening;
- one center disc at the very bottom.

All five plates cover the same large rounded-rectangle region. They are not floating squares or rings: the next stage is only visible through the opening carved into the plate above it.

## Thicker edges / smaller openings

The openings were reduced again so the visible plate borders are thicker:

```text
top opening    x=190..1100, y=820..2110
next           x=285..1005, y=940..1990
next           x=380..910,  y=1070..1860
next           x=470..820,  y=1200..1730
bottom circle  radius=128
```

## Recess cue

There are **no dark inner shadows** in this version. Each opening gets only a soft, low-opacity bright lip. The bright lip plus inner-to-outer compositing is used to make the geometry read as a smooth cavity.

## Motion profile

Upper stages move less and lower stages move more:

```text
outer/top     55.0   -> smallest motion
              28.0
              15.0
               8.5
               5.2
center/bottom  3.7   -> largest motion
```

The mesh is emitted in **inner-to-outer painter order**, so upper plates cover lower stages whenever motion causes overlap.

## Overscan

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
  --astcenc "astcenc-5.7.0-windows-x64/bin/astcenc-avx2.exe"
```

The asset generator removes stale `slice_*.png` files first.

## Bundle structure

```text
GravityLayered.spatialscene/
├── project.json
└── assets/
    ├── main.ssmesh
    ├── main.sstexture      # arrayLength = 6
    ├── backfill.ssmesh
    └── backfill.sstexture  # arrayLength = 1
```
