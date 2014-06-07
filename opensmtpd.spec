
## global prerelease	201312021558

%if 0%{?rhel} >= 7
%global _with_systemd	1
%endif
%if 0%{?fedora}
%global _with_systemd	1
%endif

# PAM support
%global _with_pam	1

Summary:	Free implementation of the server-side SMTP protocol as defined by RFC 5321
Name:		opensmtpd
Version:	5.4.2p1
Release:	2%{?prerelease:.%{prerelease}}%{?dist}

License:	ISC
URL:		http://www.opensmtpd.org/
Group:		System Environment/Daemons
Provides:	MTA smtpd smtpdaemon server(smtp)

%if 0%{?prerelease}
Source0:	http://www.opensmtpd.org/archives/%{name}-%{prerelease}p1.tar.gz
%else
Source0:	http://www.opensmtpd.org/archives/%{name}-%{version}.tar.gz
%endif

Source1:	opensmtpd.service
Source2:	opensmtpd.init
Source3:	opensmtpd.pam

# not related to systemd but can set proper dependency
%if 0%{?_with_systemd}
BuildRequires:	libdb4-devel
%else
BuildRequires:	db4-devel
%endif
BuildRequires:	libevent-devel
BuildRequires:	openssl-devel
BuildRequires:	bison
BuildRequires:	automake
BuildRequires:	libtool
%if 0%{?_with_pam}
BuildRequires:	pam-devel
%endif
%if 0%{?_with_systemd}
Requires(post):		systemd
Requires(preun):	systemd
Requires(postun):	systemd
BuildRequires:		systemd
%else
Requires:	initscripts
Requires:	chkconfig
%endif
Requires(pre):	shadow-utils

%description
OpenSMTPD is a FREE implementation of the server-side SMTP protocol as defined
by RFC 5321, with some additional standard extensions. It allows ordinary
machines to exchange e-mails with other systems speaking the SMTP protocol.
Started out of dissatisfaction with other implementations, OpenSMTPD nowadays
is a fairly complete SMTP implementation. OpenSMTPD is primarily developed
by Gilles Chehade, Eric Faurot and Charles Longeau; with contributions from
various OpenBSD hackers. OpenSMTPD is part of the OpenBSD Project.
The software is freely usable and re-usable by everyone under an ISC license.

This package uses standard "alternatives" mechanism, you may call
"/usr/sbin/alternatives --set mta /usr/sbin/sendmail.opensmtpd"
if you want to switch to OpenSMTPD MTA immediately after install, and
"/usr/sbin/alternatives --set mta /usr/sbin/sendmail.sendmail" to revert
back to Sendmail as a default mail daemon.


%prep
%setup -q %{?prerelease: -n %{name}-%{prerelease}p1}

%build
# db4 paths
export CFLAGS="$CFLAGS -g -I%{_includedir}/libdb4"
export LDFLAGS="$LDFLAGS -L%{_libdir}/libdb4"

%configure \
    --sysconfdir=%{_sysconfdir}/opensmtpd \
    --with-ca-file=%{_sysconfdir}/pki/tls/cert.pem \
    --with-mantype=man \
    %if 0%{?_with_pam}
    --with-pam \
    --with-pam-service=smtp \
    %endif
    --with-privsep-user=smtpd \
    --with-queue-user=smtpq \
    --with-privsep-path=%{_localstatedir}/empty/smtpd \
    --with-sock-dir=%{_localstatedir}/run

make %{?_smp_mflags}

%install
make install DESTDIR=%{buildroot}
mkdir -p -m 0755 %{buildroot}/%{_localstatedir}/empty/smtpd
%if 0%{?_with_systemd}
install -Dpm 0644 %SOURCE1 %{buildroot}/%{_unitdir}/opensmtpd.service
%else
install -Dpm 0755 %SOURCE2 %{buildroot}/%{_initrddir}/opensmtpd
%endif
%if 0%{?_with_pam}
install -Dpm 0644 %SOURCE3 %{buildroot}/%{_sysconfdir}/pam.d/smtp.opensmtpd
%endif
rm -rf %{buildroot}/%{_bindir}/sendmail
rm -rf %{buildroot}/%{_sbindir}/mailq
rm -rf %{buildroot}/%{_sbindir}/newaliases
mv %{buildroot}/%{_sbindir}/makemap %{buildroot}/%{_sbindir}/makemap.%{name}
ln -s %{_sbindir}/smtpctl %{buildroot}/%{_sbindir}/sendmail.%{name}
ln -s %{_sbindir}/smtpctl %{buildroot}/%{_bindir}/mailq.%{name}
ln -s %{_sbindir}/makemap.%{name} %{buildroot}/%{_bindir}/newaliases.%{name}
mv %{buildroot}/%{_mandir}/man5/aliases.5 %{buildroot}/%{_mandir}/man5/aliases.opensmtpd.5
mv %{buildroot}/%{_mandir}/man8/sendmail.8 %{buildroot}/%{_mandir}/man8/sendmail.opensmtpd.8
mv %{buildroot}/%{_mandir}/man8/makemap.8 %{buildroot}/%{_mandir}/man8/makemap.opensmtpd.8
mv %{buildroot}/%{_mandir}/man8/smtpd.8 %{buildroot}/%{_mandir}/man8/smtpd.opensmtpd.8
# fix aliases path in the config
sed -i -e 's|/etc/mail/aliases|/etc/aliases|g' %{buildroot}/%{_sysconfdir}/opensmtpd/smtpd.conf

