# StitchWell
A pure Python implementation for bulk stitching .nd2 and saving as .tif.

## General
The .nd2 acquired from Nikon Elements has metadata including the following properties: scan coordinates (x,y), channels (c), etc. Extracting this information requires the open source package `nd2reader` to run.

## Installation

1) Create and activate conda environment. 
```
conda create -n StitchWell python
conda activate StitchWell
```
2) Install required packages.
```
conda install jupyter matplotlib nd2reader numpy opencv pyqt5 scikit-image tifffile tqdm
```
3) Clone repository.
```
git clone https://github.com/SydShafferLab/StitchWell.git
cd StitchWell
```
4) Launch Jupyter notebook and open `stitch.ipynb`.
```
jupyter notebook
```

## Modules

1) Initiate GUI (for testing and seeing stitch)
2) Test Stitch 
* `file` path to .nd2
* `stitchChannel` channel used for image registration adjustments (only for multichannel .nd2)
3) See Stitch
* `performance` preview presets (`fast`, `normal`, or `fancy`)
* `adjustment` brightness and contrast adjustment
* `previewChannel` channel used for preview (only for multichannel .nd2)
4) Bulk Stitch
* `fileDir` input directory with .nd2
* `outDir` output directory for stitched .tif
* `stitchChannel` channel used for image registration adjustments (only for multichannel .nd2)
 
## Todo
* Implement fast per frame image registration adjustments.
* Add support for .nd2 with stack (z) and timelapse (t) data.
  * Use `nd2toTiff` MATLAB script for now.
* Add options for overlap blending.
