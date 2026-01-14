def update_readme(links, readme_path="README.md"):
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

        if split_index != -1:
            # Keep everything up to (and including) the marker line
            new_content = lines[:split_index + 1] + links
        else:
            # Marker not found, append to end
            new_content = lines + ["\n\n" + marker + "\n"] + links
        
        with open(readme_path, "w", encoding="UTF-8") as f:
            f.writelines(new_content)
    except Exception as e:
        print(f"Error updating README: {e}")
