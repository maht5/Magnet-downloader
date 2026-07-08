#!/usr/bin/env python3
import sys
import os
import time
import libtorrent as lt

# Trackers known for aggressive logging/tracking that we strip out.
# We keep the rest since more trackers = faster peer discovery = faster download.
BLOCKED_TRACKER_KEYWORDS = [
    "rarbg",
]


def strip_trackers(magnet: str) -> str:
    parts = magnet.split("&")
    clean = []
    for p in parts:
        if p.startswith("tr="):
            if any(bad in p.lower() for bad in BLOCKED_TRACKER_KEYWORDS):
                continue
        clean.append(p)
    return "&".join(clean)


def download(magnet: str, save_path: str = "."):
    settings = {"listen_interfaces": "0.0.0.0:6881"}
    ses = lt.session(settings)

    params = lt.parse_magnet_uri(magnet)
    params.save_path = save_path

    print(f"\n⏳ Fetching metadata...")
    handle = ses.add_torrent(params)

    while not handle.status().has_metadata:
        time.sleep(1)

    info = handle.torrent_file()
    print(f"📦 Name:  {info.name()}")
    print(f"📁 Size:  {info.total_size() / 1_000_000:.1f} MB")
    print(f"💾 Saving to: {save_path}\n")

    stall_seconds = 0
    stall_threshold = 20   # seconds with 0 peers before we force a reconnect

    while not handle.is_seed():
        s = handle.status()
        bar_len = 30
        filled = int(bar_len * s.progress)
        bar = "█" * filled + "░" * (bar_len - filled)
        dl = s.download_rate / 1000
        ul = s.upload_rate / 1000
        peers = s.num_peers

        if peers == 0:
            stall_seconds += 1
        else:
            stall_seconds = 0

        status_txt = ""
        if stall_seconds >= stall_threshold:
            status_txt = "  ⚠ reconnecting..."
            handle.force_reannounce()
            handle.force_dht_announce()
            stall_seconds = 0

        print(
            f"\r[{bar}] {s.progress * 100:.1f}%  "
            f"↓ {dl:.0f} kB/s  ↑ {ul:.0f} kB/s  peers: {peers}{status_txt}          ",
            end="", flush=True
        )
        time.sleep(1)

    print(f"\n\n✅ Done! Saved to: {save_path}/{info.name()}")


def main():
    magnet = input("Magnet link: ").strip()
    if not magnet.startswith("magnet:"):
        print("❌ Not a valid magnet link")
        sys.exit(1)

    magnet = strip_trackers(magnet)
    print("🧹 Untrustworthy trackers stripped (kept the rest for speed)")

    save_path = input("Save path [~/Downloads]: ").strip() or "~/Downloads"
    save_path = os.path.expanduser(save_path)

    try:
        download(magnet, save_path)
    except KeyboardInterrupt:
        print("\n\n⛔ Cancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()