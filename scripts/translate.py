import os
import re
import sys
import json
import hashlib
import deepl
from dotenv import load_dotenv
try:
	import tomllib
except ModuleNotFoundError:
	tomllib = None

# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()
AUTH_KEY = os.getenv("DEEPL_API_KEY")

if not AUTH_KEY:
	print("Error: DEEPL_API_KEY not found in .env file.")
	print("Please create a .env file with DEEPL_API_KEY=your_key_here")
	sys.exit(1)

BASE_LOC_PATH = os.path.join(os.path.dirname(__file__), "../main_menu/localization")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.toml")

LANGUAGE_CONFIG = {
	"english": {"deepl": "EN", "loc_id": "l_english"},
	"french": {"deepl": "FR", "loc_id": "l_french"},
	"german": {"deepl": "DE", "loc_id": "l_german"},
	"spanish": {"deepl": "ES", "loc_id": "l_spanish"},
	"polish": {"deepl": "PL", "loc_id": "l_polish"},
	"russian": {"deepl": "RU", "loc_id": "l_russian"},
	"simp_chinese": {"deepl": "ZH", "loc_id": "l_simp_chinese"},
	"turkish": {"deepl": "TR", "loc_id": "l_turkish"},
	"braz_por": {"deepl": "PT", "loc_id": "l_braz_por"},
	"japanese": {"deepl": "JA", "loc_id": "l_japanese"},
	"korean": {"deepl": "KO", "loc_id": "l_korean"}
}

TARGET_LANGUAGES = {
	"polish": "PL",
	"russian": "RU",
	"simp_chinese": "ZH",
	"spanish": "ES",
	"turkish": "TR",
	"braz_por": "PT-BR",
	"french": "FR",
	"german": "DE",
	"japanese": "JA",
	"korean": "KO"
}

# Cache of source key/value hashes to avoid re-translating unchanged lines.
HASHES_PATH = os.path.join(os.path.dirname(__file__), ".translate_hashes.json")
HASH_FILE_VERSION = 1

KEY_VALUE_RE = re.compile(r'^(\s*)([^:#]+):\s*"(.*)"(.*)$')
HEADER_RE = re.compile(r'^\s*l_[^:]+:\s*$')

# ==========================================
# LOGIC
# ==========================================

def _parse_source_language_from_line(line):
	key, sep, value = line.partition("=")
	if not sep:
		return None
	if key.strip() != "source_language":
		return None
	value = value.split("#", 1)[0].strip()
	if len(value) >= 2 and ((value[0] == value[-1]) and value[0] in ("'", '"')):
		value = value[1:-1]
	return value.strip()

def load_source_language(config_path):
	if not os.path.exists(config_path):
		print(f"Error: Config file not found: {config_path}")
		return None

	source_language = None

	try:
		if tomllib:
			with open(config_path, "rb") as f:
				data = tomllib.load(f)
			source_language = data.get("source_language")
		else:
			with open(config_path, "r", encoding="utf-8") as f:
				for line in f:
					stripped = line.strip()
					if not stripped or stripped.startswith("#"):
						continue
					value = _parse_source_language_from_line(stripped)
					if value:
						source_language = value
						break
	except Exception as e:
		print(f"Error reading config file: {e}")
		return None

	if not source_language:
		print(f"Error: source_language not set in {config_path}")
		return None

	source_language = source_language.strip().lower()
	if source_language.startswith("l_"):
		source_language = source_language[2:]

	if source_language not in LANGUAGE_CONFIG:
		valid = ", ".join(sorted(LANGUAGE_CONFIG.keys()))
		print(f"Error: Unsupported source_language '{source_language}'.")
		print(f"Supported values: {valid}")
		return None

	return source_language

def get_translator():
	try:
		return deepl.Translator(AUTH_KEY)
	except Exception as e:
		print(f"Error initializing DeepL: {e}")
		return None

def load_hashes(path):
	"""
	Load the per-file, per-key hash cache. If missing or invalid, rebuild cleanly.
	"""
	if not os.path.exists(path):
		return {"version": HASH_FILE_VERSION, "files": {}}

	try:
		with open(path, "r", encoding="utf-8") as f:
			data = json.load(f)
		if not isinstance(data, dict):
			raise ValueError("Hash file must be a JSON object.")
		if data.get("version") != HASH_FILE_VERSION:
			raise ValueError("Unsupported hash file version.")
		files = data.get("files")
		if not isinstance(files, dict):
			raise ValueError("Hash file 'files' must be a JSON object.")
		return data
	except Exception as e:
		print(f"Warning: Failed to read hash file '{path}': {e}. Rebuilding.")
		return {"version": HASH_FILE_VERSION, "files": {}}

