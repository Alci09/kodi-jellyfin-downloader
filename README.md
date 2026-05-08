# Jellyfin Local Downloader for Kodi

A Kodi Context Menu add-on that enables direct, offline downloading from a Jellyfin server to local or external storage.

This was specifically built to bypass the strict "Scoped Storage" write permissions introduced in Android TV 11, making it perfect for loading up a USB drive on portable projectors (like the BenQ GV50), Nvidia Shields, or Android TV boxes for offline viewing.

---

## ⚠️ Version 2.0 vs Version 1.1
**Version 2.0 (Latest)** requires a Jellyfin API key to function. Moving to a direct API connection unlocked massive stability improvements, support for downloading entire **Playlists**, flawless Season/Series routing, and true background downloading (allowing you to watch other media while the queue processes).

**Version 1.1 (Legacy)** does *not* require an API key (it intercepts Kodi's internal player links). If you do not want to generate an API key, and do not need Playlist support or background playback capability, you can still download [Release V1.1](https://github.com/Apollosport/kodi-jellyfin-downloader/releases/tag/v1.1).

---

## The Problem This Solves
Native Android TV streaming apps do not support offline downloading. If you try to sideload mobile versions of Jellyfin or Findroid, Android TV 11's security blocks them from writing to external USB drives.

**The Workaround:** Because Kodi natively requests proper system-level storage permissions, this add-on uses Kodi's internal Virtual File System (VFS) to securely pull video files from your Jellyfin server via the REST API and write them directly to your USB drive.

## Features (V2.0)
* **Bypasses Android TV Restrictions:** Writes directly to external USB drives natively through Kodi.
* **Bulk Downloading:** Long-press on a Season, an entire TV Show, or a Playlist to queue all contents.
* **Smart Playlist Support:** Safely extracts the raw media files from your custom Jellyfin playlists.
* **Unwatched Filtering:** Only download episodes you haven't seen yet (handled server-side for lightning-fast queuing).
* **Auto-Folder Generation:** Automatically organizes TV episodes into `Show Name/Season XX/` folders on your USB drive.
* **True Background Processing:** Downloads run silently in the background with a visual progress indicator. Because V2.0 uses pure API requests, **you can now watch other videos in Kodi while your download queue processes!**
* **Proxy & Redirect Safe:** Includes a custom network engine to safely bypass reverse proxies and HTTP redirects without dropping authentication headers.

## Installation & Setup
1. Go to the [Releases](https://github.com/Apollosport/kodi-jellyfin-downloader/releases) page and download the latest `context.jellyfin.downloader.zip` file.
2. Open Kodi and navigate to **Add-ons** -> **Install from zip file** and select the downloaded `.zip` file.
3. **Generate an API Key:** Open your Jellyfin Web UI, go to **Dashboard** -> **API Keys** (under Advanced), and click the `+` to generate a new key.
4. **Configure the Add-on:** In Kodi, go to **My Add-ons** -> **Context menus** -> **Jellyfin Downloader** -> **Configure**. 
   * Enter your Jellyfin Server URL (e.g., `https://jellyfin.yourdomain.com`).
   * Paste your new API Key.
   * *(Optional)* Set a default download path to skip the folder selection prompt every time.
5. Long-press (or right-click) on any Movie, Episode, Season, TV Show, or Playlist in your library, and click **Download file**.

## Known Limitations
* **External Subtitles:** This script requests the raw video file. If your movies are `.mkv` files with embedded subtitles, they will download perfectly. However, external `.srt` files sitting next to your movies on your server are not currently fetched.

## Disclaimer
**Use at your own risk.** This add-on is provided "as-is" without any warranty. By using this software, you agree that the developer is not responsible for any corrupted files, data loss, USB drive formatting issues, or instability caused to your Kodi installation.

This is an unofficial, community-built tool and is not affiliated with, endorsed by, or supported by the official Jellyfin or Kodi development teams.

---
## 💖 Support the Project

If you feel like this plugin has helped you out, consider supporting its development! Your sponsorship helps cover the "fuel" (mostly coffee) for late-night bug-tracking and other fun.

**[Sponsor on GitHub](https://github.com/sponsors/Apollosport)**

Every bit of support is massively appreciated! 🌌