import json
import os
from .helpers import get_now_str

class StateManager:
    def __init__(self, filepath="rss_state.json"):
        self.filepath = filepath
        self.state = self._load()
        self.dirty = False

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save(self):
        if self.dirty:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
            self.dirty = False

    def get_md5(self, section):
        return self.state.get(section, {}).get("md5", "")

    def set_md5(self, section, md5):
        if section not in self.state:
            self.state[section] = {}
        
        if self.state[section].get("md5") != md5:
            self.state[section]["md5"] = md5
            self.state[section]["last_updated"] = get_now_str()
            self.dirty = True