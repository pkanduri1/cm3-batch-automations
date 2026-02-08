#!/bin/bash

# Build script for creating PEX executable
# Usage: ./build_pex.sh

set -e

echo "Building CM3 Batch Automations PEX..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pex is installed
if ! command -v pex &> /dev/null; then
    echo -e "${YELLOW}pex not found, installing...${NC}"
    pip install pex
fi

# Check Python version
if command -v python3.9 &> /dev/null; then
    PYTHON_VERSION=$(python3.9 --version 2>&1 | awk '{print $2}')
    PYTHON_CMD="python3.9"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_CMD="python3"
else
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    PYTHON_CMD="python"
fi

echo -e "${GREEN}Using Python ${PYTHON_VERSION}${NC}"

# Create dist directory
mkdir -p dist

# Clean previous build
if [ -f "dist/cm3-batch.pex" ]; then
    echo -e "${YELLOW}Removing previous build...${NC}"
    rm dist/cm3-batch.pex
fi

# Build PEX
echo -e "${GREEN}Building PEX file...${NC}"
pex . \
  --requirement requirements.txt \
  --entry-point src.main:main \
  --output-file dist/cm3-batch.pex \
  --python-shebang="/usr/bin/env ${PYTHON_CMD}" \
  --inherit-path=prefer \
  --compile

# Make executable
chmod +x dist/cm3-batch.pex

# Get file size
FILE_SIZE=$(du -h dist/cm3-batch.pex | cut -f1)

echo -e "${GREEN}✓ PEX build complete!${NC}"
echo -e "Output: dist/cm3-batch.pex (${FILE_SIZE})"
echo ""
echo "To deploy:"
echo "  1. Copy dist/cm3-batch.pex to target server"
echo "  2. Ensure Oracle Instant Client is installed"
echo "  3. Copy config/ directory"
echo "  4. Create .env file with credentials"
echo "  5. Run: ./cm3-batch.pex"
echo ""
echo "See docs/PEX_DEPLOYMENT.md for detailed instructions"
