#!/bin/env python

import os
from gilogging import setup_logging
from argparse import ArgumentParser
import numpy as np

import matplotlib
matplotlib.use('agg')

from matplotlib import pyplot as plt
from matplotlib import rcParams

from geoips.errors import GIPlotError
from geoips.utils.gencolormap import get_cmap
from geoips import geoalgs
from geoips.geoimg.mpl_utils import create_color_gun

from geoips import productfile
from geoips.scifile import SciFile

from rsync_to_slider import RsyncGeoIPSToSlider2

from IPython import embed as shell


rsync = RsyncGeoIPSToSlider2()


class Plotter(object):
    def __call__(self, df, prod, out=None):
        # Make sure the data file only has one resolution of data
        if len(df.datasets) != 1:
            raise GIPlotError('More than one dataset encountered in data file.')

        log.info('\tCreating image')
        img = self.get_image(df, prod)

        log.info('\tCreating figure and axes')
        figsize = np.array((img.shape[1], img.shape[0])) / rcParams['figure.dpi']
        fig = plt.figure(figsize=figsize)
        ax = fig.add_axes((0, 0, 1, 1))

        # Create alpha layer for RGB images
        if img.ndim == 3:
            alpha = np.array(~np.any(img.mask, axis=2), dtype=float)
            img = np.dstack([img, alpha])

        log.info('\tPlotting image on axes')
        if prod.cmap:
            cmap = get_cmap(prod.cmap)
        else:
            cmap = None
        ax.imshow(img, vmin=0.0, vmax=1.0, cmap=cmap)

        if out:
            if not os.path.isdir(os.path.dirname(out)):
                log.info('\tCreating output directory')
                os.makedirs(os.path.dirname(out))
            log.info('\tSaving image to {}'.format(out))
            fig.savefig(out, interpolation=None, transparent=True)
            log.info('\tSUCCESS')

            if os.getenv('SLIDER2RSYNC') == 'True':
                if prod.name in rsync.PRODUCT_MAP:
                    log.debug('Attempting to rsync {} imagery to slider2'.format(prod.name))
                    rsync(out)
                else:
                    log.debug('Product {} has no path for rsync.'.format(prod.name))

        return fig, ax

    def get_image(self, df, prod):
        if prod.method == 'basic':
            img = create_color_gun(df, prod.images['img'])
        elif prod.method == 'rgb':
            red = create_color_gun(df, prod.images['red'])
            grn = create_color_gun(df, prod.images['grn'])
            blu = create_color_gun(df, prod.images['blu'])
            img = np.ma.dstack((red, grn, blu))
        elif prod.method == 'external':
            method = getattr(geoalgs, prod.name.lower().replace('-', '_'))
            img = method(df, None, None, None)
        else:
            raise NotImplementedError('{} method not yet implemented'.format(prod.method))

        # Mask where sun zenith outside of appropriate range for product
        if 'SunZenith' in df.geolocation_variables:
            # SunZenith is masked off of the disk
            off_disk_mask = df.geolocation_variables['SunZenith'].mask
            if prod.day_ngt == 'day':
                zen_mask = df.geolocation_variables['SunZenith'].data > prod.day_ang
            elif prod.day_ngt == 'night':
                zen_mask = df.geolocation_variables['SunZenith'].data < prod.ngt_ang
            elif prod.day_ngt == 'both':
                zen_mask = np.zeros_like(off_disk_mask)
            else:
                raise GIPlotError('Unknown day/night option {}'.format(prod.day_ngt))
            ang_mask = np.logical_or(off_disk_mask, zen_mask)
        else:
            if prod.day_ngt != 'both':
                raise GIPlotError('No SunZenith data available.  Unable to mask day/night.')
            if img.ndim == 2:
                ang_mask = np.zeros_like(img.mask)
            elif img.ndim == 3:
                ang_mask = np.zeros_like(img.mask[:, :, 0])

        # Mask the actual data
        if np.any(ang_mask):
            if img.ndim == 2:
                if not np.any(img.mask):
                    img = np.ma.array(img, mask=ang_mask)
                else:
                    img.mask[ang_mask] = True
            elif img.ndim == 3:
                if not np.any(img.mask):
                    img = np.ma.array(img, mask=np.repeat(ang_mask[:, :, np.newaxis], 3, 2))
                else:
                    img.mask[np.repeat(ang_mask[:, :, np.newaxis], 3, 2)] = True
            else:
                GIPlotError('Image array must have either two or three dimensions. ' +
                            'Found {}'.format(img.ndim))
        return img

