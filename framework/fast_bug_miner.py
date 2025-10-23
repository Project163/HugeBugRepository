#!/usr/bin/env python3
# framework/fast_bug_miner.py
# (已更新以匹配新架构)

import os
import sys
import subprocess
import csv
import utils
import config  # 导入同一目录下的 config.py

def main():
    # 假设 example1.txt 位于 framework/ 目录中
    input_file = os.path.join(config.SCRIPT_DIR, 'example1.txt')
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        sys.exit(1)

    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                # 解析 example1.txt
                parts = line.split('\t') # (使用Tab分隔)
                project_id = parts[0]
                project_name = parts[1]
                repository_url = parts[2]
                issue_tracker_name = parts[3]
                issue_tracker_project_id = parts[4]
                bug_fix_regex = parts[5]
            except IndexError:
                print(f"Skipping malformed line: {line}", file=sys.stderr)
                continue

            print("############################################################")
            print(f"Processing project: {project_id} ({project_name})")
            print("############################################################")

            # --- 1. 定义路径 ---
            # (!! 已修改) 使用新的 config.OUTPUT_DIR
            output_project_dir = os.path.join(config.OUTPUT_DIR, project_id)
            output_patches_dir = os.path.join(output_project_dir, 'patches')
            output_csv_file = os.path.join(output_project_dir, 'active-bugs.csv')
            
            # (!! 已修改) config.CACHE_DIR 现在指向 framework/cache/
            cache_project_dir = os.path.join(config.CACHE_DIR, project_id)
            cache_repo_dir = os.path.join(cache_project_dir, f"{project_name}.git")
            cache_issues_file = os.path.join(cache_project_dir, 'issues.txt')
            cache_gitlog_file = os.path.join(cache_project_dir, 'gitlog.txt')
            
            # --- 2. 创建目录 (替代 create-project.pl) ---
            os.makedirs(output_patches_dir, exist_ok=True)
            os.makedirs(cache_project_dir, exist_ok=True)
            
            # --- 3. 初始化 (替代 initialize-project-and-collect-issues.pl) ---
            
            # 3a. 克隆仓库 (如果不存在)
            if not os.path.exists(cache_repo_dir):
                cmd = f"git clone --bare \"{repository_url}\" \"{cache_repo_dir}\""
                success, _ = utils.exec_cmd(cmd, f"Cloning {project_name}")
                if not success:
                    print(f"Error: Failed to clone {repository_url}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Repository {project_name}.git already cached.")

            # 3b. 下载 Issues (如果不存在)
            if not os.path.exists(cache_issues_file):
                cmd_dl = (
                    # (!!) 注意: 这里的脚本路径使用了 config.SCRIPT_DIR 来确保
                    # 即使从其他地方运行 fast_bug_miner.py 也能找到 download_issues.py
                    f"python3 {os.path.join(config.SCRIPT_DIR, 'download_issues.py')} "
                    f"-g \"{issue_tracker_name}\" -t \"{issue_tracker_project_id}\" "
                    f"-o \"{cache_project_dir}\" -f \"{cache_issues_file}\""
                )
                success, _ = utils.exec_cmd(cmd_dl, f"Downloading issues for {project_id}")
                if not success:
                    print(f"Error: Failed to download issues for {project_id}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Issues for {project_id} already cached.")

            # 3c. 获取 Git Log (如果不存在)
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
                # 写入CSV表头
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
                    f"-r \"{cache_repo_dir}\" -i \"{cache_issues_file}\" "
                    f"-f \"{output_csv_file}\"" # vcs_log_xref.py 是 'a' (附加) 模式
                )
                success, _ = utils.exec_cmd(cmd_xref, f"Cross-referencing log for {project_id}")
                if not success:
                    print(f"Error: Failed to cross-reference log for {project_id}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Bugs file {output_csv_file} already exists.")

            # --- 4. 生成 Patches (来自 fast_bug_mining.sh) ---
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
                            continue # 跳过格式错误的行

                        if not commit_buggy or not commit_fixed:
                            print(f"  -> Skipping bug {bug_id} (missing commit hash).")
                            continue

                        patch_file = os.path.join(output_patches_dir, f"{bug_id}.src.patch")
                        
                        if os.path.exists(patch_file):
                            continue # 只生成不存在的 patch

                        print(f"  -> Generating patch for bug {bug_id} ({commit_buggy} -> {commit_fixed})")
                        
                        cmd_diff = f"git --git-dir=\"{cache_repo_dir}\" diff \"{commit_buggy}\" \"{commit_fixed}\" > \"{patch_file}\""
                        
                        try:
                            subprocess.run(cmd_diff, shell=True, check=True, capture_output=True)
                            
                            if os.path.getsize(patch_file) == 0:
                                print(f"  -> Warning: Generated patch for bug {bug_id} is empty.", file=sys.stderr)
                        except subprocess.CalledProcessError as e:
                            print(f"  -> Error generating patch for bug {bug_id}.", file=sys.stderr)
                            if os.path.exists(patch_file):
                                os.remove(patch_file) # 删除失败的空文件

            except IOError as e:
                print(f"Error reading {output_csv_file}: {e}", file=sys.stderr)
                continue

            print(f"Finished processing project {project_id}.\n")

    print("All projects processed.")

if __name__ == "__main__":
    main()