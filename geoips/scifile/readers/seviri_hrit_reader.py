'''
Notes:
   1) At present, this reader does not work for High Resolution Visible data, which is ignored.
      Additionally, to ease generation of geolocation fields, datasets are assumed to be square
      and centered at their sub longitude.

20170330 MLS Try to only decompress what we need (VERY filename dependent),
              make scifile and hrit channel names match (more filename dependence),
              don't try to decompress/open file for import_metadata (more filename dependence for time).
              satpy requires time to open file, and requires standard (decompressed) filenames,
              so built in filename dependence by using satpy
'''

# Python Standard Libraries
import os
import logging
from glob import glob
import numpy as np
from ..satnav import SatNav
from .hrit_reader import HritFile, HritError

# Installed Libraries

# GeoIPS Libraries
from .reader import Reader
from geoips.utils.plugin_paths import paths as gpaths

log = logging.getLogger(__name__)

# For now must include this string for automated importing of classes.
reader_class_name = 'SEVIRI_HRIT_Reader'

DONT_AUTOGEN_GEOLOCATION = False
if os.getenv('DONT_AUTOGEN_GEOLOCATION'):
    DONT_AUTOGEN_GEOLOCATION = True

GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'longterm_files/geolocation/SEVIRI')
if os.getenv('GEOLOCDIR'):
    GEOLOCDIR = os.path.join(os.getenv('GEOLOCDIR'), 'SEVIRI')

DYNAMIC_GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'intermediate_files/geolocation/SEVIRI')
if os.getenv('DYNAMIC_GEOLOCDIR'):
    DYNAMIC_GEOLOCDIR = os.path.join(os.getenv('DYNAMIC_GEOLOCDIR'), 'SEVIRI')

READ_GEOLOCDIRS = []
if os.getenv('READ_GEOLOCDIRS'):
    READ_GEOLOCDIRS = [os.path.join(pp, 'SEVIRI') for pp in os.getenv('READ_GEOLOCDIRS').split(':')]


VIS_CALIB = {'msg1': {'B01': 65.2296,
                      'B02': 73.0127,
                      'B03': 62.3715,
                      'B12': 78.7599},
             'msg2': {'B01': 65.2065,
                      'B02': 73.1869,
                      'B03': 61.9923,
                      'B12': 79.0113},
             'msg3': {'B01': 65.5148,
                      'B02': 73.1807,
                      'B03': 62.0208,
                      'B12': 78.9416},
             'msg4': {'B01': 65.2656,
                      'B02': 73.1692,
                      'B03': 61.9416,
                      'B12': 79.0035}}

