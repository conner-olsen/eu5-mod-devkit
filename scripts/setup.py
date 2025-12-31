import os, shutil, subprocess, stat, sys

# --- Configuration ---
DEVKIT_URL = "https://github.com/conner-olsen/eu5-mod-devkit.git"
REMOTE_NAME = "devkit"
TARGET_BRANCH = "tools/devkit"

# --- Path Setup ---
SCRIPT_FILE = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_FILE)

# Detect if running from root or inside scripts/
if os.path.basename(SCRIPT_DIR) == "scripts":
    ROOT_DIR = os.path.dirname(SCRIPT_DIR)
else:
    ROOT_DIR = SCRIPT_DIR

TEMP_DIR = os.path.join(ROOT_DIR, "_devkit_temp_clone")

# --- Functions ---
def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def run_git(args, cwd=ROOT_DIR):
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

# --- Script ---

# 1. Reset if this is a fresh clone of the Devkit itself
git_dir = os.path.join(ROOT_DIR, ".git")

if os.path.exists(git_dir):
    current_url = run_git(["remote", "get-url", "origin"])
    if current_url and "conner-olsen/eu5-mod-devkit" in current_url:
        shutil.rmtree(git_dir, onerror=on_rm_error)

# 2. Initialize Git if missing
is_new_repo = False
if not os.path.exists(git_dir):
    run_git(["init"])
    run_git(["branch", "-M", "main"])
    is_new_repo = True

# 3. Clone Devkit to Temp Directory
if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR, onerror=on_rm_error)

run_git(["clone", "--depth", "1", DEVKIT_URL, TEMP_DIR], cwd=ROOT_DIR)

# 4. Copy Files (No Overwrite)
if os.path.exists(TEMP_DIR):
    for root, dirs, files in os.walk(TEMP_DIR):
        if ".git" in dirs:
            dirs.remove(".git")

        rel_path = os.path.relpath(root, TEMP_DIR)
        dest_dir = os.path.join(ROOT_DIR, rel_path)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_dir, file)

            if not os.path.exists(dest_file):
                shutil.copy2(src_file, dest_file)

    shutil.rmtree(TEMP_DIR, onerror=on_rm_error)

# 5. Create Initial Commit (Only for new repos)
if is_new_repo:
    run_git(["add", "."])
    run_git(["commit", "-m", "Initialize mod from devkit"])

# 6. Setup Remote
# Add the remote if it doesn't exist
existing_remotes = run_git(["remote"])
if not existing_remotes or REMOTE_NAME not in existing_remotes:
    run_git(["remote", "add", REMOTE_NAME, DEVKIT_URL])

# Disable pushing to the devkit remote
run_git(["remote", "set-url", "--push", REMOTE_NAME, "no_push"])

# Fetch the remote data (this creates remotes/devkit/main)
run_git(["fetch", REMOTE_NAME])

# 7. Setup Tracking Branch (tools/devkit)
run_git(["branch", "--track", TARGET_BRANCH, f"{REMOTE_NAME}/main"])

# 8. Self-Destruct
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass