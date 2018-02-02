"""A setuptools based setup module.

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

For packaging information, see:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject


First must run create_links.py hardlinks to create a complete
$GEOIPS_OS directory. From clean environment:
module load python # Needed for remove_links.py IPython
export GEOIPS=~/satnrl_test/geoips_nrl
# OPTIONAL:
export STANDALONE_GEOIPS=~/satnrl_test/geoips_os
# OPTIONAL:
export EXTERNAL_GEOIPS=~/satnrl_test/geoips_nrl:~/satnrl_test/geoips_proprietary
# GEOIPS, EXTERNAL_GEOIPS, and STANDALONE_GEOIPS can all be unset after
#    creating the links if you are doing a system install.
python remove_links.py all
python create_links.py hardlinks


After running create_links.py, you can build the source distribution.
From clean environment:
    module load python # Needed for setup.py IPython
    python setup.py sdist


After creating the source distribution, you can install it with
setup.py install or pip install. From a clean environment:
    module load python # For pip
    # Must contain rayleigh, lunarref, elevation
    export GEOALGSDATA=~/satnrl_outdirs/geoalgs_data/
    # python setup.py install --user
    # OR
    pip install dist/geoips-0.4.0.tar.gz --user -vvv


Now you are ready to run GeoIPS. From a clean environment:
    module load python
    export GEOIPS_OUTDIRS=~/satnrl_outdirs
    export EXTERNAL_SECTORFILEPATH=~/satnrl_test/geoips_nrl/geoips/sectorfiles
    export EXTERNAL_PRODUCTFILEPATH=~/satnrl_test/geoips_nrl/geoips/productfiles:~/satnrl_test/geoips_os/geoips/productfiles:~/satnrl_test/geoips_proprietary/geoips/productfiles


Must have __init__.py in
top level geoips directory in order for find_packages()
to work.

Also make sure repo is clean - nothing has been built, etc.

And make sure local geoips directory is not in PYTHONPATH before
trying to pip install ! (or it will think it is already installed)


Will result in
import geoips
>geoips.geoalgs
>geoips.downloaders
or
>from geoips.scifile import SciFile

# Creates .tar.gz file with all source
python setup.py sdist

# SYSTEM install (sdist UNNECESSARY):
#python setup.py install --user
#    Defaults to /users/surratt/.local/lib/python2.7/site-packages/geoips/

# SYSTEM install - sdist REQUIRED (can leave out --upgrade):
pip install -vvv dist/geoips-0.4.0.tar.gz --user --upgrade

# LOCAL install (sdist UNNECESSARY. creates link in user site-packages to path you give it -
#     $GEOIPS - automatically finds it in your path.)
pip install -vvv -e $GEOIPS --user --upgrade

# LOCAL install (sdist UNNECESSARY):
python setup.py develop --user
#    Links to /users/surratt/.local/lib/python2.7/site-packages/geoips/



Can override any of these install-type commands using cmdclass
ie
from setuptools.command.install_egg_info import install_egg_info
class CustomEggInstall (install_egg_info):
    def run(self):
        install_egg_info.run(self)

in setup(
    cmdclass={'install': CustomInstall,
              'install_egg_info': CustomEggInstall,
              'easy_install': CustomEasyInstall,
             },

setup.py install
install
build
build_py
install_lib -> final output location


pip install
egg_info
bdist_wheel
build
build_py
install
install_lib
install_egg_info
egg_info
install_scripts
THEN, external to setup.py, pip runs it's own install command
which actually moves the setup.py local install into the final
install location.  I don't think setup.py has any knowledge of 
where the final install will be when called with pip install.

pip install -e
running develop
running egg_info
running build_ext




"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
# To use a consistent encoding
from codecs import open
import os
from glob import glob
import subprocess
try:
    from IPython import embed as shell
except:
    print 'Failed IPython import in setup.py. If you need it, install it.'

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, 'geoips/about.py')) as fp:
    exec(fp.read(), about)

# Get the long description from the README file
with open(os.path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

class CustomDevelop(develop):
    def run(self):
        print subprocess.call(['pwd'])
        print 'CustomDevelop develop.run'
        develop.run(self)
        builddir = os.getenv('PWD')+'/geoips/geoalgs'

        # print subprocess.call(['ls', '--full-time', builddir+'/*'])
        # print subprocess.call(['ls', '--full-time', ancildat+'/*'])

        print subprocess.call(['/usr/bin/make', '-C', builddir, 'clean'])
        print subprocess.call(['/usr/bin/make', '-C', builddir])

class CustomInstall(install):
    def run(self):
        print subprocess.call(['pwd'])
        print 'self.user: '+str(self.user)
        print 'self.user_options: '+str(self.user_options)
        print 'self.install_usersite: '+str(self.install_usersite)
        print 'self.install_base: '+str(self.install_base)
        print 'self.install_lib: '+str(self.install_lib)
        print 'CustomInstall install.run'
        install.run(self)
        builddir = self.install_lib+'/geoips/geoalgs'

        # print subprocess.call(['ls', '--full-time', builddir+'/*'])
        # print subprocess.call(['ls', '--full-time', ancildat+'/*'])

        print subprocess.call(['/usr/bin/make', '-C', builddir, 'clean'])
        print subprocess.call(['/usr/bin/make', '-C', builddir])


def find_version():
    print about['__version__']
    return about['__version__']


def find_license(longstring=False):
    if not longstring:
        return about['__license__']
    else:
        return 'License :: OSI Approved :: '+about['__license__']+' License',


def find_package_name(longname=False):
    if not longname:
        return about['__title__']
    else:
        return about['__summary__']


def find_install_requires():
    install_requires = about['__requires__']
    for aboutfname in glob(os.path.join(here, 'geoips/about_*.py')):
        about2 = {}
        with open(aboutfname) as fp:
            exec(fp.read(), about2)
            subpkg = about2['__subpackage__']
            install_requires += about2['__'+subpkg+'_requires__']
    return install_requires


setup(
    name=find_package_name(),

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    # Pulls version out of geoips/about.py
    version=find_version(),

    # Pulls package name out of geoips/about.py
    description=find_package_name(longname=True),
    # Pulls long description out of geoips/about.py
    long_description=long_description,

    # The project's main homepage.
    url='http://www.nrlmry.navy.mil/geoips',

    # Author details
    author='NRL Monterey Marine Meteorology Division',
    author_email='geoips@nrlmry.navy.mil',

    # Choose your license
    license=find_license(),
    cmdclass={'install': CustomInstall,
              'develop': CustomDevelop,
             },

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Meteorologists',
        'Topic :: Satellite Processing :: Meteorology and Oceanography',

        # Pick your license as you wish (should match "license" above)
        find_license(longstring=True),

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
        # 'Programming Language :: Python :: 3.5',
    ],

    # What does your project relate to?
    keywords='satellite data processing meteorology',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    # packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    packages=find_packages(),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    # Pulls required packages out of geoips/about.py
    install_requires=find_install_requires(),

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
#    extras_require={
#        'dev': ['check-manifest'],
#        'test': ['coverage'],
#    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'geoips': ['geoalgs/*', 'geoalgs/*/*', 'geoalgs/*/*/*',
                   'geoalgs/*/*/*/*', 'geoalgs/*/*/*/*/*',
                   'sectorfiles/*', 'sectorfiles/*/*',
                   'productfiles/*', 'productfiles/*/*',
                   'geoimg/ascii_palettes/*'],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
#    data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
#    entry_points={
#        'console_scripts': [
#            'sample=sample:main',
#        ],
#    },
)
