import os
import csv
import json
import re
import subprocess
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

# Configuration
API_KEY = os.getenv("SILICONCLOUD_API_KEY")
if not API_KEY:
    print("Warning: SILICONCLOUD_API_KEY is not set. API calls will fail.")

BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"  # Using a coder model if available, or instruct

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MINING_DIR = os.path.join(BASE_DIR, "bug-mining")
FRAMEWORK_DIR = os.path.join(BASE_DIR, "framework")
CACHE_DIR = os.path.join(BASE_DIR, "framework", "cache")
CLASSIFIED_DATA_PATH = os.path.join(BASE_DIR, "bug_classification", "classified_data_llm.jsonl")

SYSTEM_PROMPT_BASE = """You are an expert Software Design Engineer in Test (SDET).
Your goal is to generate a regression test case that reproduces a specific bug based on a Bug Report and the relevant Source Code.

**Instructions:**
1. Analyze the Bug Report to understand the failure scenario.
2. Analyze the provided Source Code (from the buggy version) to understand the context.
3. Write a standalone test case that attempts to trigger the bug.
4. The test should be designed to **FAIL** when run against the current (buggy) code, and **PASS** after the fix is applied.
5. Include all necessary imports.
6. Do NOT include explanations, markdown formatting, or code fences (```). Output ONLY the raw code.
"""

JAVA_SPECIFIC_INSTRUCTIONS = """
**Language Specific Guidelines (Java):**
1. Name the test class `ReproductionTest`.
2. **Target Safety**: You MUST invoke the *REAL* methods of the buggy class (the Class Under Test). **DO NOT** mock the class you are trying to test unless it is strictly necessary (e.g. Abstract Class).
3. **Handling Abstract Classes**: If the Class Under Test is abstract, use `Mockito.mock(Clazz.class, Mockito.CALLS_REAL_METHODS)` or create a minimal local subclass.
4. **Dependencies**: Use `Mockito.mock(Dependency.class)` for complex dependencies.
5. **Legacy Code/Complex Constructors**:
   - **AVOID Constructor Hell**: If a class constructor requires many arguments (>5) or many nulls, DO NOT try to call it directly.
   - **Strategy**: Use **Reflection** (`Field.setAccessible(true)`) to inject fields into an object instantiated via `Mockito` or a no-args constructor.
   - **Subclassing**: Create a local subclass to override complex logic if needed.
"""

PYTHON_SPECIFIC_INSTRUCTIONS = """
**Language Specific Guidelines (Python):**
1. Use `unittest` framework.
2. Use `unittest.mock` for dependencies.
3. Focus on reproducing the logic error described.
"""

def get_active_bugs(project_id):
    """Read active-bugs.csv for the project."""
    csv_path = os.path.join(MINING_DIR, project_id, "active-bugs.csv")
    bugs = {}
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return bugs
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bugs[row['bug.id']] = row
    return bugs

