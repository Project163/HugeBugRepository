#!/usr/bin/env python3
# framework/vcs_log_xref.py
# (已更新，添加了 URL 构建逻辑和新列)

import argparse
import sys
import os
import re
import subprocess
import csv # 导入 csv 模块
import utils
import config

# --- (get_git_parent 函数保持不变) ---
def get_git_parent(commit_hash, repo_dir):
    """
    获取一个 commit 的父 commit。只支持单个父 commit。
    """
    try:
        cmd = f"git --git-dir=\"{repo_dir}\" rev-list --parents -n 1 {commit_hash}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
        parts = result.stdout.strip().split()
        
        if len(parts) > 1:
            if len(parts) > 2:
                # 跳过 merge commits
                return None
            return parts[1] # 返回第一个父 commit
        else:
            return None # Root commit
            
    except subprocess.CalledProcessError as e:
        print(f"Warning: Error getting parent for {commit_hash}: {e}", file=sys.stderr)
        return None

# --- 新增辅助函数：构建 Commit URL ---
def construct_commit_url(repo_url, commit_hash):
    """
    根据仓库URL和commit hash构建一个可访问的URL。
    """
    if not repo_url or not commit_hash:
        return "NA"
    base_url = repo_url.rstrip('.git')
    
    if 'github.com' in repo_url:
        return f"{base_url}/tree/{commit_hash}"
    if 'gitlab.com' in repo_url:
        return f"{base_url}/-/tree/{commit_hash}"
    if 'bitbucket.org' in repo_url:
        return f"{base_url}/tree/{commit_hash}"
    # 其他 (如 Apache gitbox)
    if 'gitbox.apache.org' in repo_url:
        # 假设是 'https://gitbox.apache.org/repos/asf/project.git'
        # 变为 'https://github.com/apache/project/commit/...'
        base_url = base_url.replace('gitbox.apache.org/repos/asf', 'github.com/apache')
        return f"{base_url}/tree/{commit_hash}"
    return "NA"

# --- 新增辅助函数：构建 Compare URL ---
def construct_compare_url(repo_url, buggy_hash, fixed_hash):
    """
    根据仓库URL和两个commit hash构建一个 diff 比较 URL。
    """
    if not repo_url or not buggy_hash or not fixed_hash:
        return "NA"
    base_url = repo_url.rstrip('.git')
    
    if 'github.com' in repo_url:
        return f"{base_url}/compare/{buggy_hash}...{fixed_hash}"
    if 'gitlab.com' in repo_url:
        return f"{base_url}/-/compare/{buggy_hash}...{fixed_hash}"
    if 'bitbucket.org' in repo_url:
        # Bitbucket 顺序是 new..old
        return f"{base_url}/compare/{fixed_hash}..{buggy_hash}#diff"
    if 'gitbox.apache.org' in repo_url:
        base_url = base_url.replace('gitbox.apache.org/repos/asf', 'github.com/apache')
        return f"{base_url}/compare/{buggy_hash}...{fixed_hash}"
    return "NA"

