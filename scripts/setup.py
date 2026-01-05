import os, subprocess, sys

# --- Configuration ---
DEVKIT_URL = "https://github.com/conner-olsen/eu5-mod-devkit.git"
REMOTE_NAME = "devkit"
REMOTE_BRANCH = "devkit-release"

# --- Path Setup ---
SCRIPT_FILE = os.path.abspath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_FILE)
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

# Check for uncommitted changes (Ignoring this script itself)
status_output = run_git(["status", "--porcelain"])
if status_output:
    # Filter out the running script from the status list
    lines = status_output.splitlines()
    real_changes = [line for line in lines if not line.strip().endswith(SCRIPT_NAME)]

    if real_changes:
        print("Error: You have uncommitted changes in your repository.")
        print("Please Commit or Stash your changes before running this script.")
        print("This ensures your work isn't accidentally overwritten or mixed into the template.")
        print("\nUncommitted files:")
        for line in real_changes:
            print(line)
        sys.exit(1)

current_remotes = run_git(["remote"])
if not current_remotes or "origin" not in current_remotes:
    print("Error: No 'origin' remote found.")
    print("Please link your repository to GitHub (or another remote) before running this script.")
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
print("  [y] Yes (Default): Overwrite local files with template versions.")
print("      Overwrites will be STAGED but NOT commited so you can review and revert any unwanted changes.")
print("  [n] No: Keep your local files. Only adds new template files (no overwrites).")

while True:
    choice = input("\nOverwrite local files with template? [y/n]: ").strip().lower()
    if choice in ["", "y", "yes"]:
        overwrite = True
        break
    elif choice in ["n", "no"]:
        overwrite = False
        break

# 4. Step 1: The Link (Safe Merge)
print(f"\nLinking devkit history...")

run_git([
    "merge",
    "--no-commit",
    "--allow-unrelated-histories",
    "-s", "recursive",
    "-X", "ours",
    f"{REMOTE_NAME}/{REMOTE_BRANCH}"
])

# --- CLEANUP STEP 1: Remove temporary files from the merge commit ---
# 1. Remove the setup script so it isn't committed
run_git(["rm", "-f", "--ignore-unmatch", "scripts/setup.py"], check=False)
# 2. Remove the dummy file so it isn't committed
run_git(["rm", "-f", "--ignore-unmatch", "in_game/common/dummy.txt"], check=False)

# Now we finalize the commit.
run_git(["commit", "-m", "Link devkit history"])

# 5. Step 2: The Content (Overwrite)
if overwrite:
    print("Applying template files...")

    # Forcefully checkout the release files from the remote.
    run_git(["checkout", f"{REMOTE_NAME}/{REMOTE_BRANCH}", "--", "."])

    # --- CLEANUP STEP 2: Remove temporary files from the overwrite stage ---
    # Remove them again because 'checkout' brought them back from the remote
    run_git(["rm", "-f", "--ignore-unmatch", "scripts/setup.py"], check=False)
    run_git(["rm", "-f", "--ignore-unmatch", "in_game/common/dummy.txt"], check=False)

    print("\n--- Devkit Linked Successfully ---")
    print("If there were any conflicts, they will now appear as uncommited changes for review.")

else:
    print("\nSuccess! Devkit linked (local files preserved).")

# 6. Self-Destruct
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass