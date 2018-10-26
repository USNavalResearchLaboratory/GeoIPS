# Python Standard Libraries
import logging
import os
from datetime import datetime,timedelta
from subprocess import Popen, PIPE
from operator import mul
from math import floor, ceil
import sys
import string


# Installed Libraries
from IPython import embed as shell
# If this reader is not installed on the system, don't fail altogether, just skip this import. This reader will
# not work if the import fails, and the package will have to be installed to process data of this type.
try: import pygrib as pg
except: print 'Failed import netCDF4 in scifile/readers/amsr2_ncdf4_reader.py. If you need it, install it.'
import numpy as np


# GeoIPS Libraries
from .reader import Reader
from ..containers import _empty_varinfo
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.satellite_info import SatSensorInfo

log = logging.getLogger(__name__)

# For now must include this string for automated importing of classes.
reader_class_name = 'COAMPSIEEE_BINARY_Reader'
class COAMPSIEEE_BINARY_Reader(Reader):

    dataset_info = { 'DATA': {'wwwind':'wwwind',
                              'pottmp':'pottmp',
                              'uuwind':'uuwind',
                              'vvwind':'vvwind',
                              'relhum':'relhum',
                              'wvapor':'wvapor',
                              'cldlwp':'cldlwp',
                              'cldmix':'cldmix',
                              'icemix':'icemix',
                              'grdtmp':'grdtmp',
                              'seatmp':'seatmp',
                              'airtmp':'airtmp',
                              'lndsea':'lndsea',
                              'grdwet':'grdwet',
                              'seaice':'seaice',
                              'albedo':'albedo',
                              'cte_sa':'cte_sa',
                            },
                   }
    gvar_info = { 'DATA': {
                         'Latitude': 'latitu',
                         'Longitude': 'longit',
                        },
                }

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        df = open(fname,'rb')
        if os.path.isdir(fname):
            return False

        # Check that this file is grib first
        from ..file_format_tests import bin_format_test
        if not bin_format_test(fname):
            return False
        #return True
        
        if '3a' in fname:
            return True
        #return False
        
    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):

        class data_grid:
            #indir='devnull'...this looks for the directory that the file is in
            dtg='9999999999'
            mapvars={}
            nz=0
            nzp1=0
            nnest=0
            delx0=0
            dely0=0
            nest=[0]
        
        class Nest(object):
            def __init__(self, nx, ny, ii, jj, iref, jref, tcmx, tcmy, delx, dely):
                self.nx   = nx
                self.ny   = ny
                self.ii   = ii
                self.jj   = jj
                self.iref = iref
                self.jref = jref
                self.tcmx = tcmx
                self.tcmy = tcmy
                self.delx = delx
                self.dely = dely
        
        # define the model grid
        model_grid={}
        model_grid['im'] =  277
        model_grid['jm'] =  229
        model_grid['lm'] =  60
        model_grid['num_bytes'] = model_grid['im'] * model_grid['jm'] * 4
        
        #Constant files for geolocation and header
        latitude = '/SATPROJECT/users/projects3/users/laflash/outdirs/nrtdata/realtime/longterm_files/COAMPS_metadata/latitu_sfc_000000_000000_3a0277x0229_2018092400_00000000_fcstfld'
        longitude = '/SATPROJECT/users/projects3/users/laflash/outdirs/nrtdata/realtime/longterm_files/COAMPS_metadata/longit_sfc_000000_000000_3a0277x0229_2018092400_00000000_fcstfld'
        header = '/SATPROJECT/users/projects3/users/laflash/outdirs/nrtdata/realtime/longterm_files/COAMPS_metadata/datahd_sfc_000000_000000_1a2000x0001_2018090918_00000000_infofld'
        #def main(file, lat_file, lon_file, cdtg, fld, level, model_grid, image_dir):
        #    istat = 0
        #    lat, istat = seek_field(lat_file, model_grid, 1)
        #    lon, istat = seek_field(lon_file, model_grid, 1)
        #
        #    data, stat = seek_field(file, model_grid, level)
        #
        #    title = ( "%s lvl:%.2i %s %s" % (fld.upper(), int(level), cdtg, tau) )
        #    level_name = ( "l%.2i" % int(level) )
        #    image_name = '_'.join(["ascos1", "2a", cdtg, fld, level_name, tau])
        #
        #    plot_global(data, lat, lon, title, image_name,
        #                clabel=plot_parm[fld]['units'],
        #                range=[plot_parm[fld]['min'],plot_parm[fld]['max']])
        
        def seek_field(filename):
            print 'Reading file...'
            #metadata
            datafilename = filename.split('/')[-1].split('_')
            wxparameter = datafilename[0]
            level_type = datafilename[1]
            lvl1 = datafilename[2]
            lvl1 = "%06.1f"%(float(lvl1))
            lvl2 = datafilename[3]
            if wxparameter == 'latitu' or wxparameter == 'longit':
                lvl2 = 1
            else:
                lvl2 = "%06.1f"%(float(lvl2))
            imest_and_gridlevels = datafilename[4]
            dtg = datafilename[5]
            filetype = datafilename[6]
            record_length = model_grid['num_bytes']
            # top to bottom
            offset = (model_grid['lm'] - int(float(lvl2))) * record_length
        
            # bottom to top
            offset = (int(float(lvl2)) - 1) * record_length
            #offset = (1 - int(float(lvl2))) * record_length
            


            #  binary file read
            if os.path.isfile(filename):
                f = open( filename, 'rb' )
                f.seek( offset )
                data = np.fromstring(f.read(model_grid['num_bytes']), dtype='float32')
                if sys.byteorder == 'little':
                    data = data.byteswap()
                data = data.reshape(model_grid['jm'], model_grid['im'])
                data = np.ma.masked_equal(data, -990.99)
                istat = 0
            else:
                print "missing file"
                print filename
                data = [[-999.99] * model_grid['im']] * model_grid['jm']
                istat = -1
            return data, wxparameter, level_type, lvl1, lvl2, dtg, filetype
        
        def read_coamps_header (filename):
            #"%s/datahd_sfc_000000_000000_1a2000x0001_%s_00000000_infofld"%(indir, dtg)
            if os.path.isfile(filename):#might not need
                #data_grid.indir = indir#might not need
        
                f = open(filename, 'rb')
        
                datahd = f.read()
                datahd = list(datahd.split())
        
                # separate occasional values with no space between them
                for j in range(len(datahd)):
                    val = datahd[j]
                    if len(val) > 13:
                        i1 = 0
                        k = 0
                        for i in range(len(val)-1):
                            if val[i:i+1] == 'E':
                                newval = val[i1:i+4]
                                if i+4 < 15:
                                    datahd[j] = newval
                                else:
                                    datahd.insert(j+k,newval)
                            k = k+1
                            i1 = i+4
        
                data_grid.mapvars ['nproj']   = float(datahd[2])
                data_grid.mapvars ['stdlat1'] = float(datahd[3])
                data_grid.mapvars ['stdlat2'] = float(datahd[4])
                data_grid.mapvars ['stdlon']  = float(datahd[5])
                data_grid.mapvars ['reflat']  = float(datahd[6])
                data_grid.mapvars ['reflon']  = float(datahd[7])
        
                data_grid.nz    = int(float(datahd[1]))
                data_grid.nzp1  = int(float(datahd[1]))+1
                data_grid.nnest = int(float(datahd[10]))
                data_grid.delx0 = float(datahd[9])
                data_grid.dely0 = float(datahd[8])
        
                nn=1
                while nn <= data_grid.nnest:
                    ng = 30 + (nn-1)*30
                    nx = int(float(datahd[ng-1]))
                    ny = int(float(datahd[ng+0]))
                    ii =   float(datahd[ng+1])
                    jj =   float(datahd[ng+2])
                    iref = float(datahd[ng+3])
                    jref = float(datahd[ng+4])
                    tcmx = float(datahd[ng+27])
                    tcmy = float(datahd[ng+28])
                    delx = float(datahd[ng+6])
                    dely = float(datahd[ng+7])
                    data_grid.nest.append(Nest(nx,ny,ii,jj,iref,jref,tcmx,tcmy,delx,dely))
                    nn=nn+1
        
                # vertical indices
                nz = data_grid.nz
                dsigm = np.array(datahd[500:500+nz]).astype(np.float)
                data_grid.sigw = np.append(np.flipud(np.cumsum(np.flipud(dsigm))),[0.0])
                data_grid.sigm = datahd[800:800+nz]
                data_grid.ztop = data_grid.sigw[0]

        data, wxparameter, level_type, lvl1, lvl2, dtg, filetype = seek_field(fname)
        metadata['top']['level'] = lvl2
        metadata['top']['start_datetime'] = datetime.strptime(dtg, '%Y%m%d%H')
        metadata['top']['end_datetime'] = datetime.strptime(dtg, '%Y%m%d%H')
        metadata['top']['dataprovider'] = 'NRL'
        metadata['top']['filename_datetime'] = metadata['top']['start_datetime']
        metadata['top']['platform_name'] = 'model'
        metadata['top']['source_name'] = 'coampsieee'
        si = SatSensorInfo(metadata['top']['platform_name'],metadata['top']['source_name'])
        if not si:
            raise SciFileError('Unrecognized platform and source name combination: '+metadata['top']['platform_name']+' '+metadata['top']['source_name'])

        dfn = DataFileName(os.path.basename(fname))
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['filename_datetime'] = sdfn.datetime

        # Tells driver to NOT try to sector this data.
        metadata['top']['NON_SECTORABLE'] = True

        if chans == []:
            return
        
