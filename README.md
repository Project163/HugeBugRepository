<div align="center">
  <h1>HugeBugRepository</h1>
</div>

[简体中文](README.zh-CN.md)

## Introduction

HugeBugRepository(Based on defects4j) is a framework designed to automate the process of mining bug data from various software repositories and issue trackers. It provides a streamlined workflow to identify, collect, and process bug-related information, creating a structured dataset for analysis and research.

## Project Purpose

The primary goal of this project is to build a comprehensive bug repository. It achieves this by:

1.  Cloning Git repositories of specified projects.
2.  Downloading bug reports from various issue trackers like Jira, GitHub, and Bugzilla.
3.  Cross-referencing Git commit logs with bug reports to identify bug-fixing commits.
4.  Generating patch files (`.diff` or `.patch`) that represent the code changes for each bug fix.
5.  Consolidating this information into a structured format, including a CSV file (`active-bugs.csv`) that links bug reports to their corresponding fixing commits.

## Getting Started

Follow these steps to set up and run the bug mining framework.

### Prerequisites

*   Ubuntu(We are using 24.04)
*   Python 3(We are using 3.12)
*   Git

### Installation

1.  **Clone the repository:**
    ```sh
    git clone <your-repository-url>
    cd HugeBugRepository
    ```

2.  **Install Python dependencies:**
    The framework requires `requests` and `beautifulsoup4`. Install them using the provided requirements file.
    ```sh
    pip install -r framework/requirements.txt
    ```

### Configuration

1.  **Define Target Projects:**
    Edit the `framework/example1.txt` file to specify the projects you want to mine. Each line represents a project and should be a tab-separated list with the following format:
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
    - Windows (PowerShell)
    ```bash
    set GH_TOKEN "your_github_personal_access_token"
    ```
### Running the Miner

Execute the main script to start the mining process. The script will read the projects from `framework/example1.txt` and process them sequentially.

```sh
python framework/fast_bug_miner.py
```

The script will handle the creation of necessary cache and output directories.

### Output

The mined data for each project will be stored in the `bug-mining/` directory. For each `project_id` defined in the input file, you will find a corresponding folder:

```
bug-mining/
└── <project_id>/
    ├── active-bugs.csv      # CSV file mapping bug IDs to fixing commits
    └── patches/             # Directory containing patch files for each bug
        ├── 1.src.patch
        └── ...
```