"""Yams packaging information.

:organization: Logilab
:copyright: 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: Lesser General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

# pylint: disable-msg=W0622

# package name
modname = 'yams'

# release version
numversion = (0, 29, 0)
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

pyversions = ['2.4', '2.5']

install_requires = [
    'logilab-common >= 0.47.0',
    ]
