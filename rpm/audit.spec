# based on work by The Fedora Project (2017)
# Copyright (c) 1998, 1999, 2000 Thai Open Source Software Center Ltd
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


Summary: User space tools for 2.6 kernel auditing
Name: audit
Version: 2.8.2
Release: 1%{?dist}
License: GPLv2+
Group: System Environment/Daemons
URL: http://people.redhat.com/sgrubb/audit/
Source0: %{name}-%{version}.tar.gz
Source1: lgpl-2.1.txt
Patch0: systemd_unitdir.patch
Patch1: no_audisp_plugins.patch
BuildRequires: swig
BuildRequires: kernel-headers >= 2.6.29
BuildRequires: automake autoconf libtool

Requires: %{name}-libs%{?_isa} = %{version}-%{release}
BuildRequires: systemd
# do we really need this?
#Requires(post): systemd-units systemd-sysv chkconfig
Requires(post): coreutils
Requires(postun): coreutils

%description
The audit package contains the user space utilities for
storing and searching the audit records generated by
the audit subsystem in the Linux 2.6 and later kernels.

%package libs
Summary: Dynamic library for libaudit
License: LGPLv2+
Group: Development/Libraries

%description libs
The audit-libs package contains the dynamic libraries needed for 
applications to use the audit framework.

%package libs-devel
Summary: Header files for libaudit
License: LGPLv2+
Group: Development/Libraries
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
Requires: kernel-headers >= 2.6.29

%description libs-devel
The audit-libs-devel package contains the header files needed for
developing applications that need to use the audit framework libraries.

%package libs-static
Summary: Static version of libaudit library
License: LGPLv2+
Group: Development/Libraries
Requires: kernel-headers >= 2.6.29

%description libs-static
The audit-libs-static package contains the static libraries
needed for developing applications that need to use static audit
framework libraries

%package libs-python3
Summary: Python3 bindings for libaudit
License: LGPLv2+
Group: Development/Libraries
BuildRequires: python3-devel
Requires: %{name}-libs%{?_isa} = %{version}-%{release}

%description libs-python3
The audit-libs-python3 package contains the bindings so that libaudit
and libauparse can be used by python3.

%prep
%setup -q -n %{name}-%{version}/%{name}
%patch0
%patch1
cp %{SOURCE1} .

%build
./autogen.sh
%configure --sbindir=/sbin --libdir=/%{_lib} \
           --with-python=no --with-python3=yes --without-golang \
           --with-arm --with-aarch64 \
           --disable-zos-remote --enable-gssapi-krb-5=no \
           --enable-systemd --disable-listener

make CFLAGS="%{optflags}" %{?_smp_mflags}

%install
mkdir -p $RPM_BUILD_ROOT/{sbin,etc/audispd/plugins.d,etc/audit/rules.d}
# for some reason audisp appears to be a file without this
mkdir -p $RPM_BUILD_ROOT/etc/audisp
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/{man5,man8}
mkdir -p $RPM_BUILD_ROOT/%{_lib}
mkdir -p $RPM_BUILD_ROOT/%{_libdir}/audit
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mkdir -p --mode=0700 $RPM_BUILD_ROOT/%{_var}/log/audit
mkdir -p $RPM_BUILD_ROOT/%{_var}/spool/audit
make DESTDIR=$RPM_BUILD_ROOT install

mkdir -p $RPM_BUILD_ROOT/%{_libdir}
# This winds up in the wrong place when libtool is involved
mv $RPM_BUILD_ROOT/%{_lib}/libaudit.a $RPM_BUILD_ROOT%{_libdir}
mv $RPM_BUILD_ROOT/%{_lib}/libauparse.a $RPM_BUILD_ROOT%{_libdir}
curdir=`pwd`
cd $RPM_BUILD_ROOT/%{_libdir}
LIBNAME=`basename \`ls $RPM_BUILD_ROOT/%{_lib}/libaudit.so.1.*.*\``
ln -s ../../%{_lib}/$LIBNAME libaudit.so
LIBNAME=`basename \`ls $RPM_BUILD_ROOT/%{_lib}/libauparse.so.0.*.*\``
ln -s ../../%{_lib}/$LIBNAME libauparse.so
cd $curdir
# Remove these items so they don't get picked up.
rm -f $RPM_BUILD_ROOT/%{_lib}/libaudit.so
rm -f $RPM_BUILD_ROOT/%{_lib}/libauparse.so

find $RPM_BUILD_ROOT -name '*.la' -delete
find $RPM_BUILD_ROOT/%{_libdir}/python?.?/site-packages -name '*.a' -delete

# Move the pkgconfig file
mv $RPM_BUILD_ROOT/%{_lib}/pkgconfig $RPM_BUILD_ROOT%{_libdir}

# On platforms with 32 & 64 bit libs, we need to coordinate the timestamp
touch -r ./audit.spec $RPM_BUILD_ROOT/etc/libaudit.conf
touch -r ./audit.spec $RPM_BUILD_ROOT/usr/share/man/man5/libaudit.conf.5.gz

# for some reason, the systemd service file needs to be installed manually
cp init.d/auditd.service $RPM_BUILD_ROOT%{_unitdir}/auditd.service

