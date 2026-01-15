import configparser
import os

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        # Enable inline comments support
        self.config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        if os.path.exists(config_path):
            self.config.read(config_path, encoding='utf-8')

    def get(self, sec, name, default=None):
        try:
            return self.config.get(sec, name).strip('"')
        except:
            return default

    def sections(self):
        return self.config.sections()

    def get_translation_langs(self, sec):
        cc = self.get(sec, "action", "auto")
        if cc == "auto":
            return "auto", "zh"
        else:
            try:
                parts = cc.split("->")
                return parts[0], parts[1]
            except:
                return "auto", "zh"