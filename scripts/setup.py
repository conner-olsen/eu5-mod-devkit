import os, subprocess, sys

# --- Configuration ---
DEVKIT_URL = "https://github.com/conner-olsen/eu5-mod-devkit.git"
REMOTE_NAME = "devkit"
REMOTE_BRANCH = "release"

# --- Path Setup ---
SCRIPT_FILE = os.path.abspath(__file__)
ROOT_DIR = os.getcwd()

# --- Functions ---
def run_git(args, cwd=ROOT_DIR, check=True):
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if not check:
            return None
        print(f"Git Error: {' '.join(args)}\n{e.stderr}")
        sys.exit(1)

# --- Script ---

# 1. Validation Checks
if not os.path.exists(os.path.join(ROOT_DIR, ".git")):
    print("Error: This directory is not a git repository.")
    print("Please initialize your repository (git init) first.")
    sys.exit(1)

current_remotes = run_git(["remote"])
if not current_remotes or "origin" not in current_remotes:
    print("Error: No 'origin' remote found.")
    print("Please link your repository to GitHub using 'git remote add origin ...'")
    sys.exit(1)

# 2. Setup Remote
if REMOTE_NAME not in current_remotes:
    run_git(["remote", "add", "-t", REMOTE_BRANCH, REMOTE_NAME, DEVKIT_URL])
else:
    run_git(["remote", "set-branches", REMOTE_NAME, REMOTE_BRANCH])

run_git(["remote", "set-url", "--push", REMOTE_NAME, "no_push"])
run_git(["fetch", REMOTE_NAME])

# 3. Interactive Prompt
print("\n--- Conflict Resolution Strategy ---")
print("  [Y] Yes (Default): Overwrite local files with template versions.")
print("      Changes will be STAGED so you can review them in GitHub Desktop.")
print("  [n] No: Keep your local files. Template files are only added if they don't exist.")

while True:
    choice = input("\nOverwrite local files with template? [Y/n]: ").strip().lower()
    if choice in ["", "y", "yes"]:
        overwrite = True
        break
    elif choice in ["n", "no"]:
        overwrite = False
        break

# 4. Merge
strategy = "theirs" if overwrite else "ours"
print(f"\nMerging devkit tools...")

# We allow the commit to happen first to clear the MERGING state
run_git([
    "merge",
    "--allow-unrelated-histories",
    "-s", "recursive",
    "-X", strategy,
    "-m", "Initialize devkit",
    f"{REMOTE_NAME}/{REMOTE_BRANCH}"
])

# 5. Cleanup Staged Files (Post-Merge)
# If the setup script got committed, remove it now
run_git(["rm", "-f", "--ignore-unmatch", "scripts/setup.py"], check=False)
# Amend the commit to finalize the removal from history
run_git(["commit", "--amend", "--no-edit"])

# 6. Handle Review Mode (Soft Reset)
if overwrite:
    # This undoes the commit but leaves files Staged (Green in VS Code / Checked in GitHub Desktop)
    # This removes the "MERGING" state so GitHub Desktop behaves normally.
    run_git(["reset", "--soft", "HEAD~1"])

    print("\n--- ACTION REQUIRED ---")
    print("Files have been merged and overwrites are pending.")
    print("Changes are STAGED for review.")
    print("1. Open GitHub Desktop.")
    print("2. Review the files.")
    print("3. Commit when you are ready.")

else:
    print("\nSuccess! Devkit installed (local files preserved).")

# 7. Self-Destruct
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass