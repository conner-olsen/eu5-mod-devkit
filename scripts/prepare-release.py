import shutil, os, stat, json

# --- User Configuration ---
SOURCES = [
    "in_game",
    "main_menu",
	"loading_screen"
    # "LICENSE", - example of adding a file to the release
]

# --- Path Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# --- Generate Release Folder Name ---
dev_meta_path = os.path.join(ROOT_DIR, ".metadata", "metadata.json")

if os.path.exists(dev_meta_path):
    with open(dev_meta_path, "r", encoding="utf-8-sig") as f:
        meta_data = json.load(f)

    raw_name = meta_data["name"]
    clean_name = raw_name.removesuffix(" Dev")

    clean_name = clean_name.lower().replace(" ", "-")
    target_folder_name = f"{clean_name}-release"
else:
    raise FileNotFoundError(f"Metadata file not found at {dev_meta_path}")

RELEASE_DIR = os.path.join(os.path.dirname(ROOT_DIR), target_folder_name)

# --- Functions ---
def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# --- Script ---

# 1. Clean and Recreate Release Directory
if os.path.exists(RELEASE_DIR):
    shutil.rmtree(RELEASE_DIR, onerror=on_rm_error)

os.makedirs(RELEASE_DIR)

# 2. Copy Sources directly to Release Directory
for item in SOURCES:
    src_path = os.path.join(ROOT_DIR, item)
    dest_path = os.path.join(RELEASE_DIR, item)

    if os.path.exists(src_path):
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy(src_path, dest_path)

# 3. Generate Release Metadata
dest_meta_dir = os.path.join(RELEASE_DIR, ".metadata")
dest_meta_path = os.path.join(dest_meta_dir, "metadata.json")

if not os.path.exists(dest_meta_dir):
    os.makedirs(dest_meta_dir)

with open(dev_meta_path, "r", encoding="utf-8-sig") as f:
    data = json.load(f)

data["name"] = data["name"].removesuffix(" Dev")
data["id"] = data["id"].removesuffix(".dev")

with open(dest_meta_path, "w", encoding="utf-8-sig") as f:
    json.dump(data, f, indent=4)

# 4. Handle Thumbnail
thumb_release = os.path.join(ROOT_DIR, ".metadata", "thumbnail-release.png")
thumb_std = os.path.join(ROOT_DIR, ".metadata", "thumbnail.png")
thumb_dest = os.path.join(dest_meta_dir, "thumbnail.png")

if os.path.exists(thumb_release):
    shutil.copy(thumb_release, thumb_dest)
elif os.path.exists(thumb_std):
    shutil.copy(thumb_std, thumb_dest)