def main():
    parser = argparse.ArgumentParser(description="Cross-reference VCS log with issue tracker data.")
    parser.add_argument('-e', dest='regexp', required=True, help="Perl-compatible regex to match issue IDs")
    parser.add_argument('-l', dest='log_file', required=True, help="Path to the commit log file (from git log)")
    parser.add_argument('-r', dest='repo_dir', required=True, help="Path to the .git repository directory")
    parser.add_argument('-i', dest='issues_file', required=True, help="Path to the issues.txt file (id,url)")
    parser.add_argument('-f', dest='output_file', required=True, help="Output file for active-bugs.csv (will append)")
    # --- 新增参数 ---
    parser.add_argument('-ru', dest='repo_url', required=True, help="Public repository URL (e.g., https://github.com/org/repo.git)")
    parser.add_argument('-pid', dest='project_id', required=True, help="Project ID (e.g., 'core' or '.')")

    args = parser.parse_args()

    # 1. 加载 issues.txt 到内存
    issues_db = utils.read_config_file(args.issues_file, key_separator=',')
    if not issues_db:
        print(f"Error: Could not read or issues file is empty: {args.issues_file}", file=sys.stderr)
        sys.exit(1)
        
    issues_db_lower = {k.lower(): v for k, v in issues_db.items()}

    # 2. 解析 Perl 正则表达式
    try:
        pattern_str = args.regexp.strip('/ \t\n\r')
        flags_str = ""
        if '/' in pattern_str:
            parts = pattern_str.rsplit('/', 1)
            pattern_str = parts[0]
            flags_str = parts[1]
        
        flags = 0
        if 'm' in flags_str:
            flags |= re.MULTILINE
        if 'i' in flags_str:
            flags |= re.IGNORECASE
            
        bug_regex = re.compile(pattern_str, flags)
    except re.error as e:
        print(f"Error: Invalid regex provided: {args.regexp}. Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. 逐行读取 git log 文件
    results = {}
    version_id = 1
    current_commit = None
    commit_message_lines = []

    try:
        with open(args.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('commit '):
                    if current_commit and commit_message_lines:
                        commit_message = "\n".join(commit_message_lines)
                        match = bug_regex.search(commit_message)
                        
                        if match and match.groups():
                            bug_number = match.group(1) 
                            if bug_number.lower() in issues_db_lower:
                                parent = get_git_parent(current_commit, args.repo_dir)
                                if parent: 
                                    results[version_id] = {
                                        'p': parent,
                                        'c': current_commit,
                                        'issue_id': bug_number,
                                        'issue_url': issues_db_lower.get(bug_number.lower(), 'NA')
                                    }
                                    version_id += 1
                                    
                    current_commit = line.split()[1].strip()
                    commit_message_lines = []
                
                elif current_commit and line.startswith('    '):
                    commit_message_lines.append(line.strip())

        # 处理文件中的最后一条 commit
        if current_commit and commit_message_lines:
            commit_message = "\n".join(commit_message_lines)
            match = bug_regex.search(commit_message)
            if match and match.groups():
                bug_number = match.group(1)
                if bug_number.lower() in issues_db_lower:
                    parent = get_git_parent(current_commit, args.repo_dir)
                    if parent:
                        results[version_id] = {
                            'p': parent,
                            'c': current_commit,
                            'issue_id': bug_number,
                            'issue_url': issues_db_lower.get(bug_number.lower(), 'NA')
                        }
                        version_id += 1

    except IOError as e:
        print(f"Error reading log file {args.log_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("Warning: No commit matching the regex was found.", file=sys.stderr)

    # 4. 将结果附加到 output_file (active-bugs.csv)
    try:
        # 'a' (append) 模式, 并且使用 csv.writer 确保格式正确
        with open(args.output_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for vid in sorted(results.keys()):
                row = results[vid]
                
                # --- (已更新) 构建新数据 ---
                project_id = args.project_id
                buggy_hash = row['p']
                fixed_hash = row['c']
                issue_id = row['issue_id']
                issue_url = row['issue_url']
                
                # 调用辅助函数
                buggy_url = construct_commit_url(args.repo_url, buggy_hash)
                fixed_url = construct_commit_url(args.repo_url, fixed_hash)
                compare_url = construct_compare_url(args.repo_url, buggy_hash, fixed_hash)
                
                # --- (已更新) 写入新行 (9 列) ---
                # 顺序必须匹配 config.py 中的 ACTIVE_BUGS_HEADER
                writer.writerow([
                    vid,
                    project_id,
                    buggy_hash,
                    fixed_hash,
                    issue_id,
                    issue_url,
                    buggy_url,
                    fixed_url,
                    compare_url
                ])
    except IOError as e:
        print(f"Error writing to output file {args.output_file}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()