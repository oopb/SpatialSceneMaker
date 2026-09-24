# Gravity wallpaper demo

This demo recreates the *idea* of the supplied reference: a dark teal portrait wallpaper with a nested central well. The artwork is original and intentionally contains no lock-screen text or system UI.

Each nested shape has a discrete depth. The center is deepest:

| Region | Depth-map value | Intended relative depth |
| --- | ---: | --- |
| Background | 255 | nearest |
| Outer rounded rectangle | 220 | |
| Layer 2 | 185 | |
| Layer 3 | 150 | |
| Layer 4 | 115 | |
| Layer 5 | 80 | |
| Center circle | 45 | deepest |

Generate the source assets:

```powershell
python examples/gravity/make_assets.py
```

Then build the experimental bundle:

```powershell
spatialscene-maker examples/gravity/assets/gravity-wallpaper.png examples/gravity/assets/gravity-depth.png `
  -o GravityWallpaper.spatialscene `
  --near 1 --far 8 --fov 45 --grid-width 257 `
  --astcenc "C:\Tools\astcenc\astcenc-avx2.exe"
```

The current generic mesh path resamples depth, so this demo is primarily a compatibility PoC. A later edge-aware mesh path should duplicate vertices along discrete layer boundaries to produce truly vertical step walls.
