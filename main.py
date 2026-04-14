import sys
import os
import json
import re
import urllib.request
import xbmc
import xbmcgui
import xbmcvfs
import traceback

class MagicResolver(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.found_url = None

    def onPlayBackStarted(self):
        # Steal the fully resolved HTTP link the split-second playback starts
        self.found_url = self.getPlayingFile()
        self.stop()

def get_plugin_items(directory):
    req = {
        "jsonrpc": "2.0",
        "method": "Files.GetDirectory",
        "params": {
            "directory": directory,
            "media": "files",
            "properties": ["file", "title", "playcount", "filetype"]
        },
        "id": 1
    }
    try:
        res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
        return res.get('result', {}).get('files', [])
    except:
        return []

def gather_episodes(directory, unwatched_only):
    items = get_plugin_items(directory)
    episodes = []
    for item in items:
        if item.get('filetype') == 'directory':
            episodes.extend(gather_episodes(item.get('file'), unwatched_only))
        else:
            if unwatched_only and item.get('playcount', 0) > 0:
                continue
            file_url = item.get('file', '')
            if file_url:
                episodes.append({
                    'title': item.get('title', 'Episode'),
                    'plugin_url': file_url
                })
    return episodes

def resolve_and_download(item_label, plugin_url, download_dir, subfolder, dpBG):
    ext = '.mkv'
    if 'filename=' in plugin_url:
        match = re.search(r'filename=[^&]+\.(\w{3,4})', plugin_url)
        if match: ext = '.' + match.group(1)
        
    safe_title = "".join([c for c in item_label if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    
    # --- FOLDER STRUCTURE LOGIC ---
    final_dir = download_dir
    if not final_dir.endswith('/') and not final_dir.endswith('\\'):
        final_dir += '/'
        
    if subfolder:
        final_dir += subfolder + '/'
        
    # If the Show/Season folder doesn't exist on the USB, create it!
    if not xbmcvfs.exists(final_dir):
        xbmcvfs.mkdirs(final_dir)
        
    dest_path = final_dir + safe_title + ext
    
    if xbmcvfs.exists(dest_path):
        return True 
        
    dpBG.update(0, heading=f"Resolving: {safe_title}", message="Extracting secure link...")
    resolver = MagicResolver()
    resolver.play(plugin_url)
    
    timeout = 20
    while not resolver.found_url and timeout > 0:
        xbmc.sleep(500)
        timeout -= 1
        
    if not resolver.found_url: return False
        
    real_url = resolver.found_url
    
    try:
        req = urllib.request.Request(real_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        total_size = int(response.headers.get('content-length', 0))
        
        if total_size <= 0: return False
        
        f_out = xbmcvfs.File(dest_path, 'w')
        chunk_size = 1024 * 1024 
        downloaded = 0
        last_percent = -1
        
        while True:
            chunk = response.read(chunk_size)
            if not chunk: break
            f_out.write(chunk)
            downloaded += len(chunk)
            
            if total_size > 0:
                percent = int((downloaded / total_size) * 100)
                if percent != last_percent:
                    msg = f"{downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB"
                    dpBG.update(percent, heading=f"Downloading: {safe_title}", message=msg)
                    last_percent = percent
                    
        f_out.close()
        return True
    except Exception as e:
        xbmc.log(f"Jellyfin DL Error: {e}", xbmc.LOGERROR)
        return False

def main():
    dialog = xbmcgui.Dialog()
    
    try:
        listitem = sys.listitem
        db_type = xbmc.getInfoLabel('ListItem.DBType')
        item_label = listitem.getLabel()
        
        folder_path = ""
        try: folder_path = listitem.getPath()
        except: pass
        if not folder_path: folder_path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
        if not folder_path: folder_path = xbmc.getInfoLabel('ListItem.FolderPath')
            
        if not folder_path:
            dialog.ok("Path Error", f"Kodi refused to hand over a path for '{item_label}'.")
            return
            
        items_to_download = []
        
        # --- HANDLE SEASON AND FULL TV SHOW BULK DOWNLOADS ---
        if db_type in ['season', 'tvshow'] or folder_path.endswith('/') or ('plugin://' in folder_path and 'action=' not in folder_path):
            
            ans = dialog.select(f"Queue {item_label}?", ["Download All Episodes", "Download Unwatched Only"])
            if ans == -1: return 
            unwatched_only = (ans == 1)
            
            raw_episodes = []
            db_id = -1
            try:
                infoTag = listitem.getVideoInfoTag()
                db_id = infoTag.getDbId()
            except: pass
            if db_id <= 0:
                db_id_str = xbmc.getInfoLabel('ListItem.DBID')
                if db_id_str and db_id_str.isdigit(): db_id = int(db_id_str)

            # METHOD 1: SQLite Database Query (Added 'showtitle' to properties)
            if db_type == 'tvshow' and db_id > 0:
                req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": db_id, "properties": ["file", "playcount", "title", "episode", "season", "showtitle"]}, "id": 1}
                res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
                raw_episodes = res.get('result', {}).get('episodes', [])
                
            elif db_type == 'season' and db_id > 0:
                req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasonDetails", "params": {"seasonid": db_id, "properties": ["tvshowid", "season"]}, "id": 1}
                res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
                s_details = res.get('result', {}).get('seasondetails', {})
                if s_details and s_details.get('tvshowid'):
                    req_ep = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": s_details['tvshowid'], "season": s_details['season'], "properties": ["file", "playcount", "title", "episode", "season", "showtitle"]}, "id": 1}
                    res_ep = json.loads(xbmc.executeJSONRPC(json.dumps(req_ep)))
                    raw_episodes = res_ep.get('result', {}).get('episodes', [])
            
            # METHOD 2: Virtual Folder Scraper Fallback
            if not raw_episodes and folder_path:
                raw_episodes = gather_episodes(folder_path, unwatched_only)
                
            if not raw_episodes:
                dialog.ok("Info", "No video files found inside this folder.")
                return
                
            # Filter, assign folders, and queue episodes
            for ep in raw_episodes:
                if 'playcount' in ep and unwatched_only and ep.get('playcount', 0) > 0:
                    continue
                    
                plugin_url = ep.get('file', ep.get('plugin_url', ''))
                if not plugin_url: continue
                
                safe_ep_title = "".join([c for c in ep.get('title', 'Episode') if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                
                subfolder = ""
                # If we have Show and Season metadata, perfectly organize it!
                if 'showtitle' in ep and 'season' in ep:
                    safe_show_title = "".join([c for c in ep.get('showtitle', 'Show') if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    season_num = int(ep['season'])
                    subfolder = f"{safe_show_title}/Season {season_num:02d}"
                    ep_label = f"{safe_show_title} - S{season_num:02d}E{int(ep.get('episode', 0)):02d} - {safe_ep_title}"
                else:
                    # Fallback organization if metadata is missing
                    safe_parent = "".join([c for c in item_label if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    subfolder = safe_parent
                    ep_label = f"{safe_parent} - {safe_ep_title}"
                    
                items_to_download.append({'title': ep_label, 'plugin_url': plugin_url, 'subfolder': subfolder})
                
            if not items_to_download:
                dialog.ok("Info", "No episodes queued. (If filtering by unwatched, you might have watched them all!)")
                return
                
        # --- HANDLE SINGLE MOVIE/EPISODE DOWNLOADS ---
        else:
            plugin_url = folder_path
            db_id = -1
            try:
                infoTag = listitem.getVideoInfoTag()
                db_id = infoTag.getDbId()
            except: pass
            if db_id <= 0:
                db_id_str = xbmc.getInfoLabel('ListItem.DBID')
                if db_id_str and db_id_str.isdigit(): db_id = int(db_id_str)
                
            if db_type == 'movie' and db_id > 0:
                req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": db_id, "properties": ["file"]}, "id": 1}
                res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
                db_file = res.get('result', {}).get('moviedetails', {}).get('file', '')
                if db_file: plugin_url = db_file
            elif db_type == 'episode' and db_id > 0:
                req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid": db_id, "properties": ["file"]}, "id": 1}
                res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
                db_file = res.get('result', {}).get('episodedetails', {}).get('file', '')
                if db_file: plugin_url = db_file
                
            # Single files get dropped directly into the root of the chosen directory (No subfolder)
            items_to_download.append({'title': item_label, 'plugin_url': plugin_url, 'subfolder': ""})
            
        # --- GLOBAL DOWNLOAD PROCESS ---
        download_dir = dialog.browse(3, 'Select Download Destination', 'files')
        if not download_dir: return
        
        dpBG = xbmcgui.DialogProgressBG()
        dpBG.create("Jellyfin Downloader", "Starting...")
        
        success_count = 0
        total = len(items_to_download)
        
        try:
            for idx, item in enumerate(items_to_download):
                dpBG.update(0, heading=f"Processing {idx+1}/{total}", message=item['title'])
                if resolve_and_download(item['title'], item['plugin_url'], download_dir, item['subfolder'], dpBG):
                    success_count += 1
        finally:
            dpBG.close()
        
        dialog.notification("Complete", f"Successfully downloaded {success_count} of {total} items.", xbmcgui.NOTIFICATION_INFO, 5000)

    except Exception as e:
        tb = traceback.format_exc()
        xbmc.log(f"Jellyfin DL Crash: {tb}", xbmc.LOGFATAL)
        dialog.ok("Fatal Plugin Crash", f"An unexpected error occurred:\n{str(e)}\n\nPlease send this to the developer.")

if __name__ == '__main__':
    main()