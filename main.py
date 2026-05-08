import sys
import os
import json
import re
import urllib.request
import urllib.parse
import ssl
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import traceback

# --- LOAD USER SETTINGS ---
ADDON = xbmcaddon.Addon()
SERVER_URL = ADDON.getSetting('server_url').rstrip('/')
API_KEY = ADDON.getSetting('api_key').strip()
USE_DEFAULTS = ADDON.getSetting('use_default_folders') == 'true'
ROOT_FOLDER = ADDON.getSetting('default_root_folder')
FORCE_UNWATCHED = ADDON.getSetting('use_unwatched_toggle') == 'true'

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

AUTH_HEADER = f'MediaBrowser Client="KodiDL", Device="Kodi", DeviceId="kodi-jellyfin-dl", Version="2.0.0", Token="{API_KEY}"'

def get_jellyfin_api(endpoint):
    if not SERVER_URL or not API_KEY:
        return None
        
    url = f"{SERVER_URL}{endpoint}"
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'Authorization': AUTH_HEADER})
    try:
        with urllib.request.urlopen(req, context=CTX) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f"Jellyfin API Error on {url}: {e}", xbmc.LOGERROR)
        return None

def get_user_id():
    users = get_jellyfin_api('/Users')
    if users and isinstance(users, list) and len(users) > 0:
        for u in users:
            if u.get('Policy', {}).get('IsAdministrator'): return u.get('Id')
        return users[0].get('Id')
    return None

def extract_item_id(path):
    if not path: return None

    match_folder = re.search(r'(?i)folder=([a-fA-F0-9\-]{32,})', path)
    if match_folder: return match_folder.group(1).replace('-', '')
    
    match_id = re.search(r'(?i)(?:id|itemid|seasonid|tvshowid|seriesid)=([a-fA-F0-9\-]{32,})', path)
    if match_id: return match_id.group(1).replace('-', '')
    
    return None

def resolve_db_id(db_type, db_id, listitem):
    try:
        if db_type in ['movie', 'episode']:
            method_map = {
                'movie': ('VideoLibrary.GetMovieDetails', 'movieid', 'moviedetails'),
                'episode': ('VideoLibrary.GetEpisodeDetails', 'episodeid', 'episodedetails')
            }
            method, param_key, res_key = method_map[db_type]
            req = {"jsonrpc": "2.0", "method": method, "params": {param_key: db_id, "properties": ["file", "uniqueid"]}, "id": 1}
            res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
            details = res.get('result', {}).get(res_key, {})
            
            uids = details.get('uniqueid', {})
            for provider in ['jellyfin', 'emby']:
                if provider in uids: return uids[provider].replace('-', ''), False
            extracted = extract_item_id(details.get('file', ''))
            if extracted: return extracted, False

        if db_type in ['tvshow', 'season']:
            kodi_tvshowid = db_id if db_type == 'tvshow' else None
            season_num = None
            
            if db_type == 'season':
                path = listitem.getPath()
                if 'videodb://tvshows/titles/' in path:
                    parts = path.split('/')
                    if len(parts) >= 6:
                        kodi_tvshowid = int(parts[4])
                        season_num = int(parts[5])
                else:
                    infoTag = listitem.getVideoInfoTag()
                    try: kodi_tvshowid = infoTag.getTvShowId()
                    except: pass
                    try: season_num = infoTag.getSeason()
                    except: pass

            if kodi_tvshowid is not None:
                params = {"tvshowid": kodi_tvshowid, "properties": ["file", "uniqueid"], "limits": {"start": 0, "end": 1}}
                if season_num is not None and season_num >= 0:
                    params["season"] = season_num
                    
                req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": params, "id": 1}
                res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
                episodes = res.get('result', {}).get('episodes', [])
                if episodes:
                    uids = episodes[0].get('uniqueid', {})
                    for provider in ['jellyfin', 'emby']:
                        if provider in uids: return uids[provider].replace('-', ''), True
                    extracted = extract_item_id(episodes[0].get('file', ''))
                    if extracted: return extracted, True
                    
    except Exception as e:
        xbmc.log(f"Jellyfin DB Resolver Error: {e}", xbmc.LOGERROR)
        
    return None, False

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None 

