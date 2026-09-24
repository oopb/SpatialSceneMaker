# Layered gravity demo

This is the preferred demo for the recessed / gravity-wallpaper effect.

The current revision uses **six full-screen texture slices**:

- four full-screen plates with rounded-rectangle cut-outs;
- one full-screen plate with a circular cut-out;
- one full-screen bottom image revealed through that final circular opening.

Every layer now has the **same outer extent: the whole screen**. The apparent nested shapes come only from the holes cut through the layers above it.

## Restored opening sizes

The rounded openings use the earlier six-stage proportions again:

```text
opening 1   x=135..1155, y=790..2140, radius=150
opening 2   x=210..1080, y=900..2030, radius=130
opening 3   x=300..990,  y=1030..1900, radius=108
opening 4   x=405..885,  y=1180..1750, radius=82
final hole  circle radius=165
```

## Soft recessed highlight

There are **no dark inner shadows**.

Each cut-out gets a two-scale soft highlight:

- a broad low-intensity lift begins farther from the opening;
- a narrower highlight increases smoothly toward the cut-out edge.

This creates a natural brightness ramp into the hole instead of a hard ring.

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

The mesh is emitted in **inner-to-outer painter order**, so upper full-screen plates cover lower stages whenever motion causes overlap.

## Overscan

Each logical layer is screen-sized, but its texture canvas includes hidden overscan so motion never reveals an edge:

```text
1.035, 1.055, 1.085, 1.12, 1.17, 1.24
```

The backfill uses `1.32x` overscan.

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


## Sharpness fix

The previous layered build used a fixed `2048x2048` texture for every oversized
layer canvas. With overscan, the visible viewport used substantially fewer than
2048 vertical texels (the deepest 1.24x layer used only about 1650), which made
the result visibly soft after projection back to a 2796-high screen.

The layered builder now defaults to:

```text
texture size = 3072x3072
ASTC quality = thorough
```

You can override these with `--texture-size` and `--astc-quality`.

## Highlight direction fix

The earlier implementation brightened the **upper plate around its own hole**.
That reads like a raised bevel and can make the recess look convex.

The current implementation instead brightens the **lower surface just inside the
opening above it**. The highlight fades inward from the parent opening edge and
contains no dark shadow. This is the intended recessed-lighting direction.
