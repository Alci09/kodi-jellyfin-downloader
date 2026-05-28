## Installation & Setup
1. Install / copy the content 'context.jellyfin.downloader' into the Kodi "addon"-Folder
2. Open Kodi and navigate to **Add-ons** -> **Install from zip file** and select the downloaded `.zip` file.
3. **Generate an API Key:** Open your Jellyfin Web UI, go to **Dashboard** -> **API Keys** (under Advanced), and click the `+` to generate a new key.
4. **Configure the Add-on:** In Kodi, go to **My Add-ons** -> **Context menus** -> **Jellyfin Downloader** -> **Configure**. 
   * Enter your Jellyfin Server URL (e.g., `https://jellyfin.yourdomain.com`).
   * Paste your new API Key.
   * *(Optional)* Set a default download path to skip the folder selection prompt every time.
5. Long-press (or right-click) on any Movie, Episode, Season, TV Show, or Playlist in your library, and click **Download file**.

---

## 💡 Pro-Tip: The Best Offline User Experience Setup
For the best possible experience when taking your media off-grid (camping, road trips, airport, etc.), we highly recommend creating **two separate Profiles** in Kodi:

1. **Profile 1 (Online Manager):** This is your main profile connected to your Wi-Fi. You install the Jellyfin plugin here, browse your live server, and use this add-on to queue and download media to your external USB drive.
2. **Profile 2 (Offline Theater):** A clean profile completely disconnected from Jellyfin. Add your download folder as a standard Media Source in Kodi, and set the scraper to **"Local information only"**. 

Because this add-on automatically downloads all `.nfo` plots, posters, and fanart alongside your videos, **Profile 2 will instantly build a beautiful, Netflix-style interface offline**, requiring absolutely zero internet connection!