#        def rdata (filename)#parmnm, lvltyp, lev1, lev2, inest, dtg, tau, indir='def', outtyp='fcstfld', im=-1, jm=-1):
#        
#        # read coamps binary flat file
#        
#            if indir == 'def': indir = data_grid.indir
#            if im == -1: im = data_grid.nest[inest].nx
#            if jm == -1: jm = data_grid.nest[inest].ny
#            if inest == 0:
#        #global
#                filename = "%s/%s_%s_%06.1f_%06.1f_glob%03dx%03d_%s_%04d0000_%s" \
#                %(indir, parmnm, lvltyp, lev1, lev2, im, jm, dtg, tau, outtyp)
#            else:
#        #COAMPS
#                filename = "%s/%s_%s_%06d_%06d_%1da%04dx%04d_%s_%04d0000_%s" \
#                %(indir, parmnm, lvltyp, lev1, lev2, inest, im, jm, dtg, tau, outtyp)
#        
#        #  print "Reading %s"%filename
#            num_bytes = im*jm*4
#        
#            offset = 0
#        
#        #  binary file read
#            if os.path.isfile(filename):
#                f = open( filename, 'rb' )
#                f.seek( offset )
#                data = np.fromstring(f.read(num_bytes), dtype='float32')
#        # COAMPS irsat values are little_endian all others are big
#                if sys.byteorder == 'little':
#                    if parmnm != 'irrcmp':
#                        data = data.byteswap()
#                data = data.reshape(jm, im)
#                data = np.ma.masked_equal(data, -990.99)
#                f.close()
#                istat = 0
#            else:
#                print "MISSING %s"%parmnm
#                print filename
#                data = [[-999.99] * im] * jm
#                istat = -1
#            return data, istat
        

        # Loop through each dataset name found in the dataset_info property above.
        for dsname in self.dataset_info.keys():
            for geoipsvarname,dfvarname in self.dataset_info[dsname].items():
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                fillvalue = data.fill_value
                datavars[dsname][geoipsvarname] = np.ma.masked_equal(data,fillvalue)
        # Loop through each dataset name found in the gvar_info property above.
        for dsname in self.gvar_info.keys():
            for geoipsvarname,dfvarname in self.gvar_info[dsname].items():
                if dfvarname == 'latitu':
                    geolog, wxparameter, level_type, lvl1, lvl2, dtg, filetype = seek_field(latitude)
                if dfvarname == 'longit':
                    geolog, wxparameter, level_type, lvl1, lvl2, dtg, filetype = seek_field(longitude)
                    xx,yy=geolog.shape
                    for aa in range(xx):
                        for bb in range(yy):
                            if geolog[aa,bb] > 180:
                                geolog[aa,bb]=geolog[aa,bb]-360
                fillvalue = geolog.fill_value
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                gvars[dsname][geoipsvarname] = np.ma.masked_equal(geolog,fillvalue)
                #shell()
