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
"""Yams packaging information."""
__docformat__ = "restructuredtext en"

# pylint: disable-msg=W0622

# package name
modname = 'yams'

# release version
numversion = (0, 30, 3)
version = '.'.join(str(num) for num in numversion)

# license and copyright
license = 'LGPL'

# short and long description
short_desc = "entity / relation schema"
long_desc = """Yet Another Magic Schema !
A simple/generic but powerful entities / relations schema, suitable
to represent RDF like data. The schema is readable/writable from/to
various formats.
"""

# author name and email
author = "Logilab"
author_email = "devel@logilab.fr"

# home page
web = "http://www.logilab.org/project/%s" % modname

# mailing list
mailinglist = 'mailto://python-projects@lists.logilab.org'

# download place
ftp = "ftp://ftp.logilab.org/pub/%s" % modname

# is there some directories to include with the source installation
include_dirs = []

# executable

scripts = ['bin/yams-check', 'bin/yams-view']

install_requires = [
    'logilab-common >= 0.47.0',
    'logilab-database >= 1.3.0',
    ]