def download_file(title, download_url, dest_path, dpBG):
    if xbmcvfs.exists(dest_path):
        return True
        
    try:
        current_url = download_url
        headers = {'User-Agent': 'Mozilla/5.0', 'Authorization': AUTH_HEADER}
        
        opener = urllib.request.build_opener(NoRedirectHandler(), urllib.request.HTTPSHandler(context=CTX))
        response = None
        
        for _ in range(5):
            req = urllib.request.Request(current_url, headers=headers)
            try:
                response = opener.open(req)
                break
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    location = e.headers.get('Location')
                    if not location: return "Redirect error: Server provided no Location header."
                    current_url = urllib.parse.urljoin(current_url, location)
                else:
                    return f"HTTP Error {e.code}: {e.reason}"
        
        if not response:
            return "Failed to download after maximum redirects."
            
        total_size_str = response.headers.get('content-length')
        total_size = int(total_size_str) if total_size_str else 0
        
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
                    dpBG.update(percent, heading=f"Downloading: {title}", message=msg)
                    last_percent = percent
            else:
                msg = f"Downloaded: {downloaded // (1024*1024)} MB (Size Unknown)"
                dpBG.update(50, heading=f"Downloading: {title}", message=msg)
                    
        f_out.close()
        return True
             
    except Exception as e:
        return str(e)

