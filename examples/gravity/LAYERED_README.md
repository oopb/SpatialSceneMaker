# Layered gravity demo

This demo uses **eight full-screen texture slices**:

- six full-screen plates with geometrically similar rounded-rectangle cut-outs;
- one full-screen plate with the preserved circular cut-out;
- one full-screen bottom image.

There is no highlight / glow overlay.

## Stronger color contrast

Adjacent layers now use more separated green/teal values so the eight-stage
stack remains readable without synthetic edge lighting.

## Proportional rounded openings

The **smallest rounded opening is restored exactly to the original size**:

```text
480 x 570
corner radius = 82
```

The preserved center circle remains:

```text
center = (645, 1465)
radius = 165
diameter = 330
```

All six rounded openings are uniform scales of the same 480 x 570 / r=82 base
shape. Their current outer -> inner geometry is approximately:

```text
1020 x 1211, r=174
 877 x 1042, r=150
 754 x  896, r=129
 649 x  771, r=111
 558 x  663, r=95
 480 x  570, r=82
circle diameter 330
```

This reduces the visual jump between the smallest rounded opening and the center
circle while preserving strict geometric similarity across all rounded layers.

## Larger height separation

The deepest layer remains at the original near depth:

```text
inner depth = 3.7
```

The outer layer is moved farther away:

```text
outer depth = 75.0
```

For the six rounded-opening plates and circular-opening plate, height above the
bottom is strictly proportional to the opening perimeter. The bottom full-screen
surface has zero relative height.

Current depth values are approximately:

```text
75.000
65.019
56.423
49.074
42.728
37.254
21.455
 3.700
```

## Motion direction

Based on the latest device test, the offset direction is flipped again:

```text
camera.motionRange = -0.025
```

## Overscan

```text
1.035, 1.048, 1.062, 1.082, 1.105, 1.135, 1.18, 1.24
```

## Texture quality

The layered builder defaults to:

```text
texture size = 3072x3072
ASTC quality = thorough
```

## Build

```powershell
git pull
python -m pip install -e .

python examples/gravity/make_layered_assets.py

python examples/gravity/build_layered_bundle.py `
  examples/gravity/layered_assets `
  -o GravityLayered.spatialscene `
  --fov 45 `
  --astcenc "astcenc-5.7.0-windows-x64/bin/astcenc-avx2.exe" `
  --texture-size 3072 `
  --astc-quality thorough
```
