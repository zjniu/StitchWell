import numpy as np

from nd2reader import ND2Reader
from pathlib import Path
from tifffile import imwrite
from tqdm.auto import tqdm


class StitchWell:

    def __init__(self, path):

        path = Path(path)

        if path.is_file():

            self.files = [path]

        elif path.is_dir():

            self.files = [file for file in path.iterdir() if
                          file.is_file() and file.suffix == '.nd2']

    def nd2Open(self, fileIndex):

        file = open(self.files[fileIndex], 'rb')
        images = ND2Reader(file)
        axes = dict(images.sizes)
        if 'v' in axes.keys():
            images.iter_axes = 'v'
            axes.pop('v')
        if axes['t'] == 1:
            axes.pop('t')
        axes = ''.join(reversed(list(axes.keys())))
        images.bundle_axes = axes

        rawMetadata = images.parser._raw_metadata

        return images, rawMetadata, axes

    def calculateTotalMargins(self, width, height):

        xTotalMargin = self.images.metadata['width'] - width
        yTotalMargin = self.images.metadata['height'] - height
        totalMargins = (xTotalMargin, yTotalMargin)

        return totalMargins

    def calculateMargins(self, width, height):

        totalMargins = self.calculateTotalMargins(width, height)

        xLeftMargin = int(np.floor(totalMargins[0] / 2))
        xRightMargin = xLeftMargin + width
        xMargins = (xLeftMargin, xRightMargin)

        yTopMargin = int(np.floor(totalMargins[1] / 2))
        yBottomMargin = yTopMargin + height
        yMargins = (yTopMargin, yBottomMargin)

        return xMargins, yMargins

    def stitch(self, fileIndex=0, overlap=0.1):

        self.images, self.rawMetadata, self.axes = self.nd2Open(fileIndex)

        if 'v' not in self.images.iter_axes:
            stitched = self.images[0].astype(np.uint16)

            return stitched

        positions = self.rawMetadata.image_metadata[b'SLxExperiment'][b'uLoopPars'][b'Points'][b'']
        coords = np.array([(position[b'dPosX'], position[b'dPosY']) for position in positions]).T

        theta = self.rawMetadata.image_metadata_sequence[b'SLxPictureMetadata'][b'dAngle']
        c, s = np.cos(theta), np.sin(theta)
        R = np.array(((c, -s), (s, c)))
        x, y = np.rint(np.dot(R, coords))

        xDim = round(np.ptp(x) / abs(x[0] - x[1])) + 1
        yDim = round(np.ptp(y) / abs(x[0] - x[1])) + 1

        xScaled = np.rint((x - min(x)) / (np.ptp(x) / (xDim - 1)))
        yScaled = np.rint((y - min(y)) / (np.ptp(y) / (yDim - 1)))

        width = round(self.images.metadata['width'] * (1 - overlap))
        height = round(self.images.metadata['height'] * (1 - overlap))
        xMargins, yMargins = self.calculateMargins(width, height)

        absDim = (*self.images.frame_shape[:-2], yDim * height, xDim * width)

        stitched = np.zeros(absDim, dtype=np.uint16)

        i = 0
        for i in tqdm(self.images.metadata['fields_of_view'], desc='Image Progress'):
            xArray = int(xScaled[i] * width)
            yArray = int(absDim[-2] - yScaled[i] * height)

            stitched[..., yArray - height:yArray, xArray:xArray + width] = self.images[i][..., yMargins[0]:yMargins[1],
                                                                           xMargins[0]:xMargins[1]]

        return stitched

    def saveTIFF(self, outDir, overlap=0.1):

        for fileIndex, file in enumerate(tqdm(self.files, desc='Total Progess')):
            stitched = self.stitch(fileIndex, overlap, stitchChannel)
            imwrite(Path(outDir).joinpath(file.with_suffix('.tif').name), stitched, metadata={'axes': self.axes},
                    ome=True, photometric='minisblack')