def save_hashes(path, data):
	"""
	Atomically persist the hash cache to disk.
	"""
	os.makedirs(os.path.dirname(path), exist_ok=True)
	tmp_path = path + ".tmp"
	with open(tmp_path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, sort_keys=True)
	os.replace(tmp_path, path)

def hash_text(text):
	"""
	Stable hash of the source value to detect changes.
	"""
	return hashlib.sha256(text.encode("utf-8")).hexdigest()

def mask_text_var(text):
	"""
	Replaces blocks with [VAR_0], [VAR_1], etc to prevent DeepL from breaking it.
	"""
	placeholders = []

	def replace_match(match):
		idx = len(placeholders)
		placeholders.append(match.group(0))
		return f'[VAR_{idx}]'

	# 1. Protect [...]
	text = re.sub(r'(\[.*?\])', replace_match, text)
	# 2. Protect $...$
	text = re.sub(r'(\$.*?\$)', replace_match, text)
	# 3. Protect @...!
	text = re.sub(r'(@[a-zA-Z0-9_]+!?)', replace_match, text)
	# 4. Protect #...#!
	text = re.sub(r'(#[a-zA-Z0-9_]+|#!)', replace_match, text)

	return text, placeholders

def unmask_text_var(text, placeholders):
	"""
	Restores [VAR_0] -> Original Text.
	"""
	def restore_match(match):
		try:
			idx = int(match.group(1))
			if 0 <= idx < len(placeholders):
				return placeholders[idx]
		except ValueError:
			pass
		return match.group(0)

	# Regex matches: Optional [, whitespace, VAR_, Digit, whitespace, Optional ]
	return re.sub(r'\[?\s*VAR_(\d+)\s*\]?', restore_match, text)

def validate_translation(translated_text, placeholders):
	"""
	Checks if DeepL dropped any tags.
	"""
	found_indices = re.findall(r'VAR_(\d+)', translated_text)
	found_set = set(int(x) for x in found_indices)

	missing_indices = []
	for i in range(len(placeholders)):
		if i not in found_set:
			missing_indices.append(i)

	if missing_indices:
		missing_tags = [placeholders[i] for i in missing_indices]
		return False, f"Missing tags: {missing_tags}"

	return True, "OK"

def cleanup_text(text):
	"""
	Cleans up common AI formatting errors.
	"""
	text = re.sub(r'\s+([,.])', r'\1', text) # Fix space before punctuation
	text = re.sub(r' +', ' ', text)          # Fix double spaces
	text = text.replace('[[', '[').replace(']]', ']') # Fix double brackets
	return text.strip()

def should_auto_skip(masked_text):
	"""
	Returns True if the line should be skipped.
	Conditions:
	1. Line is empty or whitespace.
	2. Line consists only of placeholders and punctuation (e.g., "[VAR_0]").
	"""
	# 1. Check for empty/whitespace only
	if not masked_text.strip():
		return True

	# 2. Remove all [VAR_x] tags
	stripped = re.sub(r'\[VAR_\d+\]', '', masked_text)

	# 3. Remove standard punctuation and whitespace
	stripped = re.sub(r'[ \t\.,!?:;]', '', stripped)

	# If nothing is left, it was only placeholders/punctuation
	return len(stripped) == 0

def parse_source_entries(lines):
	"""
	Parse all translatable key/value entries with NO_TRANSLATE flags.
	"""
	entries = []
	ignore_block_active = False

	for line in lines:
		if "# NO_TRANSLATE BELOW" in line:
			ignore_block_active = True
		if "# NO_TRANSLATE END" in line:
			ignore_block_active = False

		no_translate = ignore_block_active or ("# NO_TRANSLATE" in line)

		match = KEY_VALUE_RE.match(line)
		if match:
			indent = match.group(1)
			key = match.group(2)
			original_value = match.group(3)
			comment = match.group(4) if match.group(4) else ""
			entries.append({
				"indent": indent,
				"key": key,
				"value": original_value,
				"comment": comment,
				"no_translate": no_translate
			})

	return entries

