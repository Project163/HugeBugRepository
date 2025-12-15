#!/usr/bin/env python3
# framework/clean_project_data.py

import os
import sys
import shutil
import argparse
try:
    import config
except ImportError:
    print("[Error]: Unable to import config.py. Please ensure this script is in the same directory as config.py.", file=sys.stderr)
    sys.exit(1)

def safe_remove_directory(path_to_remove):
    """
    安全地递归删除一个目录。
    如果目录不存在，则跳过。
    """
    if not os.path.exists(path_to_remove):
        print(f"  -> Skipping (does not exist): {path_to_remove}")
        return
    
    if not os.path.isdir(path_to_remove):
        print(f"  -> Skipping (not a directory): {path_to_remove}")
        return

    try:
        shutil.rmtree(path_to_remove)
        print(f"  -> [Success] Removed: {path_to_remove}")
    except OSError as e:
        print(f"  -> [Failed] Unable to remove {path_to_remove}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Clean data pollution for specific projects in bug-mining, cache, and shared_issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Allow users to specify the input file, defaulting to framework/delete.txt
    default_input = os.path.join(config.SCRIPT_DIR, 'delete.txt')
    parser.add_argument(
        '-i', '--input', 
        dest='input_file', 
        default=default_input,
        help=f"Specify the input file containing the list of projects (default: {default_input})"
    )

    args = parser.parse_args()
    input_file = args.input_file

    if not os.path.exists(input_file):
        print(f"[Error]: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"--- Starting to clean project caches using {input_file} ---")

    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                parts = line.split('\t')
                
                # Check if the line format is correct (at least 5 columns)
                if len(parts) < 5:
                    print(f"\n[Warning]: Skipping malformed line {line_num}: {line}", file=sys.stderr)
                    continue

                # 1. Get project_id (first column)
                project_id = parts[0]
                
                # 2. Get issue_tracker_name (fourth column)
                issue_tracker_name = parts[3]
                
                # 3. Get issue_tracker_project_id (fifth column)
                issue_tracker_project_id = parts[4]

                print(f"\nCleaning project: {project_id}")

                # --- Construct target paths ---

                # Target 1: bug-mining/<project_id>
                #
                bug_mining_path = os.path.join(config.OUTPUT_DIR, project_id)

                # Target 2: cache/<project_id>
                #
                cache_path = os.path.join(config.CACHE_DIR, project_id)

                # Target 3: cache/shared_issues/<issue_cache_key>
                #
                issue_cache_key = f"{issue_tracker_name}_{issue_tracker_project_id}"
                shared_issues_path = os.path.join(config.SHARED_ISSUES_DIR, issue_cache_key)
                
                # --- Execute safe removal ---
                safe_remove_directory(bug_mining_path)
                safe_remove_directory(cache_path)
                safe_remove_directory(shared_issues_path)

            except IndexError as e:
                print(f"\n[Error]: Skipping malformed line {line_num} (column index out of range): {e}", file=sys.stderr)
            except Exception as e:
                print(f"\n[Error]: Unexpected error while processing line {line_num}: {e}", file=sys.stderr)

    print("\n--- Cleaning completed ---")

if __name__ == "__main__":
    main()