import os
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# 1. Configuration
# API Key
api_key = os.getenv("SILICONCLOUD_API_KEY")
if not api_key:
    raise ValueError("Please set the 'SILICONCLOUD_API_KEY' environment variable")

# Initialize OpenAI client pointing to Qwen's compatible API
client = OpenAI(
    api_key=api_key,
    base_url="https://api.siliconflow.cn/v1",
)

# Labels to classify
DEFAULT_LABELS = [
    "Function :: Access Control (CWE-284)",
    "Function :: Logic Mismatch (CWE-573)",

    "Algorithm :: Calculation Error (CWE-682)",
    "Algorithm :: Resource/Memory Leak (CWE-400)",

    "Checking :: Input Validation (CWE-20)",
    "Checking :: Boundary/Buffer (CWE-119)",
    "Checking :: Missing Check (CWE-754)",

    "Assignment :: Initialization (CWE-665)",
    "Assignment :: Type/Cast Error (CWE-704)",

    "Interface :: API Misuse (CWE-628)",
    "Interface :: Data Encoding (CWE-707)",

    "Timing :: Race Condition (CWE-362)",
    "Timing :: Resource Lifecycle (CWE-664)",

    "Build :: Configuration (CWE-16)",
    "Build :: Dependency (CWE-1357)",

    "Documentation :: Wrong Comments (CWE-1116)",

    "Other"
]

# DEFAULT_LABELS = [
#     # 1. Assignment (赋值/初始化)
#     "Assignment/Initialization", # 变量/对象未初始化或初始值错误
#     "Assignment/Value",          # 简单的赋值错误（非算法计算）

#     # 2. Checking (检查/校验)
#     "Checking/Validation",       # 数据合法性检查缺失或错误 (Input, Null Check)
#     "Checking/LoopCondition",    # 循环边界或条件分支逻辑错误 (If/While)

#     # 3. Algorithm (算法/逻辑)
#     "Algorithm/Calculation",     # 数学公式、位运算或复杂逻辑推导错误
#     "Algorithm/Efficiency",      # 算法复杂度过高、性能问题

#     # 4. Interface (接口/交互)
#     "Interface/Parameter",       # 函数调用参数错误 (类型、顺序、缺失)
#     "Interface/Protocol",        # 系统间通信协议、I/O 格式或 API 契约错误

#     # 5. Timing/Serialization (时序/序列化)
#     "Timing/RaceCondition",      # 竞态条件、线程冲突
#     "Timing/Resource",           # 锁机制、死锁或资源生命周期管理

#     # 6. Build/Package/Merge (构建/打包)
#     "Build/Configuration",       # 配置文件、环境变量错误
#     "Build/Dependency",          # 依赖库版本冲突或缺失

#     # 7. Documentation (文档)
#     "Documentation/Content",     # 文档内容错误或误导
#     "Documentation/Missing",     # 缺少必要的文档或注释

#     # 8. Function (功能/宏观)
#     "Function/LogicFlow",        # 宏观业务流程错误 (无法归类为单行错误)
    
#     "Other"
# ]

LABELS_STRING = "\n".join(DEFAULT_LABELS)

# Input and output files
INPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'parsed_data.jsonl'))
OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'classified_data_llm.jsonl'))

# Concurrency settings
MAX_WORKERS = 10  # Adjust according to API limits
REQUEST_DELAY = 0.1

# 2. System Prompt
SYSTEM_PROMPT = f"""
You are an expert software engineer specializing in bug triaging and classification.
Your task is to classify bug reports into one of the following categories based on their content:
{LABELS_STRING}
Instructions:
1. Analyze the 'Title' and 'Description' of the bug report.
2. Determine the *root cause* or the *nature* of the defect, not just the symptom.
3. Select EXACTLY ONE category from the list above.
4. If the bug is a generic crash/freeze without a clear cause, look for clues about "Checking" (null pointer) or "Resource" (memory).
5. Output ONLY the category name exactly as listed. Do not add explanations.

Examples:
Bug Report: "User can access admin panel without logging in."
Classification: Function :: Access Control (CWE-284)

Bug Report: "The app crashes with NullPointerException when username is empty."
Classification: Checking :: Missing Check (CWE-754)

Bug Report: "Sorting a large list causes the UI to freeze forever."
Classification: Algorithm :: Complexity/Resource (CWE-400)

Bug Report: "Typo in the help message."
Classification: Documentation :: Wrong Comments (CWE-1116)
"""

