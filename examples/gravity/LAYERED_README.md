# Layered gravity demo

The layered demo follows `examples/gravity/make_assets.py` for proportions,
colors, and depth values, but every main layer is represented as a **full-screen
image with a cut-out**.

## Layer count

The seven main layers are:

1. full-screen background plate, cut by rounded rectangle 1;
2. full-screen layer-1 color, cut by rounded rectangle 2;
3. full-screen layer-2 color, cut by rounded rectangle 3;
4. full-screen layer-3 color, cut by rounded rectangle 4;
5. full-screen layer-4 color, cut by rounded rectangle 5;
6. full-screen layer-5 color, cut by the center circle;
7. full-screen center-color bottom image, with no cut-out.

So the circular appearance of the deepest layer comes from the circular hole in
the layer above it; the deepest texture itself is still full-screen.

## Geometry

The five rounded cut-outs are copied exactly from `make_assets.py`:

```text
margin 95,  top 720,  bottom 2190, radius 150
margin 155, top 805,  bottom 2105, radius 135
margin 220, top 900,  bottom 2010, radius 120
margin 290, top 1000, bottom 1910, radius 105
margin 365, top 1110, bottom 1800, radius 90
```

The center circle is also copied exactly:

```text
center = (645, 1455)
radius = 205
```

## Depths

The same discrete depth-map grayscale values are used:

```text
255, 220, 185, 150, 115, 80, 45
```

Using the same `near=1, far=8` inverse-depth conversion as the normal gravity
demo gives the seven camera-space depths.

## Camera

The normal reference camera settings remain:

```text
camera.motionRange = 0.035
camera.overscan = 0.015
```

## Compositing order

Because every slice is a full-screen plate, the mesh order is:

```text
inner -> outer
```

The deepest full-screen image is drawn first, then progressively shallower
plates cover it except through their own cut-outs.

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
