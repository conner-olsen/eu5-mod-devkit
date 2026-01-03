#!/bin/bash
set -e # Stop the script if any command fails

# --- Configuration ---
VERSION="Devkit v0.1"

# --- Script ---
# 1. Navigate to repo root
cd "$(dirname "$0")/.."

# 2. Switch to main
git checkout main

# 3. Delete release branch everywhere
git branch -D devkit-release
git push origin --delete devkit-release

# 4. Create fresh Orphan branch
git checkout --orphan devkit-release

# 5. Wipe directory
git rm -rf .

# 6. Overwrite everything with the current version from main
git checkout main -- .

# 7. Remove dev-only files
git rm -f README.md
git rm -f LICENSE
git rm -f scripts/create-devkit-release.sh
git rm -f scripts/reset-release.sh

# 8. Commit and Push
git commit -m "$VERSION"
git push origin devkit-release

# 9. Return to main
git checkout main