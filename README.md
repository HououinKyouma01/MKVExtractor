# <span style="color: #4a86e8;">🎬 MKV Extractor</span>

<div align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</div>


> <span style="color: #34a853;">Preserve your favorite fansubs with ease!</span>

## <span style="color: #ea4335;">🚀 Introduction</span>

MKV Extractor is a powerful tool designed primarily for archiving fansubs. It extracts chapters, subtitles, and fonts from MKV files, preserving the hard work of fansubbers and ensuring that high-quality subtitles and typesetting are not lost to time.

## <span style="color: #fbbc05;">✨ Features</span>

- 📂 Bulk extraction from multiple MKV files
- 📑 Extracts chapters, subtitles, and fonts
- 🎨 Preserves subtitle styles and fonts
- 📊 Real-time progress tracking
- ⚙️ Configurable settings
- 📝 Detailed logging

## <span style="color: #4a86e8;">🛠️ Installation</span>

1. Ensure you have Python 3.9 or higher installed.
2. Clone this repository:
   ```
   git clone https://github.com/yourusername/mkv-extractor.git
   cd mkv-extractor
   ```
3. Install the required Python modules:
   ```
   pip install rich configparser
   ```
4. Install MKVToolNix from [here](https://mkvtoolnix.download/).

## <span style="color: #34a853;">⚙️ Configuration</span>

Create a file named `mkv_extractor_config.ini` in the same directory as the script with the following content:

```ini
[Paths]
input_dir = C:\Anime
output_dir = C:\output
mkvextract_path = C:\Program Files\MKVToolNix\mkvextract.exe

[Settings]
use_parallel = false
max_workers = 4
max_log_lines = 1000
```

- `input_dir`: Directory containing your MKV files
- `output_dir`: Directory where extracted files will be saved
- `mkvextract_path`: Path to the mkvextract executable
- `use_parallel`: Set to `true` for parallel processing (faster but may use more resources or wear HDDs if files are stored on HDD - perfect option for SSDs)
- `max_workers`: Maximum number of parallel workers (if `use_parallel` is `true`)
- `max_log_lines`: Maximum number of log lines to keep in memory

## <span style="color: #ea4335;">🚀 Usage</span>

Run the script with:

```
python mkv_extractor.py
```

Or specify custom paths:

```
python mkv_extractor.py --input_dir "/path/to/input" --output_dir "/path/to/output" --mkvextract_path "/path/to/mkvextract"
```

## <span style="color: #fbbc05;">📊 Progress Tracking</span>

The script provides real-time progress tracking with a beautiful interface:

<p align="center">
  <img src="assets/Interface.jpg" alt="Progress Tracking" width="600">
</p>

## <span style="color: #4a86e8;">📁 Output Structure</span>

```
output_dir/
├── anime_name/
│   ├── chapters/
│   │   └── episode01_chapters.xml
│   ├── subs/
│   │   └── episode01_track2[English].ass
│   └── fonts/
│       └── custom_font.ttf
└── info.txt
```

