import json
import os
import re
import sys

import steamworks
import tomllib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.toml")
METADATA_PATH = os.path.join(ROOT_DIR, ".metadata", "metadata.json")
WORKSHOP_DESCRIPTION_PATH = os.path.join(ROOT_DIR, "assets", "workshop", "workshop-description.txt")
TRANSLATIONS_DIR = os.path.join(ROOT_DIR, "assets", "workshop", "translations")
APP_ID = 3450310

LANGUAGE_TO_STEAM = {
	"english": "english",
	"french": "french",
	"german": "german",
	"spanish": "spanish",
	"polish": "polish",
	"russian": "russian",
	"simp_chinese": "schinese",
	"turkish": "turkish",
	"braz_por": "brazilian",
	"japanese": "japanese",
	"korean": "koreana"
}

def load_config(config_path):
	if not os.path.exists(config_path):
		print(f"Error: Config file not found: {config_path}")
		return None, None, None

	try:
		with open(config_path, "rb") as f:
			data = tomllib.load(f)
	except Exception as e:
		print(f"Error reading config file: {e}")
		return None, None, None

	source_language = data.get("source_language")
	if not source_language:
		print(f"Error: source_language not set in {config_path}")
		return None, None, None

	source_language = str(source_language).strip().lower()
	if source_language not in LANGUAGE_TO_STEAM:
		valid = ", ".join(sorted(LANGUAGE_TO_STEAM.keys()))
		print(f"Error: Unsupported source_language '{source_language}'.")
		print(f"Supported values: {valid}")
		return None, None, None

	upload_item_id = data.get("workshop_upload_item_id")
	dry_run = data.get("workshop_upload_dry_run", False)

	if upload_item_id is None:
		print("Error: workshop_upload_item_id not set in config.toml.")
		return None, None, None

	item_id = _parse_int(upload_item_id, "item id")
	if item_id is None:
		return None, None, None

	if not isinstance(dry_run, bool):
		print("Error: workshop_upload_dry_run must be a boolean (true/false).")
		return None, None, None

	return source_language, item_id, dry_run

def read_text(path):
	try:
		with open(path, "r", encoding="utf-8-sig") as f:
			return f.read()
	except FileNotFoundError:
		return None
	except Exception as e:
		print(f"Warning: Failed to read '{path}': {e}")
		return None

def load_mod_title(metadata_path):
	if not os.path.exists(metadata_path):
		print(f"Warning: Metadata file not found: {metadata_path}")
		return None
	try:
		with open(metadata_path, "r", encoding="utf-8-sig") as f:
			data = json.load(f)
	except Exception as e:
		print(f"Warning: Failed to read metadata file '{metadata_path}': {e}")
		return None

	title = data.get("name")
	if not title:
		print(f"Warning: Metadata 'name' not found in {metadata_path}")
		return None

	title = str(title)
	if title.endswith(" Dev"):
		title = title[:-4].rstrip()
	return title.strip()

def _parse_int(value, label):
	try:
		parsed = int(value)
	except (TypeError, ValueError):
		print(f"Error: Invalid {label} '{value}'. Expected an integer.")
		return None
	if parsed <= 0:
		print(f"Error: Invalid {label} '{value}'. Expected a positive integer.")
		return None
	return parsed

