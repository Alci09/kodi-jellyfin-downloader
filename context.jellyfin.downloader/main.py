import sys
import os
import json
import re
import urllib.request
import urllib.parse
import urllib.error
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

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None 

def get_jellyfin_api(endpoint):
    if not SERVER_URL or not API_KEY: return None
    url = f"{SERVER_URL}{endpoint}"
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'Authorization': AUTH_HEADER})
    try:
        with urllib.request.urlopen(req, context=CTX) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

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
                if season_num is not None and season_num >= 0: params["season"] = season_num
                req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": params, "id": 1}
                res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
                episodes = res.get('result', {}).get('episodes', [])
                if episodes:
                    uids = episodes[0].get('uniqueid', {})
                    for provider in ['jellyfin', 'emby']:
                        if provider in uids: return uids[provider].replace('-', ''), True
                    extracted = extract_item_id(episodes[0].get('file', ''))
                    if extracted: return extracted, True
    except: pass
    return None, False

# --- METADATA & ARTWORK ENGINE ---
def safe_xml(text):
    if not text: return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&apos;")

def create_nfo(item_data, nfo_type, dest_path):
    if xbmcvfs.exists(dest_path): return
    try:
        xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<{nfo_type}>\n"
        xml += f"  <title>{safe_xml(item_data.get('Name'))}</title>\n"
        
        if item_data.get("OriginalTitle"): xml += f"  <originaltitle>{safe_xml(item_data.get('OriginalTitle'))}</originaltitle>\n"
        if item_data.get("Overview"): xml += f"  <plot>{safe_xml(item_data.get('Overview'))}</plot>\n"
        if item_data.get("ProductionYear"): xml += f"  <year>{item_data.get('ProductionYear')}</year>\n"
        if item_data.get("CommunityRating"): xml += f"  <rating>{item_data.get('CommunityRating')}</rating>\n"
        if item_data.get("OfficialRating"): xml += f"  <mpaa>{safe_xml(item_data.get('OfficialRating'))}</mpaa>\n"

        if nfo_type in ["movie", "tvshow"]:
            for genre in item_data.get("Genres", []):
                xml += f"  <genre>{safe_xml(genre)}</genre>\n"

        if nfo_type == "episodedetails":
            if item_data.get("ParentIndexNumber") is not None: xml += f"  <season>{item_data.get('ParentIndexNumber')}</season>\n"
            if item_data.get("IndexNumber") is not None: xml += f"  <episode>{item_data.get('IndexNumber')}</episode>\n"

        xml += f"</{nfo_type}>\n"
        
        f = xbmcvfs.File(dest_path, 'w')
        f.write(xml.encode('utf-8'))
        f.close()
    except Exception as e:
        xbmc.log(f"Failed to write NFO {dest_path}: {e}", xbmc.LOGWARNING)

def download_extra_file(url, dest_path):
    if not url or xbmcvfs.exists(dest_path): return True
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Authorization': AUTH_HEADER}
        opener = urllib.request.build_opener(NoRedirectHandler(), urllib.request.HTTPSHandler(context=CTX))
        current_url = url
        
        for _ in range(3):
            req = urllib.request.Request(current_url, headers=headers)
            try:
                response = opener.open(req)
                f = xbmcvfs.File(dest_path, 'w')
                f.write(response.read())
                f.close()
                return True # Success
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    location = e.headers.get('Location')
                    if not location: return False
                    current_url = urllib.parse.urljoin(current_url, location)
                else: return False
    except Exception as e: 
        xbmc.log(f"Failed to download extra file {url}: {e}", xbmc.LOGWARNING)
    return False

