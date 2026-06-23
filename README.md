# 🧲 Magnet Downloader

A simple command-line torrent downloader that works without any torrent client. Just paste a magnet link and download directly from the terminal.

## Features

- No torrent client required (no ads, no bloat)
- Live progress bar with speed and peer count
- Prompts for magnet link and save path interactively
- Ctrl+C to cancel cleanly

## Requirements

- Python 3.12+
- [Homebrew](https://brew.sh) (macOS)

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/magnet-downloader.git
cd magnet-downloader
```

### 2. Create a virtual environment

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install libtorrent
```

### 4. (Optional) Add an alias for easy access

Add this to your `~/.zshrc`:

```bash
alias magnet='source ~/path/to/magnet-downloader/venv/bin/activate && python ~/path/to/magnet-downloader/downloader.py'
```

Then reload:

```bash
source ~/.zshrc
```

## Usage

```bash
source venv/bin/activate
python downloader.py
```

You will be prompted for:

```
Magnet link: <paste your magnet link here>
Save path [~/Downloads]: 
```

Leave save path blank to use `~/Downloads`.

### Example output

```
⏳ Fetching metadata...
📦 Name:  Example.Show.S01E01.1080p.mkv
📁 Size:  1423.2 MB
💾 Saving to: /Users/you/Downloads

[████████████░░░░░░░░░░░░░░░░░░] 41.2%  ↓ 8400 kB/s  ↑ 230 kB/s  peers: 63

✅ Done! Saved to: /Users/you/Downloads/Example.Show.S01E01.1080p.mkv
```

## Notes

- The virtual environment must be active before running the script
- libtorrent uses ports 6881–6891 by default — make sure these are not blocked by your firewall
- Downloading copyrighted content without permission may be illegal in your country

## License

MIT
