# RSS-Translation-Local 架构说明文档

本文件详细记录了项目重构后的架构设计、组件职能及运行流程。

## 1. 项目整体架构

项目采用模块化设计，将原本单一的脚本拆分为：**指挥层**、**核心处理层**、**翻译层**、**第三方获取层**和**后勤工具层**。

### 目录结构预览
```text
.
├── main.py                # 项目启动入口 (总指挥)
├── .env                   # 环境变量配置 (敏感信息，不提交)
├── config/
│   └── config.ini         # RSS 源配置文件 (Git 提交)
├── data/
│   ├── rss_state.json     # RSS 状态记录 (MD5/时间，自动更新，Git 忽略)
│   ├── items_cache.json   # 条目级增量缓存 (本地数据库，Git 忽略)
│   └── debug/             # 调试用的原始 XML 文件和日志 (Git 忽略)
├── rss/                   # 生成的翻译 RSS 文件输出目录
└── src/
    ├── core/              # 核心逻辑 (生产车间)
    │   ├── processor.py   # RSS 解析、清洗、处理与生成流水线
    │   └── readme_updater.py  # README 自动更新
    ├── translators/       # 翻译接口 (翻译部)
    │   ├── base.py        # 翻译器基类
    │   └── baidu.py       # 百度翻译实现 (含 QPS 限流重试)
    ├── fetchers/          # 特定来源获取 (采购部)
    │   └── elsevier.py    # Elsevier API 摘要提取
    └── utils/             # 工具函数 (后勤部)
        ├── helpers.py     # MD5、时间处理、HTML 清洗
        ├── config.py      # 配置管理
        ├── state.py       # 状态管理
        └── item_store.py  # 条目缓存管理
```

---

## 2. 组件职能详解

### A. 总指挥 (`main.py`)
负责调度和协调各模块工作：
*   **环境配置**: 从 `.env` 文件加载敏感信息（百度 API、Elsevier API 密钥）。
*   **配置读取**: 通过 `ConfigManager` 读取 `config.ini` 中的 RSS 源配置。
*   **MD5 过滤**: 利用 `rss_state.json` 的 MD5 指纹进行**第一道防线**检查（源文件是否变化）。
*   **容错机制**: 当 RSS 获取失败时，自动降级使用本地已生成的 XML 文件，确保 README 更新不中断。
*   **README 更新**: 所有 RSS 处理完成后，调用 `readme_updater` 自动更新 README.md。

### B. 核心处理流水线 (`src/core/processor.py`)
系统的核心，具备**增量处理**、**深度清洗**和**智能容错**能力：

1.  **增量检查**: 遍历 RSS 条目，查询 `Item Store`。
    *   **Success**: 直接使用缓存，跳过翻译和 API 调用。
    *   **Partial**: 若上次因 Elsevier API 失败导致摘要残缺，检查是否过了冷却期，是则重试。
    *   **Partial Retry 优化**: 如果重试时 API 仍然失败，只更新时间戳（重置冷却期）而不重新翻译，避免无谓的 API 消耗。
    *   **New**: 执行完整处理流程。

2.  **源特定清洗**:
    *   **Nature**: 使用正则表达式匹配 DOI 并提取后续摘要内容，去除引用信息。
    *   **Elsevier**: 优先尝试 API 获取完整摘要，失败则回退使用 RSS 描述，并在缓存中标记为 Partial。
    *   **HTML 清洗**: 使用 BeautifulSoup 统一处理 HTML 标签和实体解码。

3.  **时间处理**:
    *   使用 `getTime()` 函数提取 RSS 条目的 `published_parsed` 时间。
    *   回退机制：如果没有发布时间，使用当前时间。
    *   所有条目最后按发布时间倒序排列。

4.  **合并翻译**: 标题+摘要合并为一次翻译请求，节省 API 调用开销。

5.  **调试日志**: 自动记录 Elsevier API 调用详情到 `data/debug/elsevier_debug.log`。

### C. 翻译专员 (`src/translators/`)
*   **`base.py`**: 定义翻译器抽象基类，支持自定义源语言和目标语言。
*   **`baidu.py`**: 百度翻译 API 实现，包含：
    *   QPS 限流自动重试机制（最多 3 次，指数退避）。
    *   错误码识别（54003、52003 等）。
    *   自动将 `zh-CN` 规范化为 `zh`。

### D. 第三方获取层 (`src/fetchers/`)
*   **`elsevier.py`**: Elsevier API 摘要获取器：
    *   从 ScienceDirect 链接提取 PII。
    *   调用 Elsevier Abstract API 获取完整摘要。
    *   自动清理 API 返回的版权信息前缀。
    *   支持完整的调试日志记录。

### E. 数据持久化 (`src/utils/`)
*   **`item_store.py`**: 管理文章级别的缓存，实现增量更新的关键：
    *   三种状态：`success`（完整）、`partial`（需重试）、不存在。
    *   冷却期机制：防止失败的条目过于频繁重试。
    *   脏标记：只在数据变化时写入磁盘。
*   **`state.py`**: 管理 Feed 级别的状态（MD5），防止重复下载无变化的文件。
*   **`config.py`**: 配置文件管理器，支持翻译语言对配置（`auto` 或 `src->tgt`）。
*   **`helpers.py`**: 工具函数集合：
    *   `get_md5_value()`: SHA256 哈希计算。
    *   `clean_html_text()`: HTML 清洗和实体解码。
    *   `getTime()`: 时间提取。
    *   `parse_custom_date()`: 多格式日期解析（预留，当前未使用）。

