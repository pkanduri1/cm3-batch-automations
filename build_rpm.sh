#!/bin/bash

# Build script for creating RPM package
# Usage: ./build_rpm.sh

set -e

echo "Building CM3 Batch Automations RPM..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if rpm-build is installed
if ! command -v rpmbuild &> /dev/null; then
    echo -e "${RED}Error: rpmbuild is not installed${NC}"
    echo "Install with: sudo yum install -y rpm-build rpmdevtools"
    exit 1
fi

# Get version from setup.py
VERSION=$(grep "version=" setup.py | cut -d'"' -f2)
echo -e "${GREEN}Version: ${VERSION}${NC}"

# Setup RPM build directory
if [ ! -d "$HOME/rpmbuild" ]; then
    echo -e "${YELLOW}Setting up RPM build directory...${NC}"
    rpmdev-setuptree
fi

# Create source tarball
echo -e "${GREEN}Creating source tarball...${NC}"
tar -czf "$HOME/rpmbuild/SOURCES/cm3-batch-automations-${VERSION}.tar.gz" \
    --transform "s,^,cm3-batch-automations-${VERSION}/," \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.pytest_cache' \
    --exclude='htmlcov' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='*.egg-info' \
    --exclude='rpmbuild' \
    .

# Copy spec file
echo -e "${GREEN}Copying spec file...${NC}"
mkdir -p packaging
cp packaging/cm3-batch-automations.spec "$HOME/rpmbuild/SPECS/" 2>/dev/null || {
    echo -e "${YELLOW}Spec file not found, creating default...${NC}"
    # Create default spec file if it doesn't exist
    cat > "$HOME/rpmbuild/SPECS/cm3-batch-automations.spec" << 'EOF'
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
mkdir -p %{buildroot}/var/lib/cm3-batch
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_bindir}

# Copy application files
cp -r src %{buildroot}/opt/cm3-batch-automations/
cp -r tests %{buildroot}/opt/cm3-batch-automations/
cp requirements.txt %{buildroot}/opt/cm3-batch-automations/
cp setup.py %{buildroot}/opt/cm3-batch-automations/
cp README.md %{buildroot}/opt/cm3-batch-automations/
cp pytest.ini %{buildroot}/opt/cm3-batch-automations/
cp .flake8 %{buildroot}/opt/cm3-batch-automations/

# Copy configuration
cp -r config/* %{buildroot}/etc/cm3-batch/
cp .env.example %{buildroot}/etc/cm3-batch/

# Create systemd service file
cat > %{buildroot}%{_unitdir}/cm3-batch.service << 'SERVICEEOF'
[Unit]
Description=CM3 Batch Automations
After=network.target

[Service]
Type=simple
User=cm3app
Group=cm3app
WorkingDirectory=/opt/cm3-batch-automations
EnvironmentFile=/etc/cm3-batch/.env
ExecStart=/usr/bin/python3.9 -m src.main
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Create command-line wrapper
cat > %{buildroot}%{_bindir}/cm3-batch << 'WRAPPEREOF'
#!/bin/bash
cd /opt/cm3-batch-automations
source /etc/cm3-batch/.env 2>/dev/null || true
exec /usr/bin/python3.9 -m src.main "$@"
WRAPPEREOF
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
/usr/bin/python3.9 -m pip install --user -r requirements.txt

# Set permissions
chown -R cm3app:cm3app /opt/cm3-batch-automations
chown -R cm3app:cm3app /var/log/cm3-batch
chown -R cm3app:cm3app /var/lib/cm3-batch
chmod 750 /etc/cm3-batch
chmod 600 /etc/cm3-batch/.env.example

# Reload systemd
systemctl daemon-reload

echo "CM3 Batch Automations installed successfully!"
echo "Next steps:"
echo "  1. Install Oracle Instant Client"
echo "  2. Configure /etc/cm3-batch/.env"
echo "  3. Start service: systemctl start cm3-batch"

%preun
if [ $1 -eq 0 ]; then
    # Uninstall
    systemctl stop cm3-batch.service 2>/dev/null || true
    systemctl disable cm3-batch.service 2>/dev/null || true
fi

%postun
if [ $1 -eq 0 ]; then
    # Uninstall
    systemctl daemon-reload
fi

%files
%defattr(-,root,root,-)
/opt/cm3-batch-automations/
%config(noreplace) /etc/cm3-batch/
%attr(0755,cm3app,cm3app) /var/log/cm3-batch
%attr(0755,cm3app,cm3app) /var/lib/cm3-batch
%{_unitdir}/cm3-batch.service
%attr(0755,root,root) %{_bindir}/cm3-batch

%changelog
* Thu Feb 06 2026 Development Team <dev@example.com> - 0.1.0-1
- Initial RPM release
- Core modules: parsers, database, validators, comparators
- Configuration management
- HTML reporting
- Systemd service integration
EOF
}

# Build RPM
echo -e "${GREEN}Building RPM package...${NC}"
rpmbuild -ba "$HOME/rpmbuild/SPECS/cm3-batch-automations.spec"

# Find the built RPM
RPM_FILE=$(find "$HOME/rpmbuild/RPMS" -name "cm3-batch-automations-*.rpm" | head -1)

if [ -n "$RPM_FILE" ]; then
    FILE_SIZE=$(du -h "$RPM_FILE" | cut -f1)
    echo -e "${GREEN}✓ RPM build complete!${NC}"
    echo -e "Output: ${RPM_FILE} (${FILE_SIZE})"
    echo ""
    echo "To install:"
    echo "  sudo yum install -y ${RPM_FILE}"
    echo ""
    echo "See docs/RPM_DEPLOYMENT.md for detailed instructions"
else
    echo -e "${RED}Error: RPM file not found${NC}"
    exit 1
fi
