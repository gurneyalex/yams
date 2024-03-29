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
"""XML vocabularies <-> Yams schema mapping"""

from warnings import warn

class UnsupportedVocabulary(Exception): pass

class XYRegistry(object):
    """registry of equivalence to translate yams into various xml schema such
    as dublin core, foaf, doap...

    """
    def __init__(self):
        self.prefixes = {}
        self._y2x = {}
        self._x2y = {}

    def register_prefix(self, prefix, xmlns, overwrite=False):
        if ':' in prefix:
            warn('[yams 0.30] register_prefix arguments has been switched to '
                 '(prefix, xmlns)', DeprecationWarning, stacklevel=2)
            prefix, xmlns = xmlns, prefix
        if not overwrite and prefix in self.prefixes \
                and self.prefixes.get(prefix) != xmlns:
            raise Exception('prefix %r already defined with different value'
                            % prefix)
        self.prefixes[prefix] = xmlns

    def _norm_yams_key(self, yamssnippet):
        parts = yamssnippet.split(' ')
        if len(parts) == 1:
            if parts[0][0].islower():
                return '*', parts[0], '*'
            return parts[0]
        if len(parts) == 2:
            parts.append('*')
        assert len(parts) == 3
        return tuple(parts)

    def _norm_xml_key(self, xmlsnippet, isentity=False):
        parts = []
        for xmlsnippet in xmlsnippet.split(' '):
            pfx, tag = xmlsnippet.rsplit(':', 1)
            xmlns = self.prefixes.get(pfx, pfx)
            parts.append( (xmlns, tag) )
        if isentity:
            assert len(parts) == 1
            return parts[0]
        if len(parts) == 1:
            return '*', parts[0], '*'
        if len(parts) == 2:
            parts.append('*')
        assert len(parts) == 3
        return tuple(parts)

    def add_equivalence(self, yamssnippet, xmlsnippet):
        ykey = self._norm_yams_key(yamssnippet)
        isentity = not isinstance(ykey, tuple)
        xkey = self._norm_xml_key(xmlsnippet, isentity=isentity)
        self._y2x.setdefault(ykey, []).append(xkey)
        self._x2y.setdefault(xkey, []).append(ykey)
        if not isentity:
            for dict, key, value in ((self._x2y, xkey, ykey),
                                     (self._y2x, ykey, xkey)):
                if key[0] != '*':
                    wkey = ('*',) + key[1:]
                    dict.setdefault(wkey, []).append(value)
                if key[2] != '*':
                    wkey = key[:2] + ('*',)
                    dict.setdefault(wkey, []).append(value)

    def remove_equivalence(self, yamssnippet, xmlsnippet):
        ykey = self._norm_yams_key(yamssnippet)
        isentity = not isinstance(ykey, tuple)
        xkey = self._norm_xml_key(xmlsnippet, isentity=isentity)
        self._y2x.setdefault(ykey, []).remove(xkey)
        self._x2y.setdefault(xkey, []).remove(ykey)
        if not isentity:
            for dict, key, value in ((self._x2y, xkey, ykey),
                                     (self._y2x, ykey, xkey)):
                if key[0] != '*':
                    wkey = ('*',) + key[1:]
                    dict.setdefault(wkey, []).remove(value)
                if key[2] != '*':
                    wkey = key[:2] + ('*',)
                    dict.setdefault(wkey, []).remove(value)

    def yeq(self, xmlsnippet, isentity=False):
        key = self._norm_xml_key(xmlsnippet, isentity)
        try:
            return self._x2y[key]
        except KeyError:
            raise UnsupportedVocabulary(key)

    def xeq(self, yamssnippet):
        key = self._norm_yams_key(yamssnippet)
        try:
            return self._y2x[key]
        except KeyError:
            raise UnsupportedVocabulary(key)

XY = XYRegistry()
register_prefix = XY.register_prefix
add_equivalence = XY.add_equivalence
remove_equivalence = XY.remove_equivalence
yeq = XY.yeq
xeq = XY.xeq
