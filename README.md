# Jellyfin Local Downloader for Kodi

A Kodi Context Menu add-on that enables direct, offline downloading from a Jellyfin server to local or external storage. 

This was specifically built to bypass the strict "Scoped Storage" write permissions introduced in Android TV 11, making it perfect for loading up a USB drive on portable projectors (like the BenQ GV50), Nvidia Shields, or Android TV boxes for offline viewing.

## The Problem This Solves
Native Android TV streaming apps do not support offline downloading. If you try to sideload mobile versions of Jellyfin or Findroid, Android TV 11's security blocks them from writing to external USB drives. 

**The Workaround:** Because Kodi natively requests proper system-level storage permissions, this add-on uses Kodi's internal Virtual File System (VFS) to securely pull video files from your Jellyfin server and write them directly to your USB drive.

## Features
* **Bypasses Android TV Restrictions:** Writes directly to external USB drives natively through Kodi.
* **No API Keys Required:** Uses a "Magic Resolver" intercept to securely fetch native HTTP streams directly from your existing Jellyfin Add-on session.
* **Bulk Downloading:** Long-press on a Season or an entire TV Show to queue the whole folder.
* **Unwatched Filtering:** Only download episodes you haven't seen yet.
* **Auto-Folder Generation:** Automatically organizes TV episodes into `Show Name/Season XX/` folders on your USB drive.
* **Background Processing:** Uses non-intrusive background toast notifications so you can keep browsing Kodi while files download.

## Installation
1. Go to the [Releases](https://github.com/Apollosport/kodi-jellyfin-downloader/releases) page and download the latest `context.jellyfin.downloader.zip` file.
2. Ensure you have the official **Jellyfin for Kodi** add-on installed and logged into your server. *(Note: This tool is built for Add-on mode, not Native Sync mode).*
3. Open Kodi and navigate to **Add-ons** -> **Install from zip file**.
4. Select the downloaded `.zip` file.
5. Long-press (or right-click) on any Movie, Episode, Season, or TV Show in your library, and click **Download file**.

## Known Limitations
* **External Subtitles:** This script intercepts the raw video file. If your movies are `.mkv` files with embedded subtitles, they will download perfectly. However, external `.srt` files sitting next to your movies on your server are not currently fetched.
* **No Simultaneous Downloads:** There is currently no active queue manager. Please allow a bulk download or single file download to complete before triggering another one, or the Kodi UI may throw an error.