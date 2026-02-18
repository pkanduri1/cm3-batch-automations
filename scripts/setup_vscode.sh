#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VSCODE_DIR="$PROJECT_ROOT/.vscode"

mkdir -p "$VSCODE_DIR"

cat > "$VSCODE_DIR/settings.json" <<'JSON'
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "tests/unit",
    "-q",
    "-o",
    "addopts="
  ],
  "files.associations": {
    "*.yml": "yaml",
    "*.yaml": "yaml"
  }
}
JSON

cat > "$VSCODE_DIR/tasks.json" <<'JSON'
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "CM3: Setup (mac/linux)",
      "type": "shell",
      "command": "bash scripts/setup_mac.sh",
      "group": "build"
    },
    {
      "label": "CM3: Run Unit Tests",
      "type": "shell",
      "command": ".venv/bin/pytest -q -o addopts='' tests/unit",
      "group": "test"
    },
    {
      "label": "CM3: Validate Sample",
      "type": "shell",
      "command": "cm3-batch validate -f data/samples/customers.txt -m config/mappings/customer_mapping.json -o reports/validation.html --detailed"
    }
  ]
}
JSON

echo "✅ VS Code workspace files created under .vscode/"
