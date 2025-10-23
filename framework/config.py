# framework/config.py
# (已更新，添加了新列)

import os

# --- 核心路径 ---
# SCRIPT_DIR 现在是 /.../HugeBugRepository/framework
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

# (新) 输出目录 /.../HugeBugRepository/bug-mining/
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'bug-mining'))

# (新) 缓存目录 /.../HugeBugRepository/framework/cache/
CACHE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, 'cache'))

# --- Bug CSV 列名 ---
# (已更新)
BUGS_CSV_BUGID = "bug.id"
BUGS_CSV_PROJECT_ID = "project.id"     # <-- 新增 (仓库/子模块名称)
BUGS_CSV_COMMIT_BUGGY = "revision.id.buggy"
BUGS_CSV_COMMIT_FIXED = "revision.id.fixed"
BUGS_CSV_ISSUE_ID = "report.id"
BUGS_CSV_ISSUE_URL = "report.url"
BUGS_CSV_BUGGY_URL = "buggy_commit_url"   # <-- 新增
BUGS_CSV_FIXED_URL = "fixed_commit_url"   # <-- 新增
BUGS_CSV_COMPARE_URL = "compare_url"      # <-- 新增

# (已更新) CSV 文件的表头
ACTIVE_BUGS_HEADER = [
    BUGS_CSV_BUGID,
    BUGS_CSV_PROJECT_ID,     # <-- 新增
    BUGS_CSV_COMMIT_BUGGY,
    BUGS_CSV_COMMIT_FIXED,
    BUGS_CSV_ISSUE_ID,
    BUGS_CSV_ISSUE_URL,
    BUGS_CSV_BUGGY_URL,     # <-- 新增
    BUGS_CSV_FIXED_URL,     # <-- 新增
    BUGS_CSV_COMPARE_URL      # <-- 新增
]