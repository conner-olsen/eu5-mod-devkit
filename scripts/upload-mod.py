import argparse
import json
import os
import shutil
import stat
import sys

import tomllib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEPENDENCIES_DIR = os.path.join(SCRIPT_DIR, "dependencies")
# Allow importing the bundled steamworks module from scripts/dependencies/steamworks.
sys.path.insert(0, DEPENDENCIES_DIR)

from steamworks import STEAMWORKS

# --- User Configuration ---
SOURCES = [
    "in_game",
    "main_menu",
	"loading_screen"
    # "LICENSE", - example of adding a file to the release
]

# --- Path Setup ---
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.toml")
APP_ID = 3450310

def _parse_int(value, label):
    """Parse a positive integer with a friendly error message."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        print(f"Error: Invalid {label} '{value}'. Expected an integer.")
        return None
    if parsed <= 0:
        print(f"Error: Invalid {label} '{value}'. Expected a positive integer.")
        return None
    return parsed

def load_config(config_path):
    """Load config.toml values needed for Workshop uploads."""
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        return None
    except Exception as e:
        print(f"Error reading config file: {e}")
        return None

    return data

def load_workshop_item_id(config, dev_mode):
    """Load the workshop item ID from config data."""
    key = "workshop_upload_item_id_dev" if dev_mode else "workshop_upload_item_id"
    label = "dev item id" if dev_mode else "item id"

    upload_item_id = config.get(key)
    if upload_item_id is None:
        if dev_mode:
            print("Error: workshop_upload_item_id_dev not set in config.toml.")
        else:
            print("Error: workshop_upload_item_id not set in config.toml.")
        return None

    return _parse_int(upload_item_id, label)

def load_dev_name(config):
    """Load an optional dev mod name override from config data."""
    dev_name = config.get("workshop_dev_name")
    if dev_name is None:
        return None
    dev_name = str(dev_name).strip()
    return dev_name if dev_name else None

def build_release(dev_mode=False, dev_name=None):
    # --- Generate Release Folder Name ---
    dev_meta_path = os.path.join(ROOT_DIR, ".metadata", "metadata.json")

    if os.path.exists(dev_meta_path):
        with open(dev_meta_path, "r", encoding="utf-8-sig") as f:
            meta_data = json.load(f)

        raw_name = meta_data["name"]
        base_name = dev_name if dev_mode and dev_name else raw_name
        clean_name = base_name.removesuffix(" Dev")

        clean_name = clean_name.lower().replace(" ", "-")
        target_folder_name = f"{clean_name}-dev" if dev_mode else f"{clean_name}-release"
    else:
        raise FileNotFoundError(f"Metadata file not found at {dev_meta_path}")

    release_dir = os.path.join(os.path.dirname(ROOT_DIR), target_folder_name)

    # --- Functions ---
    def on_rm_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    # --- Script ---

    # 1. Clean and Recreate Release Directory
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir, onerror=on_rm_error)

    os.makedirs(release_dir)

    # 2. Copy Sources directly to Release Directory
    for item in SOURCES:
        src_path = os.path.join(ROOT_DIR, item)
        dest_path = os.path.join(release_dir, item)

        if os.path.exists(src_path):
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy(src_path, dest_path)

    # 3. Generate Release Metadata
    dest_meta_dir = os.path.join(release_dir, ".metadata")
    dest_meta_path = os.path.join(dest_meta_dir, "metadata.json")

    if not os.path.exists(dest_meta_dir):
        os.makedirs(dest_meta_dir)

    with open(dev_meta_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if dev_mode:
        if dev_name:
            data["name"] = dev_name
    else:
        data["name"] = data["name"].removesuffix(" Dev")
        data["id"] = data["id"].removesuffix(".dev")

    with open(dest_meta_path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=4)

    # 4. Handle Thumbnail
    thumb_release = os.path.join(ROOT_DIR, ".metadata", "thumbnail-release.png")
    thumb_std = os.path.join(ROOT_DIR, ".metadata", "thumbnail.png")
    thumb_dest = os.path.join(dest_meta_dir, "thumbnail.png")

    if dev_mode:
        if os.path.exists(thumb_std):
            shutil.copy(thumb_std, thumb_dest)
        else:
            thumb_dest = None
    else:
        if os.path.exists(thumb_release):
            shutil.copy(thumb_release, thumb_dest)
        elif os.path.exists(thumb_std):
            shutil.copy(thumb_std, thumb_dest)
        else:
            thumb_dest = None

    return os.path.abspath(release_dir), os.path.abspath(thumb_dest) if thumb_dest else None

def upload_release(content_dir, preview_path, item_id):
    if not os.path.isdir(content_dir):
        print(f"Error: Release directory not found: {content_dir}")
        return False

    cwd_before = os.getcwd()
    try:
        # SteamworksPy resolves DLL/appid from the current working directory.
        os.chdir(DEPENDENCIES_DIR)
        steam = STEAMWORKS()
        steam.initialize()
        workshop = steam.Workshop

        handle = workshop.StartItemUpdate(APP_ID, item_id)
        if not handle:
            print("Error: StartItemUpdate failed. Check app ID and item ID.")
            return False

        content_result = workshop.SetItemContent(handle, content_dir)
        if content_result is False:
            print("Error: SetItemContent failed.")
            return False

        if preview_path:
            preview_result = workshop.SetItemPreview(handle, preview_path)
            if preview_result is False:
                print("Error: SetItemPreview failed.")
                return False

        workshop.SubmitItemUpdate(handle, "")
        print("Workshop update submitted. Check Steam client for upload progress.")
        return True
    finally:
        os.chdir(cwd_before)

def parse_args():
    parser = argparse.ArgumentParser(description="Build and upload an EU5 mod to Steam Workshop.")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Upload the dev Workshop item using dev metadata and thumbnail."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    config = load_config(CONFIG_PATH)
    if config is None:
        return 1

    item_id = load_workshop_item_id(config, args.dev)
    if item_id is None:
        return 1

    dev_name = load_dev_name(config) if args.dev else None
    release_dir, preview_path = build_release(dev_mode=args.dev, dev_name=dev_name)

    if not upload_release(release_dir, preview_path, item_id):
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