def process_metadata(q_item, root_dir, user_id):
    """Generates NFOs, grabs posters, and downloads subtitles via the Shotgun approach"""
    item = q_item['raw_data']
    i_type = item.get("Type")
    i_id = item.get("Id")
    
    base_path = os.path.splitext(q_item['dest_path'])[0]
    final_dir = os.path.dirname(q_item['dest_path']) + '/'
    
    if i_type == "Movie":
        create_nfo(item, "movie", base_path + ".nfo")
        if "Primary" in item.get("ImageTags", {}):
            download_extra_file(f"{SERVER_URL}/Items/{i_id}/Images/Primary", base_path + "-poster.jpg")
        if item.get("BackdropImageTags"):
            download_extra_file(f"{SERVER_URL}/Items/{i_id}/Images/Backdrop", base_path + "-fanart.jpg")
            
    elif i_type == "Episode":
        create_nfo(item, "episodedetails", base_path + ".nfo")
        if "Primary" in item.get("ImageTags", {}):
            download_extra_file(f"{SERVER_URL}/Items/{i_id}/Images/Primary", base_path + "-thumb.jpg")
            
        #series_dir = root_dir + f"Series/{safe_xml(item.get('SeriesName', 'Series'))}/"
        series_dir = root_dir + f"Series/{sanitize_name(item.get('SeriesName', 'Series'))}/"
        if not xbmcvfs.exists(series_dir + "tvshow.nfo"):
            series_id = item.get("SeriesId")
            if series_id:
                series_data = get_jellyfin_api(f"/Items/{series_id}?userId={user_id}")
                if series_data:
                    if not xbmcvfs.exists(series_dir): xbmcvfs.mkdirs(series_dir)
                    create_nfo(series_data, "tvshow", series_dir + "tvshow.nfo")
                    if "Primary" in series_data.get("ImageTags", {}):
                        download_extra_file(f"{SERVER_URL}/Items/{series_id}/Images/Primary", series_dir + "poster.jpg")
                    if series_data.get("BackdropImageTags"):
                        download_extra_file(f"{SERVER_URL}/Items/{series_id}/Images/Backdrop", series_dir + "fanart.jpg")

    media_sources = item.get("MediaSources", [])
    if media_sources:
        source = media_sources[0]
        source_id = source.get("Id")
        for stream in source.get("MediaStreams", []):
            if stream.get("Type") == "Subtitle" and stream.get("IsExternal"):
                index = stream.get("Index")
                raw_codec = stream.get("Codec", "srt").lower()
                lang = stream.get("Language", "und")

                save_ext = "srt" if raw_codec == "subrip" else raw_codec
                sub_path = f"{base_path}.{lang}.{save_ext}"

                urls_to_try = []
                delivery = stream.get("DeliveryUrl")
                if delivery: urls_to_try.append(f"{SERVER_URL}{delivery}")
                urls_to_try.append(f"{SERVER_URL}/Videos/{i_id}/{source_id}/Subtitles/{index}/Stream.{save_ext}")
                urls_to_try.append(f"{SERVER_URL}/Videos/{i_id}/{source_id}/Subtitles/{index}/Stream.{raw_codec}")

                for u in urls_to_try:
                    sep = "&" if "?" in u else "?"
                    full_url = f"{u}{sep}api_key={API_KEY}"
                    if download_extra_file(full_url, sub_path):
                        break

# --- HELPER NORMALIZE FILE NAME ---
def sanitize_name(name):
    if not name:
        return "Unknown"
    # Problemzeichen durch dateisystemfreundliche Alternativen ersetzen
    name = name.replace('&', 'and')
    name = name.replace(':', ' -')
    # Alle verbleibenden ungültigen Zeichen entfernen
    name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.', '!')]).rstrip()
    # Doppelte Leerzeichen normalisieren
    name = ' '.join(name.split())
    return name

# --- VIDEO DOWNLOAD ENGINE ---
def download_file(title, download_url, dest_path, dpBG):
    if xbmcvfs.exists(dest_path): return True
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
                else: return f"HTTP Error {e.code}: {e.reason}"
        
        if not response: return "Failed to download after maximum redirects."
            
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
    except Exception as e: return str(e)

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
            dialog.ok("Error", "Could not extract Jellyfin Item ID.")
            return

        user_id = get_user_id()
        if not user_id: return

        item_info = get_jellyfin_api(f"/Items/{item_id}?userId={user_id}")
        if not item_info: return

        if needs_climb:
            if db_type == 'tvshow' and item_info.get("SeriesId"):
                item_id = item_info.get("SeriesId")
                item_info = get_jellyfin_api(f"/Items/{item_id}?userId={user_id}")
            elif db_type == 'season' and item_info.get("SeasonId"):
                item_id = item_info.get("SeasonId")
                item_info = get_jellyfin_api(f"/Items/{item_id}?userId={user_id}")

        item_type = item_info.get("Type")
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

        fields = "Path,Container,MediaSources,UserData,Overview,ProductionYear,CommunityRating,Genres,OfficialRating"
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
            
            if media_type != "Video" and i_type not in ["Episode", "Movie", "Video"]: continue
            if unwatched_only and item.get("UserData", {}).get("Played", False): continue

            title = item.get("Name", "Unknown")
            download_id = item.get("Id")
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            
            ext = ".mkv"
            container = item.get("Container", "")
            if container: ext = "." + container.split(',')[0].lower()
            else:
                path = item.get("Path", "")
                if path:
                    ext_match = os.path.splitext(path)
                    if ext_match[1]: ext = ext_match[1]

            if i_type == "Episode":
                # show_name = "".join([c for c in item.get("SeriesName", "Series") if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                show_name = sanitize_name(item.get("SeriesName", "Series"))
                season_num = item.get("ParentIndexNumber", 0)
                ep_num = item.get("IndexNumber", 0)
                
                subfolder = f"Series/{show_name}/Season {season_num:02d}"
                file_name = f"{show_name} - S{season_num:02d}E{ep_num:02d} - {safe_title}{ext}"
            else:
                subfolder = "Movies"
                file_name = f"{safe_title}{ext}"

            dl_url = f"{SERVER_URL}/Items/{download_id}/Download"
            
            download_queue.append({
                "title": file_name.replace(ext, ""),
                "url": dl_url,
                "file_name": file_name,
                "subfolder": subfolder,
                "raw_data": item
            })

        if not download_queue:
            dialog.ok("Info", "No videos queued.")
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
                if not xbmcvfs.exists(final_dir): xbmcvfs.mkdirs(final_dir)
                
                dest_path = final_dir + q_item['file_name']
                q_item['dest_path'] = dest_path

                process_metadata(q_item, root_dir, user_id)

                dl_result = download_file(q_item['title'], q_item['url'], dest_path, dpBG)
                
                if dl_result is True: success_count += 1
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
