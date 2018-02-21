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
Requires(pos): coreutils
Requires(preun): systemd-units
Requires(postun): systemd-units coreutils

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
#rm -f rules/Makefile*

%clean
rm -rf $RPM_BUILD_ROOT

%post libs -p /sbin/ldconfig

%post
# Copy default rules into place on new installation
files=`ls /etc/audit/rules.d/ 2>/dev/null | wc -w`
if [ "$files" -eq 0 ] ; then
# FESCO asked for audit to be off by default. #1117953
	if [ -e /usr/share/doc/audit/rules/10-no-audit.rules ] ; then
	        cp /usr/share/doc/audit/rules/10-no-audit.rules /etc/audit/rules.d/audit.rules
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

%changelog
* Tue Feb 13 2018 Oliver Schmidt <oliver.schmidt@jollamobile.com>
- adjustments for Mer, conversion to tar_git package
- also reducing needed dependencies

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2.8.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Mon Feb 05 2018 Steve Grubb <sgrubb@redhat.com> 2.8.2-3
- Add a Provides audit-libs-python (#1537864)
- Remove tcp_wrappers support?

* Thu Dec 14 2017 Steve Grubb <sgrubb@redhat.com> 2.8.2-2
- Rename things from python to python2

* Thu Dec 14 2017 Steve Grubb <sgrubb@redhat.com> 2.8.2-1
- New upstream bugfix release

* Thu Oct 12 2017 Steve Grubb <sgrubb@redhat.com> 2.8.1-1
- New upstream bugfix release

* Tue Oct 10 2017 Steve Grubb <sgrubb@redhat.com> 2.8-1
- New upstream feature release

* Mon Sep 18 2017 Steve Grubb <sgrubb@redhat.com> 2.7.8-1
- New upstream bugfix release

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.7.7-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.7.7-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Jul 14 2017 Steve Grubb <sgrubb@redhat.com> 2.7.7-3
- undo scratch build

* Fri Jun 16 2017 Steve Grubb <sgrubb@redhat.com> 2.7.7-1
- New upstream bugfix release

* Wed Apr 19 2017 Steve Grubb <sgrubb@redhat.com> 2.7.6-1
- New upstream bugfix release

* Mon Apr 10 2017 Steve Grubb <sgrubb@redhat.com> 2.7.5-1
- New upstream bugfix release

* Tue Mar 28 2017 Steve Grubb <sgrubb@redhat.com> 2.7.4-1
- New upstream feature and bugfix release

* Fri Feb 24 2017 Steve Grubb <sgrubb@redhat.com> 2.7.3-1
- New upstream feature and bugfix release

* Mon Feb 13 2017 Steve Grubb <sgrubb@redhat.com> 2.7.2-2
- Fix ausearch csv output

* Mon Feb 13 2017 Steve Grubb <sgrubb@redhat.com> 2.7.2-1
- New upstream feature and bugfix release

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.7.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Fri Jan 13 2017 Steve Grubb <sgrubb@redhat.com> 2.7.1-1
- New upstream bugfix release

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 2.7-2
- Rebuild for Python 3.6

* Thu Dec 15 2016 Steve Grubb <sgrubb@redhat.com> 2.7-1
- New upstream feature release

* Sun Sep 11 2016 Steve Grubb <sgrubb@redhat.com> 2.6.7-1
- New upstream bugfix release

* Mon Aug 01 2016 Steve Grubb <sgrubb@redhat.com> 2.6.6-1
- New upstream bugfix release

* Thu Jul 21 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.5-3
- https://fedoraproject.org/wiki/Changes/golang1.7

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.5-2
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Thu Jul 14 2016 Steve Grubb <sgrubb@redhat.com> 2.6.5-1
- New upstream bugfix release

* Fri Jul 08 2016 Steve Grubb <sgrubb@redhat.com> 2.6.4-2
- Correct size information of dispatched event

* Fri Jul 08 2016 Steve Grubb <sgrubb@redhat.com> 2.6.4-1
- New upstream bugfix release

* Tue Jul 05 2016 Steve Grubb <sgrubb@redhat.com> 2.6.3-2
- Fix sockaddr event interpretation

* Tue Jul 05 2016 Steve Grubb <sgrubb@redhat.com> 2.6.3-1
- New upstream bugfix release

* Fri Jul 01 2016 Steve Grubb <sgrubb@redhat.com> 2.6.2-1
- New upstream bugfix release
- Fixes 1351954 - prevents virtual machine from starting up in GNOME Boxes

* Tue Jun 28 2016 Steve Grubb <sgrubb@redhat.com> 2.6.1-1
- New upstream bugfix release

* Wed Jun 22 2016 Steve Grubb <sgrubb@redhat.com> 2.6-3
- New upstream release

* Fri Apr 29 2016 Steve Grubb <sgrubb@redhat.com> 2.5.2-1
- New upstream release

* Thu Apr 28 2016 Steve Grubb <sgrubb@redhat.com> 2.5.1-2
- Refactor plugins to split out zos-remote to lower dependencies

* Wed Apr 13 2016 Steve Grubb <sgrubb@redhat.com> 2.5.1-1
- New upstream release

* Fri Mar 18 2016 Steve Grubb <sgrubb@redhat.com> 2.5-4
- Fixes #1313152 - post script fails on dnf --setopt=tsflags=nodocs install

* Mon Feb 22 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5-3
- https://fedoraproject.org/wiki/Changes/golang1.6

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Jan 11 2016 Steve Grubb <sgrubb@redhat.com> 2.5-1
- New upstream release
- Fixes #1241565 - still logs way too much
- Fixes #1238051 - audit.rules should be generated from by augenrules

* Fri Dec 18 2015 Steve Grubb <sgrubb@redhat.com> 2.4.4-1
- New upstream bugfix release

* Wed Nov 04 2015 Robert Kuska <rkuska@redhat.com> - 2.4.4-3
- Rebuilt for Python3.5 rebuild

* Wed Sep 16 2015 Peter Robinson <pbrobinson@fedoraproject.org> 2.4.4-2
- Fix FTBFS with hardened flags by using the distro CFLAGS
- Tighten deps with the _isa macro
- Use goarches macro to define supported GO architectures
- Minor cleanups

* Thu Aug 13 2015 Steve Grubb <sgrubb@redhat.com> 2.4.4-1
- New upstream bugfix release
- Fixes CVE-2015-5186 Audit: log terminal emulator escape sequences handling

* Thu Jul 16 2015 Steve Grubb <sgrubb@redhat.com> 2.4.3-1
- New upstream bugfix release
- Adds python3 support

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.4.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Tue Apr 28 2015 Steve Grubb <sgrubb@redhat.com> 2.4.2-1
- New upstream bugfix release

* Sat Feb 21 2015 Till Maas <opensource@till.name> - 2.4.1-2
- Rebuilt for Fedora 23 Change
  https://fedoraproject.org/wiki/Changes/Harden_all_packages_with_position-independent_code

* Tue Oct 28 2014 Steve Grubb <sgrubb@redhat.com> 2.4.1-1
- New upstream feature and bugfix release

* Mon Oct 06 2014 Karsten Hopp <karsten@redhat.com> 2.4-2
- bump release and rebuild for upgradepath

* Sun Aug 24 2014 Steve Grubb <sgrubb@redhat.com> 2.4-1
- New upstream feature and bugfix release

* Fri Aug 15 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.8-0.3.svn20140803
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Mon Aug  4 2014 Peter Robinson <pbrobinson@fedoraproject.org> 2.3.8-0.2.svn20140803
- aarch64/PPC/s390 don't have golang

* Sat Aug 02 2014 Steve Grubb <sgrubb@redhat.com> 2.3.8-0.1.svn20140803
- New upstream svn snapshot

* Tue Jul 22 2014 Steve Grubb <sgrubb@redhat.com> 2.3.7-4
- Bug 1117953 - Per fesco#1311, please disable syscall auditing by default

* Fri Jul 11 2014 Tom Callaway <spot@fedoraproject.org> - 2.3.7-3
- mark license files properly

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue Jun 03 2014 Steve Grubb <sgrubb@redhat.com> 2.3.7-1
- New upstream bugfix release

* Fri Apr 11 2014 Steve Grubb <sgrubb@redhat.com> 2.3.6-1
- New upstream bugfix/enhancement release

* Mon Mar 17 2014 Steve Grubb <sgrubb@redhat.com> 2.3.5-1
- New upstream bugfix/enhancement release

* Thu Feb 27 2014 Steve Grubb <sgrubb@redhat.com> 2.3.4-1
- New upstream bugfix/enhancement release

* Thu Jan 16 2014 Steve Grubb <sgrubb@redhat.com> 2.3.3-1
- New upstream bugfix/enhancement release

* Mon Jul 29 2013 Steve Grubb <sgrubb@redhat.com> 2.3.2-1
- New upstream bugfix/enhancement release

* Fri Jun 21 2013 Steve Grubb <sgrubb@redhat.com> 2.3.1-3
- Drop prelude support

* Fri May 31 2013 Steve Grubb <sgrubb@redhat.com> 2.3.1-2
- Fix unknown lvalue in auditd.service (#969345)

* Thu May 30 2013 Steve Grubb <sgrubb@redhat.com> 2.3.1-1
- New upstream bugfix/enhancement release

* Fri May 03 2013 Steve Grubb <sgrubb@redhat.com> 2.3-2
- If no rules exist, copy shipped rules into place

