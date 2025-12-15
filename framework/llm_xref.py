# framework/llm_xref.py
#
# 策略:
# 1. 本地 Regex r'#(\d+)' 过滤出相关 commit。
# 2. 将 (commit_message, relevant_ids) 发送给 LLM。
# 3. LLM 被要求 *只* 返回一个 JSON 列表，
#    其中 *仅包含* 被 "FIX" 的 ID (例如: ["8699"])。
# 4. 如果没有修复，LLM 将返回一个空列表: []。

import argparse
import sys
import os
import re
import subprocess
import csv
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# LLM API Configuration

# 1. Load API Key from environment variable
api_key = os.getenv("SILICONCLOUD_API_KEY")
if not api_key:
    print("[Error]: Please set the 'SILICONCLOUD_API_KEY' environment variable", file=sys.stderr)
    
client = None
if api_key:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
    )

MAX_WORKERS = 5
REQUEST_DELAY = 0.1

# Token-Optimized LLM System Prompt
# Task: Given a list of IDs, *only* return the IDs that are fixed.
RELATIONSHIP_PROMPT_TEMPLATE_V3 = """
You are a Git commit analysis assistant.
Your task is to analyze a Git Commit Message and identify which IDs from a *specific list* are *explicitly fixed*.

Key Rules:
1.  You will be given a JSON input containing "relevant_ids" and a "commit_message".
2.  Your response MUST be a valid JSON object with a single key "fixed_ids".
3.  The value of "fixed_ids" MUST be a list containing *only* the IDs from "relevant_ids" that the commit message explicitly "Fixes", "Closes", or "Resolves".
4.  If *no* IDs are explicitly fixed, return an empty list: `{"fixed_ids": []}`.
5.  Do not include IDs that are only "Related" (e.g., "See #123").

Example 1 (User Input):
{
  "relevant_ids": ["8714", "8699"],
  "commit_message": "Refactor ActiveFilter (#8714)\nClose #8699"
}

Example 1 (Your Response):
{"fixed_ids": ["8699"]}

Example 2 (User Input):
{
  "relevant_ids": ["8700", "8699"],
  "commit_message": "Work on #8699 related to #8700"
}

Example 2 (Your Response):
{"fixed_ids": []}

Example 3 (User Input):
{
  "relevant_ids": ["9001", "9002"],
  "commit_message": "Fixes bug #9001 and resolves issue #9002"
}

Example 3 (Your Response):
{"fixed_ids": ["9001", "9002"]}
"""

# LLM call function
def get_fixed_bug_ids(commit_message, relevant_bug_ids_list):
    """
    Call Qwen API and return a list containing *only* the fixed IDs.
    relevant_bug_ids_list: e.g., ["8714", "8699"]
    """
    if not client:
        print("API client not initialized, skipping LLM call", file=sys.stderr)
        return [] # Return empty list to indicate failure/no-op

    # Construct input for prompt
    llm_input = {
        "relevant_ids": relevant_bug_ids_list,
        "commit_message": commit_message
    }
    
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {"role": "system", "content": RELATIONSHIP_PROMPT_TEMPLATE_V3},
                {"role": "user", "content": json.dumps(llm_input, ensure_ascii=False)}
            ],
            temperature=0,
            response_format={"type": "json_object"} # request JSON response
        )
        
        response_text = completion.choices[0].message.content.strip()

        print(f"[DEBUG] LLM Response Text:\n{response_text}", file=sys.stderr)
        parsed_data = json.loads(response_text)
                
        # Parse the JSON list returned by LLM
        # Expected: ["8699"] or []
        
        if isinstance(parsed_data, list):
            fixed_ids_list = parsed_data
        elif isinstance(parsed_data, dict):
            target_keys = ["fixed_ids", "fix_ids", "fixed", "fix"]
            
            for key in target_keys:
                if key in parsed_data and isinstance(parsed_data[key], list):
                    fixed_ids_list = parsed_data[key]
                    break
            
            if not fixed_ids_list:
                for val in parsed_data.values():
                    if isinstance(val, list):
                        fixed_ids_list = val
                        break
        else:
            print(f"LLM returned unexpected type: {type(parsed_data)}", file=sys.stderr)
            return []

        # Validate that all IDs in the list are indeed a subset of the original IDs
        validated_list = [
            item for item in fixed_ids_list 
            if isinstance(item, str) and item in relevant_bug_ids_list
        ]
        
        return validated_list

    except json.JSONDecodeError as e:
        print(f"LLM JSON parse error: {e}\nResponse: {response_text}", file=sys.stderr)
        return [] # Failure, return empty
    except Exception as e:
        print(f"LLM relationship judgment failed: {e}", file=sys.stderr)
        return [] # Failure, return empty
    
