# Telegram Media Downloader

🇮🇹 [Leggi in italiano](README-it.md)

Automated Python tool for smart media downloads (videos, photos, documents, archives, ...) from Telegram channels, with advanced filters for date, file type, filename pattern and download limit.

---

## 🚀 Features

* **No 20 MB / 50 MB limit**: Uses Telethon's MTProto APIs (supports downloads up to 2 GB for standard accounts and 4 GB for Telegram Premium).
* **Start Date Filter (`--start-date`)**: Fetches messages starting from a specific date (`YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`).
* **Wildcard Filter (`--pattern`)**: Searches the given pattern (e.g. `*tutorial*.mp4`, `*guide*`, `*1080p*`) in both the **file name** and the **description (caption)** text of the Telegram post.
* **File Type Filter (`--media-type`)**: Downloads only the chosen categories (`video`, `photo`, `documents`, `archives`) or MIME patterns (e.g. `image/*`, `application/pdf`); default `all` downloads every format.
* **Quantity Limit (`--limit`)**: Sets the maximum number of files to download.
* **Video Resolution Filter (`--min-res` / `--max-res`)**: Filters videos by their original resolution before downloading (default: minimum `480p`, maximum `1080p`).
* **Maximum Size Filter (`--max-size`)**: Sets the maximum allowed size for downloaded videos (default: `1.5GB`).
* **Smart Duplicate Check**: Automatically skips already downloaded files without counting them toward `--limit` (e.g. with `-l 5` it will download 5 actual **new** videos).
* **Optional Size Check (`--check-size`)**: By default the download is skipped if a file with the same name already exists; enabling `--check-size` also verifies that the file size matches exactly.
* **Smart Fallback**: Recognizes both native videos and video document files; if the file has no name, a clean name is derived from the post text/caption.
* **Real-Time Scan Feedback**: Shows a live counter with the number of scanned messages, the current scan date, and downloaded and skipped files.
* **On-the-Fly Interrupt / Skip**: While any video is downloading, pressing **`S`** or **`ESC`** instantly stops the current download, deletes the partial/incomplete file from disk and moves on to the next message.
* **Interactive Progress Bar**: Shows transfer speed (MB/s), percentage and elapsed time for each download using the `rich` library.
* **Rate-Limit Handling**: Automatically handles Telegram `FloodWaitError`s, resuming once the wait is over.

---

## 📦 Installation

### 1. Clone or open the project folder
```bash
cd d:\Progetti\TelegramMediaDownloader
```

### 2. Create and activate the virtual environment
```bash
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (CMD):
.\venv\Scripts\activate.bat

# Linux / macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🔑 Telegram API Configuration

To use the Telegram client you need an `API_ID` and an `API_HASH`:

1. Log in to [https://my.telegram.org](https://my.telegram.org) with your Telegram phone number.
2. Go to **"API development tools"**.
3. Create a new application (e.g. name: `MediaDownloader`).
4. Copy `api_id` and `api_hash`.
5. Create a `.env` file from the example file:
   ```bash
   cp .env.example .env
   ```
6. Enter your credentials in the `.env` file:
   ```ini
   TG_API_ID=12345678
   TG_API_HASH=abcdef1234567890abcdef1234567890
   TG_SESSION_NAME=session_downloader
   DEFAULT_DOWNLOAD_PATH=./downloads
   ```

*Note: On first run, Telethon will ask in the terminal for your phone number and the verification code sent via Telegram (and your 2FA password, if enabled). The session will be saved locally in the `.session` file.*

---

## 💻 Usage Examples

### Example 1: Download with pattern and limit
Download the first 5 videos containing the word "tutorial" in the name or caption:
```bash
python main.py --channel @channelname --pattern "*tutorial*.mp4" --limit 5
```

### Example 2: Download from a specific date
Download all videos published since January 1st, 2024:
```bash
python main.py --channel @channelname --start-date 2024-01-01
```

### Example 3: Full download with all parameters
Download up to 10 `.mp4` videos starting from June 15th, 2024, saving them to a custom folder:
```bash
python main.py -c @channelname -d 2024-06-15 -l 10 -p "*.mp4" -o "./my_videos"
```

### Example 4: Download by file type
Download up to 50 documents and archives published since July 18th, 2023, using the virtual environment's Python directly:
```bash
.\venv\Scripts\python.exe main.py -c "t.me/channelname" -d 2023-07-18 -l 50 --media-type documents,archives -o "./files"
```

### Available CLI options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--channel` | `-c` | Channel username (`@channel`), link (`https://t.me/...`) or ID | *Required* |
| `--start-date` | `-d` | Start date (`YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`) | None |
| `--limit` | `-l` | Maximum number of files to download | All |
| `--pattern` | `-p` | Wildcard pattern for the file name (e.g. `*lesson*.mp4`) | All |
| `--media-type` | `-t` | Comma-separated categories (`video`, `photo`, `documents`, `archives`) or MIME patterns (e.g. `image/*`) | `all` |
| `--min-res` | | Minimum allowed resolution (e.g. `480p`, `720p`, `none`) | `480p` |
| `--max-res` | | Maximum allowed resolution (e.g. `1080p`, `4k`, `none`) | `1080p` |
| `--max-size` | | Maximum file size (e.g. `500MB`, `1.5GB`, `none`) | `1.5GB` |
| `--output` | `-o` | Folder where files are saved | `./downloads` |
| `--check-size` / `--no-check-size` | | Also check the file size to detect duplicates | `False` (name only) |
| `--search-caption` / `--no-search-caption` | | Also search the pattern in the post caption | `True` |
| `--reverse` / `--no-reverse` | | Download from oldest to newest starting from `start-date` | `True` |

---

## 🛡️ Security Notes
* Never share your `.env` file or your `.session` file.
* The `.gitignore` file is already configured to exclude sessions, downloads and environment variables.
