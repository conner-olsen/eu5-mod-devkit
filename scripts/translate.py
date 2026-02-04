import os
import re
import sys
import deepl
from dotenv import load_dotenv

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
SOURCE_LANG_FOLDER = "english"
SOURCE_LANG_ID = "l_english"

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

# ==========================================
# LOGIC
# ==========================================

def get_translator():
	try:
		return deepl.Translator(AUTH_KEY)
	except Exception as e:
		print(f"Error initializing DeepL: {e}")
		return None

def mask_text_var(text):
	"""
	Replaces blocks with [VAR_0], [VAR_1] etc to prevent DeepL from breaking it.
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

def process_file(translator, filepath, target_folder_name, deepl_code):
	filename = os.path.basename(filepath)
	new_lang_id = f"l_{target_folder_name}"
	new_filename = filename.replace(SOURCE_LANG_ID, new_lang_id)

	target_dir = os.path.join(BASE_LOC_PATH, target_folder_name)
	os.makedirs(target_dir, exist_ok=True)
	target_filepath = os.path.join(target_dir, new_filename)

	print(f"Translating {filename} -> {target_folder_name}...")

	with open(filepath, 'r', encoding='utf-8-sig') as f:
		lines = f.readlines()

	new_lines = []
	ignore_block_active = False

	# Iterates lines; translates key‑value pairs; preserves comments
	for line in lines:
		stripped_line = line.strip()

		# 1. Handle Language Header
		if stripped_line.startswith(f"{SOURCE_LANG_ID}:"):
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
		match = re.match(r'^(\s*)([^:#]+):\s*"(.*)"(.*)$', line)

		if match:
			indent = match.group(1)
			key = match.group(2)
			original_value = match.group(3)
			comment = match.group(4) if match.group(4) else ""

			masked_text, placeholders = mask_text_var(original_value)

			# 4. Check if the line should be skipped.
			if should_auto_skip(masked_text):
				translated_text = original_value
			else:
				try:
					# TRANSLATE
					result = translator.translate_text(
						masked_text,
						target_lang=deepl_code,
						source_lang="EN"
					)

					is_valid, msg = validate_translation(result.text, placeholders)
					if not is_valid:
						print(f"  [WARNING] {target_folder_name} issue in '{key}': {msg}")

					translated_text = unmask_text_var(result.text, placeholders)
					translated_text = cleanup_text(translated_text)

				except Exception as e:
					print(f"  [Error] Failed to translate line: {key} ({e})")
					translated_text = original_value

			new_lines.append(f'{indent}{key}: "{translated_text}"{comment}\n')
		else:
			# Copy comments / whitespace lines
			new_lines.append(line)

	with open(target_filepath, 'w', encoding='utf-8-sig') as f:
		f.writelines(new_lines)

def main():
	translator = get_translator()
	if not translator:
		return

	source_dir = os.path.join(BASE_LOC_PATH, SOURCE_LANG_FOLDER)

	if not os.path.exists(source_dir):
		print(f"Error: Source directory not found: {source_dir}")
		return

	for root, _, files in os.walk(source_dir):
		for file in files:
			if file.endswith(".yml"):
				source_filepath = os.path.join(root, file)
				for folder_name, deepl_code in TARGET_LANGUAGES.items():
					process_file(translator, source_filepath, folder_name, deepl_code)

	print("Translation complete!")

if __name__ == "__main__":
	main()
