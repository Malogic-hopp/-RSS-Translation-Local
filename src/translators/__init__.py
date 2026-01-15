import os
from .baidu import BaiduTranslator
from .tencent import TencentTranslator
from .deepseek import DeepSeekTranslator

def get_translator(service="auto", source_lang="auto", target_lang="zh"):
    # Normalize service string
    if service:
        service = service.lower().strip().strip('"').strip("'")
    
    tencent_id = os.environ.get("TENCENT_SECRET_ID")
    tencent_key = os.environ.get("TENCENT_SECRET_KEY")
    
    baidu_id = os.environ.get("BAIDU_APP_ID")
    baidu_key = os.environ.get("BAIDU_SECRET_KEY")

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    
    # 1. Explicit Selection
    if service == "deepseek":
        if deepseek_key:
            print("Using DeepSeek Translator")
            return DeepSeekTranslator(deepseek_key, source_lang, target_lang)
        else:
            print("Error: DeepSeek selected but DEEPSEEK_API_KEY not found.")
            return None

    if service == "tencent":
        if tencent_id and tencent_key:
            print("Using Tencent Translator")
            return TencentTranslator(tencent_id, tencent_key, source_lang, target_lang)
        else:
            print("Error: Tencent selected but TENCENT_SECRET_ID/KEY not found.")
            return None

    if service == "baidu":
        if baidu_id and baidu_key:
            print("Using Baidu Translator")
            return BaiduTranslator(baidu_id, baidu_key, source_lang, target_lang)
        else:
            print("Error: Baidu selected but BAIDU_APP_ID/KEY not found.")
            return None
            
    # 2. Auto Selection (Fallback Logic)
    # Order: DeepSeek -> Tencent -> Baidu (Updated per user preference for new stuff?)
    # Actually, let's keep previous logic: Tencent -> Baidu. 
    # But now with DeepSeek in the mix. 
    # Let's prioritize: DeepSeek > Tencent > Baidu if all keys exist?
    # Or just check keys.
    
    if deepseek_key:
        print("Using DeepSeek Translator (Auto-selected)")
        return DeepSeekTranslator(deepseek_key, source_lang, target_lang)
    elif tencent_id and tencent_key:
        print("Using Tencent Translator (Auto-selected)")
        return TencentTranslator(tencent_id, tencent_key, source_lang, target_lang)
    elif baidu_id and baidu_key:
        print("Using Baidu Translator (Auto-selected)")
        return BaiduTranslator(baidu_id, baidu_key, source_lang, target_lang)
    else:
        return None