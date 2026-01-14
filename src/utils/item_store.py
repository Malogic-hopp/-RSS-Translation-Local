import json
import os
import time
import datetime

class ItemStore:
    def __init__(self, filepath="items_cache.json"):
        self.filepath = filepath
        self.data = self._load()
        self.dirty = False

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _json_serial(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        raise TypeError(f"Type {type(obj)} not serializable")

    def save(self):
        if self.dirty:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False, default=self._json_serial)
            self.dirty = False

    def get_item(self, guid):
        return self.data.get(guid)

    def save_item(self, guid, item_data, status="success"):
        # When saving, if we update status, we update last_updated
        self.data[guid] = {
            "data": item_data,
            "status": status,
            "last_updated": time.time()
        }
        self.dirty = True

    def update_timestamp(self, guid):
        """Update only the timestamp for an existing item (used for failed retries)."""
        if guid in self.data:
            self.data[guid]["last_updated"] = time.time()
            self.dirty = True

    def should_retry_partial(self, guid, cooldown_hours=24):
        """
        Check if a partial/failed item should be retried based on cooldown.
        Replaces the old pii_cache logic.
        """
        entry = self.data.get(guid)
        if not entry:
            return True # Not in cache, sure process it
        
        if entry.get("status") == "success":
            return False # Already done
        
        # If partial, check cooldown
        last_check = entry.get("last_updated", 0)
        if (time.time() - last_check) > (cooldown_hours * 3600):
            return True
            
        return False
