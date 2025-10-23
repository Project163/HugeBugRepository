#!/usr/bin/env python3
# framework/fast_bug_miner.py
# (已更新，使用共享 Issues 缓存)

import os
import sys
import subprocess
import csv
import utils
import config

def main():
    input_file = os.path.join(config.SCRIPT_DIR, 'example.txt')
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        sys.exit(1)

    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                parts = line.split('\t') 
                project_id = parts[0] 
                project_name = parts[1]
                repository_url = parts[2]
                issue_tracker_name = parts[3]
                issue_tracker_project_id = parts[4]
                bug_fix_regex = parts[5]
            except IndexError:
                print(f"Skipping malformed line (expected at least 6 tab-separated parts): {line}", file=sys.stderr)
                continue

            print("############################################################")
            print(f"Processing project: {project_id} ({project_name})")
            print("############################################################")

            # --- 1. 定义路径 ---
            
            # (!! 已更新) 创建共享 Issue 缓存键 (例如 "jira_SLING")
            issue_cache_key = f"{issue_tracker_name}_{issue_tracker_project_id}"
            
            # (!! 已更新) Issues 路径现在指向共享缓存
            cache_issues_dir = os.path.join(config.SHARED_ISSUES_DIR, issue_cache_key)
            cache_issues_file = os.path.join(cache_issues_dir, 'issues.txt')

            # 输出路径 (无变化, 仍然按 project_id 组织)
            output_project_dir = os.path.join(config.OUTPUT_DIR, project_id)
            output_patches_dir = os.path.join(output_project_dir, 'patches')
            output_csv_file = os.path.join(output_project_dir, 'active-bugs.csv')
            
            # 项目特定缓存 (Repo 和 Log) (无变化)
            cache_project_dir = os.path.join(config.CACHE_DIR, project_id)
            cache_repo_dir = os.path.join(cache_project_dir, f"{project_name}.git")
            cache_gitlog_file = os.path.join(cache_project_dir, 'gitlog.txt')
            
            # --- 2. 创建目录 ---
            os.makedirs(output_patches_dir, exist_ok=True)
            os.makedirs(cache_project_dir, exist_ok=True) # <-- 创建项目特定缓存
            os.makedirs(cache_issues_dir, exist_ok=True) # <-- (!!) 创建共享 Issues 缓存
            
            # --- 3. 初始化 ---
            
            # 3a. 克隆仓库 (无变化)
            if not os.path.exists(cache_repo_dir):
                cmd = f"git clone --bare \"{repository_url}\" \"{cache_repo_dir}\""
                success, _ = utils.exec_cmd(cmd, f"Cloning {project_name}")
                if not success:
                    print(f"Error: Failed to clone {repository_url}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Repository {project_name}.git already cached.")

            # 3b. (!!) 下载 Issues (已更新)
            # 现在检查共享缓存中的 issues.txt
            if not os.path.exists(cache_issues_file) or os.path.getsize(cache_issues_file) == 0:
                print(f"Shared issues for {issue_cache_key} not found. Downloading...")
                cmd_dl = (
                    f"python3 {os.path.join(config.SCRIPT_DIR, 'download_issues.py')} "
                    f"-g \"{issue_tracker_name}\" -t \"{issue_tracker_project_id}\" "
                    # (!!) -o 和 -f 参数指向共享缓存路径
                    f"-o \"{cache_issues_dir}\" -f \"{cache_issues_file}\""
                )
                success, _ = utils.exec_cmd(cmd_dl, f"Downloading issues for {issue_cache_key}")
                if not success:
                    print(f"Error: Failed to download issues for {issue_cache_key}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Shared issues for {issue_cache_key} already cached. Skipping download.")

            # 3c. 获取 Git Log (无变化)
            if not os.path.exists(cache_gitlog_file):
                cmd_log = f"git --git-dir=\"{cache_repo_dir}\" log --reverse > \"{cache_gitlog_file}\""
                success, _ = utils.exec_cmd(cmd_log, f"Collecting git log for {project_name}")
                if not success:
                    print(f"Error: Failed to get git log for {project_name}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Git log for {project_name} already cached.")

            # 3d. 交叉引用 (如果 active-bugs.csv 不存在)
            if not os.path.exists(output_csv_file):
                try:
                    with open(output_csv_file, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(config.ACTIVE_BUGS_HEADER)
                except IOError as e:
                    print(f"Error: Cannot write header to {output_csv_file}: {e}. Skipping.", file=sys.stderr)
                    continue
                    
                cmd_xref = (
                    f"python3 {os.path.join(config.SCRIPT_DIR, 'vcs_log_xref.py')} "
                    f"-e \"{bug_fix_regex}\" -l \"{cache_gitlog_file}\" "
                    f"-r \"{cache_repo_dir}\" "
                    # (!!) -i 参数指向共享的 issues.txt
                    f"-i \"{cache_issues_file}\" "
                    f"-f \"{output_csv_file}\" "
                    f"-ru \"{repository_url}\" "
                    f"-pid \"{project_id}\""
                )
                success, _ = utils.exec_cmd(cmd_xref, f"Cross-referencing log for {project_id}")
                if not success:
                    print(f"Error: Failed to cross-reference log for {project_id}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Bugs file {output_csv_file} already exists.")

            # --- 4. 生成 Patches ---
            # (此部分无变化)
            print(f"Generating patches from {output_csv_file}...")
            
            try:
                with open(output_csv_file, 'r', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    try:
                        header = next(reader)
                        idx_bug_id = header.index(config.BUGS_CSV_BUGID)
                        idx_commit_buggy = header.index(config.BUGS_CSV_COMMIT_BUGGY)
                        idx_commit_fixed = header.index(config.BUGS_CSV_COMMIT_FIXED)
                    except (StopIteration, ValueError) as e:
                        print(f"Error: Invalid or empty CSV file: {output_csv_file}. {e}", file=sys.stderr)
                        continue
                        
                    for row in reader:
                        try:
                            bug_id = row[idx_bug_id]
                            commit_buggy = row[idx_commit_buggy]
                            commit_fixed = row[idx_commit_fixed]
                        except IndexError:
                            continue 

                        if not commit_buggy or not commit_fixed:
                            print(f"  -> Skipping bug {bug_id} (missing commit hash).")
                            continue

                        patch_file = os.path.join(output_patches_dir, f"{bug_id}.src.patch")
                        
                        if os.path.exists(patch_file):
                            continue 

                        print(f"  -> Generating patch for bug {bug_id} ({commit_buggy} -> {commit_fixed})")
                        
                        cmd_diff = f"git --git-dir=\"{cache_repo_dir}\" diff \"{commit_buggy}\" \"{commit_fixed}\" > \"{patch_file}\""
                        
                        try:
                            subprocess.run(cmd_diff, shell=True, check=True, capture_output=True)
                            
                            if os.path.getsize(patch_file) == 0:
                                print(f"  -> Warning: Generated patch for bug {bug_id} is empty.", file=sys.stderr)
                        except subprocess.CalledProcessError as e:
                            print(f"  -> Error generating patch for bug {bug_id}.", file=sys.stderr)
                            if os.path.exists(patch_file):
                                os.remove(patch_file) 

            except IOError as e:
                print(f"Error reading {output_csv_file}: {e}", file=sys.stderr)
                continue

            print(f"Finished processing project {project_id}.\n")

    print("All projects processed.")

if __name__ == "__main__":
    main()