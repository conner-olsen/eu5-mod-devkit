import os, shutil, subprocess, stat, sys

# --- Configuration ---
DEVKIT_URL = "https://github.com/conner-olsen/eu5-mod-devkit.git"
REMOTE_NAME = "devkit"
TARGET_BRANCH = "tools/devkit"

# --- Path Setup ---
SCRIPT_FILE = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_FILE)

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

# 1. Reset if origin is devkit
git_dir = os.path.join(ROOT_DIR, ".git")

if os.path.exists(git_dir):
    current_url = run_git(["remote", "get-url", "origin"])
    if current_url and "conner-olsen/eu5-mod-devkit" in current_url:
        shutil.rmtree(git_dir, onerror=on_rm_error)

# 2. Initialize Git
is_new_repo = False
if not os.path.exists(git_dir):
    run_git(["init"])
    run_git(["branch", "-M", "main"])
    is_new_repo = True

# 3. Setup Remote
existing_remotes = run_git(["remote"])
if not existing_remotes or REMOTE_NAME not in existing_remotes:
    run_git(["remote", "add", REMOTE_NAME, DEVKIT_URL])

run_git(["remote", "set-url", "--push", REMOTE_NAME, "no_push"])
run_git(["fetch", REMOTE_NAME])

# 4. Handle Content
if is_new_repo:
    run_git(["pull", REMOTE_NAME, "release"])
else:
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, onerror=on_rm_error)

    run_git(["clone", "--depth", "1", "--branch", "release", DEVKIT_URL, TEMP_DIR], cwd=ROOT_DIR)

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

# 5. Setup Tracking Branch
run_git(["branch", "--track", "--force", TARGET_BRANCH, f"{REMOTE_NAME}/release"])

# 6. Link History
if not is_new_repo:
    run_git(["add", "."])

    status = run_git(["status", "--porcelain"])
    if status:
        run_git(["commit", "-m", "Add devkit tools"])

    run_git(["merge", TARGET_BRANCH, "--allow-unrelated-histories", "-s", "ours", "-m", "Link devkit history"])

# 7. Self-Destruct
# Delete the copy inside the scripts folder if it differs from the running file
repo_script = os.path.join(ROOT_DIR, "scripts", "setup.py")
if os.path.exists(repo_script) and os.path.abspath(repo_script) != SCRIPT_FILE:
    try:
        os.remove(repo_script)
    except Exception:
        pass

# Delete the running script itself
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass