<div align="center">
  <h1>ExplainedRealBugs</h1>
</div>

[简体中文](README.zh-CN.md)

## Introduction

ExplainedRealBugs (Based on defects4j) is a framework designed to automate the process of mining bug data from various software repositories and issue trackers. It provides a streamlined workflow to identify, collect, and process bug-related information, creating a structured dataset for analysis and research.

## Project Purpose

The primary goal of this project is to build a comprehensive bug repository. It achieves this by:

1.  Cloning Git repositories of specified projects.
2.  Downloading bug reports from various issue trackers like Jira, GitHub, and Bugzilla.
3.  Cross-referencing Git commit logs with bug reports to identify bug-fixing commits.
4.  Generating patch files (`.diff` or `.patch`) that represent the code changes for each bug fix.
5.  Consolidating this information into a structured format, including a CSV file (`active-bugs.csv`) that links bug reports to their corresponding fixing commits.
6.  Gathering the bug reports and associated data.
7.  Providing a cleanup script to remove data for specific projects.

## Features

*   **Automated Bug Mining**: Automatically clones repositories, downloads bug reports, and identifies bug-fixing commits.
*   **Multi-Tracker Support**: Supports issue trackers like Jira, GitHub, and Bugzilla.
*   **Structured Output**: Generates a clean, structured dataset including patch files and a CSV mapping bugs to commits.
*   **Error Logging**: All error messages during the mining process are logged to `error.txt` for easy debugging.
*   **Data Cleanup**: Includes a script to selectively remove all cached and output data for specified projects.

## Bug Repository Overview

Currently, the repository contains bug data for **303** projects, with a total of **143,591** bugs.

For a complete list of bug report IDs and other details, please see the [`bug_summary.md`](bug_summary.md) file.

## Getting Started

Follow these steps to set up and run the bug mining framework.

### Prerequisites

*   Ubuntu(We are using 24.04)
*   Python 3(We are using 3.12)
*   Git

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/Project163/ExplainedRealBugs.git
    cd ExplainedRealBugs
    ```

2.  **Install Python dependencies:**
    The framework requires `requests` and `beautifulsoup4`. Install them using the provided requirements file.
    ```sh
    pip install -r framework/requirements.txt
    ```
    Alternatively, you can install them manually:
    ```sh
    pip install requests beautifulsoup4
    ```

### Configuration

1.  **Define Target Projects:**
    Edit the `framework/example.txt` file(if it not exists, you can create it manually) to specify the projects you want to mine. Each line represents a project and should be a **tab-separated** list with the following format:
    `project_id	project_name	repository_url	issue_tracker_name	issue_tracker_project_id	bug_fix_regex`

    Example line:
    `Bsf	bsf	https://github.com/apache/commons-bsf.git	jira	BSF	/(BSF-\\d+)/mi	.`

    Where:
    *   `issue_tracker_name` can be `github`, `jira`, `bugzilla(Waiting for update)`, etc. (see [`SUPPORTED_TRACKERS`](framework/download_issues.py) in [`framework/download_issues.py`](framework/download_issues.py)).

2.  **(Optional) GitHub API Token:**
    To avoid rate-limiting issues when downloading from GitHub, it is highly recommended to set a personal access token as an environment variable.
    - Linux
    ```sh
    export GH_TOKEN="your_github_personal_access_token"
    ```
    - Windows(Still waiting for update)
    ```bash
    set GH_TOKEN "your_github_personal_access_token"
    ```
### Running the Miner

Execute the main script to start the mining process. The script will read the projects from `framework/example.txt` and process them sequentially.

```sh
python framework/fast_bug_miner.py
```

The script will handle the creation of necessary cache and output directories. Any errors encountered during the process will be logged to `error.txt` in the root directory for debugging.

### Cleaning Up Data

The framework includes a script to clean up all data (mined output and cache) for specific projects. This is useful for removing corrupted data or starting fresh.

1.  **Create a `delete.txt` file:**
    Create a file named `framework/delete.txt`. This file should list the projects you want to clean, following the same format as `framework/example.txt`.

2.  **Run the cleanup script:**
    ```sh
    python framework/clean_bug_and_cache.py
    ```
    You can also specify a different input file using the `-i` flag:
    ```sh
    python framework/clean_bug_and_cache.py -i path/to/your/project_list.txt
    ```

## Advanced Features: LLM-Assisted Analysis

To improve the accuracy of bug mining and data usability, we have introduced LLM-based auxiliary tools. Using these features requires configuring the `SILICONCLOUD_API_KEY` environment variable.

### 1. LLM Cross-Reference
Script: `framework/llm_xref.py`

This script uses an LLM (e.g., Qwen) to intelligently analyze the relationship between Git commit messages and Issues.
- **Function**: Distinguishes whether an Issue mentioned in a commit message is "Fixed" or merely "Related".
- **Mechanism**: First filters potential associations via regex, then sends the commit message to the LLM for semantic judgment, finally outputting a precise `active-bugs.csv`.

### 2. Report Parsing
Script: `framework/parse_reports.py`

Converts raw bug reports from various sources (Jira, GitHub, Google Code) into a unified JSONL format suitable for LLM processing.
- **Function**: Extracts titles, descriptions, and comments, removes HTML tags and code blocks, and generates clear text summaries.
- **Output**: `bug-classification/parsed_data.jsonl`

### 3. Bug Classification
Script: `framework/classify_bugs_llm.py` / `framework/classify_bugs_embedding.py`

Provides two methods for automatic bug classification (e.g., Crash, UI, Logic, etc.).
- **LLM-based (`classify_bugs_llm.py`)**: Directly asks the LLM to classify the bug description. High accuracy but speed is limited by the API.
- **Embedding-based (`classify_bugs_embedding.py`)**: Calculates vector similarity between bug descriptions and predefined categories. Fast and low cost.

### Output

The mined data for each project will be stored in the `bug-mining/` directory. For each `project_id` defined in the input file, you will find a corresponding folder:

```
bug-mining/
└── <project_id>/
    ├── active-bugs.csv      # CSV file mapping bug IDs to fixing commits
    └── patches/             # Directory containing patch files for each bug
        ├── 1.src.patch
        └── ...
    └── reports/            # Directory containing downloaded report files for each bug
        ├── 1.report.xxx
        └── ...
```

Classification results will be stored in `bug-classification/classified_data_embedding.jsonl` or `bug-classification/classified_data_llm.jsonl`, depending on the classification method used.
