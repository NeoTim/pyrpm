Summary: RPM implementation in python
Name: pyrpm
Version: 0.90
Release: 1%{?dist}
License: GPLv2
URL: https://fedorahosted.org/pyrpm/

Source: pyrpm-%{version}.tar.bz2

BuildArch: noarch
BuildRequires: python >= 2.3
Requires: python >= 2.3, python-urlgrabber, libxml2-python

%description
PyRPM is a RPM implementation in Python. It can be used to study how rpm based
software management happens. Also tools can build upon it to handle rpm
packages in general e.g. to extract information, check dependancies or even
install packages.

%prep
%setup

%build
%configure
%{__make} %{?_smp_mflags}

%install
%{__rm} -rf %{buildroot}
%{__make} install DESTDIR="%{buildroot}"

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-, root, root, 0755)
%doc AUTHORS COPYING INSTALL NEWS README doc/*.html doc/*.txt
%{_bindir}/*
%{_datadir}/pyrpm/
%ghost %{_datadir}/pyrpm/*/*.pyo

%changelog
* Tue Feb 18 2014 Dhiru Kholia <dhiru@openwall.com> - 0.80-1
- Updated to release 0.90 and trimmed changelog

* Thu Jan 24 2008 Dag Wieers <dag@wieers.com> - 0.70-1
- Updated to release 0.70.
