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
Version: 3.1.5
Release: 1
License: GPLv2+
URL: http://people.redhat.com/sgrubb/audit/
Source0: %{name}-%{version}.tar.gz
Source1: lgpl-2.1.txt
Patch1: no_audisp_plugins.patch
Patch2: doc_remove_zos_pages.patch
Patch3: service_use_usr_sbin.patch
Patch4: augenrules_use_usr_sbin.patch
Patch5: 0001-backport-remove-use-deprecated-distutils-python-modu.patch
Patch6: 0002-backport-Fix-make-distcheck.-Was-failing-to-have-cor.patch
Patch7: 0003-backport-Do-not-try-to-override-the-value-of-the-PYT.patch
BuildRequires: swig
BuildRequires: kernel-headers >= 2.6.29
BuildRequires: automake autoconf libtool

Requires: %{name}-libs = %{version}-%{release}
BuildRequires: pkgconfig(systemd)
Requires(post): systemd-sysv
Requires(post): coreutils
Requires(postun): coreutils

%description
The audit package contains the user space utilities for
storing and searching the audit records generated by
the audit subsystem in the Linux 2.6 and later kernels.

%package libs
Summary: Dynamic library for libaudit
License: LGPLv2+

%description libs
The audit-libs package contains the dynamic libraries needed for 
applications to use the audit framework.

%package libs-devel
Summary: Header files for libaudit
License: LGPLv2+
Requires: %{name}-libs = %{version}-%{release}
Requires: kernel-headers >= 2.6.29

%description libs-devel
The audit-libs-devel package contains the header files needed for
developing applications that need to use the audit framework libraries.

%package libs-python3
Summary: Python3 bindings for libaudit
License: LGPLv2+
BuildRequires: python3-devel
Requires: %{name}-libs = %{version}-%{release}

%description libs-python3
The audit-libs-python3 package contains the bindings so that libaudit
and libauparse can be used by python3.

%prep
%autosetup -p1 -n %{name}-%{version}/%{name}

%build
./autogen.sh
%configure --sbindir=%{_sbindir} --libdir=%{_libdir} \
           --with-python=no --with-python3=yes --without-golang \
           --with-arm --with-aarch64 \
           --disable-zos-remote --enable-gssapi-krb-5=no \
           --enable-systemd --disable-listener

%make_build

%install
cp %{SOURCE1} .
mkdir -p $RPM_BUILD_ROOT/{sbin,etc/audispd/plugins.d,etc/audit/rules.d}
# for some reason audisp appears to be a file without this
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/audisp
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/{man5,man8}
mkdir -p $RPM_BUILD_ROOT/%{_libdir}/audit
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mkdir -p --mode=0700 $RPM_BUILD_ROOT/%{_var}/log/audit
mkdir -p $RPM_BUILD_ROOT/%{_var}/spool/audit
%make_install


# Remove these items so they don't get picked up.
rm -f $RPM_BUILD_ROOT/%{_libdir}/libaudit.a
rm -f $RPM_BUILD_ROOT/%{_libdir}/libauparse.a

find $RPM_BUILD_ROOT -name '*.la' -delete
find $RPM_BUILD_ROOT%{_libdir}/python?.?/site-packages -name '*.a' -delete

# On platforms with 32 & 64 bit libs, we need to coordinate the timestamp
touch -r ./audit.spec $RPM_BUILD_ROOT%{_sysconfdir}/libaudit.conf
touch -r ./audit.spec $RPM_BUILD_ROOT/usr/share/man/man5/libaudit.conf.5.gz

# From https://build.opensuse.org/package/view_file/openSUSE:Factory/audit/audit-secondary.spec
# Starting with audit 2.5 no config is installed so start with no rules
install -m 0644 rules/10-no-audit.rules %{buildroot}%{_sysconfdir}/%{name}/rules.d/audit.rules
install -m 0644 rules/10-no-audit.rules %{buildroot}%{_sysconfdir}/%{name}/audit.rules

# for some reason, the systemd service file needs to be installed manually
#cp init.d/auditd.service $RPM_BUILD_ROOT%{_unitdir}/auditd.service