def build_language_updates(source_language):
	base_description = read_text(WORKSHOP_DESCRIPTION_PATH)
	if base_description is None:
		print(f"Error: Workshop description file not found: {WORKSHOP_DESCRIPTION_PATH}")
		return None

	base_title = load_mod_title(METADATA_PATH)

	updates = []
	updates.append({
		"lang": source_language,
		"steam_lang": LANGUAGE_TO_STEAM[source_language],
		"title": base_title,
		"description": base_description
	})

	if not os.path.exists(TRANSLATIONS_DIR):
		print(f"Warning: Translations folder not found: {TRANSLATIONS_DIR}")
		return updates

	translations = {}
	for filename in os.listdir(TRANSLATIONS_DIR):
		if not filename.endswith(".txt"):
			continue
		match = re.match(r"^(title|description)_(.+)\.txt$", filename)
		if not match:
			continue
		kind, lang = match.group(1), match.group(2)
		if not lang:
			continue
		path = os.path.join(TRANSLATIONS_DIR, filename)
		text = read_text(path)
		if text is None:
			continue
		entry = translations.setdefault(lang, {"title": None, "description": None})
		entry[kind] = text

	for lang, entry in translations.items():
		if lang == source_language:
			continue
		if lang not in LANGUAGE_TO_STEAM:
			print(f"Warning: No Steam language mapping for '{lang}', skipping.")
			continue
		if entry["title"] is None and entry["description"] is None:
			continue
		updates.append({
			"lang": lang,
			"steam_lang": LANGUAGE_TO_STEAM[lang],
			"title": entry["title"],
			"description": entry["description"]
		})

	return updates

def _get_ugc_api(steam):
	for attr in ("UGC", "Workshop", "workshop"):
		if hasattr(steam, attr):
			return getattr(steam, attr)
	return None

def _ensure_ok(result, action, lang_label):
	if result is False:
		print(f"Error: {action} failed for {lang_label}.")
		return False
	return True

def main():
	(
		source_language,
		item_id,
		dry_run
	) = load_config(CONFIG_PATH)

	if not source_language:
		return 1

	updates = build_language_updates(source_language)
	if updates is None:
		return 1

	print("Workshop language updates:")
	for update in updates:
		title_state = "title" if update["title"] is not None else "no-title"
		desc_state = "description" if update["description"] is not None else "no-description"
		print(f"  - {update['lang']} ({update['steam_lang']}): {title_state}, {desc_state}")

	if dry_run:
		print("Dry run enabled; no upload performed.")
		return 0

	steam = None
	if hasattr(steamworks, "STEAMWORKS"):
		steam = steamworks.STEAMWORKS()
	elif hasattr(steamworks, "SteamWorks"):
		steam = steamworks.SteamWorks()

	if steam is None:
		print("Error: steamworks module found, but no STEAMWORKS/SteamWorks class.")
		return 1

	try:
		if hasattr(steam, "initialize"):
			init_result = steam.initialize()
		elif hasattr(steam, "init"):
			init_result = steam.init()
		else:
			print("Error: Steamworks instance has no initialize/init method.")
			return 1
	except Exception as e:
		print(f"Error: Steamworks initialization failed: {e}")
		print("Ensure Steam is running and steam_appid.txt is set for your app ID.")
		return 1

	if init_result is False:
		print("Error: Steamworks initialization returned false.")
		return 1

	ugc = _get_ugc_api(steam)
	if ugc is None:
		print("Error: steamworks UGC API not available on this install.")
		return 1

	for method_name in ("StartItemUpdate", "SetItemUpdateLanguage", "SetItemTitle", "SetItemDescription", "SubmitItemUpdate"):
		if not hasattr(ugc, method_name):
			print(f"Error: steamworks UGC API missing method '{method_name}'.")
			return 1

	handle = ugc.StartItemUpdate(APP_ID, item_id)
	if not handle:
		print("Error: StartItemUpdate failed. Check app ID and item ID.")
		return 1

	for update in updates:
		lang_label = f"{update['lang']} ({update['steam_lang']})"
		if not _ensure_ok(ugc.SetItemUpdateLanguage(handle, update["steam_lang"]), "SetItemUpdateLanguage", lang_label):
			return 1

		if update["title"] is not None:
			if not _ensure_ok(ugc.SetItemTitle(handle, update["title"]), "SetItemTitle", lang_label):
				return 1

		if update["description"] is not None:
			if not _ensure_ok(ugc.SetItemDescription(handle, update["description"]), "SetItemDescription", lang_label):
				return 1

	print("Submitting workshop update...")
	submit_result = ugc.SubmitItemUpdate(handle, "")
	if submit_result is False or submit_result == 0:
		print("Error: SubmitItemUpdate failed.")
		return 1

	print("Workshop update submitted. Check Steam client for upload progress.")
	return 0

if __name__ == "__main__":
	sys.exit(main())
