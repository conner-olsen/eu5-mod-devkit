#!/bin/bash
set -e # Stop the script if any command fails

# --- Configuration ---
VERSION="Devkit v0.5"

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
git rm -f scripts/create-devkit-release.sh
git rm -f scripts/reset-release.sh
git rm -f assets/images/mod-id-location.png
git mv -f README-TEMPLATE.md README.md

# 6. Reset Workshop item ID for release branch
python - <<'PY'
import re

path = "scripts/config.toml"
with open(path, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

pattern = re.compile(r"^(\s*workshop_upload_item_id\s*=\s*)([^#]*?)(\s*)(#.*)?$")
updated = False
for idx, line in enumerate(lines):
    match = pattern.match(line)
    if match:
        prefix, _old_value, gap, comment = match.groups()
        comment = comment or ""
        if comment and not gap:
            gap = " "
        elif not comment:
            gap = ""
        lines[idx] = f"{prefix}0{gap}{comment}".rstrip()
        updated = True
        break

if not updated:
    lines.append("workshop_upload_item_id = 0")

with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY

# 7. Commit and Push
git commit -m "$VERSION"
git push origin devkit-release

# 8. Return to main
git checkout main