# Install libaudit.conf files by hand
#install -m 0644 docs/libaudit.conf.5 %{buildroot}/%{_mandir}/man5
#install -m 0644 init.d/libaudit.conf %{buildroot}%{_sysconfdir}

%check
# Get rid of make files so that they don't get packaged.
rm -f rules/Makefile*

%post libs -p /sbin/ldconfig

%post
# Copy default rules into place on new installation
files=`ls %{_sysconfdir}/audit/rules.d/ 2>/dev/null | wc -w`
if [ "$files" -eq 0 ] ; then
# turn audit off by default (Fedora bug #1117953)
	if [ -e /usr/share/doc/audit/rules/10-no-audit.rules ] ; then
	        cp /usr/share/doc/audit-{%version}/rules/10-no-audit.rules %{_sysconfdir}/audit/rules.d/audit.rules
	else
		touch %{_sysconfdir}/audit/rules.d/audit.rules
	fi
	chmod 0600 %{_sysconfdir}/audit/rules.d/audit.rules
fi
%systemd_post auditd.service

%preun
%systemd_preun auditd.service

%postun libs -p /sbin/ldconfig

%postun
if [ $1 -ge 1 ]; then
   systemctl try-restart audit || :
fi

%files libs
%{!?_licensedir:%global license %%doc}
%license lgpl-2.1.txt
/%{_libdir}/libaudit.so.1*
/%{_libdir}/libauparse.so.*
%config %attr(640,root,root) %{_sysconfdir}/libaudit.conf
%{_mandir}/man5/libaudit.conf.5.gz

%files libs-devel
%doc contrib/plugin
%{_libdir}/libaudit.so
%{_libdir}/libauparse.so
%{_includedir}/libaudit.h
%{_includedir}/auparse.h
%{_includedir}/auparse-defs.h
%{_datadir}/aclocal/audit.m4
%{_libdir}/pkgconfig/audit.pc
%{_libdir}/pkgconfig/auparse.pc
%{_mandir}/man3/*
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
%attr(644,root,root) %{_mandir}/man5/auditd-plugins.5.gz
%attr(644,root,root) %{_mandir}/man5/ausearch-expression.5.gz

%files libs-python3
%attr(755,root,root) /%{_libdir}/python3.?/site-packages

%files
%doc README ChangeLog rules init.d/auditd.cron
%{!?_licensedir:%global license %%doc}
%license COPYING
%attr(755,root,root) %{_datadir}/%{name}
%attr(755,root,root) %{_sbindir}/auditctl
%attr(755,root,root) %{_sbindir}/auditd
%attr(755,root,root) %{_sbindir}/ausearch
%attr(755,root,root) %{_sbindir}/aureport
%attr(750,root,root) %{_sbindir}/autrace
%attr(755,root,root) %{_sbindir}/augenrules
%attr(755,root,root) %{_bindir}/aulast
%attr(755,root,root) %{_bindir}/aulastlog
%attr(755,root,root) %{_bindir}/ausyscall
%attr(755,root,root) %{_bindir}/auvirt
%attr(644,root,root) %{_unitdir}/auditd.service
%exclude %attr(750,root,root) %dir %{_libexecdir}/initscripts/legacy-actions/auditd
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/resume
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/reload
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/rotate
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/stop
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/restart
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/condrestart
%exclude %attr(750,root,root) %{_libexecdir}/initscripts/legacy-actions/auditd/state
%exclude %attr(750,root,root) %{_libexecdir}/audit-functions
%attr(750,root,root) %dir %{_var}/log/audit
%attr(750,root,root) %dir %{_sysconfdir}/audit
%attr(750,root,root) %dir %{_sysconfdir}/audit/rules.d
%attr(750,root,root) %dir %{_sysconfdir}/audisp
%config %attr(640,root,root) %{_sysconfdir}/audit/auditd.conf
%ghost %config %attr(640,root,root) %{_sysconfdir}/audit/rules.d/audit.rules
%ghost %config %attr(640,root,root) %{_sysconfdir}/audit/audit.rules
%config %attr(640,root,root) %{_sysconfdir}/audit/audit-stop.rules
