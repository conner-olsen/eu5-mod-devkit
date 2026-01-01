#!/bin/bash
set -e # Stop the script if any command fails

# --- Configuration ---
VERSION="v0.1"

# --- Script ---
# 1. Switch to release
git checkout release

# 2. Wipe current directory
git rm -rf .

# 3. Overwrite everything with the current version from main
git checkout main -- .

# 4. Remove this script
git rm -f create-devkit-release.sh
git rm -f README.md

# 5. Commit and Push
git commit -m "$VERSION"
git push origin release

# 6. Return to main
git checkout main