def main():
    dialog = xbmcgui.Dialog()
    
    if not SERVER_URL or not API_KEY:
        dialog.ok("Settings Required", "Please configure your Settings.")
        ADDON.openSettings()
        return

    try:
        listitem = sys.listitem
        item_label = listitem.getLabel()
        
        folder_path = ""
        try: folder_path = listitem.getPath()
        except: pass
        if not folder_path: folder_path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
        if not folder_path: folder_path = xbmc.getInfoLabel('ListItem.FolderPath')
            
        item_id = extract_item_id(folder_path)
        db_type = xbmc.getInfoLabel('ListItem.DBType')
        needs_climb = False
        
        if not item_id:
            prop_id = listitem.getProperty('ItemId')
            if prop_id and len(prop_id.replace('-', '')) == 32: item_id = prop_id.replace('-', '')
        
        if not item_id:
            db_id = -1
            try:
                infoTag = listitem.getVideoInfoTag()
                db_id = infoTag.getDbId()
            except: pass
            if db_id <= 0:
                db_id_str = xbmc.getInfoLabel('ListItem.DBID')
                if db_id_str and db_id_str.isdigit(): db_id = int(db_id_str)
                
            if db_id > 0:
                item_id, needs_climb = resolve_db_id(db_type, db_id, listitem)

        if not item_id:
            dialog.ok("Error", "Could not extract Jellyfin Item ID. Make sure you are selecting a Jellyfin item.")
            return

        user_id = get_user_id()
        if not user_id:
            dialog.ok("API Error", "Could not retrieve a User ID from the server.")
            return

        item_info = get_jellyfin_api(f"/Items/{item_id}?userId={user_id}")
        if not item_info:
            dialog.ok("API Error", "Could not connect to the Jellyfin API.")
            return

        if needs_climb:
            if db_type == 'tvshow' and item_info.get("SeriesId"):
                item_id = item_info.get("SeriesId")
                item_info = get_jellyfin_api(f"/Items/{item_id}?userId={user_id}")
            elif db_type == 'season' and item_info.get("SeasonId"):
                item_id = item_info.get("SeasonId")
                item_info = get_jellyfin_api(f"/Items/{item_id}?userId={user_id}")

        item_type = item_info.get("Type")
        
        # Absolute safety net to stop full library downloads!
        if item_type == 'CollectionFolder':
            dialog.ok("Safety Abort", f"Root Library Folder detected. Aborting to prevent full library download.")
            return

        items_to_process = []
        valid_bulk_types = ['Series', 'Season', 'Playlist', 'BoxSet', 'Folder', 'UserView']

        unwatched_only = FORCE_UNWATCHED
        if item_type in valid_bulk_types and not FORCE_UNWATCHED:
            ans = dialog.select(f"Queue {item_label}?", ["Download All Content", "Download Unwatched Only"])
            if ans == -1: return
            unwatched_only = (ans == 1)

        fields = "Path,Container,MediaSources,UserData"
        unwatched_param = "&Filters=IsUnplayed" if unwatched_only else ""

        if item_type == 'Playlist':
            url = f"/Playlists/{item_id}/Items?userId={user_id}&Fields={fields}"
            res = get_jellyfin_api(url)
            if res and "Items" in res: items_to_process = res["Items"]
                
        elif item_type == 'Series':
            url = f"/Shows/{item_id}/Episodes?userId={user_id}&Fields={fields}{unwatched_param}"
            res = get_jellyfin_api(url)
            if res and "Items" in res: items_to_process = res["Items"]
                
        elif item_type == 'Season':
            series_id = item_info.get("SeriesId", item_id)
            url = f"/Shows/{series_id}/Episodes?seasonId={item_id}&userId={user_id}&Fields={fields}{unwatched_param}"
            res = get_jellyfin_api(url)
            if res and "Items" in res: items_to_process = res["Items"]
                
        elif item_type in ['BoxSet', 'Folder', 'UserView']:
            url = f"/Users/{user_id}/Items?ParentId={item_id}&Recursive=true&IncludeItemTypes=Movie,Episode,Video&Fields={fields}{unwatched_param}"
            res = get_jellyfin_api(url)
            if res and "Items" in res: items_to_process = res["Items"]
                
        elif item_type in ['Movie', 'Episode', 'Video']:
            items_to_process = [item_info]
        else:
            dialog.ok("Error", f"Unsupported item type: {item_type}")
            return

        download_queue = []
        for item in items_to_process:
            i_type = item.get("Type")
            media_type = item.get("MediaType", "")
            
            if media_type != "Video" and i_type not in ["Episode", "Movie", "Video"]:
                continue

            if unwatched_only:
                if item.get("UserData", {}).get("Played", False):
                    continue

            title = item.get("Name", "Unknown")
            download_id = item.get("Id")
            
            ext = ".mkv"
            container = item.get("Container", "")
            if container:
                ext = "." + container.split(',')[0].lower()
            else:
                path = item.get("Path", "")
                if path:
                    ext_match = os.path.splitext(path)
                    if ext_match[1]: ext = ext_match[1]

            if i_type == "Episode":
                show_name = "".join([c for c in item.get("SeriesName", "Series") if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                season_num = item.get("ParentIndexNumber", 0)
                ep_num = item.get("IndexNumber", 0)
                safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                
                subfolder = f"Series/{show_name}/Season {season_num:02d}"
                file_name = f"{show_name} - S{season_num:02d}E{ep_num:02d} - {safe_title}{ext}"
            else:
                safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                subfolder = "Movies"
                file_name = f"{safe_title}{ext}"

            dl_url = f"{SERVER_URL}/Items/{download_id}/Download"
            
            download_queue.append({
                "title": file_name.replace(ext, ""),
                "url": dl_url,
                "file_name": file_name,
                "subfolder": subfolder
            })

        if not download_queue:
            dialog.ok("Info", "No videos queued. (Are they already watched, or is the folder empty?)")
            return

        global_dest = ROOT_FOLDER if USE_DEFAULTS else ""
        if not global_dest:
            global_dest = dialog.browse(3, 'Select Root Download Destination', 'files')
            if not global_dest: return

        window = xbmcgui.Window(10000)
        if window.getProperty('Jellyfin_DL_Running') == 'true':
            dialog.notification("Added to Queue", f"{len(download_queue)} items waiting in line...", xbmcgui.NOTIFICATION_INFO, 5000)
            
        while window.getProperty('Jellyfin_DL_Running') == 'true':
            xbmc.sleep(2000)
            if xbmc.Monitor().abortRequested(): return
                
        window.setProperty('Jellyfin_DL_Running', 'true')
        
        dpBG = xbmcgui.DialogProgressBG()
        dpBG.create("Jellyfin Downloader", "Starting...")
        
        success_count = 0
        total = len(download_queue)
        
        try:
            for idx, q_item in enumerate(download_queue):
                dpBG.update(0, heading=f"Processing {idx+1}/{total}", message=q_item['title'])
                
                root_dir = global_dest
                if not root_dir.endswith('/') and not root_dir.endswith('\\'): root_dir += '/'
                
                final_dir = root_dir + q_item['subfolder'] + '/'
                    
                if not xbmcvfs.exists(final_dir):
                    xbmcvfs.mkdirs(final_dir)
                    
                dest_path = final_dir + q_item['file_name']
                
                dl_result = download_file(q_item['title'], q_item['url'], dest_path, dpBG)
                
                if dl_result is True:
                    success_count += 1
                else:
                    dialog.ok("Download Error", f"Failed to download: {q_item['title']}\n\nError: {dl_result}")
                    break 
        finally:
            dpBG.close()
            window.clearProperty('Jellyfin_DL_Running')
        
        if success_count > 0 or total == 0:
            dialog.notification("Complete", f"Successfully downloaded {success_count} of {total} items.", xbmcgui.NOTIFICATION_INFO, 5000)

    except Exception as e:
        window = xbmcgui.Window(10000)
        window.clearProperty('Jellyfin_DL_Running')
        tb = traceback.format_exc()
        xbmc.log(f"Jellyfin DL Crash: {tb}", xbmc.LOGFATAL)
        dialog.ok("Fatal Plugin Crash", f"An unexpected error occurred:\n{str(e)}")

if __name__ == '__main__':
    main()