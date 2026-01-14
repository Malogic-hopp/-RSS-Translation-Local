import hashlib
import random
import time
import requests
from .base import BaseTranslator

class BaiduTranslator(BaseTranslator):
    def __init__(self, app_id, secret_key, source_lang="auto", target_lang="zh"):
        super().__init__(source_lang, target_lang)
        self.app_id = app_id
        self.secret_key = secret_key
        if self.target_lang.lower() in ['zh-cn', 'zh_cn']:
            self.target_lang = 'zh'

    def translate(self, content):
        if not content:
            return ""
        
        # Retry logic for rate limiting
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self._do_request(content)
                if result:
                    return result
            except Exception as e:
                print(f" [Translation Error: {e}]")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1)) # Backoff
        
        return content # Fallback to original

    def _do_request(self, content):
        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        salt = str(random.randint(32768, 65536))
        sign = self.app_id + content + salt + self.secret_key
        sign = hashlib.md5(sign.encode()).hexdigest()
        
        data = {
            "q": content,
            "from": self.source_lang,
            "to": self.target_lang,
            "appid": self.app_id,
            "salt": salt,
            "sign": sign,
        }
        
        response = requests.get(url, params=data, timeout=10)
        result = response.json()
        
        if "trans_result" in result and len(result["trans_result"]) > 0:
            # Join multiple segments (if query was split by newlines)
            dst_lines = [item["dst"] for item in result["trans_result"]]
            dst = "\n".join(dst_lines)
            return dst.replace("；", ";")
        else:
            if "error_code" in result:
                if result['error_code'] == '54003': # QPS Limit
                    time.sleep(1) # Wait a bit before retry loop catches it
                    raise Exception("QPS Limit Reached")
                elif result['error_code'] == '52003': # Unauthorized (Check ID)
                    print(f" [Baidu Auth Failed: {result.get('error_msg')}]")
                    return content
                else:
                    print(f" [Baidu API Error: {result['error_code']} - {result.get('error_msg')}]")
            return None