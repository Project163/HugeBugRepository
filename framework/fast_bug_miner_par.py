#!/usr/bin/env python3
# framework/fast_bug_miner.py

import os
import sys
import subprocess
import csv
import utils
import config
import multiprocessing 
import contextlib 

# Not suit for Windows due to multiprocessing and redirection issues.

def process_project(line):
    """
    处理单个项目（此函数将在并行工作进程中执行）。
    所有 stdout/stderr 输出将被重定向到项目目录下的 mining.log。
    函数将返回一个元组: (project_id, "STATUS", "Reason")
    """
    
    # --- 1. 解析 Project ID 和设置日志文件 ---
    try:
        parts_prelim = line.split('\t') 
        project_id = parts_prelim[0] 
    except IndexError:
        msg = f"Skipping malformed line (cannot parse project_id): {line}"
        print(msg, file=sys.stderr) 
        return (None, "SKIPPED", "Malformed line")

    # 定义日志文件路径
    output_project_dir = os.path.join(config.OUTPUT_DIR, project_id)
    os.makedirs(output_project_dir, exist_ok=True) 
    log_file_path = os.path.join(output_project_dir, 'mining.log')

    # --- 2. 开始重定向并执行主要逻辑 ---
    try:
        with open(log_file_path, 'w', encoding='utf-8') as log_f:
            with contextlib.redirect_stdout(log_f), contextlib.redirect_stderr(log_f):
                
                # 所有的 print 都会进入 log_file_path ---
                try:
                    parts = line.split('\t') 
                    project_id = parts[0] # 
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
                    return (project_id, "FAILED", "Malformed line parts")

                PYTHON_EXECUTABLE = sys.executable

                print("############################################################")
                print(f"Processing project: {project_id} ({project_name})")
                print(f"Full log redirect to: {log_file_path}")
                print("############################################################")

                # 1. define paths
                issue_cache_key = f"{issue_tracker_name}_{issue_tracker_project_id}"
                cache_issues_dir = os.path.join(config.SHARED_ISSUES_DIR, issue_cache_key)
                cache_issues_file = os.path.join(cache_issues_dir, 'issues.txt')

                output_patches_dir = os.path.join(output_project_dir, 'patches')
                output_csv_file = os.path.join(output_project_dir, 'active-bugs.csv')
                
                cache_project_dir = os.path.join(config.CACHE_DIR, project_id)
                cache_repo_dir = os.path.join(cache_project_dir, f"{project_name}.git")
                cache_gitlog_file = os.path.join(cache_project_dir, 'gitlog.txt')
                
                # 2. create necessary directories
                os.makedirs(output_patches_dir, exist_ok=True)
                os.makedirs(cache_project_dir, exist_ok=True) 
                os.makedirs(cache_issues_dir, exist_ok=True)
                
                # 3. initialize git repository
                
                # 3a. cloning repository
                if not os.path.exists(cache_repo_dir):
                    cmd = f"git clone --bare \"{repository_url}\" \"{cache_repo_dir}\""
                    success, _ = utils.exec_cmd(cmd, f"({project_id}) Cloning {project_name}")
                    if not success:
                        print(f"Error: Failed to clone {repository_url}. Skipping.", file=sys.stderr)
                        return (project_id, "FAILED", "Clone failed") # (!!) 返回状态
                else:
                    print(f"({project_id}) Repository {project_name}.git already cached.")
                
                # TODO shared_issues下载竞态条件可能性？添加锁？（download_issues.py）
                # 3b. downloading shared issues
                if not os.path.exists(cache_issues_file) or os.path.getsize(cache_issues_file) == 0:
                    print(f"({project_id}) Shared issues for {issue_cache_key} not found. Downloading...")
                    
                    cmd_dl = (
                        f"\"{PYTHON_EXECUTABLE}\" {os.path.join(config.SCRIPT_DIR, 'download_issues.py')} "
                        f"-g \"{issue_tracker_name}\" -t \"{issue_tracker_project_id}\" "
                        f"-o \"{cache_issues_dir}\" -f \"{cache_issues_file}\""
                    )
                    success, _ = utils.exec_cmd(cmd_dl, f"({project_id}) Downloading issues for {issue_cache_key}")
                    if not success:
                        print(f"Error: Failed to download issues for {issue_cache_key}. Skipping.", file=sys.stderr)
                        return (project_id, "FAILED", "Issue download failed")
                else:
                    print(f"({project_id}) Shared issues for {issue_cache_key} already cached. Skipping download.")

                # 3c. getting git log
                if not os.path.exists(cache_gitlog_file):
                    cmd_log = f"git --git-dir=\"{cache_repo_dir}\" log --reverse -- \"{sub_project_path}\" > \"{cache_gitlog_file}\""
                    success, _ = utils.exec_cmd(cmd_log, f"({project_id}) Collecting git log for {project_name}")
                    if not success:
                        print(f"Error: Failed to get git log for {project_name}. Skipping.", file=sys.stderr)
                        return (project_id, "FAILED", "Git log failed")
                else:
                    print(f"({project_id}) Git log for {project_name} already cached.")

                # 3d. cross-referencing git log with issues
                if not os.path.exists(output_csv_file):
                    try:
                        with open(output_csv_file, 'w', encoding='utf-8', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(config.ACTIVE_BUGS_HEADER)
                    except IOError as e:
                        print(f"Error: Cannot write header to {output_csv_file}: {e}. Skipping.", file=sys.stderr)
                        return (project_id, "FAILED", "CSV header write failed")

                    print(f"({project_id}) Regex for bug-fixing commits: {bug_fix_regex!r}")

                    cmd_xref = (
                        f"\"{PYTHON_EXECUTABLE}\" {os.path.join(config.SCRIPT_DIR, 'vcs_log_xref.py')} "
                        f"-e \"{bug_fix_regex}\" -l \"{cache_gitlog_file}\" "
                        f"-r \"{cache_repo_dir}\" "
                        f"-i \"{cache_issues_file}\" "
                        f"-f \"{output_csv_file}\" "
                        f"-ru \"{repository_url}\" "
                        f"-pid \"{project_id}\""
                    )
                    success, _ = utils.exec_cmd(cmd_xref, f"({project_id}) Cross-referencing log for {project_id}")
                    if not success:
                        print(f"Error: Failed to cross-reference log for {project_id}. Skipping.", file=sys.stderr)
                        return (project_id, "FAILED", "XRef failed")
                else:
                    print(f"({project_id}) Bugs file {output_csv_file} already exists.")

                # generating patches
                print(f"({project_id}) Generating patches from {output_csv_file}...")
                
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
                            return (project_id, "FAILED", "Invalid CSV file")
                            
                        for row in reader:
                            try:
                                bug_id = row[idx_bug_id]
                                commit_buggy = row[idx_commit_buggy]
                                commit_fixed = row[idx_commit_fixed]
                            except IndexError:
                                continue 

                            if not commit_buggy or not commit_fixed:
                                print(f"  -> ({project_id}) Skipping bug {bug_id} (missing commit hash).")
                                continue

                            patch_file = os.path.join(output_patches_dir, f"{bug_id}.src.patch")
                            
                            if os.path.exists(patch_file):
                                continue 

                            print(f"  -> ({project_id}) Generating patch for bug {bug_id} ({commit_buggy} -> {commit_fixed})")

                            cmd_diff = f"git --git-dir=\"{cache_repo_dir}\" diff \"{commit_buggy}\" \"{commit_fixed}\" -- \"{sub_project_path}\" > \"{patch_file}\""

                            try:
                                subprocess.run(cmd_diff, shell=True, check=True, capture_output=True)
                                
                                if os.path.getsize(patch_file) == 0:
                                    print(f"  -> ({project_id}) Warning: Generated patch for bug {bug_id} is empty.", file=sys.stderr)
                            except subprocess.CalledProcessError as e:
                                print(f"  -> ({project_id}) Error generating patch for bug {bug_id}.", file=sys.stderr)
                                if os.path.exists(patch_file):
                                    os.remove(patch_file) 

                except IOError as e:
                    print(f"Error reading {output_csv_file}: {e}", file=sys.stderr)
                    return (project_id, "FAILED", "CSV read failed")

                print(f"Finished processing project {project_id}.\n")
                
                # (!!) 成功返回
                return (project_id, "SUCCESS", None)

    except Exception as e:
        # 捕获意外错误 (例如日志文件打开失败)
        # 尝试最后一次打印到主控制台
        error_msg = f"CRITICAL ERROR processing {project_id}: {e}"
        print(error_msg, file=sys.stderr)
        
        # 尝试写入日志文件
        try:
            with open(log_file_path, 'a') as f_err:
                f_err.write(f"\n--- CRITICAL ERROR ---\n{error_msg}\n{traceback.format_exc()}\n")
        except:
            pass
            
        return (project_id, "FAILED", f"Critical Error: {e}")


def main():
    input_file = os.path.join(config.SCRIPT_DIR, 'test.txt') 
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        sys.exit(1)

    # 1. 读取所有待处理的项目行
    project_lines = []
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            project_lines.append(line)

    if not project_lines:
        print("No projects found in input file.")
        sys.exit(0)

    # 2. 设定并行工作进程数量
    num_workers = os.cpu_count() or 4 
    print(f"Starting parallel processing with {num_workers} workers for {len(project_lines)} projects...")
    print("Detailed logs will be saved to 'bug-mining/<project_id>/mining.log'")
    print("-" * 60)

    # 3. 使用 multiprocessing.Pool 来并发执行
    try:
        with multiprocessing.Pool(processes=num_workers) as pool:

            results = pool.imap_unordered(process_project, project_lines)

            success_count = 0
            fail_count = 0
            skip_count = 0
        
            for (project_id, status, reason) in results:
                if status == "SUCCESS":
                    print(f"[SUCCESS] {project_id}")
                    success_count += 1
                elif status == "FAILED":
                    # 失败信息
                    print(f"[FAILED]  {project_id:<15} (Reason: {reason})")
                    fail_count += 1
                elif status == "SKIPPED":
                    # 跳过信息
                    print(f"[SKIPPED] Malformed line (Reason: {reason})")
                    skip_count += 1

        # 打印最终摘要
        print("-" * 60)
        print("\n--- Summary ---")
        print(f"  Successful: {success_count}")
        print(f"  Failed:     {fail_count}")
        print(f"  Skipped:    {skip_count}")
        print(f"  Total:      {len(project_lines)}")

    except KeyboardInterrupt:
        print("\nCaught KeyboardInterrupt! Terminating workers.", file=sys.stderr)
        pool.terminate()
        pool.join()
        sys.exit(1)
    
    print("\nAll projects processed.")

if __name__ == "__main__":
    main()