import os, shutil, subprocess, stat, sys

# --- Configuration ---
DEVKIT_URL = "https://github.com/conner-olsen/eu5-mod-devkit.git"
REMOTE_NAME = "devkit"

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
        subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

# --- Script ---

# 1. Initialize Git if missing
if not os.path.exists(os.path.join(ROOT_DIR, ".git")):
    run_git(["init"])
    run_git(["branch", "-M", "main"])

# 2. Clone Devkit to Temp Directory
if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR, onerror=on_rm_error)

run_git(["clone", "--depth", "1", DEVKIT_URL, TEMP_DIR], cwd=ROOT_DIR)

# 3. Copy Files (No Overwrite)
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

            # Only copy if file does not exist
            if not os.path.exists(dest_file):
                shutil.copy2(src_file, dest_file)

    shutil.rmtree(TEMP_DIR, onerror=on_rm_error)

# 4. Add Remote
run_git(["remote", "add", REMOTE_NAME, DEVKIT_URL])
run_git(["fetch", REMOTE_NAME])

# 5. Self-Destruct
try:
    os.remove(SCRIPT_FILE)
except Exception:
    pass