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
import os.path as osp
import sys
import shutil
from io import open

from setuptools import setup, find_packages


here = osp.abspath(osp.dirname(__file__))

pkginfo = {}
with open(osp.join(here, '__pkginfo__.py')) as f:
    exec(f.read(), pkginfo)

# Get the long description from the relevant file
with open(osp.join(here, 'README'), encoding='utf-8') as f:
    long_description = f.read()

kwargs = {}
if 'subpackage_of' in pkginfo:
    kwargs['namespace_packages'] = [pkginfo['subpackage_of']]

setup(
    name=pkginfo.get('distname', pkginfo['modname']),
    version=pkginfo['version'],
    license=pkginfo['license'],
    description=pkginfo['description'],
    long_description=long_description,
    author=pkginfo['author'],
    author_email=pkginfo['author_email'],
    url=pkginfo['web'],
    classifiers=pkginfo.get('classifiers', []),
    packages=find_packages(exclude=['test*']),
    install_requires=pkginfo.get('install_requires'),
    scripts=pkginfo.get('scripts', []),
    ext_modules=pkginfo.get('ext_modules'),
    **kwargs
)
