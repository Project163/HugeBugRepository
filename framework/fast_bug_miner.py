#!/usr/bin/env python3
# framework/fast_bug_miner.py

import os
import sys  # <-- (!!) 导入 sys 模块
import subprocess
import csv
import utils
import config
import codecs

def main():
    PYTHON_EXECUTABLE = sys.executable

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
                
                sub_project_path = "."
                if len(parts) > 6 and parts[6].strip() and parts[6].strip() != ".":
                    sub_project_path = parts[6].strip()
                    

            except IndexError:
                print(f"Skipping malformed line (expected at least 6 tab-separated parts): {line}", file=sys.stderr)
                continue

            print("############################################################")
            print(f"Processing project: {project_id} ({project_name})")
            print("############################################################")

            # 1. define paths
            issue_cache_key = f"{issue_tracker_name}_{issue_tracker_project_id}"
            cache_issues_dir = os.path.join(config.SHARED_ISSUES_DIR, issue_cache_key)
            cache_issues_file = os.path.join(cache_issues_dir, 'issues.txt')

            output_project_dir = os.path.join(config.OUTPUT_DIR, project_id)
            output_patches_dir = os.path.join(output_project_dir, 'patches')
            output_csv_file = os.path.join(output_project_dir, 'active-bugs.csv')
            
            cache_project_dir = os.path.join(config.CACHE_DIR, project_id)
            cache_repo_dir = os.path.join(cache_project_dir, f"{project_name}.git")
            cache_gitlog_file = os.path.join(cache_project_dir, 'gitlog.txt')
            
            # 2. create necessary directories
            os.makedirs(output_patches_dir, exist_ok=True)
            os.makedirs(cache_project_dir, exist_ok=True) 
            os.makedirs(cache_issues_dir, exist_ok=True)
            
            # 3. initialize git repository if not already done
            
            # 3a. cloning repository
            if not os.path.exists(cache_repo_dir):
                # (!!) 更改为列表
                cmd_list = [
                    'git', 
                    'clone', 
                    '--bare', 
                    repository_url, 
                    cache_repo_dir
                ]
                success, _ = utils.exec_cmd(cmd_list, f"Cloning {project_name}")
                if not success:
                    print(f"Error: Failed to clone {repository_url}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Repository {project_name}.git already cached.")

            # 3b. downloading shared issues
            if not os.path.exists(cache_issues_file) or os.path.getsize(cache_issues_file) == 0:
                print(f"Shared issues for {issue_cache_key} not found. Downloading...")
                
                # (!!) 更改为列表
                cmd_dl_list = [
                    PYTHON_EXECUTABLE,
                    os.path.join(config.SCRIPT_DIR, 'download_issues.py'),
                    '-g', issue_tracker_name,
                    '-t', issue_tracker_project_id,
                    '-o', cache_issues_dir,
                    '-f', cache_issues_file
                ]
                success, _ = utils.exec_cmd(cmd_dl_list, f"Downloading issues for {issue_cache_key}")
                if not success:
                    print(f"Error: Failed to download issues for {issue_cache_key}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Shared issues for {issue_cache_key} already cached. Skipping download.")

            # 3c. getting git log
            if not os.path.exists(cache_gitlog_file):
                # (!!) 更改为列表, 移除 '>'
                cmd_log_list = [
                    'git',
                    f'--git-dir={cache_repo_dir}',
                    'log',
                    '--reverse',
                    '--', # (!!) 添加 '--' 以安全地处理子路径
                    sub_project_path
                ]
                # (!!) 使用 output_file 参数将 stdout 写入文件
                success, _ = utils.exec_cmd(
                    cmd_log_list, 
                    f"Collecting git log for {project_name}",
                    output_file=cache_gitlog_file # (!!) 关键: 传递输出文件
                )
                if not success:
                    print(f"Error: Failed to get git log for {project_name}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Git log for {project_name} already cached.")

            # 3d. cross-referencing git log with issues
            if not os.path.exists(output_csv_file):
                try:
                    with open(output_csv_file, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(config.ACTIVE_BUGS_HEADER)
                except IOError as e:
                    print(f"Error: Cannot write header to {output_csv_file}: {e}. Skipping.", file=sys.stderr)
                    continue

                print(f"Regex for bug-fixing commits: {bug_fix_regex!r}")

                try:
                    processed_regex = codecs.decode(bug_fix_regex, 'unicode_escape')
                except Exception:
                    print(f"  -> Warning: Could not unescape regex: {bug_fix_regex!r}. Using raw value.", file=sys.stderr)
                    processed_regex = bug_fix_regex
                
                # (!!) 更改为列表
                cmd_xref_list = [
                    PYTHON_EXECUTABLE,
                    os.path.join(config.SCRIPT_DIR, 'vcs_log_xref.py'),
                    '-e', processed_regex,
                    '-l', cache_gitlog_file,
                    '-r', cache_repo_dir,
                    '-i', cache_issues_file,
                    '-f', output_csv_file,
                    '-ru', repository_url,
                    '-pid', project_id
                ]
                success, _ = utils.exec_cmd(cmd_xref_list, f"Cross-referencing log for {project_id}")
                if not success:
                    print(f"Error: Failed to cross-reference log for {project_id}. Skipping.", file=sys.stderr)
                    continue
            else:
                print(f"Bugs file {output_csv_file} already exists.")

            # generating patches
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

                        # (!!) 更改为列表, 移除 '>'
                        cmd_diff_list = [
                            'git',
                            f'--git-dir={cache_repo_dir}',
                            'diff',
                            commit_buggy,
                            commit_fixed,
                            '--', # (!!) 添加 '--' 以安全地处理子路径
                            sub_project_path
                        ]

                        try:
                            # (!!) 直接调用 subprocess.run (不使用 utils.exec_cmd)
                            result = subprocess.run(
                                cmd_diff_list, 
                                shell=False, # (!!) 关键: 关闭 shell
                                check=True, 
                                capture_output=True, # (!!) 捕获 stdout
                                text=True,
                                encoding='utf-8',
                                errors='ignore'
                            )
                            
                            # (!!) 手动将 stdout 写入 patch 文件
                            with open(patch_file, 'w', encoding='utf-8') as f:
                                f.write(result.stdout)
                            
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