%pre
getent group smtpd &>/dev/null || %{_sbindir}/groupadd -r smtpd
getent group smtpq &>/dev/null || %{_sbindir}/groupadd -r smtpq
getent passwd smtpd &>/dev/null || \
    %{_sbindir}/useradd -r -g smtpd -s /sbin/nologin -c "opensmtpd privsep user" -d %{_localstatedir}/empty/smtpd smtpd
getent passwd smtpq &>/dev/null || \
    %{_sbindir}/useradd -r -g smtpq -s /sbin/nologin -c "opensmtpd queue user" -d %{_localstatedir}/empty/smtpd smtpq
exit 0

%post
%if 0%{?_with_systemd}
%systemd_post %{name}.service
%else
/sbin/chkconfig --add opensmtpd
%endif
%{_sbindir}/alternatives --install %{_sbindir}/sendmail mta %{_sbindir}/sendmail.opensmtpd 10 \
	--slave %{_bindir}/mailq mta-mailq %{_bindir}/mailq.opensmtpd \
	--slave /etc/pam.d/smtp mta-pam /etc/pam.d/smtp.opensmtpd \
	--slave %{_bindir}/newaliases mta-newaliases %{_bindir}/newaliases.opensmtpd \
	--slave %{_sbindir}/makemap mta-makemap %{_sbindir}/makemap.opensmtpd \
	--slave /usr/lib/sendmail mta-sendmail %{_sbindir}/sendmail.opensmtpd \
	--slave %{_mandir}/man1/makemap.1.gz mta-makemapman %{_mandir}/man8/makemap.opensmtpd.8.gz \
	--slave %{_mandir}/man1/mailq.1.gz mta-mailqman %{_mandir}/man8/smtpctl.8.gz \
	--slave %{_mandir}/man1/newaliases.1.gz mta-newaliasesman %{_mandir}/man8/newaliases.8.gz \
	--slave %{_mandir}/man5/aliases.5.gz mta-aliasesman %{_mandir}/man5/aliases.opensmtpd.5.gz \
	--slave %{_mandir}/man8/sendmail.8.gz mta-sendmailman %{_mandir}/man8/sendmail.opensmtpd.8.gz \
	--slave %{_mandir}/man8/smtpd.8.gz mta-smtpdman %{_mandir}/man8/smtpd.opensmtpd.8.gz \
	--initscript opensmtpd
exit 0

%preun
%if 0%{?_with_systemd}
%systemd_preun %{name}.service
%else
if [ $1 = 0 ]; then
	/sbin/service opensmtpd stop > /dev/null 2>&1
	/sbin/chkconfig --del opensmtpd
fi
%endif
if [ "$1" = 0 ]; then
    %{_sbindir}/alternatives --remove mta %{_sbindir}/sendmail.opensmtpd
fi
exit 0

%postun
%if 0%{?_with_systemd}
%systemd_postun_with_restart %{name}.service
%else
if [ "$1" -ge "1" ]; then
	/sbin/service opensmtpd condrestart > /dev/null 2>&1
fi
%endif
if [ "$1" -ge "1" ]; then
	mta=`readlink /etc/alternatives/mta`
	if [ "$mta" == "%{_sbindir}/sendmail.opensmtpd" ]; then
	    /usr/sbin/alternatives --set mta %{_sbindir}/sendmail.opensmtpd
	fi
fi
exit 0


%files
%dir %attr(0711,root,root) %{_localstatedir}/empty/smtpd
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/smtpd.conf
%doc LICENSE README.md THANKS
%{_mandir}/man5/*.5*
%{_mandir}/man8/*.8*
%if 0%{?_with_pam}
%config(noreplace) %{_sysconfdir}/pam.d/smtp.%{name}
%endif
%if 0%{?_with_systemd}
%{_unitdir}/%{name}.service
%else
%{_initrddir}/opensmtpd
%endif
%{_libexecdir}/%{name}
%{_bindir}/mailq.%{name}
%{_bindir}/newaliases.%{name}
%{_sbindir}/sendmail.%{name}
%{_sbindir}/makemap.%{name}
%{_sbindir}/smtpctl
%{_sbindir}/smtpd


%changelog
* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 5.4.2p1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu Mar 06 2014 Denis Fateyev <denis@fateyev.com> - 5.4.2p1-1
- Small enhancements, man-page and pam fixes
- Update to 5.4.2 release

* Mon Dec 09 2013 Denis Fateyev <denis@fateyev.com> - 5.4.1p1-1
- Multiple enhancements, systemd migration, spec cleanup
- Update to 5.4.1 release

* Wed Sep 04 2013 Denis Fateyev <denis@fateyev.com> - 5.3.3p1-2
- Better snapshots support, script cleanup

* Mon Jun 10 2013 Denis Fateyev <denis@fateyev.com> - 5.3.3p1-1
- Initial release
