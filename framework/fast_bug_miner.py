#!/usr/bin/env python3
# framework/fast_bug_miner.py

import os
import sys  
import subprocess
import csv
import utils
import config
import codecs
import shutil

# Tee class for duplicating stderr output
class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

def process_project(project_id, project_name, repository_url, issue_tracker_name, issue_tracker_project_id, bug_fix_regex, sub_project_path):
    """
    处理单个项目的完整挖掘流程。
    如果成功，返回 True；如果任何关键步骤失败，返回 False。
    """
    PYTHON_EXECUTABLE = sys.executable

    print("############################################################")
    print(f"Processing project: {project_id} ({project_name})")
    print("############################################################")

    # 1. define paths
    issue_cache_key = f"{issue_tracker_name}_{issue_tracker_project_id}"
    cache_issues_dir = os.path.join(config.SHARED_ISSUES_DIR, issue_cache_key)
    cache_issues_file = os.path.join(cache_issues_dir, 'issues.txt')

    output_project_dir = os.path.join(config.OUTPUT_DIR, project_id)
    output_patches_dir = os.path.join(output_project_dir, 'patches')
    output_reports_dir = os.path.join(output_project_dir, 'reports') 
    output_csv_file = os.path.join(output_project_dir, 'active-bugs.csv')
    
    cache_project_dir = os.path.join(config.CACHE_DIR, project_id)
    cache_repo_dir = os.path.join(cache_project_dir, f"{project_name}.git")
    cache_gitlog_file = os.path.join(cache_project_dir, 'gitlog.txt')
    
    # 2. create necessary directories
    os.makedirs(output_patches_dir, exist_ok=True)
    os.makedirs(output_reports_dir, exist_ok=True) 
    os.makedirs(cache_project_dir, exist_ok=True) 
    os.makedirs(cache_issues_dir, exist_ok=True)
    
    # 3. initialize git repository if not already done
    
    # 3a. cloning repository
    if not os.path.exists(cache_repo_dir):
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
            return False # 
    else:
        print(f"Repository {project_name}.git already cached.")

    # 3b. downloading shared issues
    if not os.path.exists(cache_issues_file) or os.path.getsize(cache_issues_file) == 0:
        print(f"Shared issues for {issue_cache_key} not found. Downloading...")
        
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
            return False
    else:
        print(f"Shared issues for {issue_cache_key} already cached. Skipping download.")

    # 3c. getting git log
    if not os.path.exists(cache_gitlog_file):
        cmd_log_list = [
            'git',
            f'--git-dir={cache_repo_dir}',
            'log',
            '--reverse',
            '--', 
            sub_project_path
        ]
        success, _ = utils.exec_cmd(
            cmd_log_list, 
            f"Collecting git log for {project_name}",
            output_file=cache_gitlog_file 
        )
        if not success:
            print(f"Error: Failed to get git log for {project_name}. Skipping.", file=sys.stderr)
            return False
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
            return False

        print(f"Regex for bug-fixing commits: {bug_fix_regex!r}")

        try:
            processed_regex = codecs.decode(bug_fix_regex, 'unicode_escape')
        except Exception:
            print(f"  -> Warning: Could not unescape regex: {bug_fix_regex!r}. Using raw value.", file=sys.stderr)
            processed_regex = bug_fix_regex
        
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
            return False
    else:
        print(f"Bugs file {output_csv_file} already exists.")

    # 4. generating patches AND downloading reports
    print(f"Generating patches and downloading reports from {output_csv_file}...")
    
    try:
        with open(output_csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            try:
                header = next(reader)
                idx_bug_id = header.index(config.BUGS_CSV_BUGID) 
                idx_commit_buggy = header.index(config.BUGS_CSV_COMMIT_BUGGY)
                idx_commit_fixed = header.index(config.BUGS_CSV_COMMIT_FIXED)
                idx_report_url = header.index(config.BUGS_CSV_ISSUE_URL) 
                
            except (StopIteration, ValueError) as e:
                print(f"Error: Invalid or empty CSV file: {output_csv_file}. {e}", file=sys.stderr)
                return False
                
            for row in reader:
                try:
                    bug_id = row[idx_bug_id]
                    commit_buggy = row[idx_commit_buggy]
                    commit_fixed = row[idx_commit_fixed]
                    report_url = row[idx_report_url] 
                except IndexError:
                    continue 

                # --- 4a. Download Report (NEW LOGIC) ---
                if not report_url or report_url == "NA":
                    print(f"  -> Skipping report for bug {bug_id} (missing URL).")
                else:
                    ext = '.json' 
                    if 'issues.apache.org/jira' in report_url or 'bz.apache.org/bugzilla' in report_url:
                        ext = '.xml' 
                    
                    report_file = os.path.join(output_reports_dir, f"{bug_id}{ext}")
                    
                    if os.path.exists(report_file):
                        pass 
                    else:
                        print(f"\n  -> Downloading report for bug {bug_id}...")
                        utils.download_report_data(report_url, report_file)


                # --- 4b. Generate Patch (Existing logic) ---
                if not commit_buggy or not commit_fixed:
                    print(f"  -> Skipping patch for bug {bug_id} (missing commit hash).")
                    continue

                patch_file = os.path.join(output_patches_dir, f"{bug_id}.src.patch")
                
                if os.path.exists(patch_file):
                    continue 

                print(f"  -> Generating patch for bug {bug_id} ({commit_buggy} -> {commit_fixed})")

                cmd_diff_list = [
                    'git',
                    f'--git-dir={cache_repo_dir}',
                    'diff',
                    commit_buggy,
                    commit_fixed,
                    '--', 
                    sub_project_path
                ]

                try:
                    result = subprocess.run(
                        cmd_diff_list, 
                        shell=False, 
                        check=True, 
                        capture_output=True, 
                        text=True,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    
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
        return False

    print(f"Finished processing project {project_id}.\n")
    return True

def main():
    
    # define error log file
    ERROR_LOG_FILE = 'error.txt'
    
    # save original stderr
    original_stderr = sys.stderr
    
    try:
        # open error log file and redirect stderr
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as error_log:
            sys.stderr = Tee(original_stderr, error_log)
            
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

                    # define project output directory
                    output_project_dir = os.path.join(config.OUTPUT_DIR, project_id)
                    
                    success = process_project(
                        project_id, 
                        project_name, 
                        repository_url, 
                        issue_tracker_name, 
                        issue_tracker_project_id, 
                        bug_fix_regex, 
                        sub_project_path
                    )
                    
                    # check success and clean up on failure
                    if not success:
                        print(f"--- Project {project_id} FAILED. Cleaning up output directory. ---", file=sys.stderr)
                        if os.path.exists(output_project_dir):
                            try:
                                shutil.rmtree(output_project_dir)
                                print(f"  -> Successfully removed {output_project_dir}", file=sys.stderr)
                            except OSError as e:
                                print(f"  -> Error: Could not remove directory {output_project_dir}: {e}", file=sys.stderr)
                        else:
                            print(f"  -> Directory {output_project_dir} was not created. No cleanup needed.", file=sys.stderr)
                        print("------------------------------------------------------------\n", file=sys.stderr)


            print("All projects processed.")
            
    except Exception as e:
        print(f"CRITICAL ERROR: An unexpected exception occurred: {e}", file=sys.stderr)
        sys.stderr = original_stderr
        print(f"CRITICAL ERROR: An unexpected exception occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        sys.stderr = original_stderr

if __name__ == "__main__":
    main()