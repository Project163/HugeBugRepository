<div align="center">
  <h1>HugeBugRepository</h1>
</div>

[English](README.md)

## 介绍

HugeBugRepository（基于 defects4j）是一个旨在自动化从各种软件仓库和问题跟踪器中挖掘错误数据的框架。它提供了一个简化的工作流程来识别、收集和处理与错误相关的信息，从而创建一个用于分析和研究的结构化数据集。

## 项目目标

该项目的主要目标是构建一个全面的错误存储库。它通过以下方式实现这一目标：

1.  克隆指定项目的 Git 仓库。
2.  从 Jira、GitHub 和 Bugzilla 等各种问题跟踪器下载错误报告。
3.  将 Git 提交日志与错误报告进行交叉引用，以识别修复错误的提交。
4.  生成代表每个错误修复的代码更改的补丁文件（`.diff` 或 `.patch`）。
5.  将此信息整合为结构化格式，包括一个将错误报告链接到其相应修复提交的 CSV 文件（`active-bugs.csv`）。

## 入门指南

请按照以下步骤设置和运行错误挖掘框架。

### 先决条件

*   Python 3（我们使用的是 3.12）
*   Git

### 安装

1.  **克隆存储库：**
    ```sh
    git clone <your-repository-url>
    cd HugeBugRepository
    ```

2.  **安装 Python 依赖项：**
    该框架需要 `requests` 和 `beautifulsoup4`。请使用提供的需求文件进行安装。
    ```sh
    pip install -r framework/requirements.txt
    ```

### 配置

1.  **定义目标项目：**
    编辑 `framework/example.txt` 文件以指定要挖掘的项目。每行代表一个项目，应为以下格式的制表符分隔列表：
    `project_id	project_name	repository_url	issue_tracker_name	issue_tracker_project_id	bug_fix_regex`

    示例行：
    `Bsf	bsf	https://github.com/apache/commons-bsf.git	jira	BSF	/(BSF-\\d+)/mi	.`

    其中：
    *   `issue_tracker_name` 可以是 `github`、`jira`、`bugzilla（等待更新）`等（请参阅 [`framework/download_issues.py`](framework/download_issues.py) 中的 [`SUPPORTED_TRACKERS`](framework/download_issues.py)）。

2.  **（可选）GitHub API 令牌：**
    为避免从 GitHub 下载时出现速率限制问题，强烈建议将个人访问令牌设置为环境变量。
    ```sh
    export GH_TOKEN="your_github_personal_access_token"
    ```

### 运行挖掘器

执行主脚本以启动挖掘过程。该脚本将从 `framework/example.txt` 读取项目并按顺序处理它们。

```sh
python3 framework/fast_bug_miner.py
```

该脚本将处理必要的缓存和输出目录的创建。

### 输出

每个项目的挖掘数据将存储在 `bug-mining/` 目录中。对于输入文件中定义的每个 `project_id`，您将找到一个相应的文件夹：

```
bug-mining/
└── <project_id>/
    ├── active-bugs.csv      # CSV 文件，将错误 ID 映射到修复提交
    └── patches/             # 包含每个错误补丁文件的目录
        ├── 1.src.patch
        └── ...
```
