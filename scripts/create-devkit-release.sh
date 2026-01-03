#!/bin/bash
set -e # Stop the script if any command fails

# --- Configuration ---
VERSION="Devkit v0.2"

# --- Script ---
# 1. Navigate to repo root
cd "$(dirname "$0")/.."

# 2. Switch to release
git checkout devkit-release

# 3. Wipe current directory
git rm -rf .

# 4. Overwrite everything with the current version from main
git checkout main -- .

# 5. Remove dev-only files
git rm -f README.md
git rm -f LICENSE
git rm -f scripts/create-devkit-release.sh
git rm -f scripts/reset-release.sh

# 6. Commit and Push
git commit -m "$VERSION"
git push origin devkit-release

# 7. Return to main
git checkout main