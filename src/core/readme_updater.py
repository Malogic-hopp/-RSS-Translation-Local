def update_readme(feeds_data, readme_path="README.md"):
    try:
        with open(readme_path, "r", encoding="UTF-8") as f:
            lines = f.readlines()
        
        # Find the marker line
        marker = "## 已转换翻译源"
        split_index = -1
        for i, line in enumerate(lines):
            if marker in line:
                split_index = i
                break

        new_content_links = []
        for feed in feeds_data:
            # feed: { "name": ..., "url": ..., "xml_path": ..., "items": [...] }
            line = f" - {feed['name']} [{feed['url']}]({feed['url']}) -> [{feed['name']}]({feed['xml_path']})\n"
            new_content_links.append(line)
            
            if feed.get("items"):
                new_content_links.append("   <details>\n")
                new_content_links.append("     <summary>Latest Updates (Click to expand)</summary>\n\n")
                for item in feed["items"][:3]:
                    title = item.get("title", "No Title").replace("\n", " ")
                    link = item.get("link", "")
                    new_content_links.append(f"     * [{title}]({link})\n")
                new_content_links.append("   </details>\n\n")

        if split_index != -1:
            # Keep everything up to (and including) the marker line
            new_content = lines[:split_index + 1] + new_content_links
        else:
            # Marker not found, append to end
            new_content = lines + ["\n\n" + marker + "\n"] + new_content_links
        
        with open(readme_path, "w", encoding="UTF-8") as f:
            f.writelines(new_content)
    except Exception as e:
        print(f"Error updating README: {e}")