def translate_value(translator, key, original_value, deepl_code, source_lang_deepl, target_folder_name, no_translate):
	"""
	Translate a single value with tag masking and validation.
	"""
	if no_translate:
		return original_value

	masked_text, placeholders = mask_text_var(original_value)

	if should_auto_skip(masked_text):
		return original_value

	try:
		result = translator.translate_text(
			masked_text,
			target_lang=deepl_code,
			source_lang=source_lang_deepl
		)

		is_valid, msg = validate_translation(result.text, placeholders)
		if not is_valid:
			print(f"  [WARNING] {target_folder_name} issue in '{key}': {msg}")

		translated_text = unmask_text_var(result.text, placeholders)
		translated_text = cleanup_text(translated_text)
		return translated_text

	except Exception as e:
		print(f"  [Error] Failed to translate line: {key} ({e})")
		return original_value

def build_line(indent, key, text, comment):
	return f'{indent}{key}: "{text}"{comment}\n'

def ensure_target_header(target_lines, new_lang_id):
	"""
	Ensure the localization header matches the target language.
	"""
	for i, line in enumerate(target_lines):
		if HEADER_RE.match(line.strip()):
			if line.strip() != f"{new_lang_id}:":
				target_lines[i] = f"{new_lang_id}:\n"
				return True
			return False
	return False

def build_target_key_index(lines):
	"""
	Build a key->line index for fast in-place updates.
	"""
	index = {}
	for i, line in enumerate(lines):
		match = KEY_VALUE_RE.match(line)
		if match:
			index[match.group(2)] = i
	return index

def update_target_lines(translator, target_lines, source_entries, changed_keys, deepl_code, source_lang_deepl, target_folder_name):
	"""
	Update only keys that changed in the source (or are missing in the target).
	"""
	target_index = build_target_key_index(target_lines)
	file_changed = False

	for entry in source_entries:
		key = entry["key"]

		needs_update = key in changed_keys or key not in target_index
		if not needs_update:
			continue

		translated_text = translate_value(
			translator,
			key,
			entry["value"],
			deepl_code,
			source_lang_deepl,
			target_folder_name,
			entry["no_translate"]
		)

		if key in target_index:
			line_index = target_index[key]
			existing_line = target_lines[line_index]
			match = KEY_VALUE_RE.match(existing_line)
			if match:
				indent = match.group(1)
				comment = match.group(4) if match.group(4) else ""
				new_line = build_line(indent, key, translated_text, comment)
			else:
				new_line = build_line(entry["indent"], key, translated_text, entry["comment"])

			if new_line != existing_line:
				target_lines[line_index] = new_line
				file_changed = True
		else:
			new_line = build_line(entry["indent"], key, translated_text, entry["comment"])
			if target_lines and not target_lines[-1].endswith("\n"):
				target_lines[-1] = target_lines[-1] + "\n"
			target_lines.append(new_line)
			target_index[key] = len(target_lines) - 1
			file_changed = True

	return file_changed

def translate_source_lines(translator, source_lines, target_folder_name, deepl_code, source_lang_id, source_lang_deepl):
	"""
	Translate a full source file into a new target file.
	"""
	new_lang_id = f"l_{target_folder_name}"
	new_lines = []
	ignore_block_active = False

	for line in source_lines:
		stripped_line = line.strip()

		# 1. Handle Language Header
		if stripped_line.startswith(f"{source_lang_id}:"):
			new_lines.append(f"{new_lang_id}:\n")
			continue

		# 2. Check for ignored lines
		if "# NO_TRANSLATE BELOW" in line:
			ignore_block_active = True
			new_lines.append(line)
			continue

		if "# NO_TRANSLATE END" in line:
			ignore_block_active = False
			new_lines.append(line)
			continue

		if ignore_block_active:
			new_lines.append(line)
			continue

		if "# NO_TRANSLATE" in line:
			new_lines.append(line)
			continue

		# 3. Parse Key-Value Pairs
		match = KEY_VALUE_RE.match(line)

		if match:
			indent = match.group(1)
			key = match.group(2)
			original_value = match.group(3)
			comment = match.group(4) if match.group(4) else ""

			translated_text = translate_value(
				translator,
				key,
				original_value,
				deepl_code,
				source_lang_deepl,
				target_folder_name,
				False
			)

			new_lines.append(build_line(indent, key, translated_text, comment))
		else:
			# Copy comments / whitespace lines
			new_lines.append(line)

	return new_lines

