#!/bin/bash
# Dependency Update Script for Marketing OS
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
BACKUP_FILE="$REQUIREMENTS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "=== Marketing OS Dependency Updater ==="
cp "$REQUIREMENTS_FILE" "$BACKUP_FILE"
echo "Backup saved to: $BACKUP_FILE"
pip install --upgrade -r "$REQUIREMENTS_FILE"
echo "Done! Run tests to verify."
