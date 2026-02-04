# EU5 Mod Devkit

A development kit for Europa Universalis V (EU5) including a template and tools for creating mods.

## Requirements

- **Python 3.x**: Required for running the setup and release scripts.
- **Git**: Required for version control and using the devkit tools.
- **Europa Universalis V**: The game this devkit is designed for.

## Project Structure

```text
eu5-mod-devkit/
├── .metadata/                  # Mod metadata and thumbnails
│   ├── metadata.json            # Mod configuration (name, id, tags, etc.)
│   ├── thumbnail.png            # Default/Dev thumbnail template
│   └── thumbnail-release.png    # Release thumbnail template
├── assets/                     # Source assets (images, etc.)
│   └── images/                  # Images used in the mod
│       ├── thumbnail.psd          # Photoshop template for the thumbnail
│       └── thumbnail-alt.psd      # Alternative Photoshop template for the thumbnail
├── scripts/                    # Automation scripts
│   ├── setup.py                 # Initial project setup script
│   ├── prepare-release.py       # Auto-manages separate release and development versions of your mod
│   ├── translate.py             # Auto-translate localization files with DeepL
│   ├── create-devkit-release.sh # (Internal) Devkit release management
│   └── reset-release.sh         # (Internal) Devkit release management
├── in_game/common/dummy.txt    # stub file to create the folder
├── main_menu/
│   └── localization
│       └── english
│          └── tmp_l_english.yml    # localization template file
├── .editorconfig               # Standardizes editor settings for EU5
├── .gitattributes              # Makes all text files use crlf line endings
├── .gitignore                  # Standard gitignore
├── .env-template               # For setting the DeepL api key, will be copied to .env in the release branch.
├── LICENSE                     # (Internal) Project license
├── README.md                   # (Internal) This file
└── README-TEMPLATE.md          # GitHub repo readme template, will be copied to README.md in the release branch.
```
* Files marked as `(internal)` are not included in the release version, and are just for the devkit's own use. You do not need to copy them, and they will not be included if you run the setup script.

## Setup

### setup.py
This will copy all files from the `release` branch into your mod folder, and add the devkit repository as a remote.
By having the devkit as a remote, you can easily update the devkit by merging from the remote `tools/devkit` branch.

1. **Push your mod to a Git repository**:
   * **Existing Mods**: If you haven't already, push your mod to a Git repository.
   * **New Mods**: Create, initialize, and push, a new empty Git repo in the Europa Universalis V/mod folder.
2. a) From the root of your mod folder, run:
   ```bash
   curl -sL https://raw.githubusercontent.com/conner-olsen/eu5-mod-devkit/devkit-release/scripts/setup.py -o setup.py && python setup.py
   ```
   *Note: The script will not overwrite any existing files and can be run on existing repositories safely.*

After running, the setup script will delete itself and should not need to be used again.

Once the devkit files are in place, install the Python dependencies:
```bash
pip install -r scripts/requirements.txt
```

### Manual Setup
Simply copy any files you want to use from the `release` branch into your mod folder.
Note that without the devkit remote, you will have to manually check and copy over updates to the devkit.

If you are familiar with Git, you can also manually add the remote for ease of updating.

## Provided Tools

### prepare-release.py
Auto-manages separate release and development versions of your mod. This has multiple benefits such as:
* Tooling, git files, and anything else you don't want on the workshop will get omitted from the release version.
* Separate IDs, names, and (optionally) thumbnails allow you to easily swap between your dev, and workshop versions through the in-game mod manager.
* Makes it easy to swap between for joining multiplayer sessions.
* Can more easily swap to the released version to look verify reported issues.

To use the script:
1. **Modify Metadata**: Edit `.metadata/metadata.json` adding ` Dev` and `.dev` to the name and id respectively.
2. **(optionally) Add Separate Release/Dev Thumbnails**: If you want to use a different thumbnail for the release version:
   * The dev thumbnail will use `.metadata/thumbnail.png`.
   * Make the release thumbnail `.metadata/thumbnail-release.png` (if it does not exist, the `.metadata/thumbnail.png` will be used for both).
3. **(optionally) Configure Included Files**: By default, the release version only includes the `.metadata/`, `in_game/` and `main_menu/` folders.
   * If you want to include more files (i.e., LICENSE), you can add them to the `SOURCES` list in `scripts/prepare-release.py`.
4. **Run `prepare-release.py`**: When ready to create/update the release version to upload to the workshop:
   ```bash
   python scripts/prepare-release.py
   ```
   This will create a new folder `../mod-name-release` with:
   * The metadata.json file from `.metadata/` with " Dev" and ".dev" removed from the name and id respectively.
   * The thumbnail from `.metadata/thumbnail-release.png` or the default thumbnail if it doesn't exist.
   * The `in_game/`, `main_menu/` and any other files specified in the `SOURCES` list of `scripts/prepare-release.py`.

### translate.py
Auto-translates localization files using the DeepL API.
It reads from `main_menu/localization/<source_language>` and writes translated `.yml` files for supported languages into `main_menu/localization/<language>/`.
* It preserves EU5 localization tags like `[...], $...$, @...!, #...#!`.
* It will automatically skip lines that consist purely of tags or formatting characters.
* You can skip translation on specific lines by adding `# NO_TRANSLATE` to the end of any line you want skipped.
* You can skip blocks by wrapping them in `# NO_TRANSLATE BELOW` and `# NO_TRANSLATE END` (with the latter being optional).
* Translates from the configured source language to all other supported languages.
* Only translates keys that changed since the last run, updating those keys in-place without rewriting the rest of the file.
* Tracks per-key hashes in `scripts/.translate_hashes.json` (delete this file to force a full re-translate).
* You can lock a translated output line by adding `# LOCK` at the end; locked lines are never overwritten even if the source changes.
* If you want to completely disable a output language, you can delete its entry in `TARGET_LANGUAGES` from `scripts/config.toml`.

Setup:
1. Copy `.env-template` to `.env`.
2. Add your DeepL API key as `DEEPL_API_KEY=your_key_here`.
3. Set `source_language` in `scripts/config.toml` (supported values: english, french, german, spanish, polish, russian, simp_chinese, turkish, braz_por, japanese, korean).

To run:
```bash
python scripts/translate.py
```

Note: You need to install the dependencies in `scripts/requirements.txt` before running this script.
```bash
pip install -r scripts/requirements.txt
```

## License

This project is licensed under the terms found in the [LICENSE](LICENSE) file.
