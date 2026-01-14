# RSS-Translation-Local 架构说明文档

本文件详细记录了项目重构后的架构设计、组件职能及运行流程。

## 1. 项目整体架构

项目采用模块化设计，将原本单一的脚本拆分为：**指挥层**、**核心处理层**、**翻译层**、**第三方获取层**和**后勤工具层**。

### 目录结构预览
```text
.
├── main.py                # 项目启动入口 (总指挥)
├── config/
│   └── config.ini         # 用户配置文件 (只读，Git 提交)
├── data/
│   ├── rss_state.json     # RSS 状态记录 (MD5/时间，自动更新)
│   ├── items_cache.json   # 条目级增量缓存 (本地数据库)
│   └── debug/             # 调试用的原始 XML 文件
└── src/
    ├── core/              # 核心逻辑 (生产车间)
    │   ├── processor.py   # RSS 解析、清洗、时间提取与生成流水线
    │   └── readme_updater.py
    ├── translators/       # 翻译接口 (翻译部)
    │   ├── base.py        # 翻译器基类
    │   └── baidu.py       # 百度翻译实现 (含重试逻辑)
    ├── fetchers/          # 特定来源获取 (采购部)
    │   └── elsevier.py    # Elsevier API 摘要提取
    └── utils/             # 工具函数 (后勤部)
        ├── helpers.py     # MD5、时间处理、HTML清洗
        ├── config.py      # 配置管理
        ├── state.py       # 状态管理
        └── item_store.py  # 条目缓存管理
```

---

## 2. 组件职能详解

### A. 总指挥 (`main.py`)
负责调度。读取 `config.ini`，利用 `rss_state.json` 的 MD5 指纹进行**第一道防线**（源文件是否变化）检查。

### B. 核心处理流水线 (`src/core/processor.py`)
系统的核心，具备**增量处理**和**深度清洗**能力：
1.  **增量检查**: 遍历 RSS 条目，查询 `Item Store`。
    *   **Success**: 直接使用缓存，跳过翻译和 API 调用。
    *   **Partial**: 若上次因 Elsevier API 失败导致摘要残缺，检查是否过了冷却期，是则重试。
    *   **New**: 执行完整处理流程。
2.  **源特定清洗**:
    *   **Nature**: 自动正则剔除 `Nature, Published online...` 等引用前缀，保留纯净摘要。
    *   **Elsevier**: 优先尝试 API 获取，失败则回退并在缓存中标记为 Partial。
3.  **精准时间提取**:
    *   不再盲目使用 RSS 生成时间。
    *   优先提取 `dc:date` (Nature/Science) 或从描述文本正则提取发表日期 (Elsevier)。
4.  **合并翻译**: 标题+摘要合并请求，节省开销。

### C. 翻译专员 (`src/translators/`)
*   **`baidu.py`**: 封装百度翻译 API，内置 QPS 限流自动重试机制。

### D. 数据持久化 (`src/utils/`)
*   **`item_store.py`**: 管理文章级别的缓存，是实现增量更新的关键，极大降低了 API 调用频率。
*   **`state.py`**: 管理 Feed 级别的状态（MD5），防止重复下载无变化的文件。

---

## 3. 核心运行流程

1.  **初始化**: 加载配置与缓存。
2.  **源级过滤**: 对比 MD5，若 RSS 源文件未变，直接跳过（除非有强制重试需求）。
3.  **条目级过滤**: 解析 RSS，对每篇文章检查 `Item Store`。
    *   已存在且完整的文章 -> **零消耗**。
    *   新文章或需修复的文章 -> **进入处理**。
4.  **深度处理**:
    *   **清洗**: 剥离 HTML，针对 Nature 去除引用头。
    *   **时间**: 提取文章真实的 Publication Date。
    *   **翻译**: 合并文本 -> 百度翻译 -> 拆分结果。
5.  **生成与保存**: 生成标准 XML，更新所有状态文件。

---

## 4. 优化亮点

*   **双重增量机制**: MD5 过滤文件级变化 + Item Store 过滤条目级变化，效率极大提升。
*   **智能清洗**: 针对 Nature 等特定源的格式污染进行正则清洗。
*   **精准时间**: 还原文章真实的发表日期，而非抓取时间。
*   **配置解耦**: 静态配置 (`config.ini`) 与动态状态 (`rss_state.json`) 分离。

---

## 更新日志 (Changelog)

### 2026-01-13
*   **Refactor**: 将单文件脚本重构为模块化架构 (`src/`)。
*   **Feature**: 引入 `ItemStore` 实现文章级增量更新，大幅减少 API 调用。
*   **Feature**: 实现 Nature RSS 的特定清洗逻辑，去除引用前缀。
*   **Feature**: 实现多策略时间提取 (dc:date, 正则匹配等)，确保文章日期准确。
*   **Opt**: 配置文件分离为 `config.ini` 和 `rss_state.json`。
*   **Opt**: 合并翻译请求 (Title + Description)，API 消耗减半。