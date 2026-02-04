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
git rm -f scripts/create-devkit-release.sh
git rm -f scripts/reset-release.sh
git mv -f README-TEMPLATE.md README.md

# 8. Create .env from template for release
cp -f .env-template .env

# 9. Commit and Push
git commit -m "$VERSION"
git push origin devkit-release

# 10. Return to main
git checkout main
