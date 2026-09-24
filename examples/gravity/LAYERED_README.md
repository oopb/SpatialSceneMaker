# Layered gravity demo

This demo now uses **eight full-screen texture slices**:

- six full-screen plates with geometrically similar rounded-rectangle cut-outs;
- one full-screen plate with the preserved circular cut-out;
- one full-screen bottom image revealed through that circle.

There is no highlight / glow overlay.

## Proportional rounded openings

The first rounded opening keeps the established size:

```text
1020 x 1350, corner radius 150
```

The sixth/innermost rounded opening keeps an approximately 480 px width. The
five transitions between them use one fixed scale ratio:

```text
ratio ≈ 0.86005894
```

Therefore every rounded opening is a uniform scale of the same base shape:
width, height, corner radius, and rounded-rectangle perimeter all scale together.

The terminal circular opening is preserved:

```text
center = (645, 1465)
radius = 165
diameter = 330
```

## Layer height / depth

The total parallax depth range is restored to the earlier useful range:

```text
outer depth = 55.0
inner depth = 3.7
```

For the eight stages, relative camera-space height above the deepest stage is
mapped linearly from the perimeter of the corresponding visible window:

```text
full screen
rounded opening 1
rounded opening 2
rounded opening 3
rounded opening 4
rounded opening 5
rounded opening 6
circular opening
```

So larger-perimeter windows are higher/farther and smaller-perimeter windows are
lower/deeper, while the total motion range stays comparable to the original
55 -> 3.7 setup.

## Motion direction

Device-motion direction is restored to normal:

```text
camera.motionRange = 0.025
```

## Overscan

The eight slices use progressively larger hidden margins:

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
