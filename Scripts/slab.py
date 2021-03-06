import os
import glob
import msgpack
import cPickle as pickle
import collections
import numpy as np
import scipy as sp
import nibabel as nib
import matplotlib.pyplot as plt
from scipy import stats
from scipy.ndimage import label, generate_binary_structure
import errno


def get_colors(inp,colormap,vmin=None,vmax=None):
	norm = plt.Normalize(vmin,vmax)
	return colormap(norm(inp))

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def LoadPermResults(path,name,method,idx):
    if method=='msgpack':
        with open(os.path.join(path,name+'.mpac')) as f:
            data = msgpack.load(f)[idx]
    else:
        with open(os.path.join(path,name+'.pickle')) as f:
            data = pickle.load(f)[idx]
    return data

def SavePermResults(path,name,method,*args):
    data = []
    for thing in enumerate(args):
        data.append(thing)
    if method=='msgpack':
        with open(os.path.join(path,name+'.mpac'),'wb') as f:
            msgpack.dump(data,f)
    else:
        with open(os.path.join(path,name+'.pickle'),'wb') as f:
            pickle.dump(data,f)

def CalculatePermutation(flatdata, design, mask, thresh, i):
    permflatdata = SimpleGLM(flatdata,design[:,i])[0]
    permdata = UnflattenandUnmask(permflatdata,mask)
    cci = ClusterizeImage(permdata,thresh)
    unique, counts = np.unique(cci,return_counts=True)
    return sorted(counts[1:])

def CalculateSinglePermutation(flatdata,design,mask,thresh):
    permflatdata = SimpleGLM(flatdata,design)[0]
    permdata = UnflattenandUnmask(permflatdata,mask)
    cci = ClusterizeImage(permdata,thresh)
    unique, counts = np.unique(cci,return_counts=True)
    return sorted(counts[1:])

def flatten(l):
    for el in l:
        if isinstance(el,collections.Iterable) and not isinstance(el,basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el

def ClusterizeImage(image,thresh=None,connectivity=3):
    if thresh is None:
        thresh = 0
    image[np.where(image<=thresh)] = 0
    s = generate_binary_structure(3,connectivity)
    larray, nf = label(image,s)
    return larray

def LoadImageList(path,pattern='*.nii.gz'):
    files = glob.glob(os.path.join(path,pattern))
    data = []
    dim = []
    for i in xrange(0,len(files)):
        tempnii = nib.load(files[i])
        dim = tempnii.shape
        if i==0:
            data = tempnii.get_data()
        elif i==1:
            data = np.stack((data,tempnii.get_data()),axis=3)
        else:
            data = np.concatenate((data[...],tempnii.get_data()[...,np.newaxis]),axis=3)
    return data, dim

def FlattenandMask(data,mask=None):    
    if mask is None:
        mask = np.ones(data.shape[0:3])
    dx = data.shape[0]
    dy = data.shape[1]
    dz = data.shape[2]
    n  = data.shape[3]
    rdata = np.reshape(data,(dx*dy*dz,n))
    rmask = np.reshape(mask,(dx*dy*dz,1))
    return np.transpose(rdata[np.nonzero(rmask)[0],:])

def UnflattenandUnmask(flatdata,mask):
    dx = mask.shape[0]
    dy = mask.shape[1]
    dz = mask.shape[2]
    unmasked = np.zeros((1,dx*dy*dz))
    flatmask = np.reshape(mask,(1,dx*dy*dz))
    unmasked[np.nonzero(flatmask)] = flatdata
    data = np.reshape(unmasked,(dx,dy,dz))
    return data

def SimpleGLM(Y,X=None):
    if X is None:
        X = np.ones((Y.shape[0],1))
    nFeat = Y.shape[1]
    nSub = Y.shape[0]
    nPred = X.shape[1]
    Y = np.matrix(Y)
    X = np.matrix(X)
    b = (X.T*X).I*X.T*Y
    pred = X*b
    res = Y-pred
    C = (X.T*X).I
    xvar_inv = np.diag(C)
    xvar_inv = np.tile(xvar_inv,(1,nFeat))
    sse = np.sum(np.multiply(res,res),axis=0)/(nSub-nPred)
    bSE = np.sqrt(np.multiply(xvar_inv,sse))
    t = b / bSE
    return t,b,pred,res

