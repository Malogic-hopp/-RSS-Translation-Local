import os
import requests
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
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)

    secs = config_mgr.sections()
    links = []

    print(f"Baidu Translator Init... (AppID: {BAIDU_APP_ID[:4]}***)")

    for sec in secs:
        if sec == "cfg": continue 

        name = config_mgr.get(sec, "name")
        url = config_mgr.get(sec, "url")
        max_item = int(config_mgr.get(sec, "max", 10))
        source_lang, target_lang = config_mgr.get_translation_langs(sec)

        old_md5 = state_mgr.get_md5(sec)
        xml_file = os.path.join(base_dir, f"{name}.xml")
        links.append(f" - {sec} [{url}]({url}) -> [{name}]({xml_file.replace(os.sep, '/')})\n")

        print(f"Checking {sec} ({name})...")

        try:
            r = requests.get(url, timeout=10)
            
            # Save raw content for debug
            raw_debug_file = os.path.join(DEBUG_DIR, f"{name}.xml")
            with open(raw_debug_file, "w", encoding="utf-8") as f:
                f.write(r.text)
                
            new_md5 = get_md5_value(r.text)
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            continue

        needs_update = False
        if old_md5 != new_md5:
            needs_update = True
        elif not os.path.exists(xml_file):
             needs_update = True
        
        if not needs_update:
            print(f"  No update needed (MD5 Match).")
            continue

        print(f"  Updating...")
        translator = BaiduTranslator(BAIDU_APP_ID, BAIDU_SECRET_KEY, source_lang, target_lang)
        # Pass only item_store
        processor = RSSProcessor(translator, item_store)
        
        try:
            feed_info = processor.process_feed(url, max_item)
            rss_xml = processor.generate_rss_xml(feed_info)
            
            with open(xml_file, "w", encoding="utf-8") as f:
                f.write(rss_xml)
            
            state_mgr.set_md5(sec, new_md5)
            state_mgr.save()
            item_store.save() 
            
        except Exception as e:
            print(f"  Error processing {sec}: {e}")

    # Finalize
    state_mgr.save()
    item_store.save()
    update_readme(links)
    print("Done.")

if __name__ == "__main__":
    main()