def process_file(
	translator,
	source_lines,
	source_entries,
	source_filepath,
	target_folder_name,
	deepl_code,
	source_lang_id,
	source_lang_deepl,
	changed_keys
):
	filename = os.path.basename(source_filepath)
	new_lang_id = f"l_{target_folder_name}"
	if source_lang_id in filename:
		new_filename = filename.replace(source_lang_id, new_lang_id)
	else:
		new_filename = filename

	target_dir = os.path.join(BASE_LOC_PATH, target_folder_name)
	os.makedirs(target_dir, exist_ok=True)
	target_filepath = os.path.join(target_dir, new_filename)

	print(f"Translating {filename} -> {target_folder_name}...")

	# If the target doesn't exist yet, write a fully translated file.
	if not os.path.exists(target_filepath):
		new_lines = translate_source_lines(
			translator,
			source_lines,
			target_folder_name,
			deepl_code,
			source_lang_id,
			source_lang_deepl
		)
		with open(target_filepath, 'w', encoding='utf-8-sig') as f:
			f.writelines(new_lines)
		return

	with open(target_filepath, 'r', encoding='utf-8-sig') as f:
		target_lines = f.readlines()

	# Update only changed or missing keys; preserve everything else.
	file_changed = ensure_target_header(target_lines, new_lang_id)
	file_changed = update_target_lines(
		translator,
		target_lines,
		source_entries,
		changed_keys,
		deepl_code,
		source_lang_deepl,
		target_folder_name
	) or file_changed

	if file_changed:
		with open(target_filepath, 'w', encoding='utf-8-sig') as f:
			f.writelines(target_lines)

def main():
	translator = get_translator()
	if not translator:
		return

	source_language = load_source_language(CONFIG_PATH)
	if not source_language:
		return

	source_lang_id = LANGUAGE_CONFIG[source_language]["loc_id"]
	source_lang_deepl = LANGUAGE_CONFIG[source_language]["deepl"]

	source_dir = os.path.join(BASE_LOC_PATH, source_language)

	if not os.path.exists(source_dir):
		print(f"Error: Source directory not found: {source_dir}")
		return

	# Load existing hash cache to identify changed keys.
	hash_data = load_hashes(HASHES_PATH)
	hashes_modified = False
	processed_files = set()

	for root, _, files in os.walk(source_dir):
		for file in files:
			if file.endswith(".yml"):
				source_filepath = os.path.join(root, file)
				with open(source_filepath, 'r', encoding='utf-8-sig') as f:
					source_lines = f.readlines()

				# Build per-key hashes from the source file.
				source_entries = parse_source_entries(source_lines)
				source_hashes = {}
				for entry in source_entries:
					source_hashes[entry["key"]] = hash_text(entry["value"])

				source_rel_path = os.path.relpath(source_filepath, BASE_LOC_PATH)
				processed_files.add(source_rel_path)

				# Determine which keys changed since last run.
				prev_hashes = hash_data["files"].get(source_rel_path, {})
				changed_keys = set()
				for key, current_hash in source_hashes.items():
					if prev_hashes.get(key) != current_hash:
						changed_keys.add(key)

				for folder_name, deepl_code in TARGET_LANGUAGES.items():
					if folder_name == source_language:
						continue
					process_file(
						translator,
						source_lines,
						source_entries,
						source_filepath,
						folder_name,
						deepl_code,
						source_lang_id,
						source_lang_deepl,
						changed_keys
					)

				# Persist updated hashes for this file.
				if prev_hashes != source_hashes:
					hash_data["files"][source_rel_path] = source_hashes
					hashes_modified = True

	# Drop cache entries for source files that no longer exist.
	for rel_path in list(hash_data["files"].keys()):
		if rel_path not in processed_files:
			del hash_data["files"][rel_path]
			hashes_modified = True

	# Write cache only if something changed.
	if hashes_modified:
		save_hashes(HASHES_PATH, hash_data)

	print("Translation complete!")

if __name__ == "__main__":
	main()