IR_CALIB = {'msg1': {'B04': {'wn': 2567.330, 'a': 0.9956, 'b': 3.410},
                     'B05': {'wn': 1598.103, 'a': 0.9962, 'b': 2.218},
                     'B06': {'wn': 1362.081, 'a': 0.9991, 'b': 0.478},
                     'B07': {'wn': 1149.069, 'a': 0.9996, 'b': 0.179},
                     'B08': {'wn': 1034.343, 'a': 0.9999, 'b': 0.060},
                     'B09': {'wn': 930.647, 'a': 0.9983, 'b': 0.625},
                     'B10': {'wn': 839.660, 'a': 0.9988, 'b': 0.397},
                     'B11': {'wn': 752.387, 'a': 0.9981, 'b': 0.578}},
            'msg2': {'B04': {'wn': 2568.832, 'a': 0.9954, 'b': 3.438},
                     'B05': {'wn': 1600.548, 'a': 0.9963, 'b': 2.185},
                     'B06': {'wn': 1360.330, 'a': 0.9991, 'b': 0.470},
                     'B07': {'wn': 1148.620, 'a': 0.9996, 'b': 0.179},
                     'B08': {'wn': 1035.289, 'a': 0.9999, 'b': 0.056},
                     'B09': {'wn': 931.700, 'a': 0.9983, 'b': 0.640},
                     'B10': {'wn': 836.445, 'a': 0.9988, 'b': 0.408},
                     'B11': {'wn': 751.792, 'a': 0.9981, 'b': 0.561}},
            'msg3': {'B04': {'wn': 2547.771, 'a': 0.9915, 'b': 2.9002},
                     'B05': {'wn': 1595.621, 'a': 0.9960, 'b': 2.0337},
                     'B06': {'wn': 1360.377, 'a': 0.9991, 'b': 0.4340},
                     'B07': {'wn': 1148.130, 'a': 0.9996, 'b': 0.1714},
                     'B08': {'wn': 1034.715, 'a': 0.9999, 'b': 0.0527},
                     'B09': {'wn': 929.842, 'a': 0.9983, 'b': 0.6084},
                     'B10': {'wn': 838.659, 'a': 0.9988, 'b': 0.3882},
                     'B11': {'wn': 750.653, 'a': 0.9982, 'b': 0.5390}},
            'msg4': {'B04': {'wn': 2555.280, 'a': 0.9916, 'b': 2.9438},
                     'B05': {'wn': 1596.080, 'a': 0.9959, 'b': 2.0780},
                     'B06': {'wn': 1361.748, 'a': 0.9990, 'b': 0.4929},
                     'B07': {'wn': 1148.130, 'a': 0.9996, 'b': 0.1731},
                     'B08': {'wn': 1034.851, 'a': 0.9998, 'b': 0.0597},
                     'B09': {'wn': 931.122, 'a': 0.9983, 'b': 0.6256},
                     'B10': {'wn': 839.113, 'a': 0.9988, 'b': 0.4002},
                     'B11': {'wn': 748.585, 'a': 0.9981, 'b': 0.5635}}}


class XritError(Exception):
    def __init__(self, msg, code=None):
        self.code = code
        self.value = msg

    def __str__(self):
        if self.code:
            return '{}: {}'.format(self.code, self.value)
        else:
            return self.value


def compare_dicts(d1, d2, skip=None):
    '''
    Compare the values in two dictionaries
    If they are equal, return True, otherwise False
    If skip is set and contains one of the keys, skip that key
    '''
    if d1.keys() != d2.keys():
        return False

    for key in d1.keys():
        if skip and key in skip:
            continue
        if d1[key] != d2[key]:
            return False
    return True


def get_top_level_metadata(fnames, sect):
    for fname in fnames:
        df = HritFile(fname)
        if 'block_2' in df.metadata.keys():
            break
    md = {}
    if 'GEOS' in df.metadata['block_2']['projection']:
        md['sector_name'] = 'Full-Disk'
    else:
        raise HritError('Unknown projection encountered: {}'.format(df.metadata['block_2']['projection']))
    md['start_datetime'] = df.start_datetime
    md['end_datetime'] = df.start_datetime
    md['data_provider'] = 'nesdisstar'
    # MLS Check platform_name
    # Turn msg4_iodc into msg4.  Then pull geoips satname (meteoEU/meteoIO) 
    # from utils/satellite_info.py
    msg_satname = df.annotation_metadata['platform'].lower().replace('_iodc','')
    # Save actual satellite name (msg1 / msg4) for the coefficient tables above.
    # geoips specific platform_name should be meteoEU or meteoIO
    md['satellite_name'] = msg_satname
    from geoips.utils.satellite_info import open_satinfo
    try:
        satinfo = open_satinfo(msg_satname)
        if hasattr(satinfo, 'geoips_satname'):
            msg_satname = satinfo.geoips_satname
    except KeyError:
        raise HritError('Unknown satname encountered: {}'.format(msg_satname))
    md['platform_name'] = msg_satname
    md['source_name'] = 'seviri'
    md['sector_definition'] = sect
    md['NO_GRANULE_COMPOSITES'] = True
    md['SECTOR_ON_READ'] = True

    return md


