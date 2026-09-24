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

The sharp per-layer overscan layout is restored:

```text
1.035, 1.055, 1.085, 1.12, 1.17, 1.24
```

This keeps more effective texture resolution on upper layers while still giving
deeper layers enough hidden border for motion.

All quads now use the normal perspective geometry again; the previous horizontal
geometry stretch was removed so circular features remain circular.

The renderer motion direction is globally reversed by setting:

```text
camera.motionRange = -0.025
```

This is intended to flip both horizontal and vertical device-motion response
without introducing X/Y-specific geometry distortion.

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
