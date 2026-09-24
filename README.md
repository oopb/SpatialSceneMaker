# SpatialSceneMaker

Experimental Python generator for SpatialScene V3 bundles from an RGB image and a user-supplied depth map.

> **Status:** reverse-engineering / proof of concept. The SSM3 mesh layout and SST3 container header are derived from observed SpatialSceneWallpaper samples. Output still needs renderer/device validation and this project is not an Apple-supported file-format implementation.

## What it does

- Reads an RGB image and grayscale/16-bit depth map.
- Builds camera-space geometry with depth stored as negative Z.
- Writes the reverse-engineered `SSM3` mesh container.
- Encodes a 2048x2048 ASTC 4x4 sRGB texture through ARM `astcenc`.
- Wraps raw ASTC blocks in the reverse-engineered `SST3` texture container.
- Emits a `.spatialscene` directory with `project.json` and main/backfill assets.
- Uses a conservative flat far-plane backfill for the first PoC.

## Install

```bash
python -m pip install -e .
```

Install `astcenc` separately and make sure `astcenc` (or `astcenc-avx2`) is on PATH.

## Usage

```bash
spatialscene-maker image.png depth.png -o ManualDepthTest.spatialscene --near 1 --far 10 --fov 45
```

Depth convention: white = near, black = far by default. Use `--invert-depth` to reverse it.

For a deliberately coarse first test:

```bash
spatialscene-maker image.png depth.png -o Test.spatialscene --grid-width 65 --near 1 --far 10
```

## Reverse-engineered formats

### SSM3

32-byte little-endian header:

```text
char[4]  magic = "SSM3"
u32      version = 1
u32      vertexCount
u32      indexCount
u32      triangleCount
u32      vertexStride = 32
u32      indexType = 1
u32      reserved = 0
```

Each 32-byte vertex:

```text
f32 x, y, z
f32 reserved0
f32 u, v
u32 textureSlice
u32 reserved1
```

Indices are little-endian `u32`. In observed samples, `depth = -Z`, UVs use texel-center coordinates, and `textureSlice` indexes the SST3 texture array.

### SST3

40-byte little-endian header:

```text
char[4] magic = "SST3"
u32 version = 1
u32 pixelFormat = 186
u32 width
u32 height
u32 arrayLength
u32 mipCount
u32 bytesPerRow
u32 bytesPerImage
u32 headerSize = 40
```

Observed V3 samples use Metal pixel format 186 (ASTC 4x4 sRGB), 2048x2048 slices, one mip, and raw ASTC payload immediately after the header.

## Notes

The project-specific `.ssmesh` / `.sstexture` representation is not presented here as an Apple public file-format specification. This project is intended for interoperability research and experimentation.

## License

MIT
