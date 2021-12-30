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

        self.images = None
        self.raw_metadata = None
        self.axes = None

    def read_nd2(self, file_index):

        file = open(self.files[file_index], 'rb')
        images = ND2Reader(file)
        axes = dict(images.sizes)
        if 'v' in axes.keys():
            images.iter_axes = 'v'
            axes.pop('v')
        if axes['t'] == 1:
            axes.pop('t')
        axes = ''.join(reversed(list(axes.keys())))
        images.bundle_axes = axes

        raw_metadata = images.parser._raw_metadata

        return images, raw_metadata, axes

    def calculate_total_margins(self, width, height):

        x_total_margin = self.images.metadata['width'] - width
        y_total_margin = self.images.metadata['height'] - height
        total_margins = (x_total_margin, y_total_margin)

        return total_margins

    def calculate_margins(self, width, height):

        total_margins = self.calculate_total_margins(width, height)

        x_left_margin = int(np.floor(total_margins[0] / 2))
        x_right_margin = x_left_margin + width
        x_margins = (x_left_margin, x_right_margin)

        y_top_margin = int(np.floor(total_margins[1] / 2))
        y_bottom_margin = y_top_margin + height
        y_margins = (y_top_margin, y_bottom_margin)

        return x_margins, y_margins

    def stitch(self, file_index=0, overlap=0.1):

        self.images, self.raw_metadata, self.axes = self.read_nd2(file_index)

        if 'v' not in self.images.iter_axes:
            stitched = self.images[0].astype(np.uint16)

            return stitched

        positions = self.raw_metadata.image_metadata[b'SLxExperiment'][b'uLoopPars'][b'Points'][b'']
        coords = np.array([(position[b'dPosX'], position[b'dPosY']) for position in positions]).T

        theta = self.raw_metadata.image_metadata_sequence[b'SLxPictureMetadata'][b'dAngle']
        c, s = np.cos(theta), np.sin(theta)
        r = np.array(((c, -s), (s, c)))
        x, y = np.rint(np.dot(r, coords))

        x_dim = round(np.ptp(x) / abs(x[0] - x[1])) + 1
        y_dim = round(np.ptp(y) / abs(x[0] - x[1])) + 1

        x_scaled = np.rint((x - min(x)) / (np.ptp(x) / (x_dim - 1)))
        y_scaled = np.rint((y - min(y)) / (np.ptp(y) / (y_dim - 1)))

        width = round(self.images.metadata['width'] * (1 - overlap))
        height = round(self.images.metadata['height'] * (1 - overlap))
        x_margins, y_margins = self.calculate_margins(width, height)

        abs_dim = (*self.images.frame_shape[:-2], y_dim * height, x_dim * width)

        stitched = np.zeros(abs_dim, dtype=np.uint16)

        for i in tqdm(self.images.metadata['fields_of_view'], desc='Image Progress'):
            x_array = int(x_scaled[i] * width)
            y_array = int(abs_dim[-2] - y_scaled[i] * height)

            stitched[..., y_array - height:y_array, x_array:x_array + width] = \
                self.images[i][..., y_margins[0]:y_margins[1], x_margins[0]:x_margins[1]]

        return stitched

    def save_tiff(self, out_dir, overlap=0.1):

        for fileIndex, file in enumerate(tqdm(self.files, desc='Total Progress')):
            stitched = self.stitch(fileIndex, overlap)
            imwrite(Path(out_dir).joinpath(file.with_suffix('.tif').name), stitched,
                    metadata={'axes': self.axes}, ome=True, photometric='minisblack')
