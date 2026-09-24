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

## Highlight direction

The current version restores the earlier highlight behavior:

- the highlight belongs to the **current plate**;
- brightness rises softly as the plate approaches its own cut-out edge;
- there is no dark shadow;
- two blur scales are combined so the transition is broad and soft rather than
  a hard glowing outline.

## Parallax geometry

All six visual layers now use the **same overscan**:

```text
1.24, 1.24, 1.24, 1.24, 1.24, 1.24
```

This is deliberate. The previous version used different overscan values per
layer, which meant deeper layers were also physically larger quads. That mixed
geometry scaling with depth-based parallax and could make horizontal and
vertical tilt behave differently.

Now layer-to-layer motion is controlled only by camera-space depth:

```text
outer/top     55.0   -> smallest motion
              28.0
              15.0
               8.5
               5.2
center/bottom  3.7   -> largest motion
```

With standard perspective motion, smaller camera-space depth should produce
larger displacement on both X and Y axes. This is the normal geometry path; no
post-process X-only scaling or per-axis helper is used.

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
