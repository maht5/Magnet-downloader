#!/usr/bin/env python3
import sys
import os
import time
import libtorrent as lt


def strip_trackers(magnet: str) -> str:
    parts = magnet.split("&")
    clean = [p for p in parts if not p.startswith("tr=")]
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

    while not handle.is_seed():
        s = handle.status()
        bar_len = 30
        filled = int(bar_len * s.progress)
        bar = "█" * filled + "░" * (bar_len - filled)
        dl = s.download_rate / 1000
        ul = s.upload_rate / 1000
        peers = s.num_peers
        print(
            f"\r[{bar}] {s.progress * 100:.1f}%  "
            f"↓ {dl:.0f} kB/s  ↑ {ul:.0f} kB/s  peers: {peers}  ",
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
    print("🧹 Trackers stripped")

    save_path = input("Save path [~/Downloads]: ").strip() or "~/Downloads"
    save_path = os.path.expanduser(save_path)

    try:
        download(magnet, save_path)
    except KeyboardInterrupt:
        print("\n\n⛔ Cancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()