import shutil, os, stat, json

# --- User Configuration ---
SOURCES = [
    "in_game",
    "main_menu",
    # "LICENSE", - example of adding a file
]

RELEASE_NAME = "release"
TARGET_DIR_NAME = "mod-devkit"

# --- Path Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RELEASE_PATH = os.path.join(ROOT_DIR, RELEASE_NAME)
EXTERNAL_DEST = os.path.join(os.path.dirname(ROOT_DIR), TARGET_DIR_NAME)

# --- Functions ---
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
if os.path.exists(EXTERNAL_DEST):
    shutil.rmtree(EXTERNAL_DEST, onerror=on_rm_error)

shutil.copytree(RELEASE_PATH, EXTERNAL_DEST)

# 3. Generate Release Metadata
dev_meta_path = os.path.join(ROOT_DIR, ".metadata", "metadata.json")
dest_meta_dir = os.path.join(EXTERNAL_DEST, ".metadata")
dest_meta_path = os.path.join(dest_meta_dir, "metadata.json")

if os.path.exists(dev_meta_path):
    if not os.path.exists(dest_meta_dir):
        os.makedirs(dest_meta_dir)

    with open(dev_meta_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if "name" in data:
        data["name"] = data["name"].replace(" Dev", "")

    if "id" in data:
        data["id"] = data["id"].replace(".dev", "")

    with open(dest_meta_path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=4)
else:
    print(f"Warning: Source metadata not found at {dev_meta_path}")

# 4. Cleanup Release Folder
for item in os.listdir(RELEASE_PATH):
    if item == ".metadata":
        continue

    item_path = os.path.join(RELEASE_PATH, item)
    if os.path.isdir(item_path):
        shutil.rmtree(item_path, onerror=on_rm_error)
    else:
        os.remove(item_path)