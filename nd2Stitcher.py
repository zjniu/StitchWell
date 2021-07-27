import cv2 as cv
import numpy as np
import os
import tifffile

from imshowFast import imshow
from imAdjust import imAdjust
from matplotlib import pyplot as plt
from nd2reader import ND2Reader
from nd2reader.parser import Parser
from skimage.registration import phase_cross_correlation
from tqdm.auto import tqdm

def nd2Open(file):

    file = open(file,'rb')
    images = ND2Reader(file)
    images.iter_axes = 'v'

    rawMetadata = Parser(file)._raw_metadata

    try:
        images.bundle_axes = 'cyx'
        images.metadata['multichannel'] = True
    except:
        images.bundle_axes = 'yx'
        images.metadata['multichannel'] = False
        pass

    return images,rawMetadata

def calculateMargins(metadata,width,height):

    xTotalMargin = metadata['width'] - width
    yTotalMargin = metadata['height'] - height
    totalMargins = (xTotalMargin,yTotalMargin)

    xLeftMargin = int(np.floor(xTotalMargin / 2))
    xRightMargin = xLeftMargin + width
    xMargins = (xLeftMargin,xRightMargin)

    yTopMargin = int(np.floor(yTotalMargin / 2))
    yBottomMargin = yTopMargin + height
    yMargins = (yTopMargin,yBottomMargin)

    return totalMargins,xMargins,yMargins

def calculateOffsets(images,frames,i1,axis,totalMargins,stitchChannel=0):

    if axis == 'x':
        axisIndex = 1
    elif axis == 'y':
        axisIndex = 0

    offsets = list()

    if images.metadata['multichannel']:
        image1 = images[i1][stitchChannel-1]
    else:
        image1 = images[i1]

    for i2 in frames[1:]:

        try:
            image1 = image2
        except:
            pass

        if images.metadata['multichannel']:
            image2 = images[i2][stitchChannel-1]
        else:
            image2 = images[i2]

        if axis == 'x':
            overlap1 = image1[:,-totalMargins[0]:]
            overlap2 = image2[:,:totalMargins[0]]
        elif axis == 'y':
            overlap1 = image1[-totalMargins[1]:,:]
            overlap2 = image2[:totalMargins[1],:]

        offset = phase_cross_correlation(overlap1,overlap2,upsample_factor=100)[0][axisIndex]
        if abs(offset) < 0.1 * totalMargins[axisIndex]:
            offsets.append(offset)
            
        i1 = i2

    return np.array(offsets)

def filter(array,m=2):

    if len(array[array > 0]) != len(array[array < 0]):
        if len(array[array > 0]) > len(array[array < 0]):
            array = array[array > 0]
        else:
            array = array[array < 0]
        
        d = np.abs(array - np.median(array))
        mdev = np.median(d)
        s = d/mdev if mdev else 0.
        
        array = array[s<m]
    else:
        array = list()

    return array

def stitch(file,stitchChannel=0,progress=True):

    images,rawMetadata = nd2Open(file)

    x,y = rawMetadata.x_data,rawMetadata.y_data

    x -= np.mean(x)
    y -= np.mean(y)

    coords = np.array((x,y))
    v = coords[:,0] - coords[:,1]
    theta = - np.arctan(v[1] / v[0])
    c,s = np.cos(theta),np.sin(theta)
    R = np.array(((c,-s),(s,c)))
    x,y = np.rint(np.dot(R, coords))

    xDim = round(np.ptp(x) / abs(x[0] - x[1])) + 1
    yDim = round(np.ptp(y) / abs(x[0] - x[1])) + 1

    xScaled = np.rint((x - min(x)) / (np.ptp(x) / (xDim - 1)))
    yScaled = np.rint((y - min(y)) / (np.ptp(y) / (yDim - 1)))

    width = round(np.ptp(x) / images.metadata['pixel_microns'] / (xDim - 1))
    height = round(np.ptp(y) / images.metadata['pixel_microns'] / (yDim - 1))

    totalMargins,xMargins,yMargins = calculateMargins(images.metadata,width,height)

    grid = np.empty((yDim,xDim),dtype=int)
    grid[:] = -1

    i = 0
    for coord in list(zip(xScaled,yScaled)):
        grid[yDim - int(coord[1]) - 1,int(coord[0])] = i
        i += 1

    middleRow = grid[round(grid.shape[0] / 2),:]
    middleCol = grid[:,round(grid.shape[0] / 2)]

    xOverlapOffsets = calculateOffsets(images,middleRow,middleRow[0],'x',totalMargins,stitchChannel)
    yOverlapOffsets = calculateOffsets(images,middleCol,middleCol[0],'y',totalMargins,stitchChannel)

    xOverlapOffsets = filter(xOverlapOffsets)
    yOverlapOffsets = filter(yOverlapOffsets)

    if len(xOverlapOffsets) > 2 and len(yOverlapOffsets) > 2:
        width = width + round(np.mean(xOverlapOffsets))
        height = height + round(np.mean(yOverlapOffsets))
        totalMargins,xMargins,yMargins = calculateMargins(images.metadata,width,height)

    if images.metadata['multichannel']:
        absDim = (len(images.metadata['channels']),yDim * height,xDim * width)
    else:
        absDim = (yDim * height,xDim * width)

    stitched = np.zeros(absDim,dtype=np.uint16)

    i = 0
    for i in tqdm(images.metadata['fields_of_view'],desc='Image Progress',leave=progress):
        xArray = int(xScaled[i] * width)
        yArray = int(absDim[-2] - yScaled[i] * height)
        if images.metadata['multichannel']:
            stitched[:,yArray - height:yArray,xArray:xArray + width] = images[i][:,yMargins[0]:yMargins[1],xMargins[0]:xMargins[1]]
        else:
            stitched[yArray - height:yArray,xArray:xArray + width] = images[i][yMargins[0]:yMargins[1],xMargins[0]:xMargins[1]]

    return stitched

def seeStitch(stitched,performance,adjustment,previewChannel=0):

    if stitched.ndim == 3:
        stitched = stitched[previewChannel-1]

    previewScale,strideScale = {'normal':(0.5,0.25),'fast':(0.25,0.5),'fancy':(1,0.25)}[performance]
    if previewScale != 1 :
        stitchedPreview = cv.resize(stitched, dsize = tuple([int(previewScale * i) for i in stitched.shape]))
        stitchedAdjusted = imAdjust(stitchedPreview,*adjustment)
    else :
        stitchedAdjusted = imAdjust(stitched,*adjustment)
    plt.figure(figsize=(6,6))
    ax = plt.subplot(1,1,1)
    imshow(strideScale,ax,stitchedAdjusted,vmin=0,vmax=255,cmap='gray')
    plt.show()

def bulkStitch(fileDir,outDir,stitchChannel=0):

    files = [file for file in os.listdir(fileDir) if os.path.isfile(os.path.join(fileDir,file)) and file.endswith('.nd2')]

    for file in tqdm(files,desc='Total Progess'):
        stitched = stitch(os.path.join(fileDir,file),stitchChannel,False)
        tifffile.imwrite(os.path.join(outDir,file.replace('.nd2','.tif')),stitched,photometric='minisblack')
