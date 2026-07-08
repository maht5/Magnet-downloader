#!/usr/bin/env python3
import sys
import os
import time
import json
import subprocess
import argparse
import urllib.request
import libtorrent as lt


def mac_dialog(prompt: str, default: str = "") -> str | None:
    """Show a native macOS input dialog and return the entered text, or None if cancelled."""
    script = f'''
    set userInput to display dialog "{prompt}" default answer "{default}" with title "Magnet Downloader"
    return text returned of userInput
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None  # user cancelled
        return result.stdout.strip()
    except FileNotFoundError:
        return None


def mac_alert(message: str):
    """Show a native macOS error alert. No-op if osascript is unavailable."""
    script = f'''
    display alert "Magnet Downloader" message "{message}" as critical
    '''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    except FileNotFoundError:
        pass


def get_vpn_status(timeout: int = 10) -> dict:
    """Ask Mullvad where we exit from. Raises on any network failure."""
    with urllib.request.urlopen("https://am.i.mullvad.net/json", timeout=timeout) as r:
        return json.load(r)


def check_vpn(gui: bool = False) -> str:
    """Confirm traffic exits through Mullvad before downloading.
    Fail-closed: if we can't confirm the VPN, we abort.
    Returns the current Mullvad exit IP (for the cleanup check to watch)."""
    try:
        data = get_vpn_status(timeout=10)
    except Exception as e:
        msg = f"Could not verify VPN ({e}). Aborting for safety."
        print(f"⛔ {msg}")
        if gui:
            mac_alert(msg)
        sys.exit(1)

    ip = data.get("ip", "?")
    if data.get("mullvad_exit_ip"):
        host = data.get("mullvad_exit_ip_hostname", "?")
        city = data.get("city", "?")
        country = data.get("country", "?")
        print(f"✅ VPN active — {ip} via {host} ({city}, {country})")
        return ip
    else:
        msg = f"You are NOT on Mullvad! Your visible IP is {ip}. Aborting."
        print(f"⛔ {msg}")
        if gui:
            mac_alert(msg)
        sys.exit(1)


def detect_vpn_interface():
    """Find the interface carrying the default route — the Mullvad tunnel when
    full-system VPN is active. Returns (device, local_ip) or (None, None).

    Assumes full-system VPN (default route through Mullvad). If you switch to
    split tunneling — only routing Python through the VPN — the default route
    is your physical NIC instead, and you'd bind to the utun by name manually.
    """
    try:
        out = subprocess.run(
            ["route", "-n", "get", "default"], capture_output=True, text=True
        ).stdout
    except Exception:
        return None, None

    dev = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("interface:"):
            dev = line.split(":", 1)[1].strip()

    if not dev:
        return None, None

    try:
        out = subprocess.run(["ifconfig", dev], capture_output=True, text=True).stdout
    except Exception:
        return dev, None

    ip = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            ip = line.split()[1]
            break

    return dev, ip


def _abort_download(handle, message: str, gui: bool):
    """Pause the torrent and exit — used when the cleanup check trips."""
    print(f"\n\n⛔ {message}")
    if gui:
        mac_alert(message)
    try:
        handle.pause()
    except Exception:
        pass
    sys.exit(1)


def _cleanup_check(handle, expected_exit_ip: str, gui: bool):
    """Secondary check. The interface binding already prevents leaks the instant
    the tunnel drops; this just notices we've lost the tunnel and exits cleanly
    instead of leaving a dead, stalled download hanging silently."""
    try:
        data = get_vpn_status(timeout=8)
    except Exception as e:
        _abort_download(handle, f"Lost connection to the VPN ({e}). Stopping.", gui)
        return

    if not data.get("mullvad_exit_ip"):
        _abort_download(
            handle,
            f"VPN dropped — traffic now exits from {data.get('ip', '?')}. Stopping.",
            gui,
        )
        return

    ip = data.get("ip")
    if expected_exit_ip and ip != expected_exit_ip:
        print(f"\n⚠ Mullvad exit changed ({expected_exit_ip} → {ip}), still protected.\n")


def download(magnet: str, save_path: str = ".", expected_exit_ip: str = None,
             gui: bool = False, cleanup_interval: int = 30):
    # Bind the torrent session to the VPN tunnel so it physically cannot send
    # outside the tunnel. If the interface disappears, the sockets just fail.
    dev, tun_ip = detect_vpn_interface()
    if not (dev and dev.startswith("utun") and tun_ip):
        msg = ("Found no active VPN tunnel to bind to. "
               "Is Mullvad connected with full-system VPN? Aborting.")
        print(f"⛔ {msg}")
        if gui:
            mac_alert(msg)
        sys.exit(1)

    settings = {
        "listen_interfaces": f"{tun_ip}:6881",
        "outgoing_interfaces": tun_ip,
    }
    print(f"🔒 Bound to VPN interface {dev} ({tun_ip}) — cannot send outside it.")

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
    stall_threshold = 20
    last_cleanup_check = time.time()

    while True:
        s = handle.status()
        if s.progress >= 1.0:
            break

        if time.time() - last_cleanup_check >= cleanup_interval:
            last_cleanup_check = time.time()
            _cleanup_check(handle, expected_exit_ip, gui)

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
    parser = argparse.ArgumentParser(description="Magnet link downloader")
    parser.add_argument("magnet", nargs="?", help="Magnet link (wrap in quotes)")
    parser.add_argument("save_path", nargs="?", default=None, help="Where to save the download")
    args = parser.parse_args()

    magnet = args.magnet
    save_path = args.save_path

    # GUI mode = launched without a magnet argument (double-click / Automator etc.)
    gui = not magnet

    # Confirm Mullvad exit; keep the exit IP for the cleanup check.
    exit_ip = check_vpn(gui=gui)

    if not magnet:
        magnet = mac_dialog("Paste magnet link:")
        if not magnet:
            print("⛔ Cancelled")
            sys.exit(0)

    if not magnet.startswith("magnet:"):
        print("❌ Not a valid magnet link")
        sys.exit(1)

    if not save_path:
        save_path = mac_dialog("Save path:", default="~/Downloads")
        if save_path is None:
            print("⛔ Cancelled")
            sys.exit(0)

    save_path = save_path or "~/Downloads"
    save_path = os.path.expanduser(save_path)

    try:
        download(magnet, save_path, expected_exit_ip=exit_ip, gui=gui)
    except KeyboardInterrupt:
        print("\n\n⛔ Cancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()