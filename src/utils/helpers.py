import hashlib
import time
import datetime
import re
from bs4 import BeautifulSoup

def get_md5_value(src):
    _m = hashlib.sha256()
    _m.update(src.encode(encoding="utf-8"))
    return _m.hexdigest()

def getTime(e):
    # This is the old fallback, we might need a better one
    try:
        struct_time = e.published_parsed
    except AttributeError:
        struct_time = time.localtime()
    return datetime.datetime(*struct_time[:6])

def parse_custom_date(date_str):
    """
    Tries to parse various date string formats.
    Returns datetime object or None.
    """
    if not date_str:
        return None
    
    # List of formats to try
    formats = [
        "%Y-%m-%d",           # 2026-01-07 (Nature, Science DC)
        "%Y-%m-%dT%H:%M:%SZ", # 2026-01-06T08:00:00Z (Science ISO)
        "%d %B %Y",           # 15 April 2026 (Elsevier text)
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def get_now_str():
    """Returns current local time as a string: YYYY-MM-DD HH:MM:SS"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def clean_html_text(raw_html):
    """
    Strips HTML tags and decodes HTML entities.
    Returns clean text suitable for translation.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=' ', strip=True)
    return text
