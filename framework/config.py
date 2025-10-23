# framework/config.py
import os

# --- 核心路径 ---
# SCRIPT_DIR 现在是 /.../HugeBugRepository/framework
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

# (新) 输出目录 /.../HugeBugRepository/bug-mining/
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'bug-mining'))

# (新) 缓存目录 /.../HugeBugRepository/framework/cache/
CACHE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, 'cache'))

# --- Bug CSV 列名 ---
# (这部分无变化)
BUGS_CSV_BUGID = "bug.id"
BUGS_CSV_COMMIT_BUGGY = "revision.id.buggy"
BUGS_CSV_COMMIT_FIXED = "revision.id.fixed"
BUGS_CSV_ISSUE_ID = "report.id"
BUGS_CSV_ISSUE_URL = "report.url"

# CSV 文件的表头
ACTIVE_BUGS_HEADER = [
    BUGS_CSV_BUGID,
    BUGS_CSV_COMMIT_BUGGY,
    BUGS_CSV_COMMIT_FIXED,
    BUGS_CSV_ISSUE_ID,
    BUGS_CSV_ISSUE_URL
]