def get_bug_reports():
    """Read parsed bug reports from classified_data_llm.jsonl."""
    reports = {}
    if not os.path.exists(CLASSIFIED_DATA_PATH):
        print(f"Error: {CLASSIFIED_DATA_PATH} not found.")
        return reports
        
    with open(CLASSIFIED_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                # Key format: ProjectID-BugID to avoid collisions if multiple projects
                key = f"{data['project_id']}-{data['bug_id']}"
                reports[key] = data
            except json.JSONDecodeError:
                continue
    return reports

def ensure_repo(project_id, repo_url):
    """Ensure the git repository is cloned in cache."""
    project_cache_dir = os.path.join(CACHE_DIR, project_id)
    if not os.path.exists(project_cache_dir):
        os.makedirs(project_cache_dir)
    
    # Assuming repo name from URL
    repo_name = repo_url.split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    repo_path = os.path.join(project_cache_dir, f"{repo_name}.git")
    
    if not os.path.exists(repo_path):
        print(f"Cloning {repo_url} to {repo_path}...")
        # Clone bare to save space and time, or normal? 
        # framework/fast_bug_miner.py seems to imply full access, but let's do a mirror or full clone.
        # Given we need `git show`, a bare clone is sufficient and faster.
        subprocess.run(["git", "clone", "--bare", repo_url, repo_path], check=True)
    
    return repo_path

def parse_patch_info(patch_path):
    """
    Parse .patch file to identify modified files and their modified line ranges.
    Returns: dict { "path/to/file.java": [line_number_start, line_number_end, ...] }
    Actually, we just need a list of 'start' lines to center our context around.
    """
    files_info = {}
    current_file = None
    
    if not os.path.exists(patch_path):
        return files_info
        
    with open(patch_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('--- a/'):
                # Format: --- a/path/to/file.java
                path = line[6:].strip()
                if path != "/dev/null":
                    current_file = path
                    if current_file not in files_info:
                        files_info[current_file] = []
            elif line.startswith('@@') and current_file:
                # Format: @@ -172,7 +172,7 @@
                # We are interested in the first number pair (original file)
                # "-172,7" -> start at 172
                try:
                    match = re.search(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@', line)
                    if match:
                        start_line = int(match.group(1))
                        files_info[current_file].append(start_line)
                except:
                    pass
                    
    return files_info

def get_smart_source_code(repo_path, commit_hash, files_info, context_window=50):
    """
    Retrieve content of files, but only around the modified regions.
    Visual context: context_window lines before and after the modification.
    """
    context_output = ""
    
    for fp, change_points in files_info.items():
        try:
            # git show commit:path
            cmd = ["git", "--git-dir", repo_path, "show", f"{commit_hash}:{fp}"]
            result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
            
            if result.returncode != 0:
                print(f"Warning: Could not read {fp} from commit {commit_hash}")
                continue
                
            full_content_lines = result.stdout.splitlines()
            total_lines = len(full_content_lines)
            
            # Identify lines to keep
            lines_to_keep = set()
            
            # If no specific change points (e.g. binary file or weird patch), fallback to top
            if not change_points: 
                # keep first 200 lines as fallback
                for i in range(min(200, total_lines)):
                    lines_to_keep.add(i + 1)
            else:
                for start_line in change_points:
                    # 1-based index in patch -> 0-based index in list
                    # Range: [start - context, start + context]
                    min_l = max(1, start_line - context_window)
                    max_l = min(total_lines, start_line + context_window + 20) # +20 for the old length approximation
                    
                    for i in range(min_l, max_l + 1):
                        lines_to_keep.add(i)

            # Construct the partial file content
            context_output += f"\n\n// File: {fp}\n"
            sorted_lines = sorted(list(lines_to_keep))
            
            if not sorted_lines:
                continue

            last_line_idx = -1
            
            for line_num in sorted_lines:
                # Add ellipse if there is a gap
                if last_line_idx != -1 and line_num > last_line_idx + 1:
                    context_output += f"// ... existing code ... (lines {last_line_idx+1}-{line_num-1} omitted)\n"
                
                # line_num is 1-based
                if line_num <= total_lines:
                    context_output += full_content_lines[line_num - 1] + "\n"
                    last_line_idx = line_num
            
            if last_line_idx < total_lines:
                 context_output += "// ... existing code ... (end of file omitted)\n"

        except Exception as e:
            print(f"Error reading {fp}: {e}")
            
    return context_output

def generate_test_case(client, bug_report_text, source_code, language="Java"):
    """Call LLM to generate test case with validation for quality."""
    
    # Construct Dynamic Prompt
    system_prompt = SYSTEM_PROMPT_BASE
    if language == "Java":
        system_prompt += JAVA_SPECIFIC_INSTRUCTIONS
    elif language == "Python":
        system_prompt += PYTHON_SPECIFIC_INSTRUCTIONS
        
    base_prompt = f"Language: {language}\n\nBug Report:\n{bug_report_text}\n\nSource Code Context:\n{source_code}"
    current_prompt = base_prompt
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": current_prompt}
                ],
                temperature=0.2, # Lower temperature for code
            )
            content = completion.choices[0].message.content
            
            # Validation: Check for Constructor Hell (repeated nulls)
            null_pattern = "null, null, null, null"
            if language == "Java" and null_pattern in content:
                print(f"    [Warning] Detected 'Constructor Hell' (excessive nulls) in attempt {attempt+1}. Retrying with strict reflection instructions...")
                current_prompt = base_prompt + "\n\nFAILED ATTEMPT FEEDBACK: The previous code contained `new Class(null, null, null, null...)`. THIS IS FORBIDDEN. \nFor Abstract Classes: Use `Mockito.mock(Clazz.class, Mockito.CALLS_REAL_METHODS)` and then use Reflection to initialize internal fields (lists/maps) that are null.\nFor Concrete Classes: Use Reflection to instantiate or just partial mocks."
                continue
                
            return content
            
        except Exception as e:
            # If it's the last attempt or a non-recoverable API error
            if attempt == max_retries - 1:
                return f"Error generating test: {str(e)}"
            import time
            time.sleep(2 * (attempt + 1)) # Simple backoff
    
    return "Error: Failed to generate valid code after retries."

def process_single_bug(work_item):
    """Worker function."""
    project_id, bug_id, bug_info, report_data, repo_path, output_dir = work_item
    
    print(f"Generating test for {project_id}-{bug_id}...")
    
    # 1. content of bug report
    bug_text = report_data.get('llm_input_text', '')
    if not bug_text:
        return
    
    # 2. source code context
    patch_file = os.path.join(MINING_DIR, project_id, "patches", f"{bug_id}.src.patch")
    
    # New Smart Context Extraction
    files_info = parse_patch_info(patch_file)
    
    # Limit to top 3 files (by file order in patch)
    # Convert dict to list of items, take first 3, convert back to dict
    limited_files_info = dict(list(files_info.items())[:3])
    
    buggy_commit = bug_info['revision.id.buggy']
    
    # Use the new smart retriever
    source_context = get_smart_source_code(repo_path, buggy_commit, limited_files_info)
    
    if not source_context:
        print(f"Skipping {bug_id}: No source context found (maybe all new files?)")
        return

    # 3. Call LLM
    # Determine language from file extension of first modified file
    lang = "Java" # Default
    if limited_files_info:
        first_file = list(limited_files_info.keys())[0]
        ext = os.path.splitext(first_file)[1]
        if ext == '.py': lang = "Python"
        elif ext == '.js': lang = "JavaScript"
        elif ext == '.c': lang = "C"
    
    # Retry logic for 429/403 errors
    max_retries = 5
    generated_code = None
    
    import time
    import random
    
    for attempt in range(max_retries):
        generated_code = generate_test_case(CLIENT, bug_text, source_context, lang)
        
        # Check if the result looks like an error message
        if "Error generating test" in generated_code and ("rate" in generated_code.lower() or "limit" in generated_code.lower() or "429" in generated_code or "403" in generated_code):
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limit hit for {bug_id}, retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)
        else:
            break
            
    # 4. Save
    ext_map = {"Java": ".java", "Python": ".py", "JavaScript": ".js", "C": ".c"}
    out_ext = ext_map.get(lang, ".txt")
    
    out_file = os.path.join(output_dir, f"{bug_id}_test{out_ext}")
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(generated_code)
    
    print(f"Saved: {out_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate reproduction test cases using LLM.")
    parser.add_argument("--project", "-p", default="ActiveMQ", help="Project ID")
    parser.add_argument("--workers", "-n", type=int, default=1, help="Number of concurrent workers")
    parser.add_argument("--bugs", "-b", type=str, help="Comma-separated list of bug IDs to process (e.g. '16,17,23')")
    args = parser.parse_args()

    project_id = args.project
    
    # Load Data
    active_bugs = get_active_bugs(project_id)
    bug_reports = get_bug_reports()
    
    if not active_bugs:
        print(f"No active bugs found for {project_id}")
        return

    # Ensure Repo
    # We take the first bug's url to clone the repo
    first_bug = next(iter(active_bugs.values()))
    repo_url_full = first_bug.get('buggy_commit_url', '')
    # Hacky parsing of github url
    # Expecting: https://github.com/apache/activemq/tree/...
    if 'github.com' in repo_url_full:
        parts = repo_url_full.split('/')
        if len(parts) >= 5:
            base_repo_url = f"{parts[0]}//{parts[2]}/{parts[3]}/{parts[4]}.git"
        else:
            base_repo_url = "https://github.com/apache/activemq.git" # Fallback
    else:
        # Fallback for ActiveMQ if unsure
        base_repo_url = "https://github.com/apache/activemq.git"
        
    repo_path = ensure_repo(project_id, base_repo_url)
    
    # Output Directory
    output_dir = os.path.join(MINING_DIR, project_id, "generated_tests")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Prepare Tasks
    tasks = []
    
    # Decide which bugs to process
    if args.bugs:
        # User specified prompt list
        target_ids = [bid.strip() for bid in args.bugs.split(',')]
        # Filter for only those that exist
        sorted_ids = []
        for bid in target_ids:
            try:
                sorted_ids.append(int(bid))
            except ValueError:
                print(f"Warning: Invalid bug ID '{bid}'")
    else:
        # Default: all bugs in active-bugs.csv
        sorted_ids = sorted([int(bid) for bid in active_bugs.keys()])
    
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    global CLIENT
    CLIENT = client

    for bug_id_int in sorted_ids:
        bug_id = str(bug_id_int)
        
        # Check if we have a report for this bug if strict checking needed
        # Or just try anyway
        report_key = f"{project_id}-{bug_id}"
        if report_key not in bug_reports:
             # Try fallback if report not found in jsonl (maybe not classified yet)?
             # For now, stick to the rule
             pass

        # Even if report key missing, we might want to skip if bug not in csv
        if bug_id not in active_bugs:
            print(f"Skipping {bug_id} (not in active-bugs.csv)")
            continue

        # Get Report Data (using empty dict if missing to avoid crash, though logic above skips)
        report_data = bug_reports.get(report_key, {})
        bug_info = active_bugs[bug_id]
        
        tasks.append((project_id, bug_id, bug_info, report_data, repo_path, output_dir))
        
    print(f"Found {len(tasks)} bugs to process.")
    
    # processing
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        executor.map(process_single_bug, tasks)

if __name__ == "__main__":
    main()