# SYSTEM_PROMPT = f"""
# You are an expert in IBM Orthogonal Defect Classification (ODC).
# Your task is to classify software defects based on the *nature of the fix* and the *root cause*.

# The taxonomy is STRICTLY hierarchical (Level 1 / Level 2):
# {LABELS_STRING}

# Classification Rules:
# 1. **Assignment**: The fix involves changing a value assignment or initialization.
#    - Use 'Initialization' if a variable was used before being set.
#    - Use 'Value' for simple wrong scalars/strings.
# 2. **Checking**: The fix involves validation logic.
#    - Use 'Validation' for missing null checks, input sanitization, or boundary guards.
#    - Use 'LoopCondition' for errors in 'if', 'while', or 'for' logic expressions.
# 3. **Algorithm**: The fix involves transforming data or complex calculations.
#    - Use 'Efficiency' for performance optimizations.
# 4. **Interface**: The fix involves function calls or external communication.
#    - Use 'Parameter' for wrong arguments passed to a function.
#    - Use 'Protocol' for API mismatches or file format errors.
# 5. **Timing**: The fix involves concurrency or shared resources.
# 6. **Build**: The fix is in config files, makefiles, or dependencies (not source code).

# Instructions:
# - Analyze the Bug Report carefully.
# - Think: "What type of code needs to be written to fix this?"
# - Output ONLY the exact label from the list above.

# Example 1:
# Bug: "Application crashes because 'user_id' can be null."
# Classification: Checking/Validation

# Example 2:
# Bug: "The loop runs one extra time causing index out of bounds."
# Classification: Checking/LoopCondition

# Example 3:
# Bug: "Sorting takes too long on large arrays."
# Classification: Algorithm/Efficiency
# """

# 3. API Call Function
def get_bug_classification(bug_text):
    """
    Call API to classify a single bug text.
    """
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen3-8B",  
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": bug_text}
            ],
            temperature=0,
        )
        
        # Extract the raw label returned by the model
        raw_label = completion.choices[0].message.content.strip()
        
        # Validate if the returned label is in our list
        if raw_label in DEFAULT_LABELS:
            return raw_label
        else:
            for label in DEFAULT_LABELS:
                if label in raw_label:
                    return label
            return "Other"
            
    except Exception as e:
        print(f"[Error]: API call failed: {e}")
        return "Error"


# 4. Main Processing Logic
def process_bug_file():
    print(f"Processing {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"[Error]: Input file {INPUT_FILE} not found.")
        return
        
    print(f"Found a total of {len(lines)} bug reports.")

    # List to store (original data, Future object) in order
    tasks = []

    # Use ThreadPoolExecutor to submit tasks
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 1. Submit all tasks
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                bug_text = data.get("llm_input_text")
                
                if bug_text:
                    future = executor.submit(get_bug_classification, bug_text)
                    # Store the original data and future together to maintain order
                    tasks.append((data, future))
                else:
                    print(f"Line {i+1} missing 'llm_input_text', skipping.")
            except json.JSONDecodeError:
                print(f"Line {i+1} JSON decode error, skipping.")

        print("All tasks submitted, waiting for results and writing in order...")
        # 2. Retrieve results in order and write
        # The key here is to iterate over the `tasks` list we created, rather than using as_completed
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
            processed_count = 0
            
            for original_data, future in tasks:
                predicted_label = future.result()

                new_data = {
                    "project_id": original_data.get("project_id"),
                    "bug_id": original_data.get("bug_id"),
                    "source_type": original_data.get("source_type"),
                    "label": predicted_label,
                    "llm_input_text": original_data.get("llm_input_text")
                }
                
                outfile.write(json.dumps(new_data, ensure_ascii=False) + '\n')
                
                processed_count += 1
                if processed_count % 10 == 0:
                    print(f"Processed {processed_count}/{len(tasks)} records...")
                
                # Avoid rate limiting due to high concurrency
                time.sleep(REQUEST_DELAY)

    print(f"Processing completed!")
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_bug_file()