# Layered gravity demo

The layered demo now follows `examples/gravity/make_assets.py` directly instead
of maintaining a separately tuned geometry.

## Layer count

`make_assets.py` contains seven visible discrete-depth regions:

1. outer background;
2. rounded rectangle 1;
3. rounded rectangle 2;
4. rounded rectangle 3;
5. rounded rectangle 4;
6. rounded rectangle 5;
7. center circle.

The layered implementation therefore uses **seven main texture slices** plus one
backfill safety surface.

## Geometry

The five rounded rectangles are copied exactly from `make_assets.py`:

```text
margin 95,  top 720,  bottom 2190, radius 150
margin 155, top 805,  bottom 2105, radius 135
margin 220, top 900,  bottom 2010, radius 120
margin 290, top 1000, bottom 1910, radius 105
margin 365, top 1110, bottom 1800, radius 90
```

The center circle is also restored exactly:

```text
center = (645, 1455)
radius = 205
```

The layered slices are decomposed as:

- background outside rectangle 1;
- five rounded rings;
- center circle.

At rest this reconstructs the same nested proportions as `make_assets.py`.

## Depths

The same discrete depth-map grayscale values are used:

```text
255, 220, 185, 150, 115, 80, 45
```

Using the same `near=1, far=8` inverse-depth conversion as the normal gravity
demo gives:

```text
1.000000
1.136490
1.316129
1.563218
1.924528
2.503067
3.578947
```

These values match the actual depth levels found in the supplied
`GravityWallpaper.spatialscene` reference.

The backfill depth is restored to the reference value:

```text
8.4
```

## Camera direction

Commit history was checked rather than continuing to flip the sign manually:

- `ef4ee9a`: first layered implementation used positive `motionRange=0.030`;
- `e021f35` through `58da483`: stable layered period used positive
  `motionRange=0.025`;
- `8883b84`: first negative `motionRange` experiment;
- later commits alternated the sign while tuning the demo.

The supplied reference bundle itself uses:

```text
camera.motionRange = 0.035
camera.overscan = 0.015
```

The layered version now restores those exact positive reference values.

## Mesh order

The first layered implementation used outer-to-inner mesh construction. Because
the current assets are non-overlapping background/ring/disc slices rather than
full-screen opaque plates, that original order is restored:

```text
outer -> inner
```

## Texture quality

The layered builder still defaults to:

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
