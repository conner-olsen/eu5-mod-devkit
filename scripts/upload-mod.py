import argparse
import json
import os
import re
import shutil
import stat
import sys
import time
from contextlib import contextmanager

import tomllib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEPENDENCIES_DIR = os.path.join(SCRIPT_DIR, "dependencies")
# Allow importing the bundled steamworks module from scripts/dependencies/steamworks.
sys.path.insert(0, DEPENDENCIES_DIR)

from steamworks import STEAMWORKS
from steamworks.enums import EResult, EWorkshopFileType

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
CREATE_ITEM_TIMEOUT_SECONDS = 30
CREATE_ITEM_POLL_INTERVAL_SECONDS = 0.1
WORKSHOP_FILE_TYPE = EWorkshopFileType.COMMUNITY

def _parse_int(value, label, allow_zero=False):
    """Parse a positive integer (or zero when allowed) with a friendly error message."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        print(f"Error: Invalid {label} '{value}'. Expected an integer.")
        return None
    if parsed == 0 and allow_zero:
        return 0
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

def load_workshop_item_id(config, key, label):
    """Load the workshop item ID from config data."""
    upload_item_id = config.get(key)
    if upload_item_id is None:
        print(f"Error: {key} not set in config.toml.")
        return None

    return _parse_int(upload_item_id, label, allow_zero=True)

def load_dev_name(config):
    """Load an optional dev mod name override from config data."""
    dev_name = config.get("workshop_dev_name")
    if dev_name is None:
        return None
    dev_name = str(dev_name).strip()
    return dev_name if dev_name else None

def update_config_value(config_path, key, value):
    """Update a single key in config.toml while preserving comments."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"Error reading config file: {e}")
        return False

    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)([^#]*?)(\s*)(#.*)?$")
    updated = False
    for idx, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            prefix, _old_value, gap, comment = match.groups()
            comment = comment or ""
            if comment and not gap:
                gap = " "
            elif not comment:
                gap = ""
            lines[idx] = f"{prefix}{value}{gap}{comment}".rstrip()
            updated = True
            break

    if not updated:
        lines.append(f"{key} = {value}")

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"Error writing config file: {e}")
        return False

    return True

@contextmanager
def steamworks_session():
    cwd_before = os.getcwd()
    try:
        os.chdir(DEPENDENCIES_DIR)
        steam = STEAMWORKS()
        steam.initialize()
        yield steam
    finally:
        os.chdir(cwd_before)

def create_workshop_item(steam):
    result_holder = {"done": False, "result": None}

    def on_created(result):
        result_holder["done"] = True
        result_holder["result"] = result

    workshop = steam.Workshop
    workshop.CreateItem(APP_ID, WORKSHOP_FILE_TYPE, callback=on_created)

    start = time.time()
    while not result_holder["done"]:
        steam.run_callbacks()
        time.sleep(CREATE_ITEM_POLL_INTERVAL_SECONDS)
        if time.time() - start > CREATE_ITEM_TIMEOUT_SECONDS:
            print("Error: Timed out while waiting for Workshop item creation.")
            return None

    result = result_holder["result"]
    if result is None:
        print("Error: Workshop item creation did not return a result.")
        return None

    try:
        result_code = EResult(result.result)
    except ValueError:
        print(f"Error: Workshop item creation failed with unknown result code {result.result}.")
        return None

    if result_code != EResult.OK:
        print(f"Error: Workshop item creation failed with result {result_code.name}.")
        return None

    if result.userNeedsToAcceptWorkshopLegalAgreement:
        print("Warning: You must accept the Workshop legal agreement in Steam before uploading.")

    new_id = int(result.publishedFileId)
    if new_id <= 0:
        print("Error: Workshop item creation returned an invalid published file id.")
        return None

    print(f"Created new Workshop item: {new_id}")
    return new_id

def ensure_item_id(steam, item_id, config_path, config_key):
    if item_id != 0:
        return item_id

    print("Workshop item id is 0; creating a new Workshop item...")
    new_id = create_workshop_item(steam)
    if new_id is None:
        return None

    if update_config_value(config_path, config_key, new_id):
        print(f"Updated {config_key} in {config_path}.")
    else:
        print(
            f"Warning: Failed to update {config_path}. "
            f"Please set {config_key} = {new_id} manually."
        )

    return new_id

def _normalize_release_title(raw_name):
    title = str(raw_name)
    if title.endswith(" Dev"):
        title = title[:-4].rstrip()
    return title.strip()

def build_release(dev_mode=False, dev_name=None):
    # --- Generate Release Folder Name ---
    dev_meta_path = os.path.join(ROOT_DIR, ".metadata", "metadata.json")

    if os.path.exists(dev_meta_path):
        with open(dev_meta_path, "r", encoding="utf-8-sig") as f:
            meta_data = json.load(f)

        raw_name = meta_data["name"]
        resolved_dev_name = dev_name if dev_mode and dev_name else raw_name
        workshop_title = (
            str(resolved_dev_name).strip()
            if dev_mode
            else _normalize_release_title(raw_name)
        )
        base_name = resolved_dev_name if dev_mode else raw_name
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
        data["name"] = resolved_dev_name
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

    return (
        os.path.abspath(release_dir),
        os.path.abspath(thumb_dest) if thumb_dest else None,
        workshop_title
    )

def upload_release(workshop, content_dir, preview_path, item_id, workshop_title=None):
    if not os.path.isdir(content_dir):
        print(f"Error: Release directory not found: {content_dir}")
        return False

    handle = workshop.StartItemUpdate(APP_ID, item_id)
    if not handle:
        print("Error: StartItemUpdate failed. Check app ID and item ID.")
        return False

    if workshop_title:
        title_result = workshop.SetItemTitle(handle, workshop_title)
        if title_result is False:
            print("Error: SetItemTitle failed.")
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

    item_id_key = "workshop_upload_item_id_dev" if args.dev else "workshop_upload_item_id"
    item_label = "dev item id" if args.dev else "item id"
    item_id = load_workshop_item_id(config, item_id_key, item_label)
    if item_id is None:
        return 1

    dev_name = load_dev_name(config) if args.dev else None
    release_dir, preview_path, workshop_title = build_release(dev_mode=args.dev, dev_name=dev_name)

    with steamworks_session() as steam:
        item_id = ensure_item_id(steam, item_id, CONFIG_PATH, item_id_key)
        if item_id is None:
            return 1
        if not upload_release(steam.Workshop, release_dir, preview_path, item_id, workshop_title):
            return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
