<div align="center">
  <h1>ExplainedRealBugs</h1>
</div>

[English](README.md)

## 介绍

ExplainedRealBugs（基于 defects4j）是一个旨在自动化从各种软件仓库和问题跟踪器中挖掘缺陷数据的框架。它提供了一个简化的工作流程来识别、收集和处理与缺陷相关的信息，从而创建一个用于分析和研究的结构化数据集。

## 项目目标

该项目的主要目标是构建一个全面的缺陷存储库。它通过以下方式实现这一目标：

1.  克隆指定项目的 Git 仓库。
2.  从 Jira、GitHub 和 Bugzilla 等各种问题跟踪器下载缺陷报告。
3.  将 Git 提交日志与缺陷报告进行交叉引用，以识别修复缺陷的提交。
4.  生成代表每个缺陷修复的代码更改的补丁文件（`.diff` 或 `.patch`）。
5.  将此信息整合为结构化格式，包括一个将缺陷报告链接到其相应修复提交的 CSV 文件（`active-bugs.csv`）。
6.  收集缺陷报告及相关数据。
7.  提供清理脚本以删除特定项目的数据。

## 功能特性

*   **自动化缺陷挖掘**: 自动克隆仓库、下载缺陷报告并识别缺陷修复提交。
*   **多跟踪器支持**: 支持 Jira、GitHub 和 Bugzilla 等问题跟踪器。
*   **结构化输出**: 生成干净、结构化的数据集，包括补丁文件和将缺陷映射到提交的 CSV 文件。
*   **缺陷日志记录**: 挖掘过程中的所有缺陷消息都会记录到 `error.txt` 中，便于调试。
*   **数据清理**: 包含一个脚本，可选择性地删除指定项目的所有缓存和输出数据。

## 缺陷库概览

目前，该缺陷库包含了 **303** 个项目的缺陷数据，总计 **143,591** 个缺陷。

如需查看完整的缺陷报告 ID 列表及其他详细信息，请参阅 [`bug_summary.md`](bug_summary.md) 文件。

## 入门指南

请按照以下步骤设置和运行缺陷挖掘框架。

### 先决条件

*   Ubuntu（我们使用的是 24.04）
*   Python 3（我们使用的是 3.12）
*   Git

### 安装

1.  **克隆存储库：**
    ```sh
    git clone https://github.com/Project163/ExplainedRealBugs.git
    cd ExplainedRealBugs
    ```

2.  **安装 Python 依赖项：**
    该框架需要 `requests` 和 `beautifulsoup4`。请使用提供的需求文件进行安装。
    ```sh
    pip install -r framework/requirements.txt
    ```
    除此之外，您还可以手动安装它们：
    ```sh
    pip install requests beautifulsoup4
    ```

### 配置

1.  **定义目标项目：**
    编辑 `framework/example.txt` 文件（若文件不存在，您可以手动创建它）以指定要挖掘的项目。每行代表一个项目，应为以下格式的制表符分隔列表：

    `project_id	project_name	repository_url	issue_tracker_name	issue_tracker_project_id	bug_fix_regex`

    示例行：

    `Bsf	bsf	https://github.com/apache/commons-bsf.git	jira	BSF	/(BSF-\\d+)/mi	.`

    其中：
    *   `issue_tracker_name` 可以是 `github`、`jira`、`bugzilla（等待更新）`等（请参阅 [`framework/download_issues.py`](framework/download_issues.py) 中的 [`SUPPORTED_TRACKERS`](framework/download_issues.py)）。

2.  **（可选）GitHub API 令牌：**
    为避免从 GitHub 下载时出现速率限制问题，强烈建议将个人访问令牌设置为环境变量。
    - Linux
    ```sh
    export GH_TOKEN="your_github_personal_access_token"
    ```
    - Windows (仍待更新)
    ```bash
    set GH_TOKEN "your_github_personal_access_token"
    ```
### 运行挖掘器

执行主脚本以启动挖掘过程。该脚本将从 `framework/example.txt` 读取项目并按顺序处理它们。

```sh
python framework/fast_bug_miner.py
```

该脚本将处理必要的缓存和输出目录的创建。在此过程中遇到的任何缺陷都将记录在根目录下的 `error.txt` 文件中，以方便调试。

### 清理数据

该框架包含一个脚本，用于清理特定项目的所有数据（挖掘输出和缓存）。这对于删除损坏的数据或重新开始非常有用。

1.  **创建 `delete.txt` 文件：**
    创建一个名为 `framework/delete.txt` 的文件。该文件应列出您要清理的项目，格式与 `framework/example.txt` 相同。

2.  **运行清理脚本：**
    ```sh
    python framework/clean_bug_and_cache.py
    ```
    您也可以使用 `-i` 标志指定不同的输入文件：
    ```sh
    python framework/clean_bug_and_cache.py -i path/to/your/project_list.txt
    ```

## 高级功能：LLM 辅助分析

为了提高缺陷挖掘的准确性和数据的可用性，我们引入了基于 LLM 的辅助工具。使用这些功能需要配置 `SILICONCLOUD_API_KEY` 环境变量。

### 1. GitHub 交叉引用 (LLM Cross-Reference)
脚本: `framework/llm_xref.py`

此脚本利用 LLM（如 Qwen）来智能分析 Git 提交信息与 Issue 之间的关系。
- **功能**: 区分提交信息中提到的 Issue 是被“修复 (Fixed)”还是仅仅是“相关 (Related)”。
- **原理**: 首先通过正则筛选潜在关联，然后将提交信息发送给 LLM 进行语义判定，最后输出精准的 `active-bugs.csv`。

### 2. 缺陷报告格式化 (Report Parsing)
脚本: `framework/parse_reports.py`

将来自不同源（Jira, GitHub, Google Code）的原始缺陷报告统一转换为适合 LLM 处理的 JSONL 格式。
- **功能**: 提取标题、描述和评论，去除 HTML 标签和代码块，生成清晰的文本摘要。
- **输出**: `bug-classification/parsed_data.jsonl`

### 3. 缺陷分类 (Bug Classification)
脚本: `framework/classify_bugs_llm.py` / `framework/classify_bugs_embedding.py`

提供两种方式对缺陷进行自动分类（如 Crash, UI, Logic 等）。
- **基于 LLM (`classify_bugs_llm.py`)**: 直接询问 LLM 对缺陷描述进行分类，准确度高但速度受限于 API。
- **基于 Embedding (`classify_bugs_embedding.py`)**: 计算缺陷描述与预定义类别的向量相似度，速度快且成本低。

### 输出

每个项目的挖掘数据将存储在 `bug-mining/` 目录中。对于输入文件中定义的每个 `project_id`，您将找到一个相应的文件夹：

```
bug-mining/
└── <project_id>/
    ├── active-bugs.csv      # CSV 文件，将缺陷 ID 映射到修复提交
    └── patches/             # 包含每个缺陷补丁文件的目录
        ├── 1.src.patch
        └── ...
    └── reports/            # 包含每个缺陷下载的报告文件的目录
        ├── 1.report.xxx
        └── ...
```

分类结果将存储在 `bug-classification/classified_data_embedding.jsonl` 或 `bug-classification/classified_data_llm.jsonl` 中，具体取决于使用的分类方法。
