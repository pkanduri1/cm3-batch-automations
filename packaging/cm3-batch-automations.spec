Name:           cm3-batch-automations
Version:        0.1.0
Release:        1%{?dist}
Summary:        CM3 Batch Automations - File parsing and validation tool

License:        Proprietary
URL:            https://gitlab.com/your-org/cm3-batch-automations
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python39 >= 3.9.0
Requires:       python39-pip

%description
Automated file parsing, validation, and comparison tool for CM3 batch
processing with Oracle database integration.

Features:
- File parsing (pipe-delimited, fixed-width)
- Oracle database connectivity
- Data validation and comparison
- HTML report generation
- Configurable for multiple environments

%prep
%setup -q

%build
# Nothing to build for pure Python

%install
rm -rf %{buildroot}

# Create directories
mkdir -p %{buildroot}/opt/cm3-batch-automations
mkdir -p %{buildroot}/etc/cm3-batch
mkdir -p %{buildroot}/var/log/cm3-batch
mkdir -p %{buildroot}/var/lib/cm3-batch/data
mkdir -p %{buildroot}/var/lib/cm3-batch/reports
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_bindir}

# Copy application files
cp -r src %{buildroot}/opt/cm3-batch-automations/
cp -r tests %{buildroot}/opt/cm3-batch-automations/
cp -r docs %{buildroot}/opt/cm3-batch-automations/
cp requirements.txt %{buildroot}/opt/cm3-batch-automations/
cp setup.py %{buildroot}/opt/cm3-batch-automations/
cp README.md %{buildroot}/opt/cm3-batch-automations/
cp pytest.ini %{buildroot}/opt/cm3-batch-automations/
cp .flake8 %{buildroot}/opt/cm3-batch-automations/

# Copy configuration
cp -r config/* %{buildroot}/etc/cm3-batch/
cp .env.example %{buildroot}/etc/cm3-batch/

# Create systemd service file
cat > %{buildroot}%{_unitdir}/cm3-batch.service << 'EOF'
[Unit]
Description=CM3 Batch Automations
After=network.target

[Service]
Type=simple
User=cm3app
Group=cm3app
WorkingDirectory=/opt/cm3-batch-automations
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="ORACLE_HOME=/opt/oracle/instantclient_19_23"
Environment="LD_LIBRARY_PATH=/opt/oracle/instantclient_19_23"
EnvironmentFile=-/etc/cm3-batch/.env
ExecStart=/usr/bin/python3.9 -m src.main
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Create command-line wrapper
cat > %{buildroot}%{_bindir}/cm3-batch << 'EOF'
#!/bin/bash
cd /opt/cm3-batch-automations
[ -f /etc/cm3-batch/.env ] && source /etc/cm3-batch/.env
export ORACLE_HOME=${ORACLE_HOME:-/opt/oracle/instantclient_19_23}
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-$ORACLE_HOME}
exec /usr/bin/python3.9 -m src.main "$@"
EOF
chmod +x %{buildroot}%{_bindir}/cm3-batch

%pre
# Create user if it doesn't exist
getent group cm3app >/dev/null || groupadd -r cm3app
getent passwd cm3app >/dev/null || \
    useradd -r -g cm3app -d /opt/cm3-batch-automations -s /sbin/nologin \
    -c "CM3 Batch Automations" cm3app
exit 0

%post
# Install Python dependencies
cd /opt/cm3-batch-automations
/usr/bin/python3.9 -m pip install --quiet --user -r requirements.txt 2>/dev/null || true

# Set permissions
chown -R cm3app:cm3app /opt/cm3-batch-automations
chown -R cm3app:cm3app /var/log/cm3-batch
chown -R cm3app:cm3app /var/lib/cm3-batch
chmod 750 /etc/cm3-batch
if [ -f /etc/cm3-batch/.env ]; then
    chmod 600 /etc/cm3-batch/.env
fi
chmod 600 /etc/cm3-batch/.env.example

# Reload systemd
systemctl daemon-reload >/dev/null 2>&1 || true

cat << 'POSTEOF'

========================================
CM3 Batch Automations installed!
========================================

Next steps:

1. Install Oracle Instant Client:
   See /opt/cm3-batch-automations/docs/RHEL_DEPLOYMENT.md

2. Configure application:
   sudo cp /etc/cm3-batch/.env.example /etc/cm3-batch/.env
   sudo vim /etc/cm3-batch/.env
   sudo chmod 600 /etc/cm3-batch/.env

3. Start service:
   sudo systemctl enable cm3-batch
   sudo systemctl start cm3-batch

4. Check status:
   sudo systemctl status cm3-batch

Documentation: /opt/cm3-batch-automations/docs/
========================================

POSTEOF

%preun
if [ $1 -eq 0 ]; then
    # Uninstall
    systemctl stop cm3-batch.service 2>/dev/null || true
    systemctl disable cm3-batch.service 2>/dev/null || true
fi

%postun
if [ $1 -eq 0 ]; then
    # Uninstall - cleanup
    systemctl daemon-reload >/dev/null 2>&1 || true
    echo "CM3 Batch Automations removed."
    echo "Configuration preserved in /etc/cm3-batch/"
    echo "To remove completely: sudo rm -rf /etc/cm3-batch"
fi

%files
%defattr(-,root,root,-)
%doc README.md
%doc docs/
/opt/cm3-batch-automations/
%dir %attr(0750,root,cm3app) /etc/cm3-batch
%config(noreplace) %attr(0640,root,cm3app) /etc/cm3-batch/*.json
%config(noreplace) %attr(0600,root,cm3app) /etc/cm3-batch/.env.example
%dir %attr(0755,cm3app,cm3app) /var/log/cm3-batch
%dir %attr(0755,cm3app,cm3app) /var/lib/cm3-batch
%dir %attr(0755,cm3app,cm3app) /var/lib/cm3-batch/data
%dir %attr(0755,cm3app,cm3app) /var/lib/cm3-batch/reports
%{_unitdir}/cm3-batch.service
%attr(0755,root,root) %{_bindir}/cm3-batch

%changelog
* Thu Feb 06 2026 Development Team <dev@example.com> - 0.1.0-1
- Initial RPM release
- Core modules implemented:
  * File parsers (pipe-delimited, fixed-width)
  * Oracle database connectivity
  * Data validators and comparators
  * HTML report generation
  * Configuration management
- Systemd service integration
- RHEL 8.9 compatible
- Comprehensive documentation included
