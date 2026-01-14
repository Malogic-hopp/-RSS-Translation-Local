import os
import requests
import feedparser
from dotenv import load_dotenv

from src.utils.helpers import get_md5_value
from src.utils.config import ConfigManager
from src.utils.state import StateManager
from src.utils.item_store import ItemStore
from src.translators.baidu import BaiduTranslator
from src.core.processor import RSSProcessor
from src.core.readme_updater import update_readme

# Load environment variables
load_dotenv()

BAIDU_APP_ID = os.environ.get("BAIDU_APP_ID")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY")

STATE_FILE = "data/rss_state.json"
ITEM_STORE_FILE = "data/items_cache.json"
CONFIG_FILE = "config/config.ini"
DEBUG_DIR = "data/debug/"

def main():
    if not BAIDU_APP_ID or not BAIDU_SECRET_KEY:
        print("Error: BAIDU_APP_ID or BAIDU_SECRET_KEY not set in environment.")
        return

    # Initialize Managers
    config_mgr = ConfigManager(CONFIG_FILE)
    state_mgr = StateManager(STATE_FILE)
    item_store = ItemStore(ITEM_STORE_FILE)
    
    base_dir = config_mgr.get("cfg", "base", "rss/")
    cooldown_hours = int(config_mgr.get("cfg", "cooldown_hours", 24))

    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)

    secs = config_mgr.sections()
    feeds_data = []

    print(f"Baidu Translator Init... (AppID: {BAIDU_APP_ID[:4]}***)")

    for sec in secs:
        if sec == "cfg": continue 

        name = config_mgr.get(sec, "name")
        url = config_mgr.get(sec, "url")
        max_item = int(config_mgr.get(sec, "max", 10))
        source_lang, target_lang = config_mgr.get_translation_langs(sec)

        old_md5 = state_mgr.get_md5(sec)
        xml_file = os.path.join(base_dir, f"{name}.xml")
        xml_path_display = xml_file.replace(os.sep, '/')
        
        # Prepare feed entry
        feed_entry = {
            "name": name,
            "url": url,
            "xml_path": xml_path_display,
            "items": []
        }

        print(f"Checking {sec} ({name})...")

        try:
            r = requests.get(url, timeout=10)
            
            # Save raw content for debug
            raw_debug_file = os.path.join(DEBUG_DIR, f"{name}.xml")
            with open(raw_debug_file, "w", encoding="utf-8") as f:
                f.write(r.text)
                
            new_md5 = get_md5_value(r.text)
            parsed_feed = feedparser.parse(r.text)
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            # If fetch fails, try to load existing local items
            if os.path.exists(xml_file):
                 try:
                    d = feedparser.parse(xml_file)
                    for entry in d.entries[:5]:
                        feed_entry["items"].append({
                            "title": entry.title,
                            "link": entry.link
                        })
                 except: pass
            feeds_data.append(feed_entry)
            continue

        needs_update = False
        if old_md5 != new_md5:
            needs_update = True
        elif not os.path.exists(xml_file):
             needs_update = True
        else:
            # Check if any items in the current feed need retry (e.g. they were "partial")
            for entry in parsed_feed.entries[:max_item]:
                if item_store.should_retry_partial(entry.link, cooldown_hours):
                    needs_update = True
                    print(f"  Found item(s) needing retry (partial or missing).")
                    break
        
        if not needs_update:
            print(f"  No update needed (MD5 Match & No Partials).")
            # Load existing items from local file
            if os.path.exists(xml_file):
                try:
                    d = feedparser.parse(xml_file)
                    for entry in d.entries[:5]:
                        feed_entry["items"].append({
                            "title": entry.title,
                            "link": entry.link
                        })
                except Exception as e:
                    print(f"  Error parsing local file: {e}")
            
            feeds_data.append(feed_entry)
            continue

        print(f"  Updating...")
        translator = BaiduTranslator(BAIDU_APP_ID, BAIDU_SECRET_KEY, source_lang, target_lang)
        # Pass only item_store
        processor = RSSProcessor(translator, item_store, cooldown_hours)
        
        try:
            feed_info = processor.process_feed(url, max_item)
            rss_xml = processor.generate_rss_xml(feed_info)
            
            with open(xml_file, "w", encoding="utf-8") as f:
                f.write(rss_xml)
            
            state_mgr.set_md5(sec, new_md5)
            state_mgr.save()
            item_store.save() 
            
            # Use the processed items
            for item in feed_info.get("items", [])[:5]:
                feed_entry["items"].append({
                    "title": item["title"],
                    "link": item["link"]
                })
            
        except Exception as e:
            print(f"  Error processing {sec}: {e}")
            # Fallback to local if update failed but file exists
            if os.path.exists(xml_file):
                try:
                    d = feedparser.parse(xml_file)
                    for entry in d.entries[:5]:
                        feed_entry["items"].append({
                            "title": entry.title,
                            "link": entry.link
                        })
                except: pass

        feeds_data.append(feed_entry)

    # Finalize
    state_mgr.save()
    item_store.save()
    update_readme(feeds_data)
    print("Done.")

if __name__ == "__main__":
    main()