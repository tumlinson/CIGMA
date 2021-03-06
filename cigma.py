#! /usr/bin/env python2

import numpy as np
import os
#from astropy.io import ascii
#from astropy.table import Table
import pandas
import glob
import subprocess
from website.host_cigma import host_cigma

__version__ = '0.1'
__author__  = 'Sean Lockwood'


class SIMBAD_IOError(IOError):
    pass


#def sdss2(qso):
#    from astroquery.sdss import SDSS
#    from astropy import coordinates as coords
#    from astroquery.simbad import Simbad
#    
#    res = Simbad.query_object('iau {:s} = qso'.format(qso))
#    
#    if res is None or len(res) == 0:
#        raise SIMBAD_IOError('QSO not found:  '.format(qso))
#    else:
#        res = res[0]  # QUESTIONABLE! ***
#    
#    ra_num  = map(float, res['RA'].split())
#    dec_num = map(float, res['DEC'].split())
#    
#    # *** Questionable! ***:
#    if len(ra_num) == 2:
#        ra_num.append(0.)
#    if len(dec_num) == 2:
#        dec_num.append(0.)
#    
#    coord_str = '{RA[0]:.0f}h{RA[1]:.0f}m{RA[2]:.2f}s {DEC[0]:+.0f}d{DEC[1]:.0f}m{DEC[2]:.1f}s'.format( \
#        **{'RA':ra_num, 'DEC':dec_num})
#    print coord_str
#    pos = coords.SkyCoord(coord_str, frame='icrs')
#    
#    xid = SDSS.query_region(pos, spectro=True)
#    
#    im = SDSS.get_images(matches=xid, band='g')
#    
#    embed()


def sdss_thumbnail(ra, dec, dest_dir, scale=0.2, clobber=False):
    import urllib
    
    outname = os.path.join(dest_dir, '{:016.12f}_{:+017.13f}_{:.1f}.jpg'.format(ra, dec, scale))
    
    if not os.access(outname, os.F_OK) or clobber == True:
        urllib.urlretrieve( 
            'http://skyserver.sdss.org/dr13/SkyServerWS/ImgCutout/getjpeg?'    + \
            'TaskName=Skyserver.Chart.Image&'                                  + \
            'ra={:16.12f}&dec={:16.13f}&width=256&height=256&scale={:.1f}'.format(ra, dec, scale), 
            filename=outname)
    
    return outname


def resolve_name(qso='J1059+2517'):
    from astroquery.simbad import Simbad
    
    res = Simbad.query_object('iau {:s} = qso'.format(qso))
    
    if res is None or len(res) == 0:
        raise SIMBAD_IOError('QSO not found:  '.format(qso))
    
    ra_str  = map(float, res['RA'][0].split())
    dec_str = map(float, res['DEC'][0].split())
    
    # *** Questionable! ***:
    if len(ra_str) == 2:
        ra_str.append(0.)
    if len(dec_str) == 2:
        dec_str.append(0.)
    
    ra  = ra_str[0]  + (ra_str[1]  + ra_str[2] /60.) / 60.
    dec = dec_str[0] + (dec_str[1] + dec_str[2]/60.) / 60.
    
    return ra, dec


def get_thumbnail(qso, galname, config):
    print 'Working on thumbnails for qso {:s}...'.format(qso)
    try:
        ra, dec = resolve_name(qso)
    except SIMBAD_IOError:
        print 'Object not found in Simbad:  {:s}'.format(qso)
        return 'Not found'
    
    # Find offset from QSO:
    posang, dist = map(float, galname.split('_'))
    dx = dist * np.sin(np.deg2rad(posang)) / 3600.  # deg
    dy = dist * np.cos(np.deg2rad(posang)) / 3600.  # deg
    #print 'dx={}\tdy={}'.format(dx, dy)
    
    return sdss_thumbnail(ra + dx, dec + dy, config['img_dir'], clobber=config['clobber_sdss_thumbnail'])


def get_shortsum_png(pdf_file, config):
    # Use a different destination directory?
    
    print pdf_file
    outname = os.path.join(config['img_dir'], os.path.basename(pdf_file[0:-4] + '.png'))
    # Recreate PNG if clobber=True, PNG does not exist, or PDF is newer than existing PNG:
    if config['clobber_shortsum_png'] or not os.access(outname, os.F_OK) or os.path.getmtime(pdf_file) > os.path.getmtime(outname):
        ret_status = subprocess.call(
            ['convert', '-density', '400', pdf_file, '-resize', '25%', '-quality', '90', outname])
        if ret_status != 0:
            raise IOError('Unable to convert PDF file to PNG (error status {}):\n    {:s}'.format(
                ret_status, pdf_file))
    return outname