def get_low_res_geolocation_args(prologue):
    sensor = 'seviri'
    scan_mode = prologue['imageDescription']['projectionDescription']['typeOfProjection']
    lon0 = prologue['imageDescription']['projectionDescription']['longitudeOfSSP']
    num_lines = prologue['imageDescription']['referenceGridVIS_IR']['numberOfLines']
    num_samples = prologue['imageDescription']['referenceGridVIS_IR']['numberOfColumns']
    line_scale = -13642337  # This will only work for low resolution data
    sample_scale = -13642337
    line_offset = num_lines / 2
    sample_offset = num_samples / 2
    start_datetime = prologue['imageAcquisition']['plannedAcquisitionTime']['trueRepeatCycleStart']
    return [sensor, scan_mode, lon0, num_lines, num_samples, line_scale, sample_scale,
            line_offset, sample_offset, start_datetime]


def countsToRad(counts, slope, offset):
    rad = np.full_like(counts, -999.0)
    rad[counts > 0] = offset + (slope * counts[counts > 0])
    return rad


def radToRef(rad, sun_zen, platform, band):
    irrad = VIS_CALIB[platform][band]
    ref = np.full_like(rad, -999.0)
    ref[rad > 0] = rad[rad > 0] * 100.0 / irrad
    ref[rad > 0] = np.pi * rad[rad > 0] / (irrad * np.cos((np.pi / 180) * sun_zen[rad > 0]))
    ref[ref < 0] = 0
    ref[ref > 100] = 100
    ref[sun_zen > 90] = -999.0
    ref[sun_zen <= -999] = -999.0
    return ref


def radToBT(rad, platform, band):
    c1 = 1.19104e-05
    c2 = 1.43877
    wn = IR_CALIB[platform][band]['wn']
    a = IR_CALIB[platform][band]['a']
    b = IR_CALIB[platform][band]['b']
    temp = np.full_like(rad, -999.0)
    temp[rad > 0] = ((c2 * wn) / np.log(1 + wn**3 * c1 / rad[rad > 0]) - b) / a
    return temp


class Chan(object):
    _good_names = ['B01Rad', 'B01Ref',
                   'B02Rad', 'B02Ref',
                   'B03Rad', 'B03Ref',
                   'B04Rad', 'B04BT',
                   'B05Rad', 'B05BT',
                   'B06Rad', 'B06BT',
                   'B07Rad', 'B07BT',
                   'B08Rad', 'B08BT',
                   'B09Rad', 'B09BT',
                   'B10Rad', 'B10BT',
                   'B11Rad', 'B11BT']

    def __init__(self, name):
        if 'B12' in name:
            raise HritError('Channel 12 (High Resolution Visible) currently not handled.')
        if name not in self._good_names:
            raise ValueError('Unknown channel name: {}'.format(name))
        self._name = name
        self._band = name[0:3]
        self._type = name[3:]

    @property
    def name(self):
        return self._name

    @property
    def band(self):
        return self._band

    @property
    def band_num(self):
        return int(self._band[1:])

    @property
    def type(self):
        return self._type


class ChanList(object):
    def __init__(self, chans):
        chans = set(chans)
        self._info = {'chans': [Chan(chan) for chan in chans]}
        self._info['names'] = list(set([chan.name for chan in self.chans]))
        self._info['bands'] = list(set([chan.band for chan in self.chans]))
        self._info['types'] = list(set([chan.type for chan in self.chans]))

    @property
    def chans(self):
        return self._info['chans']

    @property
    def names(self):
        return self._info['names']

    @property
    def bands(self):
        return self._info['bands']

    @classmethod
    def _all_types_for_bands(cls, bands):
        good_names = Chan._good_names
        chans = set()
        for chan in good_names:
            for band in bands:
                if band in chan:
                    chans.add(chan)
        return cls(chans)


