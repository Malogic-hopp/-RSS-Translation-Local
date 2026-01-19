# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 核心命令

- **运行应用**: `python main.py`
- **安装依赖**: `pip install -r requirements.txt`

注意：此项目目前没有配置构建、测试或代码检查命令，是一个直接运行的 Python 脚本。

## 架构概览

本项目采用 5 层模块化架构，需要阅读多个文件才能完全理解：

1. **指挥层** (`main.py`): 入口点，协调整个处理流程，包括环境配置、RSS 源遍历、MD5 变化检测和 README 更新
2. **核心处理层** (`src/core/`): RSS 解析、翻译流水线、XML 生成
3. **翻译层** (`src/translators/`): 服务抽象与工厂模式
4. **获取层** (`src/fetchers/`): 第三方 API 集成（如 Elsevier API 获取完整摘要）
5. **工具层** (`src/utils/`): 配置管理、状态管理、缓存

## 关键架构模式

### 两级缓存系统

- **Feed 级别**: [StateManager](src/utils/state.py) 使用 `data/rss_state.json` 中的 MD5 哈希检测源变化，避免处理未变更的 feed
- **Item 级别**: [ItemStore](src/utils/item_store.py) 使用 `data/items_cache.json` 存储完整翻译缓存，带状态跟踪：
  - `success`: 完全处理，直接使用缓存
  - `partial`: 不完整（如 Elsevier API 失败），冷却期后重试

### 翻译服务工厂

[src/translators/__init__.py](src/translators/__init__.py) 实现工厂模式：

- **手动选择**: 在 `config/config.ini` 的 `[cfg]` 部分设置 `service` 为 `deepseek`、`tencent` 或 `baidu`
- **自动选择**: 设置 `service = "auto"` 按优先级自动降级：
  1. DeepSeek → 2. 腾讯云 → 3. 百度

所有翻译器继承自 [base.py](src/translators/base.py) 抽象基类。

### 增量处理

[main.py:87-100](main.py#L87-L100) 实现增量更新逻辑：
- MD5 匹配且无 partial 条目时跳过处理
- 只处理新增或变更的条目，避免冗余 API 调用

## 关键配置文件

### `.env`
API 密钥（不提交到 git）：
- `DEEPSEEK_API_KEY`
- `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`
- `BAIDU_APP_ID`, `BAIDU_SECRET_KEY`
- `ELSEVIER_API_KEY`（用于 ScienceDirect 期刊的增强摘要获取）

### `config/config.ini`
RSS 源定义和全局设置：

```ini
[cfg]
base = "rss/"          # 输出目录
cooldown_hours = 0     # partial 条目重试冷却时间
service = "tencent"    # 翻译服务: auto, deepseek, tencent, baidu

[source001]
name = "RESS"
url = "https://rss.sciencedirect.com/publication/science/09518320"
max = "100"
action = "auto"
```

## 重要实现细节

### 源特定处理

[processor.py:92-151](src/core/processor.py#L92-L151) 包含针对不同 RSS 源的特殊处理：

- **ScienceDirect feeds**: 尝试通过 Elsevier API 获取完整摘要。API 失败时标记为 "partial"，冷却后可重试。重试时若 API 再次失败，只更新时间戳而不重新翻译（避免浪费 API 调用）。
- **Nature feeds**: 使用正则表达式提取 DOI 后的摘要内容，移除引用信息（[processor.py:34-38](src/core/processor.py#L34-L38)）。

### 错误容错

[main.py:72-85](main.py#L72-L85) 实现多层容错：
- **网络失败**: 降级使用本地已生成的 XML 文件，确保 README 更新不中断
- **API 失败**: 将条目标记为 "partial" 以便稍后重试
- **解析失败**: 记录错误但继续处理其他条目

### 翻译策略

[processor.py:159-173](src/core/processor.py#L159-L173) 将标题 + 摘要合并为单次 API 调用，然后用 `\n\n` 分割结果。这减少了 API 调用次数，节省成本。

## 输出

- 翻译后的 RSS 文件写入 `rss/` 目录
- [readme_updater.py](src/core/readme_updater.py) 自动更新 README.md，添加最新文章列表
- 调试日志（如 Elsevier API 调用详情）保存到 `data/debug/` 目录

## 添加新的翻译服务

1. 在 `src/translators/` 创建新文件，继承 `BaseTranslator`
2. 实现 `translate()` 方法
3. 在 `src/translators/__init__.py` 的 `get_translator()` 函数中添加选择逻辑
4. 在 `.env` 添加必要的 API 密钥
5. 在 `config/config.ini` 的 `service` 选项中添加服务名称

## 添加新的 RSS 源

在 `config/config.ini` 中添加新的 `[sourceXXX]` 部分：
```ini
[source018]
name = "期刊名称"
url = "RSS URL"
max = "100"
action = "auto"
```