#     @property
#     def datafile(self):
#         return self._df
#
#     @property
#     def _dataset(self):
#         return self.datafile.datasets[self.datafile.datasets.keys()[0]]
#
#     @property
#     def product(self):
#         return self._prod
#
#     @property
#     def shape(self):
#         return self._dataset.shape
#
#     @property
#     def figsize(self):
#         dpi = rcParams['figure.dpi']
#         fs = np.array(self.shape) / dpi
#         return fs
#
#     @property
#     def fig(self):
#         self._fig = plt.figure(figsize=self.figsize)


def get_out_fname(df, prod):
    dirname = os.path.join('/mnt',
                           'geoips_images',
                           df.metadata['top']['sector_name'],
                           df.source_name,
                           prod.name)
    # dirname = os.path.join(os.path.getenv('SATOPS'),
    #                        'intermediate_files',
    #                        'GeoIPSfinal',
    #                        'Full-Disk',
    #                        df.source_name,
    #                        prod.name)
    basename = '{}.{}.{}.{}.{}.png'.format(df.start_datetime.strftime('%Y%m%d.%H%M%S'),
                                           df.platform_name,
                                           df.source_name,
                                           df.metadata['top']['sector_name'],
                                           prod.name)
    return os.path.join(dirname, basename)


def run(path, products=[]):
    log.info('Starting new file: {}'.format(path))
    # Read the metadata for the input data file or directory
    log.info('Reading metadata')
    df = SciFile()
    df.import_metadata([path])

    log.info('\tSatellite: {}'.format(df.platform_name))
    log.info('\tSource:    {}'.format(df.source_name))
    log.info('\tDate/Time: {}'.format(df.start_datetime.strftime('%Y/%m/%d %H:%M:%S')))

    # Get the available products for the input data
    prods = productfile.open2(df.source_name, products)
    if not prods:
        raise ValueError('No products found for input product list.')
    log.info('\tProducts: {}'.format(prods.productnames()))

    # Get a list of the required channels for the full set of data
    req_chans = prods.get_required_source_vars(df.source_name)
    log.debug('\tRequired Channels: {}'.format(req_chans))

    # Read the actual data
    # Reinitializing to get rid of METADATA dataset
    # This is ugly and needs to be fixed
    # Temporarily only use "LOW" resolution
    # Need to sort this out later
    log.info('Reading {}'.format(path))
    df = SciFile()
    df.import_data([path], chans=req_chans, self_register="LOW")

    # Plot the data
    log.info('Plotting data from {}'.format(path))
    plotter = Plotter()
    for prod in prods.iterproducts():
        log.info('\t{}'.format(prod.name))
        # Only do "basic" and "external" for now
        plotter(df, prod, out=get_out_fname(df, prod))
        plt.clf()


def split_on_space(string):
    '''
    Splits a string on spaces and returns a list of strings.
    '''
    return string.strip().strip('"').strip("'").split(' ')


if __name__ == '__main__':
    path_help = ('Absolute path to data to be processed. '
                 'Must either be a directory containing data files from the same '
                 'sensor and observation time or a single data file.')
    products_help = ('The name of a product or a list of space delmited product names to '
                     'be produced.')
    log_level_help = ('Minimum level of log output to be produced.')
    parser = ArgumentParser()
    parser.add_argument('path', help=path_help)
    parser.add_argument('-p', '--products', type=split_on_space, default=[], help=products_help)
    # parser.add_argument('-l', '--log_level', choices=['debug', 'info', 'warn', 'error'],
    #                     help=log_level_help)

    args = parser.parse_args()
    path = args.path
    products = args.products

    # Set up logging for the entire package
    log = setup_logging('driver_fulldisk_{}'.format(path.replace('/', '_')),
                        config_file='./logging.json', log_dir=os.getenv('LOGDIR'))

    log.info('Starting full disk processing with:\n\tPath: {}\n\tProducts: {}'.format(
        path, products))

    run(path, products)
