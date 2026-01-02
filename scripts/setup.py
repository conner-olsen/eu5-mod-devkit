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
        # If check is False, just return None on error
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
    print("This ensures your mod keeps its own identity.")
    sys.exit(1)

# 2. Setup Remote
if REMOTE_NAME not in current_remotes:
    run_git(["remote", "add", "-t", REMOTE_BRANCH, REMOTE_NAME, DEVKIT_URL])
else:
    run_git(["remote", "set-branches", REMOTE_NAME, REMOTE_BRANCH])

run_git(["remote", "set-url", "--push", REMOTE_NAME, "no_push"])
run_git(["fetch", REMOTE_NAME])

# 3. Native Merge
# Use -X to merge the files in, but keep all present files.
# --no-commit pauses the merge to remove the setup script before finishing.
print("Merging devkit tools...")
run_git([
    "merge",
    "--no-commit",
    "--allow-unrelated-histories",
    "-s", "recursive",
    "-X", "ours",
    f"{REMOTE_NAME}/{REMOTE_BRANCH}"
])

# 4. Cleanup Staged Files
# Remove scripts/setup.py from the staging area so it doesn't get committed to the repo.
run_git(["rm", "-f", "--ignore-unmatch", "scripts/setup.py"], check=False)

# 5. Finalize Commit
run_git(["commit", "-m", "Initialize devkit"])

# 6. Self-Destruct
# Delete the running script (root level)
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass

print("Success! Devkit installed.")