### F. README 更新器 (`src/core/readme_updater.py`)
*   自动生成 RSS 源列表，包含最新 3 篇文章的可展开预览。
*   使用 HTML `<details>` 标签实现折叠效果。

---

## 3. 核心运行流程

1.  **初始化**:
    *   加载 `.env` 环境变量（API 密钥）。
    *   加载 `config.ini` 配置文件。
    *   加载 `rss_state.json` 和 `items_cache.json` 缓存文件。

2.  **源级过滤**:
    *   遍历配置中的所有 RSS 源。
    *   下载 RSS 内容并计算 MD5 哈希。
    *   对比 MD5，若 RSS 源文件未变且无 Partial 条目需要重试，直接跳过。
    *   保存原始 XML 到 `data/debug/` 供调试。

3.  **条目级过滤**:
    *   解析 RSS，对每篇文章检查 `Item Store`。
    *   已存在且完整的文章 -> **零消耗**，直接使用缓存。
    *   新文章或需修复的文章 -> **进入处理流程**。

4.  **深度处理**:
    *   **清洗**: 使用 BeautifulSoup 剥离 HTML 标签，针对 Nature 去除 DOI 前缀。
    *   **增强**: 对于 Elsevier 文章，尝试通过 API 获取完整摘要。
    *   **时间**: 提取文章的发布时间（`published_parsed`）。
    *   **翻译**: 合并标题和摘要 -> 百度翻译 -> 拆分结果。
    *   **XML 转义**: 对翻译结果进行 XML 实体转义。

5.  **生成与保存**:
    *   使用 Jinja2 模板生成标准 RSS XML。
    *   保存到 `rss/` 目录。
    *   更新 `rss_state.json` 和 `items_cache.json`。
    *   收集文章信息用于 README 更新。

6.  **README 更新**:
    *   所有 RSS 处理完成后，统一更新 README.md。
    *   生成 RSS 源列表，包含最新文章预览。
    *   即使部分 RSS 获取失败，也能基于本地文件完成更新。

---

## 4. 优化亮点

*   **双重增量机制**: MD5 过滤文件级变化 + Item Store 过滤条目级变化，效率极大提升，减少不必要的 API 调用。
*   **智能清洗**: 针对 Nature、Elsevier 等特定源的格式问题进行针对性清洗，提升翻译质量。
*   **容错降级**: 多层级容错机制（RSS 获取失败、翻译失败、API 失败），确保系统稳定运行。
*   **Partial Retry 优化**: 失败条目重试时，如果 API 仍然失败，只更新时间戳而不重新翻译，避免资源浪费。
*   **配置解耦**: 敏感信息 (`.env`)、静态配置 (`config.ini`) 与动态状态 (`rss_state.json`、`items_cache.json`) 三层分离。
*   **调试友好**: 自动保存原始 XML 和 API 调用日志，便于问题排查。
*   **README 自动化**: 每次运行后自动更新 README，保持项目文档的时效性。

---

## 5. 依赖项

主要依赖库（见 `requirements.txt`）：
*   **feedparser**: RSS 解析
*   **requests**: HTTP 请求
*   **beautifulsoup4** / **bs4**: HTML 清洗
*   **jinja2**: RSS XML 模板生成
*   **python-dotenv**: 环境变量管理
*   **configparser**: INI 配置文件解析

其他依赖：
*   **mtranslate, googletrans, pygtrans**: 其他翻译服务（备用，当前未使用）

---

## 6. 配置说明

### 6.1 环境变量 (`.env`)
```ini
BAIDU_APP_ID=your_app_id
BAIDU_SECRET_KEY=your_secret_key
ELSEVIER_API_KEY=your_elsevier_key  # 可选
```

### 6.2 RSS 源配置 (`config/config.ini`)
```ini
[cfg]
base = "rss/"           # 输出目录
cooldown_hours = 0      # Partial 条目重试冷却期（小时）

[source001]
name = "RESS"                                           # RSS 源名称
url = "https://rss.sciencedirect.com/publication/..."   # RSS 源 URL
max = "50"                                              # 最大处理条目数
action = "auto"                                         # 翻译语言对（auto = auto->zh）
```

---

## 7. Git 管理策略

**提交到 Git**：
*   源代码 (`src/`, `main.py`)
*   配置文件 (`config/`, `requirements.txt`)
*   文档 (`README.md`, `ARCHITECTURE.md`)
*   Git 配置 (`.gitignore`)

**不提交** (见 `.gitignore`)：
*   敏感信息 (`.env`)
*   动态状态 (`data/rss_state.json`, `data/items_cache.json`)
*   调试文件 (`data/debug/`)
*   虚拟环境 (`.venv/`)
*   生成的 RSS 文件 (`rss/`)

---

## 更新日志 (Changelog)

### 2026-01-14
*   **文档更新**: 更新 ARCHITECTURE.md 以反映实际代码实现，补充环境变量配置、容错机制等说明。
*   **优化**: 实现 Partial Retry 优化，避免无谓的 API 消耗。
*   **功能**: 添加 README 自动更新功能，每次运行后自动生成 RSS 源列表。

### 2026-01-13
*   **Refactor**: 将单文件脚本重构为模块化架构 (`src/`)。
*   **Feature**: 引入 `ItemStore` 实现文章级增量更新，大幅减少 API 调用。
*   **Feature**: 实现 Nature RSS 的特定清洗逻辑，去除 DOI 前缀。
*   **Feature**: 实现多策略时间提取 (dc:date, 正则匹配等)，确保文章日期准确。
*   **Opt**: 配置文件分离为 `config.ini` 和 `rss_state.json`。
*   **Opt**: 合并翻译请求 (Title + Description)，API 消耗减半。