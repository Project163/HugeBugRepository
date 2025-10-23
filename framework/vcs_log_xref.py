#!/usr/bin/env python3
# vcs_log_xref.py
# (翻译自 vcs-log-xref.pl)

import argparse
import sys
import os
import re
import subprocess
import utils
import config

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

def main():
    parser = argparse.ArgumentParser(description="Cross-reference VCS log with issue tracker data.")
    parser.add_argument('-e', dest='regexp', required=True, help="Perl-compatible regex to match issue IDs (e.g., '/(LANG-\\d+)/mi')")
    parser.add_argument('-l', dest='log_file', required=True, help="Path to the commit log file (from git log)")
    parser.add_argument('-r', dest='repo_dir', required=True, help="Path to the .git repository directory")
    parser.add_argument('-i', dest='issues_file', required=True, help="Path to the issues.txt file (id,url)")
    parser.add_argument('-f', dest='output_file', required=True, help="Output file for active-bugs.csv (will append)")
    
    args = parser.parse_args()

    # 1. 加载 issues.txt 到内存 (关键优化)
    issues_db = utils.read_config_file(args.issues_file, key_separator=',')
    if not issues_db:
        print(f"Error: Could not read or issues file is empty: {args.issues_file}", file=sys.stderr)
        sys.exit(1)
        
    # 将key转为小写 (来自原始脚本)
    issues_db_lower = {k.lower(): v for k, v in issues_db.items()}

    # 2. 解析 Perl 正则表达式
    try:
        # 移除 Perl 的 /.../mi 分隔符
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
                    # 找到了新 commit, 处理上一条
                    if current_commit and commit_message_lines:
                        commit_message = "\n".join(commit_message_lines)
                        match = bug_regex.search(commit_message)
                        
                        if match and match.groups():
                            bug_number = match.group(1) # 假设在第一个捕获组
                            
                            # (!!!) 内存哈希表优化 (来自 vcs-log-xref.pl L111)
                            if bug_number.lower() in issues_db_lower:
                                parent = get_git_parent(current_commit, args.repo_dir)
                                if parent: # 确保有父节点 (非merge, 非root)
                                    results[version_id] = {
                                        'p': parent,
                                        'c': current_commit,
                                        'issue_id': bug_number,
                                        'issue_url': issues_db_lower.get(bug_number.lower(), 'NA')
                                    }
                                    version_id += 1
                                    
                    # 重置
                    current_commit = line.split()[1].strip()
                    commit_message_lines = []
                
                elif current_commit and line.startswith('    '):
                    # 缩进的行是 commit message
                    commit_message_lines.append(line.strip())

        # (!!) 处理文件中的最后一条 commit
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
    # 原始脚本是 '>>' 附加模式
    try:
        # 'a' (append) 模式
        with open(args.output_file, 'a', encoding='utf-8') as f:
            for vid in sorted(results.keys()):
                row = results[vid]
                # 格式: <d4j_bug_id, bug_commit_hash, fix_commit_hash, issue_id, issue_url>
                f.write(f"{vid},{row['p']},{row['c']},{row['issue_id']},{row['issue_url']}\n")
    except IOError as e:
        print(f"Error writing to output file {args.output_file}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()