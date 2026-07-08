# 🧲 Magnet Downloader

A simple command-line torrent downloader that works without any torrent client. Paste a magnet link and download directly from the terminal — with VPN leak protection built in.

> **macOS only.** This tool relies on macOS-specific features — `osascript` dialogs and `route`/`ifconfig` for VPN interface detection — so it won't run on Windows or Linux without changes.

## Features

- No torrent client required (no ads, no bloat)
- **VPN-aware:** verifies you're on Mullvad before downloading and binds the download to the VPN tunnel so it physically cannot leak your real IP
- Live progress bar with speed and peer count
- Accepts a magnet link on the command line, or pops up a native macOS dialog when launched without arguments
- Ctrl+C to cancel cleanly

## Requirements

- macOS
- Python 3.12+
- [Homebrew](https://brew.sh)
- [Mullvad VPN](https://mullvad.net), connected with **full-system VPN** and the **kill switch** enabled

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

Make sure Mullvad is connected first, then:

```bash
source venv/bin/activate
python downloader.py "magnet:?xt=..."
```

You can also pass an optional save path as a second argument:

```bash
python downloader.py "magnet:?xt=..." ~/Downloads/Movies
```

If you run it **without** a magnet link, it opens native macOS dialogs asking for the magnet link and save path — handy for launching via double-click or an Automator app. Leave the save path blank to use `~/Downloads`.

### Example output

```
✅ VPN active — 193.138.7.x via se-mma-wg-001 (Malmö, Sweden)
🔒 Bound to VPN interface utun4 (10.64.x.x) — cannot send outside it.

⏳ Fetching metadata...
📦 Name:  Example.Show.S01E01.1080p.mkv
📁 Size:  1423.2 MB
💾 Saving to: /Users/you/Downloads
[████████████░░░░░░░░░░░░░░░░░░] 41.2%  ↓ 8400 kB/s  ↑ 230 kB/s  peers: 63
✅ Done! Saved to: /Users/you/Downloads/Example.Show.S01E01.1080p.mkv
```

## VPN protection

The script protects against IP leaks in three layers:

1. **Startup check** — queries `am.i.mullvad.net` and refuses to start unless you're exiting through a Mullvad server. Fail-closed: if it can't confirm the VPN, it aborts.
2. **Interface binding** — the torrent session is bound to the Mullvad tunnel interface (`utun`). If the tunnel drops, the sockets simply fail; there is no fallback route to leak over, so protection is instant with no polling gap.
3. **Cleanup check** — every 30 seconds it re-confirms the tunnel and, if it's gone, pauses the download and exits with a clear message instead of hanging silently. This is a courtesy layer; the binding above is what actually prevents leaks.

Keep Mullvad's own **kill switch** enabled as well — it blocks traffic at the firewall level in milliseconds and is the outermost safety net.

> **Note:** interface binding assumes **full-system VPN** (the default route goes through Mullvad). If you switch to split tunneling, the detection binds to the wrong interface — see the note in `detect_vpn_interface()`.

## Notes

- The virtual environment must be active before running the script
- libtorrent uses ports 6881–6891 by default — make sure these are not blocked by your firewall
- If the VPN drops and reconnects with a new tunnel IP, the download stops (fail-safe) rather than resuming — just run the script again
- Downloading copyrighted content without permission may be illegal in your country

## License

MIT