def parse_master(config):
    dir = config['cos_dwarfs_dir']
    master_file = os.path.join(dir, config['cos_dwarfs_master_file'])
    
    t = pandas.read_table(master_file, 
        comment='#', 
        names=['flg', 'qso', 'galname', 'zgal', 'canonical', 'HIflg'], 
        delim_whitespace=True)
    
    t['index'] = 0
    t['dir'] = ''
    t['lst'] = ''
    t['shortsum'] = ''
    t['shortsum_png'] = ''
    t['redshift_file'] = ''
    t['redshift'] = ''
    t['sdss_thumbnail'] = ''
    for i, zgal in enumerate(t['zgal']):
        t['index'][i] = i
        t['dir'][i] = os.path.join(dir, t['qso'][i], '{}_z{:01.3f}'.format(t['galname'][i], zgal))
        t['lst'][i] = os.path.join(t['dir'][i], '{}_z{:01.3f}.lst'.format(t['galname'][i], zgal))
        try:
            t['redshift_file'][i] = glob.glob(os.path.join(t['dir'][i], 'redshift.info'))[0]
            line = ''
            with open(t['redshift_file'][i]) as f:
                line = f.readline()
                t['redshift'][i] = line.split()[-1]
            t['shortsum'][i] = glob.glob(os.path.join(t['dir'][i], 'plots', 
                '{}_{}_{:s}_shortsum_bin3.pdf'.format(t['qso'][i], t['galname'][i], t['redshift'][i])))[0]
        except IndexError:
            t['redshift_file'][i] = ''
            searchstr = os.path.join(t['dir'][i], 'plots', 
                '{}_{}_*_shortsum_bin3.pdf'.format(t['qso'][i], t['galname'][i]))
            shortsums =  glob.glob(searchstr)
            if len(shortsums) == 1:
                t['shortsum'][i] = shortsums[0]
                t['redshift'][i] = os.path.basename(t['shortsum'][i]).split('_')[-3]
            elif len(shortsums) > 1:
                raise IOerror('More than one shortsum PDF plot found!  {}'.format(searchstr))
            else:
                t['shortsum'][i] = 'UNDEFINED'
        t['shortsum_png'][i] = get_shortsum_png(t['shortsum'][i], config)
        t['sdss_thumbnail'][i] = get_thumbnail(t['qso'][i], t['galname'][i], config)
    
    t.set_index('index', inplace=True)
    
    return t  #[t['canonical'] != 0]


#def pdf_to_png(filename):
#    '''
#    From http://stackoverflow.com/a/36279291/6377060
#    '''
#    from wand.image import Image
#    from wand.color import Color
#    
#    all_pages = Image(blob=filename)        # PDF will have several pages.
#    single_image = all_pages.sequence[0]    # Just work on first page
#    with Image(single_image) as i:
#        i.format = 'png'
#        i.background_color = Color('white') # Set white background.
#        i.alpha_channel = 'remove'          # Remove transparency and replace with bg.


def read_config(config_file):
    '''
    Parse configuration file into dictionary.
    '''
    import yaml
    
    with open(config_file, 'r') as file:
        config = yaml.load(file)
    return config


def cigma(config_file, host_only=False, static=False):
    '''
    Main documentation string is here.
    
    The config file must contain the following keys:
        pickle_file                    [str]
        cos_dwarfs_dir                 [str]
        cos_dwarfs_master_file         [str]
        img_dir                        [str]      
        clobber_sdss_thumbnail         [bool]
        clobber_shortsum_png           [bool]
    '''
    config = read_config(config_file)
    
    if not host_only:
        # Skim data:
        t = parse_master(config)
        t.to_pickle(config['pickle_file'])
        
        for x in t['shortsum']:
            print x
    
    # Host the Flask website:
    host_cigma(pickle_file=config['pickle_file'], static=static)


if __name__ == '__main__':
    import argparse
    
    default_config_file = 'cigma_config.yml'
    
    parser = argparse.ArgumentParser(
        description='Skim data and host the CIGMA website.', 
        epilog='Version {:s}; Written by {:s}'.format(__version__, __author__))
    parser.add_argument('-c', dest='config_file', type=str, 
        help='YAML file containing data [default={:s}]'.format(default_config_file), 
        default=default_config_file)
    parser.add_argument('--host', dest='host', action='store_true', 
        help='Only host the CIGMA website.')
    parser.add_argument('-s', '--static', dest='static', default=False, action='store_true', 
        help='Build static pages rather than hosting a dynamic webserver. [default=False]')
    args = parser.parse_args()
    
    cigma(args.config_file, host_only=args.host, static=args.static)