# Git helper functions
def get_git_parent(commit_hash, repo_dir):
    try:
        cmd_list = ['git', f'--git-dir={repo_dir}', 'rev-list', '--parents', '-n', '1', commit_hash]
        git_env = os.environ.copy()
        git_env['GIT_TERMINAL_PROMPT'] = '0'
        result = subprocess.run(
            cmd_list, shell=False, capture_output=True, text=True, check=True, 
            encoding='utf-8', errors='ignore', stdin=subprocess.DEVNULL, timeout=1800, env=git_env
        )
        parts = result.stdout.strip().split()
        if len(parts) > 1:
            if len(parts) > 2: return None
            return parts[1]
        else:
            return None
    except subprocess.CalledProcessError as e:
        print(f"Warning: Error getting parent for {commit_hash}: {e}", file=sys.stderr)
        return None

# Commit URL constructors
def construct_commit_url(repo_url, commit_hash):
    if not repo_url or not commit_hash: return "NA"
    base_url = repo_url.rstrip('.git')
    if 'github.com' in repo_url:
        return f"{base_url}/tree/{commit_hash}"
    return "NA"

# Compare URL constructor
def construct_compare_url(repo_url, buggy_hash, fixed_hash):
    if not repo_url or not buggy_hash or not fixed_hash: return "NA"
    base_url = repo_url.rstrip('.git')
    if 'github.com' in repo_url:
        return f"{base_url}/compare/{buggy_hash}...{fixed_hash}"
    return "NA"

