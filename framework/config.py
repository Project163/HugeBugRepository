# framework/config.py

import os

# Key directories
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'bug-mining'))
CACHE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, 'cache'))

# added shared issues directory
# .../cache/shared_issues/jira_SLING/issues.txt
SHARED_ISSUES_DIR = os.path.abspath(os.path.join(CACHE_DIR, 'shared_issues'))

# Bug CSV column names
BUGS_CSV_BUGID = "bug.id"
BUGS_CSV_PROJECT_ID = "project_id"
BUGS_CSV_COMMIT_BUGGY = "revision.id.buggy"
BUGS_CSV_COMMIT_FIXED = "revision.id.fixed"
BUGS_CSV_ISSUE_ID = "report.id"
BUGS_CSV_ISSUE_URL = "report.url"
BUGS_CSV_BUGGY_URL = "buggy_commit_url"
BUGS_CSV_FIXED_URL = "fixed_commit_url"
BUGS_CSV_COMPARE_URL = "compare_url"

# CSV Header
ACTIVE_BUGS_HEADER = [
    BUGS_CSV_BUGID,
    BUGS_CSV_PROJECT_ID,
    BUGS_CSV_COMMIT_BUGGY,
    BUGS_CSV_COMMIT_FIXED,
    BUGS_CSV_ISSUE_ID,
    BUGS_CSV_ISSUE_URL,
    BUGS_CSV_BUGGY_URL,
    BUGS_CSV_FIXED_URL,
    BUGS_CSV_COMPARE_URL
]