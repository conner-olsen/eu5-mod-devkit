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
print("      Changes will be STAGED for review in GitHub Desktop.")
print("  [n] No: Keep your local files. Only adds new template files (no overwrites).")

while True:
    choice = input("\nOverwrite local files with template? [Y/n]: ").strip().lower()
    if choice in ["", "y", "yes"]:
        overwrite = True
        break
    elif choice in ["n", "no"]:
        overwrite = False
        break

# 4. Step 1: The Link (Safe Merge)
# We ALWAYS merge first with '-X ours'.
# This creates the necessary Merge Commit to link the histories safely.
# It brings in new files but refuses to overwrite your existing work.
print(f"\nLinking devkit history...")

run_git([
    "merge",
    "--allow-unrelated-histories",
    "-s", "recursive",
    "-X", "ours",
    "-m", "Link devkit history",
    f"{REMOTE_NAME}/{REMOTE_BRANCH}"
])

# 5. Step 2: The Content (Overwrite)
if overwrite:
    print("Applying template files...")

    # We forcefully checkout the release files from the remote.
    # This updates your working directory to match the template exactly.
    # These show up as "Staged Changes" in GitHub Desktop.
    run_git(["checkout", f"{REMOTE_NAME}/{REMOTE_BRANCH}", "--", "."])

    # Unstage the setup script so it doesn't get committed
    run_git(["rm", "-f", "--ignore-unmatch", "scripts/setup.py"], check=False)

    print("\n--- ACTION REQUIRED ---")
    print("1. History linked successfully.")
    print("2. Template files have been staged for overwrite.")
    print("3. Open GitHub Desktop to review the changes and commit.")

else:
    # If they chose 'No', the previous merge step was enough.
    # We just cleanup the script from the history.
    run_git(["rm", "-f", "--ignore-unmatch", "scripts/setup.py"], check=False)
    run_git(["commit", "--amend", "--no-edit"])

    print("\nSuccess! Devkit linked (local files preserved).")

# 6. Self-Destruct
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass