import shutil, os, stat

# --- User Configuration ---
SOURCES = [
    "in_game",
    "main_menu",
    # "LICENSE",
]

RELEASE_NAME = "release"
TARGET_DIR_NAME = "mod-devkit"

# --- Path Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RELEASE_PATH = os.path.join(ROOT_DIR, RELEASE_NAME)
EXTERNAL_DEST = os.path.join(os.path.dirname(ROOT_DIR), TARGET_DIR_NAME)

# --- Functions ---
# This fixes the [WinError 5] Access is denied error
def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# --- Execution ---
# 1. Sync Sources to Release Folder
if not os.path.exists(RELEASE_PATH):
    os.makedirs(RELEASE_PATH)

for item in SOURCES:
    src_path = os.path.join(ROOT_DIR, item)
    dest_path = os.path.join(RELEASE_PATH, item)

    if os.path.exists(src_path):
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy(src_path, dest_path)

# 2. Deploy to External Directory
# We delete the old folder first to ensure a clean install
if os.path.exists(EXTERNAL_DEST):
    # The 'onerror' argument calls our helper if deletion fails (e.g., read-only files)
    shutil.rmtree(EXTERNAL_DEST, onerror=on_rm_error)

shutil.copytree(RELEASE_PATH, EXTERNAL_DEST)

# 3. Rename Metadata in External Directory
meta_folder = os.path.join(EXTERNAL_DEST, ".metadata")
meta_src = os.path.join(meta_folder, "release-metadata.json")
meta_dest = os.path.join(meta_folder, "metadata.json")

os.replace(meta_src, meta_dest)

# 4. Cleanup Release Folder
for item in os.listdir(RELEASE_PATH):
    if item == ".metadata":
        continue

    item_path = os.path.join(RELEASE_PATH, item)
    if os.path.isdir(item_path):
        shutil.rmtree(item_path, onerror=on_rm_error)
    else:
        os.remove(item_path)