# Load known bugs from issues file
def load_known_bugs_map(issues_file_path):
    known_bugs_map = {}
    try:
        with open(issues_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    try:
                        key, val = line.split(',', 1)
                        known_bugs_map[key.strip()] = val.strip()
                    except ValueError:
                        pass
    except FileNotFoundError:
        print(f"[Error]: Unable to read issues file: {issues_file_path}", file=sys.stderr)
        return None
    return known_bugs_map

def main():
    parser = argparse.ArgumentParser(description="Cross-reference VCS log with issue tracker data using LLM.")
    parser.add_argument('-l', dest='log_file', required=True, help="Path to the commit log file (from git log)")
    parser.add_argument('-r', dest='repo_dir', required=True, help="Path to the .git repository directory")
    parser.add_argument('-i', dest='issues_file', required=True, help="Path to the issues.txt file (id,url)")
    parser.add_argument('-f', dest='output_file', required=True, help="Output file for active-bugs.csv (will append)")
    parser.add_argument('-ru', dest='repo_url', required=True, help="Public repository URL (e.g., https://github.com/org/repo.git)")
    parser.add_argument('-pid', dest='project_id', required=True, help="Project ID (e.g., 'core' or '.')")

    args = parser.parse_args()

    # 1. Load known Bug IDs
    known_bugs_map = load_known_bugs_map(args.issues_file)
    if not known_bugs_map:
        print(f"Error: Could not read or issues file is empty: {args.issues_file}", file=sys.stderr)
        sys.exit(1)
    
    known_bug_ids_set = set(known_bugs_map.keys())
    print(f"Loaded {len(known_bug_ids_set)} known bug IDs for pre-filtering.")

    # 2. First filter: Define a loose local pre-filtering Regex
    LINKING_REGEX = re.compile(r'#(\d+)')

    # 3. Stage One: Scan GitLog
    print("Pass 1: Scanning git log for relevant commits...")
    tasks_to_process = [] # Store (commit_hash, commit_message, relevant_bug_ids_list)
    current_commit = None
    commit_message_lines = []

    try:
        with open(args.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('commit '):
                    if current_commit and commit_message_lines:
                        commit_message = "\n".join(commit_message_lines)
                        
                        mentioned_ids = set(LINKING_REGEX.findall(commit_message))
                        relevant_bug_ids_set = mentioned_ids.intersection(known_bug_ids_set)
                        
                        if relevant_bug_ids_set:
                            tasks_to_process.append((current_commit, commit_message, list(relevant_bug_ids_set)))
                            
                    current_commit = line.split()[1].strip()
                    commit_message_lines = []
                
                elif current_commit and line.startswith('    '):
                    commit_message_lines.append(line.strip())

        # Handle the last commit
        if current_commit and commit_message_lines:
            commit_message = "\n".join(commit_message_lines)
            mentioned_ids = set(LINKING_REGEX.findall(commit_message))
            relevant_bug_ids_set = mentioned_ids.intersection(known_bug_ids_set)
            if relevant_bug_ids_set:
                tasks_to_process.append((current_commit, commit_message, list(relevant_bug_ids_set)))

    except IOError as e:
        print(f"Error reading log file {args.log_file}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Pass 1 complete. Found {len(tasks_to_process)} commits for LLM analysis.")

    if not tasks_to_process or not client:
        if not client: print("Error: DASHSCOPE_API_KEY not set. Cannot proceed.", file=sys.stderr)
        else: print("No relevant commits found. Exiting.")
        sys.exit(0)

    # 4. Second filter: LLM Analysis
    print(f"Pass 2: Running LLM analysis (Max Workers: {MAX_WORKERS})...")
    results_to_write = [] # Store (parent, commit, issue_id, issue_url)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {}
        
        for (commit_hash, message, bug_ids_list) in tasks_to_process:
            future = executor.submit(get_fixed_bug_ids, message, bug_ids_list)
            future_to_task[future] = commit_hash
            
        for i, future in enumerate(as_completed(future_to_task)):
            # A list only containing fixed IDs
            # e.g., ["8699"] or []
            fixed_ids = future.result() 
            commit_hash = future_to_task[future]
            
            if (i + 1) % 50 == 0:
                print(f"  -> LLM processed {i + 1}/{len(tasks_to_process)} commits...")

            if fixed_ids: # Only process if the list is not empty
                parent = get_git_parent(commit_hash, args.repo_dir)
                if parent:
                    # Iterate over the "FIX" list confirmed by LLM
                    for bug_id in fixed_ids:
                        issue_url = known_bugs_map.get(bug_id, 'NA')
                        results_to_write.append({
                            'p': parent,
                            'c': commit_hash,
                            'issue_id': bug_id,
                            'issue_url': issue_url
                        })
            
            time.sleep(REQUEST_DELAY)

    print(f"Pass 2 complete. Found {len(results_to_write)} validated bug-fix entries.")

    # 5. Write to CSV
    print(f"Pass 3: Writing results to {args.output_file}...")
    try:
        file_is_empty = (not os.path.exists(args.output_file)) or (os.path.getsize(args.output_file) < 10)
        with open(args.output_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            if file_is_empty:
                try:
                    import config
                    writer.writerow(config.ACTIVE_BUGS_HEADER)
                except (ImportError, AttributeError):
                    # Fallback header
                    writer.writerow(["bug.id", "project_id", "revision.id.buggy", "revision.id.fixed", "report.id", "report.url", "buggy_commit_url", "fixed_commit_url", "compare_url"])
                
            vid_start = 1
            if not file_is_empty:
                try:
                    with open(args.output_file, 'r', encoding='utf-8') as read_f:
                        reader = csv.reader(read_f)
                        next(reader) # skip header
                        last_line = None
                        for line in reader: last_line = line
                        if last_line:
                            vid_start = int(last_line[0]) + 1
                except Exception:
                     pass

            for i, row in enumerate(results_to_write):
                vid = vid_start + i
                project_id = args.project_id
                buggy_hash = row['p']
                fixed_hash = row['c']
                issue_id = row['issue_id']
                issue_url = row['issue_url']
                
                buggy_url = construct_commit_url(args.repo_url, buggy_hash)
                fixed_url = construct_commit_url(args.repo_url, fixed_hash)
                compare_url = construct_compare_url(args.repo_url, buggy_hash, fixed_hash)
                
                writer.writerow([
                    vid, project_id, buggy_hash, fixed_hash, issue_id, issue_url,
                    buggy_url, fixed_url, compare_url
                ])
                
    except IOError as e:
        print(f"Error writing to output file {args.output_file}: {e}", file=sys.stderr)
        sys.exit(1)

    print("LLM cross-referencing complete.")

if __name__ == "__main__":
    main()