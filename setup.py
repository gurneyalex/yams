#!/usr/bin/env python
# pylint: disable-msg=W0404,W0622,W0704,W0613,W0152
# copyright 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of yams.
#
# yams is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# yams is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with yams. If not, see <http://www.gnu.org/licenses/>.
"""Generic Setup script, takes package info from __pkginfo__.py file.

"""
__docformat__ = "restructuredtext en"

import os
import sys
import shutil
from os.path import isdir, exists, join

try:
    if os.environ.get('NO_SETUPTOOLS'):
        raise ImportError()
    from setuptools import setup
    from setuptools.command import install_lib
    USE_SETUPTOOLS = 1
except ImportError:
    from distutils.core import setup
    from distutils.command import install_lib
    USE_SETUPTOOLS = 0


sys.modules.pop('__pkginfo__', None)
# import required features
from __pkginfo__ import modname, version, license, short_desc, long_desc, \
     web, author, author_email
# import optional features
import __pkginfo__
distname = getattr(__pkginfo__, 'distname', modname)
scripts = getattr(__pkginfo__, 'scripts', [])
data_files = getattr(__pkginfo__, 'data_files', None)
include_dirs = getattr(__pkginfo__, 'include_dirs', [])
ext_modules = getattr(__pkginfo__, 'ext_modules', None)
install_requires = getattr(__pkginfo__, 'install_requires', None)
dependency_links = getattr(__pkginfo__, 'dependency_links', [])

STD_BLACKLIST = ('CVS', '.svn', '.hg', 'debian', 'dist', 'build')

IGNORED_EXTENSIONS = ('.pyc', '.pyo', '.elc', '~')



def ensure_scripts(linux_scripts):
    """
    Creates the proper script names required for each platform
    (taken from 4Suite)
    """
    from distutils import util
    if util.get_platform()[:3] == 'win':
        scripts_ = [script + '.bat' for script in linux_scripts]
    else:
        scripts_ = linux_scripts
    return scripts_


def get_packages(directory, prefix):
    """return a list of subpackages for the given directory
    """
    result = []
    for package in os.listdir(directory):
        absfile = join(directory, package)
        if isdir(absfile):
            if exists(join(absfile, '__init__.py')) or \
                   package in ('test', 'tests'):
                if prefix:
                    result.append('%s.%s' % (prefix, package))
                else:
                    result.append(package)
                result += get_packages(absfile, result[-1])
    return result

def install(**kwargs):
    """setup entry point"""
    if USE_SETUPTOOLS:
        if '--force-manifest' in sys.argv:
            sys.argv.remove('--force-manifest')
    # install-layout option was introduced in 2.5.3-1~exp1
    elif sys.version_info < (2, 5, 4) and '--install-layout=deb' in sys.argv:
        sys.argv.remove('--install-layout=deb')
    kwargs['package_dir'] = {modname : '.'}
    packages = [modname] + get_packages(os.getcwd(), modname)
    if USE_SETUPTOOLS and install_requires:
        kwargs['install_requires'] = install_requires
        kwargs['dependency_links'] = dependency_links
    kwargs['packages'] = packages
    return setup(name = distname,
                 version = version,
                 license = license,
                 description = short_desc,
                 long_description = long_desc,
                 author = author,
                 author_email = author_email,
                 url = web,
                 scripts = ensure_scripts(scripts),
                 data_files = data_files,
                 ext_modules = ext_modules,
                 **kwargs
                 )

if __name__ == '__main__' :
    install()
