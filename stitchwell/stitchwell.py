import numpy as np
import os

from nd2reader import ND2Reader
from nd2reader.parser import Parser
from skimage.registration import phase_cross_correlation
from tifffile import imwrite
from tqdm.auto import tqdm

class StitchWell:

    def __init__(self,path):

        if os.path.isfile(path):

            self.fileDir = os.path.dirname(path)
            self.files = [os.path.basename(path)]

        elif os.path.isdir(path):
            
            self.fileDir = path
            self.files = [file for file in os.listdir(path) if os.path.isfile(os.path.join(path,file)) and file.endswith('.nd2')]

    def nd2Open(self,fileIndex):

        file = open(os.path.join(self.fileDir,self.files[fileIndex]),'rb')
        images = ND2Reader(file)
        axes = dict(images.sizes)
        axes.pop('v')
        if axes['t'] == 1:
            axes.pop('t')
        axes = ''.join(reversed(list(axes.keys())))
        images.bundle_axes = axes
        images.iter_axes = 'v'

        rawMetadata = Parser(file)._raw_metadata

        return images,rawMetadata,axes

    def calculateTotalMargins(self,width,height):

        xTotalMargin = self.images.metadata['width'] - width
        yTotalMargin = self.images.metadata['height'] - height
        totalMargins = (xTotalMargin,yTotalMargin)

        return totalMargins

    def calculateMargins(self,width,height):

        totalMargins = self.calculateTotalMargins(width,height)

        xLeftMargin = int(np.floor(totalMargins[0] / 2))
        xRightMargin = xLeftMargin + width
        xMargins = (xLeftMargin,xRightMargin)

        yTopMargin = int(np.floor(totalMargins[1] / 2))
        yBottomMargin = yTopMargin + height
        yMargins = (yTopMargin,yBottomMargin)

        return xMargins,yMargins

    def calculateOffsets(self,frames,i1,axis,stitchChannel):

        if axis == 'x':
            axisIndex = 1
        elif axis == 'y':
            axisIndex = 0

        offsets = list()

        if 'c' in self.axes:
            image1 = np.take(self.images[i1],stitchChannel,self.axes.find('c'))
        else:
            image1 = self.images[i1]

        while image1.ndim > 2:
            image1.take(0,0)

        for i2 in frames[1:]:

            try:
                image1 = image2
            except:
                pass

            if 'c' in self.axes:
                image2 = np.take(self.images[i2],stitchChannel,self.axes.find('c'))
            else:
                image2 = self.images[i2]

            while image2.ndim > 2:
                image2.take(0,0)

            if axis == 'x':
                overlap1 = image1[:,-self.totalMargins[0]:]
                overlap2 = image2[:,:self.totalMargins[0]]
            elif axis == 'y':
                overlap1 = image1[-self.totalMargins[1]:,:]
                overlap2 = image2[:self.totalMargins[1],:]

            offset = phase_cross_correlation(overlap1,overlap2,upsample_factor=100)[0][axisIndex]
            if abs(offset) < 0.1 * self.totalMargins[axisIndex]:
                offsets.append(offset)
                
            i1 = i2
            
        offsets = np.array(offsets)

        if len(offsets[offsets > 0]) != len(offsets[offsets < 0]):
            if len(offsets[offsets > 0]) > len(offsets[offsets < 0]):
                offsets = offsets[offsets > 0]
            else:
                offsets = offsets[offsets < 0]
            
            d = np.abs(offsets - np.median(offsets))
            mdev = np.median(d)
            s = d/mdev if mdev else 0.
            
            offsets = offsets[s < 2]
        else:
            offsets = list()

        return offsets

    def stitch(self,fileIndex,overlap=None,stitchChannel=0):

        self.images,self.rawMetadata,self.axes = self.nd2Open(fileIndex)

        positions = self.rawMetadata.image_metadata[b'SLxExperiment'][b'uLoopPars'][b'Points'][b'']
        coords = np.array([(position[b'dPosX'],position[b'dPosY']) for position in positions]).T
        
        theta = self.rawMetadata.image_metadata_sequence[b'SLxPictureMetadata'][b'dAngle']
        c,s = np.cos(theta),np.sin(theta)
        R = np.array(((c,-s),(s,c)))
        x,y = np.rint(np.dot(R, coords))

        xDim = round(np.ptp(x) / abs(x[0] - x[1])) + 1
        yDim = round(np.ptp(y) / abs(x[0] - x[1])) + 1

        xScaled = np.rint((x - min(x)) / (np.ptp(x) / (xDim - 1)))
        yScaled = np.rint((y - min(y)) / (np.ptp(y) / (yDim - 1)))

        if overlap == None:

            width = round(np.ptp(x) / self.images.metadata['pixel_microns'] / (xDim - 1))
            height = round(np.ptp(y) / self.images.metadata['pixel_microns'] / (yDim - 1))

            self.totalMargins = self.calculateTotalMargins(width,height)

            grid = np.empty((yDim,xDim),dtype=int)
            grid[:] = -1

            i = 0
            for coord in list(zip(xScaled,yScaled)):
                grid[yDim - int(coord[1]) - 1,int(coord[0])] = i
                i += 1

            rotation = self.rawMetadata.image_metadata_sequence[b'SLxPictureMetadata'][b'sPicturePlanes'][b'sSampleSetting'][b'a0'][b'pCameraSetting'][b'PropertiesFast'][b'Rotate']

            np.rot90(grid,round((180 - rotation) / 2))

            middleRow = grid[round(grid.shape[0] / 2),:]
            middleCol = grid[:,round(grid.shape[0] / 2)]

            xOverlapOffsets = self.calculateOffsets(middleRow,middleRow[0],'x',stitchChannel)
            yOverlapOffsets = self.calculateOffsets(middleCol,middleCol[0],'y',stitchChannel)

            if len(xOverlapOffsets) > 2 and len(yOverlapOffsets) > 2:
                width = width + round(np.mean(xOverlapOffsets))
                height = height + round(np.mean(yOverlapOffsets))

            xMargins,yMargins = self.calculateMargins(width,height)

        else:

            width = round(self.images.metadata['width'] * (1 - overlap))
            height = round(self.images.metadata['height'] * (1 - overlap))
            xMargins,yMargins = self.calculateMargins(width,height)

        absDim = (*self.images.frame_shape[:-2],yDim * height,xDim * width)

        stitched = np.zeros(absDim,dtype=np.uint16)

        i = 0
        for i in tqdm(self.images.metadata['fields_of_view'],desc='Image Progress'):

            xArray = int(xScaled[i] * width)
            yArray = int(absDim[-2] - yScaled[i] * height)

            stitched[...,yArray - height:yArray,xArray:xArray + width] = self.images[i][...,yMargins[0]:yMargins[1],xMargins[0]:xMargins[1]]

        return stitched

    def saveTIFF(self,outDir,overlap=None,stitchChannel=0):

        for fileIndex,file in enumerate(tqdm(self.files,desc='Total Progess')):
            stitched = self.stitch(fileIndex,overlap,stitchChannel)
            imwrite(os.path.join(outDir,file.replace('.nd2','.tif')),stitched,metadata={'axes':self.axes},ome=True,photometric='minisblack')