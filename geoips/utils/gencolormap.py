#!/bin/env python

# Author:
#    Naval Research Laboratory, Marine Meteorology Division
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the NRLMMD License included with this program.  If you did not
# receive the license, see http://www.nrlmry.navy.mil/geoips for more
# information.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# included license for more details.


# Standard Python Libraries
import os
import sys
import numpy as np


# Installed Libraries
from matplotlib import cm, colors, pyplot as plt
from matplotlib.colorbar import ColorbarBase
from IPython import embed as shell


# GeoIPS Libraries
from .plugin_paths import paths as gpaths


def cmap_discretize(cmap, N):
    """Return a discrete colormap from the continuous colormap cmap.

        cmap: colormap instance, eg. cm.jet. 
        N: number of colors.

    Example
        x = resize(arange(100), (5,100))
        djet = cmap_discretize(cm.jet, 5)
        imshow(x, cmap=djet)
    """

    if type(cmap) == str:
        cmap = get_cmap(cmap)
    colors_i = np.concatenate((np.linspace(0, 1., N), (0.,0.,0.,0.)))
    colors_rgba = cmap(colors_i)
    indices = np.linspace(0, 1., N+1)
    cdict = {}
    for ki,key in enumerate(('red','green','blue')):
        cdict[key] = [ (indices[i], colors_rgba[i-1,ki], colors_rgba[i,ki]) for i in xrange(N+1) ]
    # Return colormap object.
    return colors.LinearSegmentedColormap(cmap.name + "_%d"%N, cdict, 1024)

def write_cmap(name, r, g, b, path=None):
    '''Write a new colormap to a three column ascii file.

    ::Inputs
    `name` will be the name of the data file and the name used to call the palette.
    `r` a 256 element array of values ranging from either 0.0-1.0 or 0-255
        to be used as the red portion of the colormap
    `g` a 256 element array of values ranging from either 0.0-1.0 or 0-255
        to be used as the green portion of the colormap
    `b` a 256 element array of values ranging from either 0.0-1.0 or 0-255
        to be used as the blue portion of the colormap

    ::Outputs
    A new file in $NRLPALETTES/ascii_palettes/`name`.
    '''
    if r.shape[0] != 256 or g.shape[0] != 256 or b.shape[0] != 256:
        raise ValueError('r, g, and b arrays must be of shape (256).')

    if path is None:
        file = os.path.join(os.getenv('GEOIPS'),'geoimg', 'ascii_palettes', name)
        print 'Getting palette from '+str(file)
    else:
        file = os.path.join(path, name)
    pal = open(file, 'w')

    for cind in range(256):
        pal.write('%9.4f%9.4f%9.4f\n' % (r[cind], g[cind], b[cind]))
    pal.close()

def test_cmap(name, **kwargs):
    '''Shows a colorbar for a given colormap.'''
    fig = plt.figure(figsize=[5, 1])
    ax = fig.add_axes([0.05, 0.25, 0.9, 0.5])
    cbar = ColorbarBase(ax,
                        cmap=get_cmap(name, **kwargs),
                        extend='both',
                        orientation='horizontal',
                        ticks=[0, 1],
                        norm=colors.Normalize(vmin=0.0, vmax=1.0)
                       )
    fig.show()

def get_cmap(name, paths=[]):
    '''
    Open a colormap.

    Will search the following locations in order:
        1) Any paths specified by the paths keyword.
        2) The current working directory.
        3) $NRLPALETTES/ascii_palettes.
        4) Matplotlib default colormaps.

    If no regular file is found in those locations with the correct name,
        will look for a native matplotlib palette with the correct name.
    '''

    if name[-2:] == '_r':
        fname = name[:-2]
    else:
        fname = name

    # MLS paths is getting preserved from call to call.  So this is actually 
    # having duplicates or triplicates of  PALETTEPATHS and cwd.
    # For now use list(set(paths))....
    paths.append(os.getcwd())
    paths.extend(gpaths['PALETTEPATHS'])
    paths.extend(gpaths['TESTPALETTEPATHS'])
    paths = list(set(paths))
    print 'Using palettes directories: '+str(paths)
    #Attempt to find a user defined colormap in the above paths
    for path in paths:
        if not os.path.isdir(path):
            continue
        try:
            fullpath = os.path.join(path, fname.text)
        except AttributeError:
            fullpath = os.path.join(path, fname)
        if os.path.isfile(fullpath):
            return from_ascii(fullpath, name=name)
    #If not user defined colormap was found, look for a matplotlib colormap
    cmap = cm.get_cmap(name)
    if cmap is not None:
        return cmap
    #If no colormap found, raise an error
    raise ValueError('No colormap found for name: %s' % name)

def from_ascii(filename, name):
    '''Creates a ListedColormap instance and registers it in the current python
    session.  Note: Will have to be re-registered in all new python sessions.

    Inputs:
        filename - Full path to a three column ascii file whose contents must
                   be floats that either range from 0.0-1.0 or from 0-255.
        name - Name of the colorbar for registration and later recall.
    '''
    #Read data from ascii file into an NLines by 3 float array
    palette = open(filename)
    lines = palette.readlines()
    palette.close()
    carray = np.zeros([len(lines), 3])
    for num, line in enumerate(lines):
        carray[num, :] = [float(val) for val in line.strip().split()]

    #Normalize from 0-255 to 0.0-1.0
    if carray.max() > 1.0:
        carray /= 255.0

    #Test to be sure all color array values are between 0.0 and 1.0
    if not (carray.min() >= 0.0 and carray.max() <= 1.0):
        raise ValueError('All values in carray must be between 0.0 and 1.0.')

    if name[-2:] == '_r':
        carray = np.flipud(carray)

    #Create colormap instance and register for further use in this python session
    cmap = colors.ListedColormap(carray, name=name)
    cm.register_cmap(name=str(name), cmap=cmap)
    return cmap

if __name__ == '__main__':
    get_cmap(sys.argv[1])