class SEVIRI_HRIT_Reader(Reader):
    dataset_info = {'LOW': ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B10', 'B11'],
                    'HIGH': ['HRV'],
                    }

    @staticmethod
    def format_test(path):
        # MLS Temporary until we completely replace msg_hrit_reader.py
        # return False
        if not os.path.isdir(path):
            return False

        # Test reading block_4/annotation and ensure that it contains "MSG"
        singlefname = glob('{}/*'.format(path))[0]
        if os.path.basename(singlefname) == 'DONE':
            singlefname = glob('{}/*'.format(path))[1]

        # First three bytes should be >u1 equal to 0 and >u2 equal to 16
        # This should catch any non-hrit files
        df = open(singlefname, 'r')
        if np.fromfile(df, dtype='>u1', count=1)[0] != 0:
            return False
        if np.fromfile(df, dtype='>u2', count=1)[0] != 16:
            return False

        # This will attempt to read the hrit file and check the platform name
        try:
            df = HritFile(singlefname)
        except Exception:
            return False
        try:
            if 'MSG' in df.metadata['block_4']['annotation']:
                return True
        except KeyError:
            pass
        return False

    def read(self, path, datavars, gvars, metadata, chans=None,
             sector_definition=None, self_register=False):
        if os.path.isdir(path):
            fnames = glob(os.path.join(path, '*'))
        else:
            raise ValueError('Input path must be a directory')

        # Remove any HRV files from file list
        # See note 1 at top of module
        fnames = [fname for fname in fnames if not any(val in fname for val in ['HRV'])]

        # Check inputs
        if self_register and self_register != 'LOW':
            raise XritError('Unknown resolution supplied to self_register: {}'.format(self_register))
        if sector_definition:
            try:
                adname = sector_definition.name
            except AttributeError:
                TypeError('Keyword sector_definition must be of type Sector.')
        else:
            adname = 'FULL_DISK'

        # Gather top-level metadata. MUst pass ALL fnames to make sure we 
 		# use a datafile, and not pro or epi (they do not contain projection 
		# information)
        metadata['top'] = get_top_level_metadata(fnames, sector_definition)

        # chans == [] specifies we don't want to read ANY data, just metadata.
        # chans == None specifies that we are not specifying a channel list,
        #               and thus want ALL channels.
        if chans == []:
            # If NO CHANNELS were specifically requested, just return at this
            # point with the metadata fields populated. A dummy SciFile dataset
            # will be created with only metadata. This is for checking what
            # platform/source combination we are using, etc.
            return

        # Create file objects for each input file and organize
        dfs = {}
        pro = None
        epi = None
        sdt = None
        imgf = None
        all_segs = set()
        for fname in fnames:
            df = HritFile(fname)
            # Ensure all files have same start datetime
            if not sdt:
                sdt = df.start_datetime
            if df.start_datetime != sdt:
                raise HritError('Start date time does not match for all files in path: {}'.format(path))
            # Get prologue
            if df.file_type == 'prologue':
                pro = df.prologue
                metadata['top']['prologue'] = pro
            # Get epilogue
            elif df.file_type == 'epilogue':
                epi = df.epilogue
                metadata['top']['epilogue'] = epi
            # Store data files, organized by band, then segment
            elif df.file_type == 'image':
                # Ensure all files have the same geolocation information
                if not imgf:
                    imgf = df
                if not compare_dicts(imgf.geolocation_metadata, df.geolocation_metadata,
                                     skip=['line_offset', 'sample_offset']):
                    raise HritError(
                        'Geolocation metadata do not match for image files found in path: {}'.format(path))
                # Initialize band info with None for eight segments
                if df.band not in dfs:
                    dfs[df.band] = {num: None for num in range(1, 9)}
                dfs[df.band][df.segment] = df
                all_segs.add(df.segment)
            else:
                log.warning('Unhandled file type encountered: {}'.format(df.file_type))
        if not pro:
            raise HritError('No prologue file found')

        # If specific channels were requested, check them against the input data
        if chans:
            chlist = ChanList(chans)
            for chan in chlist.chans:
                if chan.band not in dfs.keys():
                    raise ValueError('Requested channel {} not found in input data.'.format(chan.name))
        # If no specific channels were requested, get everything
        else:
            chlist = ChanList._all_types_for_bands(dfs.keys())

        # Gather geolocation data
        # Assume the datetime is the same for all resolution.  Not true, but close enough.
        # This saves us from having slightly different solar angles for each channel.
        geoloc_args = get_low_res_geolocation_args(pro)
        gvars[adname] = SatNav(*geoloc_args).get_geolocation(sector_definition)

        # Drop files for channels other than those requested and decompress
        outdir = os.path.join(gpaths['LOCALSCRATCH'],
                              metadata['top']['source_name'],
                              metadata['top']['satellite_name'],
                              metadata['top']['start_datetime'].strftime('%Y%m%d%H%M'))
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        for band in dfs.keys():
            if band not in chlist.bands:
                dfs.pop(band)
            else:
                dfs[band] = {seg: df.decompress(outdir) for seg, df in dfs[band].items()}

        # Create data arrays for requested data and read count data
        num_lines = pro['imageDescription']['referenceGridVIS_IR']['numberOfLines']
        num_samples = pro['imageDescription']['referenceGridVIS_IR']['numberOfColumns']
        count_data = {}
        annotation_metadata = {}
        for band in chlist.bands:
            # Create empty full-disk array for this channel
            data = np.full((num_lines, num_samples), -999.9, dtype=np.float)
            # Read data into data array
            for seg, df in dfs[band].items():
                seg_num_lines = df.metadata['block_1']['num_lines']
                start_line = seg_num_lines * (seg - 1)
                end_line = seg_num_lines * seg
                data[start_line:end_line, 0:] = df._read_image_data()
            log.info('Read band %s %s'%(band, df.annotation_metadata['band']))
            if 'Lines' in gvars[adname]:
                count_data[band] = data[gvars[adname]['Lines'], gvars[adname]['Samples']]
            else:
                count_data[band] = data
            annotation_metadata[band] = df.annotation_metadata

        datavars[adname] = {}
        radiances = {}
        image_cal = pro['radiometricProcessing']['level15ImageCalibration']
        for chan in chlist.chans:
            counts = count_data[chan.band]
            if chan.band not in radiances:
                band_cal = image_cal[chan.band_num - 1]
                offset = band_cal['offset']
                slope = band_cal['slope']
                radiances[chan.band] = countsToRad(counts, slope, offset)
            if chan.type == 'Rad':
                datavars[adname][chan.name] = radiances[chan.band]
            if chan.type == 'Ref':
                log.info('Calculating reflectances for %s'%(chan.band))
                datavars[adname][chan.name] = radToRef(radiances[chan.band],
                                                       gvars[adname]['SunZenith'],
                                                       metadata['top']['satellite_name'],
                                                       chan.band)
            if chan.type == 'BT':
                log.info('Calculating brightness temperatures for %s'%(chan.band))
                datavars[adname][chan.name] = radToBT(radiances[chan.band],
                                                      metadata['top']['satellite_name'],
                                                      chan.band)
            if adname not in metadata['datavars'].keys():
                metadata['datavars'][adname] = {}
            if chan.name not in metadata['datavars'].keys():
                metadata['datavars'][adname][chan.name] = {}

            metadata['datavars'][adname][chan.name]['wavelength'] = float(annotation_metadata[chan.band]['band'][3:4]+'.'+annotation_metadata[chan.band]['band'][4:])

        for var in datavars[adname].keys():
            datavars[adname][var] = np.ma.masked_less_equal(np.flipud(datavars[adname][var]), -999)
        for var in gvars[adname].keys():
            gvars[adname][var] = np.ma.masked_less_equal(np.flipud(gvars[adname][var]), -999)
