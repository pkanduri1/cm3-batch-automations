#!/usr/bin/env bash
set -euo pipefail

# CM3 Batch Automations - RHEL 8.9 Setup Script
# This script automates the setup process for RHEL servers.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CM3 Batch Automations Setup for RHEL...${NC}"

# Check for RHEL/CentOS/Rocky 8+
if [ -f /etc/redhat-release ]; then
    VERSION_ID=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
    if [ "$VERSION_ID" -lt 8 ]; then
        echo -e "${YELLOW}Warning: Detected RHEL/CentOS version < 8. This script is optimized for RHEL 8+.${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Parameters check passed: $(cat /etc/redhat-release)${NC}"
    fi
else
    echo -e "${YELLOW}Warning: Not running on a RedHat-based system.${NC}"
fi

cd "$PROJECT_ROOT"

# 1. System Dependencies
echo -e "\n${YELLOW}[1/6] Installing system dependencies...${NC}"
echo "We need sudo access to install packages. You may be prompted for your password."

sudo dnf update -y
sudo dnf install -y python39 python39-devel python39-pip gcc make wget unzip libaio

# 2. Oracle Instant Client (Optional)
echo -e "\n${YELLOW}[2/6] Oracle Instant Client checks...${NC}"
if [ -d "/opt/oracle/instantclient_19_23" ] || [ -d "/usr/lib/oracle" ]; then
    echo -e "${GREEN}✅ Oracle Instant Client appears to be installed.${NC}"
else
    echo -e "${YELLOW}Oracle Instant Client not found in standard locations.${NC}"
    echo "The application works in 'Thin Mode' without Instant Client for most cases."
    echo "However, for advanced features or legacy connectivity, you might need it."
    echo "Skipping automatic installation (refer to docs/ORACLE_RHEL_SETUP.md for manual steps)."
fi

# 3. Virtual Environment
echo -e "\n${YELLOW}[3/6] Creating virtual environment (.venv)...${NC}"
if [ -d ".venv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    python3.9 -m venv .venv
    echo -e "${GREEN}✅ Virtual environment created.${NC}"
fi

# 4. Python Dependencies
echo -e "\n${YELLOW}[4/6] Installing Python dependencies...${NC}"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e . # Install CLI tool
echo -e "${GREEN}✅ Dependencies installed.${NC}"

# 5. Configuration Setup
echo -e "\n${YELLOW}[5/6] Setting up configuration...${NC}"

# Create directories
mkdir -p logs data/samples data/mappings reports uploads config/mappings config/rules
echo "Created working directories."

# .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env from template.${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANT: Please edit .env with your Oracle credentials!${NC}"
    else
        echo -e "${RED}Error: .env.example not found!${NC}"
    fi
else
    echo ".env already exists. Skipping."
fi

# Set permissions (safe defaults)
chmod 600 .env 2>/dev/null || true
chmod 755 scripts/*.sh

# 6. Verification
echo -e "\n${YELLOW}[6/6] Verifying setup...${NC}"
if command -v cm3-batch >/dev/null; then
    echo -e "${GREEN}✅ CLI tool 'cm3-batch' is ready.${NC}"
    cm3-batch --version 2>/dev/null || echo "cm3-batch installed."
else
    echo -e "${RED}❌ CLI tool installation failed.${NC}"
fi

echo -e "\n${GREEN}🎉 Setup Complete!${NC}"
echo -e "To start using the application:"
echo -e "  1. Edit configuration: ${YELLOW}nano .env${NC}"
echo -e "  2. Activate environment: ${YELLOW}source .venv/bin/activate${NC}"
echo -e "  3. Run help: ${YELLOW}cm3-batch --help${NC}"
