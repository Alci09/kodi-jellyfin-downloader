# Jellyfin Local Downloader for Kodi

A Kodi Context Menu add-on that enables direct, offline downloading from a Jellyfin server to local or external storage.

This was specifically built to bypass the strict "Scoped Storage" write permissions introduced in Android TV 11, making it perfect for loading up a USB drive on portable projectors (like the BenQ GV50), Nvidia Shields, or Android TV boxes for offline viewing.

---

## ⚠️ Version 2.1 vs Version 1.1
**Version 2.1 (Latest)** requires a Jellyfin API key to function. Moving to a direct API connection unlocked massive stability improvements, support for downloading entire **Playlists**, flawless Season/Series routing, true background downloading, and **Full Offline Library Sync** (auto-generating metadata and artwork).

**Version 1.1 (Legacy)** does *not* require an API key (it intercepts Kodi's internal player links). If you do not want to generate an API key, and do not need Playlist support, metadata generation, or background playback capability, you can still download [Release V1.1](https://github.com/Apollosport/kodi-jellyfin-downloader/releases/tag/v1.1).

---

## The Problem This Solves
Native Android TV streaming apps do not support offline downloading. If you try to sideload mobile versions of Jellyfin or Findroid, Android TV 11's security blocks them from writing to external USB drives.

**The Workaround:** Because Kodi natively requests proper system-level storage permissions, this add-on uses Kodi's internal Virtual File System (VFS) to securely pull video files from your Jellyfin server via the REST API and write them directly to your USB drive.

## Features
* **Full Offline Library Sync (New in 2.1):** It doesn't just download the video. It automatically generates Kodi-perfect `.nfo` metadata files, grabs posters/fanart, and downloads external `.srt`/`.ass` subtitles, perfectly renaming them to match your video files.
* **Bypasses Android TV Restrictions:** Writes directly to external USB drives natively through Kodi.
* **Bulk Downloading:** Long-press on a Season, an entire TV Show, or a Playlist to queue all contents.
* **Smart Playlist Support:** Safely extracts the raw media files from your custom Jellyfin playlists.
* **Unwatched Filtering:** Only download episodes you haven't seen yet (handled server-side for lightning-fast queuing).
* **Auto-Folder Generation:** Automatically organizes TV episodes into `Show Name/Season XX/` folders on your USB drive.
* **True Background Processing:** Downloads run silently in the background with a visual progress indicator. Because V2.1 uses pure API requests, **you can now watch other videos in Kodi while your download queue processes!**

## Installation & Setup
1. Go to the [Releases](https://github.com/Apollosport/kodi-jellyfin-downloader/releases) page and download the latest `context.jellyfin.downloader.zip` file.
2. Open Kodi and navigate to **Add-ons** -> **Install from zip file** and select the downloaded `.zip` file.
3. **Generate an API Key:** Open your Jellyfin Web UI, go to **Dashboard** -> **API Keys** (under Advanced), and click the `+` to generate a new key.
4. **Configure the Add-on:** In Kodi, go to **My Add-ons** -> **Context menus** -> **Jellyfin Downloader** -> **Configure**. 
   * Enter your Jellyfin Server URL (e.g., `https://jellyfin.yourdomain.com`).
   * Paste your new API Key.
   * *(Optional)* Set a default download path to skip the folder selection prompt every time.
5. Long-press (or right-click) on any Movie, Episode, Season, TV Show, or Playlist in your library, and click **Download file**.

---

## 💡 Pro-Tip: The Best Offline User Experience Setup
For the best possible experience when taking your media off-grid (camping, road trips, Airport, etc.), we highly recommend creating **two separate Profiles** in Kodi:

1. **Profile 1 (Online Manager):** This is your main profile connected to your Wi-Fi. You install the Jellyfin plugin here, browse your live server, and use this add-on to queue and download media to your external USB drive.
2. **Profile 2 (Offline Theater):** A clean profile completely disconnected from Jellyfin. Add your download folder as a standard Media Source in Kodi, and set the scraper to **"Local information only"**. 

Because this add-on automatically downloads all `.nfo` plots, posters, and fanart alongside your videos, **Profile 2 will instantly build a beautiful, Netflix-style interface offline**, requiring absolutely zero internet connection!

---

## Known Limitations
* **Messy Subtitle Filenames:** While this add-on *does* download external subtitles, it relies on Jellyfin's API knowing they exist. If your `.srt` files on your server are named poorly (e.g., `movietitle.spa.45.srt` instead of matching the video file exactly) and Jellyfin's scanner ignores them, this add-on will not be able to find them either. Keep your server library well-organized! (I failed at this in the past ;)

## Disclaimer
**Use at your own risk.** This add-on is provided "as-is" without any warranty. By using this software, you agree that the developer is not responsible for any corrupted files, data loss, USB drive formatting issues, or instability caused to your Kodi installation.

This is an unofficial, community-built tool and is not affiliated with, endorsed by, or supported by the official Jellyfin or Kodi development teams.

---
## 💖 Support the Project

If you feel like this plugin has helped you out, consider supporting its development! Your sponsorship helps cover the "fuel" (mostly coffee) for late-night bug-tracking and other fun.

**[Sponsor on GitHub](https://github.com/sponsors/Apollosport)**

Every bit of support is massively appreciated! 🌌