%check
# Get rid of make files so that they don't get packaged.
rm -f rules/Makefile*

%clean
rm -rf $RPM_BUILD_ROOT

%post libs -p /sbin/ldconfig

%post
# Copy default rules into place on new installation
files=`ls /etc/audit/rules.d/ 2>/dev/null | wc -w`
if [ "$files" -eq 0 ] ; then
# turn audit off by default (Fedora bug #1117953)
	if [ -e /usr/share/doc/audit/rules/10-no-audit.rules ] ; then
	        cp /usr/share/doc/audit-{%version}/rules/10-no-audit.rules /etc/audit/rules.d/audit.rules
	else
		touch /etc/audit/rules.d/audit.rules
	fi
	chmod 0600 /etc/audit/rules.d/audit.rules
fi
%systemd_post auditd.service

%preun
%systemd_preun auditd.service

%postun libs -p /sbin/ldconfig

%postun
if [ $1 -ge 1 ]; then
   /sbin/service auditd condrestart > /dev/null 2>&1 || :
fi

%files libs
%defattr(-,root,root,-)
%{!?_licensedir:%global license %%doc}
%license lgpl-2.1.txt
/%{_lib}/libaudit.so.1*
/%{_lib}/libauparse.*
%config(noreplace) %attr(640,root,root) /etc/libaudit.conf
%{_mandir}/man5/libaudit.conf.5.gz

%files libs-devel
%defattr(-,root,root,-)
%doc contrib/skeleton.c contrib/plugin
%{_libdir}/libaudit.so
%{_libdir}/libauparse.so
%{_includedir}/libaudit.h
%{_includedir}/auparse.h
%{_includedir}/auparse-defs.h
%{_datadir}/aclocal/audit.m4
%{_libdir}/pkgconfig/audit.pc
%{_libdir}/pkgconfig/auparse.pc
%{_mandir}/man3/*

%files libs-static
%defattr(-,root,root,-)
%{!?_licensedir:%global license %%doc}
%license lgpl-2.1.txt
%{_libdir}/libaudit.a
%{_libdir}/libauparse.a

%files libs-python3
%defattr(-,root,root,-)
%attr(755,root,root) /%{_libdir}/python3.?/site-packages

%files
%defattr(-,root,root,-)
%doc README ChangeLog rules init.d/auditd.cron
%{!?_licensedir:%global license %%doc}
%license COPYING
%attr(644,root,root) %{_mandir}/man8/audispd.8.gz
%attr(644,root,root) %{_mandir}/man8/auditctl.8.gz
%attr(644,root,root) %{_mandir}/man8/auditd.8.gz
%attr(644,root,root) %{_mandir}/man8/aureport.8.gz
%attr(644,root,root) %{_mandir}/man8/ausearch.8.gz
%attr(644,root,root) %{_mandir}/man8/autrace.8.gz
%attr(644,root,root) %{_mandir}/man8/aulast.8.gz
%attr(644,root,root) %{_mandir}/man8/aulastlog.8.gz
%attr(644,root,root) %{_mandir}/man8/auvirt.8.gz
%attr(644,root,root) %{_mandir}/man8/augenrules.8.gz
%attr(644,root,root) %{_mandir}/man8/ausyscall.8.gz
%attr(644,root,root) %{_mandir}/man7/audit.rules.7.gz
%attr(644,root,root) %{_mandir}/man5/auditd.conf.5.gz
%attr(644,root,root) %{_mandir}/man5/audispd.conf.5.gz
%attr(644,root,root) %{_mandir}/man5/ausearch-expression.5.gz
%attr(755,root,root) /sbin/auditctl
%attr(755,root,root) /sbin/auditd
%attr(755,root,root) /sbin/ausearch
%attr(755,root,root) /sbin/aureport
%attr(750,root,root) /sbin/autrace
%attr(755,root,root) /sbin/audispd
%attr(755,root,root) /sbin/augenrules
%attr(755,root,root) %{_bindir}/aulast
%attr(755,root,root) %{_bindir}/aulastlog
%attr(755,root,root) %{_bindir}/ausyscall
%attr(755,root,root) %{_bindir}/auvirt
%attr(644,root,root) %{_unitdir}/auditd.service
%attr(750,root,root) %dir %{_libexecdir}/initscripts/legacy-actions/auditd
%attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/resume
%attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/reload
%attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/rotate
%attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/stop
%attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/restart
%attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/condrestart
%attr(750,root,root) %dir %{_var}/log/audit
%attr(750,root,root) %dir /etc/audit
%attr(750,root,root) %dir /etc/audit/rules.d
%attr(750,root,root) %dir /etc/audisp
%config(noreplace) %attr(640,root,root) /etc/audit/auditd.conf
%ghost %config(noreplace) %attr(640,root,root) /etc/audit/rules.d/audit.rules
%ghost %config(noreplace) %attr(640,root,root) /etc/audit/audit.rules
%config(noreplace) %attr(640,root,root) /etc/audit/audit-stop.rules
%config(noreplace) %attr(640,root,root) /etc/audisp/audispd.conf
