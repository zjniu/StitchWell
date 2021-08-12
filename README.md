# StitchWell
A pure Python implementation for bulk stitching ND2 files.

## General
ND2 files acquired from Nikon Elements has metadata including the following properties: scan coordinates (x,y), channels (c), stack (z), and time (t). Extracting this information requires the open source package `nd2reader` to run.

## Installation

Install StitchWell from [PyPI](https://pypi.org/project/stitchwell/).

```
pip install stitchwell
```

## Usage

Stitch ND2 into a NumPy array.

```python
from stitchwell import StitchWell

# path: path to a ND2 file or a folder containing ND2 files
# fileIndex: index of file in a folder to stitch, leave as 0 if the path is a file
# overlap = overlap percentage used for stitching, leave as None for automatic overlap calculation
# stitchChannel = channel used for image registration adjustments (only for multichannel .nd2)

stitched = StitchWell(path).stitch(fileIndex,overlap,stitchChannel)
```

Stitch ND2 and save as TIFF.

```python
from stitchwell import StitchWell

# path: path to a ND2 file or a folder containing ND2 files
# outDir: path to output directory for saving stitched TIFF files
# overlap = overlap percentage used for stitching, leave as None for automatic overlap calculation
# stitchChannel = channel used for image registration adjustments (only for multichannel .nd2)

StitchWell(path).saveTIFF(outDir,overlap,stitchChannel)
```