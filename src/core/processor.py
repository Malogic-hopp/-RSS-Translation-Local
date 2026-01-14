import feedparser
from jinja2 import Template
import re
import datetime
import os
import json
from ..utils.helpers import getTime, clean_html_text
from ..fetchers.elsevier import fetch_elsevier_abstract

DEBUG_LOG_FILE = "data/debug/elsevier_debug.log"

class RSSProcessor:
    def __init__(self, translator, item_store, cooldown_hours=24):
        self.translator = translator
        self.item_store = item_store
        self.cooldown_hours = cooldown_hours
        
        # Ensure debug dir exists
        os.makedirs(os.path.dirname(DEBUG_LOG_FILE), exist_ok=True)

    def _log_debug(self, guid, raw):
        try:
            with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.datetime.now()} ---\n")
                f.write(f"GUID: {guid}\n")
                if isinstance(raw, (dict, list)):
                    f.write(f"RAW JSON:\n{json.dumps(raw, indent=2, ensure_ascii=False)}\n")
                else:
                    f.write(f"RAW Content:\n{raw}\n")
                f.write("-" * 50 + "\n\n")
        except:
            pass

    def _clean_nature_description(self, text):
        match = re.match(r'^.*?(?:doi:10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text

    def process_feed(self, url, max_items=10):
        d = feedparser.parse(url)
        processed_items = []
        item_guids = set()

        total_entries = len(d.entries)
        print(f"  Found {total_entries} entries. Processing top {max_items}...")

        for idx, entry in enumerate(d.entries):
            if len(processed_items) >= max_items:
                break

            if not hasattr(entry, 'link'):
                print(f"  [{idx+1}/{total_entries}] [SKIP] Item missing link attribute: {getattr(entry, 'title', 'No Title')[:30]}...")
                continue

            guid = entry.link 
            
            cached_entry = self.item_store.get_item(guid)
            should_process = True
            
            if cached_entry:
                status = cached_entry.get("status")
                if status == "success":
                    should_process = False
                elif status == "partial":
                    if not self.item_store.should_retry_partial(guid, self.cooldown_hours):
                        should_process = False
            
            if not should_process:
                status = cached_entry.get("status", "CACHED").upper()
                if status == "PARTIAL": status = "PARTIAL/COOLDOWN"
                print(f"  [{idx+1}/{total_entries}] [SKIP: {status}] {entry.title[:30]}...", end="", flush=True)
                item_data = cached_entry["data"]
                try:
                    item_data["pubDate"] = datetime.datetime.strptime(item_data["pubDate"], "%Y-%m-%d %H:%M:%S")
                except:
                    item_data["pubDate"] = datetime.datetime.now()
                
                processed_items.append(item_data)
                item_guids.add(guid)
                print(" Done.")
                continue
            
            print(f"  [{idx+1}/{total_entries}] Processing: {entry.title[:30]}...", end="", flush=True)

            try:
                raw_title = entry.title.replace('\n', ' ').strip()
                link = entry.link
                raw_desc = ""
                status = "success"

                if "sciencedirect.com" in link:
                    api_abstract, api_full_data = fetch_elsevier_abstract(link)
                    
                    # Optimization: If this is a retry for a partial item and API failed to get abstract,
                    # just update the timestamp (to reset cooldown) and keep using the existing partial data.
                    # This avoids unnecessary re-translation and re-saving.
                    is_partial_retry = cached_entry and cached_entry.get("status") == "partial"
                    if is_partial_retry and not api_abstract:
                        print(" [API Failed] Keeping cached partial item.", end="", flush=True)
                        self.item_store.update_timestamp(guid)
                        
                        item_data = cached_entry["data"]
                        # Ensure pubDate is a datetime object
                        if isinstance(item_data["pubDate"], str):
                            try:
                                item_data["pubDate"] = datetime.datetime.strptime(item_data["pubDate"], "%Y-%m-%d %H:%M:%S")
                            except:
                                item_data["pubDate"] = datetime.datetime.now()
                        
                        if item_data["guid"] not in item_guids:
                            item_guids.add(item_data["guid"])
                            processed_items.append(item_data)
                        print(" Done.")
                        continue

                    if api_full_data:
                        print(" [API Abstract]", end="", flush=True)
                        
                        # Extract info for focused logging
                        resp_root = api_full_data.get('abstracts-retrieval-response', {})
                        coredata = resp_root.get('coredata', {})
                        raw_abstract = resp_root.get('item', {}).get('bibrecord', {}).get('head', {}).get('abstracts')
                        if not raw_abstract:
                             raw_abstract = coredata.get('dc:description')
                        copyright_info = coredata.get('publishercopyright')
                        
                        log_data = {
                            "original_abstract": raw_abstract,
                            "copyright_info": copyright_info,
                            "cleaned_abstract": api_abstract
                        }
                        self._log_debug(guid, log_data)

                        if api_abstract:
                            raw_desc = api_abstract
                            status = "success"
                        else:
                            status = "partial"
                            raw_desc = getattr(entry, 'summary', '')
                            if not raw_desc and hasattr(entry, 'content'):
                                raw_desc = entry.content[0].value
                    else:
                        status = "partial"
                        raw_desc = getattr(entry, 'summary', '')
                        if not raw_desc and hasattr(entry, 'content'):
                            raw_desc = entry.content[0].value
                else:
                    raw_desc = getattr(entry, 'summary', '')
                    if not raw_desc and hasattr(entry, 'content'):
                        raw_desc = entry.content[0].value

                clean_desc = clean_html_text(raw_desc)
                
                # Apply source-specific cleaning
                if "nature.com" in link:
                    clean_desc = self._clean_nature_description(clean_desc)

                combined_text = f"{raw_title}\n\n{clean_desc}"
                translated_text = self.translator.translate(combined_text)
                
                parts = translated_text.split('\n\n', 1)
                if len(parts) == 2:
                    final_title = parts[0].strip()
                    final_desc = parts[1].strip()
                else:
                    parts_single = translated_text.split('\n', 1)
                    if len(parts_single) == 2:
                        final_title = parts_single[0].strip()
                        final_desc = parts_single[1].strip()
                    else:
                        final_title = raw_title 
                        final_desc = translated_text

                final_desc = (
                    final_desc.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;")
                )

                pub_date = getTime(entry)

                item_data = {
                    "title": final_title,
                    "link": link.replace("&", "&amp;"),
                    "description": final_desc,
                    "guid": link.replace("&", "&amp;"),
                    "pubDate": pub_date, 
                }

                store_data = item_data.copy()
                store_data["pubDate"] = item_data["pubDate"].strftime("%Y-%m-%d %H:%M:%S")
                self.item_store.save_item(guid, store_data, status)

                if item_data["guid"] not in item_guids:
                    item_guids.add(item_data["guid"])
                    processed_items.append(item_data)
                
                print(" Done.")
            except Exception as e:
                print(f" Error processing item: {e}")
                continue

        sorted_list = sorted(processed_items, key=lambda x: x["pubDate"], reverse=True)
        
        feed_title = self.translator.translate(d.feed.title)
        feed_desc = self.translator.translate(getattr(d.feed, 'subtitle', ''))
        
        feed_info = {
            "title": feed_title,
            "link": getattr(d.feed, 'link', ''),
            "description": feed_desc,
            "lastBuildDate": getTime(d.feed),
            "items": sorted_list,
        }
        return feed_info

    def generate_rss_xml(self, feed_info):
        template_str = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{{ title }}</title>
    <link>{{ link }}</link>
    <description>{{ description }}</description>
    <lastBuildDate>{{ lastBuildDate.strftime('%a, %d %b %Y %H:%M:%S GMT') }}</lastBuildDate>
    {% for item in items -%}
    <item>
      <title><![CDATA[{{ item.title }}]]></title>
      <link>{{ item.link }}</link>
      <description><![CDATA[{{ item.description }}]]></description>
      <guid isPermaLink="false">{{ item.guid }}</guid>
      <pubDate>{{ item.pubDate.strftime('%a, %d %b %Y %H:%M:%S GMT') }}</pubDate>
    </item>
    {% endfor -%}
  </channel>
</rss>"""
        template = Template(template_str)
        return template.render(**feed_info)