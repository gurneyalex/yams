# pylint: disable-msg=W0622
# Copyright (c) 2003-2007 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr

# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""yams packaging information
"""

# package name
modname = 'yams'

# release version
numversion = (0, 9, 4)
version = '.'.join([str(num) for num in numversion])

# license and copyright
license = 'GPL'
copyright = '''Copyright (c) 2004-2007 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr'''

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
web = "http://www.logilab.org/projects/%s" % modname

# mailing list
mailinglist = 'mailto://python-projects@lists.logilab.org' 

# download place
ftp = "ftp://ftp.logilab.org/pub/%s" % modname

# is there some directories to include with the source installation
include_dirs = []

pyversions = ['2.4']
