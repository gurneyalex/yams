%if 0%{?el5}
%define python python26
%define __python /usr/bin/python2.6
%{!?python_scriptarch: %define python_scriptarch %(%{__python} -c "from distutils.sysconfig import get_python_lib; from os.path import join; print join(get_python_lib(1, 1), 'scripts')")}
%else
%define python python
%define __python /usr/bin/python
%endif

Summary:        entity / relation schema
Name:           %{python}-yams
Version:        0.41.1
Release:        logilab.1%{?dist}
Source0:        http://download.logilab.org/pub/yams/yams-%{version}.tar.gz
License:        LGPLv2+
Group:          Development/Languages/Python
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch:      noarch
Vendor:         Logilab <contact@logilab.fr>
Url:            http://www.logilab.org/project/yams

Requires:       %{python}, %{python}-logilab-common >= 0.55.2, %{python}-logilab-database >= 1.11
Requires:       %{python}-six >= 1.4.0
BuildRequires:  %{python}


%description
Yet Another Magic Schema ! A simple/generic but powerful entities / relations
schema, suitable to represent RDF like data. The schema is readable/writable
from/to various formats.

%prep
%setup -q -n yams-%{version}

%build
%{__python} setup.py build
%if 0%{?el5}
# change the python version in shebangs
find . -name '*.py' -type f -print0 |  xargs -0 sed -i '1,3s;^#!.*python.*$;#! /usr/bin/python2.6;'
%endif

%install
rm -rf $RPM_BUILD_ROOT
NO_SETUPTOOLS=1 %{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT %{?python_scriptarch: --install-scripts=%{python_scriptarch}}

%clean
rm -rf $RPM_BUILD_ROOT

%files 
%defattr(-, root, root)
/*

