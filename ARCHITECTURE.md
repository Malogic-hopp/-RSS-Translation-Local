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
    │   ├── baidu.py       # 百度翻译实现 (含 QPS 限流重试)
    │   ├── tencent.py     # 腾讯云 TMT 翻译实现
    │   └── deepseek.py    # DeepSeek (LLM) 翻译实现
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
*   **环境配置**: 从 `.env` 文件加载敏感信息（百度 API、腾讯云 API、DeepSeek API、Elsevier API 密钥）。
*   **配置读取**: 通过 `ConfigManager` 读取 `config.ini` 中的 RSS 源配置，包括全局翻译服务选择。
*   **翻译器初始化**: 根据配置（`service` 参数）和环境变量自动选择或手动指定翻译服务。
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
*   **`base.py`**: 定义翻译器抽象基类。
*   **`baidu.py`**: 百度翻译 API 实现，包含 QPS 限流重试机制。
*   **`tencent.py`**: 腾讯云 TMT 翻译实现，使用 `tencentcloud-sdk-python`。
*   **`deepseek.py`**: 基于 DeepSeek API (OpenAI 兼容) 的大模型翻译实现。
*   **`__init__.py` (工厂模式)**: 实现翻译器选择逻辑。
    *   **手动模式**: 若 `config.ini` 中指定了 `service`，则强制使用该服务。
    *   **自动模式**: 若设为 `auto`，则按 `DeepSeek -> Tencent -> Baidu` 的优先级自动检测可用密钥。

### D. 第三方获取层 (`src/fetchers/`)
*   **`elsevier.py`**: Elsevier API 摘要获取器。

### E. 数据持久化 (`src/utils/`)
*   **`item_store.py`**: 管理文章级别的缓存，实现增量更新。
*   **`state.py`**: 管理 Feed 级别的状态（MD5）。
*   **`config.py`**: 配置文件管理器。
*   **`helpers.py`**: 工具函数集合。

---

## 3. 核心运行流程

1.  **初始化**:
    *   加载 `.env` 环境变量。
    *   加载 `config.ini` 配置文件，读取 `service` 选择。
    *   加载 `rss_state.json` 和 `items_cache.json` 缓存文件。

2.  **源级过滤**:
    *   遍历配置中的所有 RSS 源。
    *   下载 RSS 内容并计算 MD5 哈希。
    *   对比 MD5，跳过无变化的源。

3.  **条目级过滤**:
    *   解析 RSS，对每篇文章检查 `Item Store`。

4.  **深度处理**:
    *   **清洗/增强**: 获取内容并进行格式清洗。
    *   **翻译器实例化**: 调用 `get_translator()`，根据配置初始化 DeepSeek、腾讯或百度翻译器。
    *   **翻译**: 合并标题和摘要 -> 翻译 -> 拆分结果。

5.  **生成与保存**:
    *   使用 Jinja2 模板生成标准 RSS XML。
    *   更新缓存。

6.  **README 更新**:
    *   所有 RSS 处理完成后，统一更新 README.md。

---

## 6. 配置说明

### 6.1 环境变量 (`.env`)
```ini
BAIDU_APP_ID=...
BAIDU_SECRET_KEY=...
TENCENT_SECRET_ID=...
TENCENT_SECRET_KEY=...
DEEPSEEK_API_KEY=...
ELSEVIER_API_KEY=...
```

### 6.2 RSS 源配置 (`config/config.ini`)
```ini
[cfg]
base = "rss/"
cooldown_hours = 0
service = "auto"  # 选择: auto, deepseek, tencent, baidu
```

---

## 更新日志 (Changelog)

### 2026-01-15
*   **Feature**: 集成腾讯云 TMT 翻译接口。
*   **Feature**: 集成 DeepSeek 大模型翻译接口。
*   **Feature**: 支持在 `config.ini` 中通过 `service` 参数手动选择翻译服务。

### 2026-01-14
*   **文档更新**: 更新 ARCHITECTURE.md 以反映实际代码实现。
*   **功能**: 添加 README 自动更新功能。

### 2026-01-13
*   **Refactor**: 将单文件脚本重构为模块化架构。
*   **Feature**: 引入 `ItemStore` 实现增量更新。
