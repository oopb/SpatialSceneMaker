# Layered gravity demo

This demo uses six full-screen texture slices:

- four full-screen plates with rounded-rectangle cut-outs;
- one full-screen plate with a circular cut-out;
- one full-screen bottom image.

Every visual layer has the same outer extent. Nested depth is created only by
cut-outs and painter order.

## Opening sizes

```text
opening 1   x=135..1155, y=790..2140, radius=150
opening 2   x=210..1080, y=900..2030, radius=130
opening 3   x=300..990,  y=1030..1900, radius=108
opening 4   x=405..885,  y=1180..1750, radius=82
final hole  circle radius=165
```

## No highlight overlay

All per-layer highlight / glow effects are disabled in this revision.

- cut-out edges are sharp alpha boundaries;
- plate faces are flat colors;
- the bottom full-screen image has no center glow.

This isolates texture sharpness and parallax geometry from lighting effects.

## Depth proportional to window size

Each stage is assigned a linear window-size metric:

```text
linear size = sqrt(window area)
```

For the final circular window, the diameter is used directly. The six stage
windows are:

```text
full screen
rounded opening 1
rounded opening 2
rounded opening 3
rounded opening 4
final circular opening
```

The outer full-screen stage remains at depth `55.0`. Every other main-layer
depth is obtained by multiplying its linear window size by the same constant.
The current generated values are approximately:

```text
55.000
33.983
28.714
22.438
15.148
 9.557
```

So the depth ratios now exactly follow the ratios of the corresponding window
linear sizes instead of using hand-tuned depth values.

## Overscan

The sharper per-layer overscan layout remains:

```text
1.035, 1.055, 1.085, 1.12, 1.17, 1.24
```

## Motion direction

The renderer motion direction remains globally reversed:

```text
camera.motionRange = -0.025
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
