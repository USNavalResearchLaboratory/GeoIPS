# Author:
#    Naval Research Laboratory, Marine Meteorology Division
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the NRLMMD License included with this program.  If you did not
# receive the license, see http://www.nrlmry.navy.mil/geoips for more
# information.

# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# included license for more details.

__all__ = [
        "__title__", "__summary__", "__uri__", "__version__",
        "__author__", "__email__", "__license__", "__copyright__",
        "__requires__",
]


__title__ = "geoips"
__summary__ = "Geolocated Information Processing System (GeoIPS(TM))"
__uri__ = "http://www.nrlmry.navy.mil/geoips"

__version__ = "1.0.4"

__author__ = "Naval Research Laboratory Marine Meteorology Division"
__email__ = "geoips@nrlmry.navy.mil"

__license__ = "NRLMMD"
__copyright__ = "2017 %s" % __author__
__requires__ = [ 'h5py', # Anaconda
                'pygrib', # conda install -c conda-forge pygrib
                 # 'pyhdf',
                 'cftime', # Doesn't appear to automatically install for netCDF4
                 'netCDF4', # Anaconda - netcdf4 -- needs basemap first
                 'pyproj',
                 'argparse', # Doesn't appear to automatically install for msgpack
                 'msgpack', # Doesn't appear to automatically install for pyresample
                 'pyresample', # conda install -c conda-forge pyresample -- couldn't compile pykdtreeimpo
                 'memory_profiler',
                 'numpy', # Anaconda
                 'scipy', # Anaconda
                 'Pillow', # Anaconda - pillow
                 'matplotlib', # Anaconda
                 'lxml', # Anaconda
                 'ephem', # Anaconda. Didn't auto install ???
                 'geos', # needed for basemap. Didn't auto-install?
                 'numexpr',
                 'basemap', # conda install -c anaconda basemap
               ]
